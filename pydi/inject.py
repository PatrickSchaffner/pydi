from inspect import Parameter, signature
from typing import Callable, Dict, Tuple, Any, get_args, Annotated, TypeVar, Generic

from makefun import wraps

from .qualifiers import Qualifiers
from .component import Component
from .container import Container


Inject = Annotated[TypeVar('T'), Qualifiers('default', 'any')]
container = Container(__name__)
provides = container.provides


def inject(target: type = None, *qualifiers, **kw_qualifiers):
    if target is not None and isinstance(target, str):
        qualifiers = (target, *qualifiers)
        target = None

    if target is not None:
        if len(qualifiers) == 0 and len(kw_qualifiers) == 0:
            qualifiers = ('default', 'any')
        return Annotated[target, Qualifiers(*qualifiers, **kw_qualifiers)]

    if len(qualifiers) > 0:
        raise ValueError('Cannot specify qualifiers for inject decorator.')

    def _decorator(target):
        injector = Injector(target)

        @wraps(target, remove_args=injector.injected_params)
        def _wrapper(*args, **kwargs):
            global container
            args, kwargs = injector.inject_args(container, args, kwargs)
            return target(*args, **kwargs)

        return _wrapper
    return _decorator


class Injector:

    @classmethod
    def _is_injection_point(cls, parameter: Parameter) -> bool:
        return hasattr(parameter.annotation, '__metadata__') and \
               any(isinstance(m, Qualifiers) or m == inject for m in parameter.annotation.__metadata__)

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
            qual = Qualifiers()
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


class InjectionPoint(object):

    def __init__(self, func):
        self._name = func.__qualname__
        self._func = func

    @property
    def func(self):
        return self._func

    @property
    def name(self):
        return self._name


T = TypeVar("T")


class InjectionParameter(Generic[T]):

    def __init__(self, injection_point: InjectionPoint, parameter: Parameter, target: type[T], qualifiers: Qualifiers):
        self._injection_point = injection_point
        self._parameter = parameter
        self._target = target
        self._qualifiers = qualifiers
        self._name = injection_point.name + ':' + parameter.name

    @property
    def injection_point(self):
        return self._injection_point

    @property
    def name(self):
        return self._name

