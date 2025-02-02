from inspect import Parameter, signature
from typing import Callable, Dict, Tuple, Any, get_args, get_origin, Annotated

from makefun import wraps

from .qualifiers import Qualifiers


class ComponentDescriptor(object):

    def __init__(self, target: type, qualifiers: Qualifiers):
        self._target: type = target
        self._qualifiers: Qualifiers = qualifiers

    @property
    def target(self):
        return self._target

    @property
    def qualifiers(self):
        return self._qualifiers

    def __hash__(self):
        return (103 + hash(self.target)) ^ hash(self.qualifiers)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, ComponentDescriptor):
            return False
        return self.target == other.target and self.qualifiers == other.qualifiers

    def __str__(self):
        return f"{self.target.__module__}.{self.target.__qualname__}[{str(self.qualifiers)}]"

    def satisfies(self, other):
        return self._issubclass(self.target, other.target) and other.qualifiers in self.qualifiers

    @classmethod
    def _issubclass(cls, this, other):
        def _get_origin(x):
            return get_origin(x) if hasattr(x, '__origin__') else x
        return issubclass(_get_origin(this), _get_origin(other))


class Context:

    def __init__(self):
        self._singletons: dict[type, object] = dict()

    def register(self,
                 target: type,
                 factory: object,
                 qualifiers: Qualifiers = Qualifiers(),
                 ):
        descriptor = ComponentDescriptor(target, qualifiers)
        if descriptor in self._singletons:
            raise ValueError(f"Cannot register multiple components for '{descriptor}'")
        self._singletons[descriptor] = factory

    def resolve(self,
                target: type,
                qualifiers: Qualifiers = Qualifiers(),
                *,
                many: bool = False,
                named: bool = False,
                ):

        request = ComponentDescriptor(target, qualifiers)
        components = [comp for comp in self._singletons.keys() if comp.satisfies(request)]
        if many:
            if named:
                instances = {comp.qualifiers['name']: self._singletons[comp]() for comp in components if 'name' in comp.qualifiers}
            else:
                instances = (self._singletons[comp]() for comp in components)
            return instances
        elif named:
            raise ValueError("Parameter 'named=True' can only be used with 'many=True'.")
        elif len(components) == 0:
            raise ValueError(f'Cannot resolve dependency {request}.')
        elif len(components) > 1:
            raise ValueError(f'Dependency resolution for {request} is ambiguous: {" | ".join(str(c) for c in components)}')
        return self._singletons[components[0]]()


ctx = Context()


def provides(target: type | None = None, *, function: bool = False, **qualifiers):
    global ctx

    def _decorator(func):
        nonlocal target
        factory: Callable[[], Any] = None
        if function:
            if target is None:
                sig = signature(func)
                return_type = sig.return_annotation
                param_types = [p.annotation for p in sig.parameters.values()]
                target = Callable[[*param_types], return_type]
            factory = lambda: func
        else:
            if target is None:
                target = signature(func).return_annotation
            factory = func
        ctx.register(target, factory, Qualifiers(**qualifiers))
        return func
    return _decorator


def singleton():
    def _decorator(func):
        instance = None

        @wraps(func)
        def _wrapper(*args, **kwargs):
            nonlocal instance
            if instance is None:
                instance = func(*args, **kwargs)
            return instance

        return _wrapper
    return _decorator


def inject(*types, **qualifiers):
    if len(types) > 1:
        raise ValueError("Cannot inject more than one type per parameter.")
    if len(types) == 1:
        if len(qualifiers) > 0:
            return Annotated[types[0], inject, Qualifiers(**qualifiers)]
        else:
            return Annotated[types[0], inject]

    if len(qualifiers) > 0:
        raise ValueError('Cannot specify qualifiers for inject decorator.')

    def _decorator(target):
        injector = Injector(target)

        @wraps(target, remove_args=injector.injected_params)
        def _wrapper(*args, **kwargs):
            global ctx
            args, kwargs = injector.inject_args(ctx, args, kwargs)
            return target(*args, **kwargs)

        return _wrapper
    return _decorator


QUALIFIERS_PREFIX = 'qualifiers:'


