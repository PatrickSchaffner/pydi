from typing import Callable, Any, Annotated, Tuple, Dict
from inspect import signature, Parameter

from makefun import wraps
from typing_extensions import get_args

from .qualifiers import Qualifiers, NAME
from .component import Component, T


class Container(object):

    def __init__(self, name: str):
        self._name = name
        self._providers: dict[type, Callable[[], Any]] = dict()

    @property
    def name(self) -> str:
        return self._name

    def provides(self, target: type | None = None, *flags: str, function: bool = False, **params: str):
        if target is not None and isinstance(target, str):
            flags = (target, *flags)
            target = None
        qualifiers = Qualifiers.for_provider(*flags, **params)

        def _decorator(func):
            nonlocal target
            provider: Callable[[], Any]
            if function:
                if target is None:
                    sig = signature(func)
                    return_type = sig.return_annotation
                    param_types = [p.annotation for p in sig.parameters.values()]
                    target = Callable[[*param_types], return_type]
                provider = lambda: func
            else:
                if target is None:
                    target = signature(func).return_annotation
                provider = func
            component = Component(target, qualifiers)
            self.register(component, provider)
            return func

        return _decorator

    def inject(self, target: type[T] | None = None, *qualifiers, **kw_qualifiers):
        if target is not None and isinstance(target, str):
            qualifiers = (target, *qualifiers)
            target = None

        if target is not None:
            return Annotated[target, Qualifiers.for_injector(*qualifiers, **kw_qualifiers)]

        if len(qualifiers) > 0:
            raise ValueError('Cannot specify qualifiers for inject decorator.')

        def _decorator(func):
            injector = Injector(func)

            @wraps(func, remove_args=injector.injected_params)
            def _wrapper(*args, **kwargs):
                args, kwargs = injector.inject_args(self, args, kwargs)
                return func(*args, **kwargs)

            return _wrapper

        return _decorator

    def register(self, component: Component[T], provider: Callable[[], T]) -> None:
        if component in self._providers:
            raise ValueError(f"Cannot register multiple providers for '{component}'")
        self._providers[component] = provider

    def resolve(self, request: Component[T], *, many: bool = False, named: bool = False) -> T | tuple[T, ...] | dict[str, T]:
        components = [comp for comp in self._providers.keys() if comp.satisfies(request)]
        if many:
            if named:
                instances = {comp.qualifiers[NAME]: self._providers[comp]()
                             for comp in components if NAME in comp.qualifiers}
            else:
                instances = (self._providers[comp]() for comp in components)
            return instances
        elif named:
            raise ValueError("Parameter 'named=True' can only be used with 'many=True'.")
        elif len(components) == 0:
            raise ValueError(f'Cannot resolve dependency {request}.')
        elif len(components) > 1:
            raise ValueError(f'Dependency resolution for {request} is ambiguous: {" | ".join(str(c) for c in components)}')
        return self._providers[components[0]]()


class Injector:

    @classmethod
    def _is_injection_point(cls, parameter: Parameter) -> bool:
        return hasattr(parameter.annotation, '__metadata__') and \
               any(isinstance(m, Qualifiers) for m in parameter.annotation.__metadata__)

    @classmethod
    def _parse_inject(cls, parameter: Parameter) -> tuple[type, dict[str, str]]:
        args = get_args(parameter.annotation)
        target = args[0]
        qual = None
        for q in args[1:]:
            if isinstance(q, Qualifiers):
                qual = q
                break
        if qual is None:
            raise ValueError(f"Did not find qualifiers on injection point {parameter}.")
        return (Component(target, qual), )

    def __init__(self, injection_point: Callable, /):
        self._parameters = [p for p in signature(injection_point).parameters.values()]
        self._injects = {p: self._parse_inject(p) for p in self._parameters
                         if self._is_injection_point(p)}

    @property
    def injected_params(self):
        return set(p.name for p in self._injects.keys())

    def inject_args(self, context: Container, args: Tuple[Any], kwargs: Dict[str, Any]) -> Tuple[Tuple[Any], Dict[str, Any]]:
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