def qualifiers(**q: str):
    return compile_qualifiers(q)


def compile_qualifiers(qualifiers: dict[str, str]):
    qualifiers = [f'{key}={value}' for (key, value) in sorted(qualifiers.items())]
    qualifiers = f"{QUALIFIERS_PREFIX}{','.join(qualifiers)}"
    return qualifiers


def parse_qualifiers(qualifiers: str):
    if not qualifiers.startswith(QUALIFIERS_PREFIX):
        raise ValueError(f"Qualifier string does not start with '{QUALIFIERS_PREFIX}'")
    qualifiers = [tuple(q.split('=')) for q in qualifiers[len(QUALIFIERS_PREFIX):].split(',')]
    qualifiers = dict(qualifiers)
    return qualifiers


class Injector:

    @classmethod
    def _parse_inject(cls, parameter: Parameter) -> tuple[type, dict[str, str]]:
        args = get_args(parameter.annotation)
        t = args[0]
        q = args[2] if len(args) >= 3 else Qualifiers()
        return t, q

    def __init__(self, injection_point: Callable, /):
        self._parameters = [p for p in signature(injection_point).parameters.values()]
        self._injects = {p: self._parse_inject(p) for p in self._parameters
                         if hasattr(p.annotation, '__metadata__') and inject in p.annotation.__metadata__}

    @property
    def injected_params(self):
        return set(p.name for p in self._injects.keys())

    def inject_args(self, context: Context, args: Tuple[Any], kwargs: Dict[str, Any]) -> Tuple[Tuple[Any], Dict[str, Any]]:
        kwargs = kwargs.copy()
        param_idx = 0
        arg_idx = 0
        param: Parameter = None
        merged_args = list()
        merged_kwargs = dict()

        def _init_param(kind) -> bool:
            if param_idx >= len(self._parameters):
                return False
            if not isinstance(kind, set):
                kind = {kind}
            if self._parameters[param_idx].kind not in kind:
                return False
            nonlocal param
            param = self._parameters[param_idx]
            return True

        # Fill positional-only paramenters.
        while _init_param(Parameter.POSITIONAL_ONLY):
            if param in self._injects:
                merged_args.append(context.resolve(*self._injects[param]))
            else:
                if arg_idx >= len(args):
                    raise ValueError("Not enough positional arguments.")
                merged_args.append(args[arg_idx])
                arg_idx += 1
            param_idx += 1

        # Fill positional-or-keyword parameters being used as positionals.
        while _init_param(Parameter.POSITIONAL_OR_KEYWORD):
            if param in self._injects:
                merged_args.append(context.resolve(*self._injects[param]))
            elif arg_idx >= len(args):
                break
            else:
                if param.name in kwargs:
                    raise ValueError("Cannot provide argument twice.")
                merged_args.append(args[arg_idx])
                arg_idx += 1
            param_idx += 1

        # Fill variable-length positional parameters.
        while _init_param(Parameter.VAR_POSITIONAL):
            if param in self._injects:
                merged_args.extend(context.resolve(*self._injects[param], many=True))
            else:
                remaining = args[arg_idx:]
                merged_args.extend(remaining)
                arg_idx += len(remaining)
            param_idx += 1

        # Fill keyword-only parameters.
        while _init_param({Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}):
            if param in self._injects:
                if param.name in kwargs:
                    raise ValueError("Cannot provide argument twice.")
                merged_kwargs[param.name] = context.resolve(*self._injects[param])
            elif param.name in kwargs:
                merged_kwargs[param.name] = kwargs[param.name]
                del kwargs[param.name]
            else:
                pass
            param_idx += 1

        # Fill variable-length keyword parameters.
        while _init_param(Parameter.VAR_KEYWORD):
            if param in self._injects:
                merged_kwargs.update(context.resolve(*self._injects[param], many=True, named=True))
            else:
                for key in list(kwargs.keys()):
                    merged_kwargs[key] = kwargs[key]
                    del kwargs[key]
            param_idx += 1

        assert arg_idx == len(args)
        assert len(kwargs) == 0

        return tuple(merged_args), merged_kwargs
