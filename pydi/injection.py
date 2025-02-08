from abc import ABC, abstractmethod
from inspect import signature, Parameter
from typing import get_args, Callable, Tuple, Any, Dict, Sequence

from .component import Component, T
from .qualifiers import Qualifiers


class InjectionContext(ABC):

    @abstractmethod
    def resolve(self, request: Component[T], *,
                many: bool = False,
                named: bool = False,
                ) -> T | tuple[T, ...] | dict[str, T]:
        raise NotImplementedError()


def get_component(parameter: Parameter) -> Component:
    if not hasattr(parameter.annotation, '__metadata__'):
        return None
    args = get_args(parameter.annotation)
    target = args[0]
    qualifiers = next((arg for arg in args[1:] if isinstance(arg, Qualifiers)), None)
    if qualifiers is None:
        return None
    return Component(target, qualifiers)


def get_components(parameters: Sequence[Parameter]) -> dict[Parameter, Component]:
    return dict((p, c) for (p, c) in ((p, get_component(p)) for p in parameters) if c is not None)


class Injector:

    def __init__(self, function: Callable):
        self._parameters = tuple(signature(function).parameters.values())
        self._components = get_components(self._parameters)

    @property
    def parameters(self):
        return set(p.name for p in self._components.keys())

    def inject(self,
               context: InjectionContext,
               args: Tuple[Any, ...],
               kwargs: Dict[str, Any],
               ) -> Tuple[Tuple[Any], Dict[str, Any]]:
        kwargs = kwargs.copy()
        param_idx = 0
        arg_idx = 0
        param: Parameter = None
        merged_args = list()
        merged_kwargs = dict()

        def _init_next_param(kind) -> bool:
            if param_idx >= len(self._parameters):
                return False
            if not isinstance(kind, set):
                kind = {kind}
            if self._parameters[param_idx].kind not in kind:
                return False
            nonlocal param
            param = self._parameters[param_idx]
            return True

        def _resolve_param(**resolve_kwargs):
            return context.resolve(self._components[param], **resolve_kwargs)

        # Fill positional-only parameters.
        while _init_next_param(Parameter.POSITIONAL_ONLY):
            if param in self._components:
                value = _resolve_param()
            elif arg_idx >= len(args):
                raise ValueError("Not enough positional arguments.")
            else:
                value = args[arg_idx]
                arg_idx += 1
            merged_args.append(value)
            param_idx += 1

        # Fill positional-or-keyword parameters being used as positionals.
        while _init_next_param(Parameter.POSITIONAL_OR_KEYWORD):
            if param in self._components:
                value = _resolve_param()
            elif arg_idx >= len(args):
                break
            elif param.name in kwargs:
                raise ValueError("Cannot provide argument twice.")
            else:
                value = args[arg_idx]
                arg_idx += 1
            merged_args.append(value)
            param_idx += 1

        # Fill variable-length positional parameters.
        while _init_next_param(Parameter.VAR_POSITIONAL):
            if param in self._components:
                values = _resolve_param(many=True)
            else:
                values = args[arg_idx:]
                arg_idx += len(values)
            merged_args.extend(values)
            param_idx += 1

        assert arg_idx == len(args)

        # Fill positional-or-keyword parameters being used as keywords, and keyword-only parameters.
        while _init_next_param({Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}):
            resolve = param in self._components
            in_kwargs = param.name in kwargs
            if resolve and in_kwargs:
                raise ValueError("Cannot provide argument twice.")
            elif resolve:
                value = _resolve_param()
            elif in_kwargs:
                value = kwargs[param.name]
                del kwargs[param.name]
            if resolve or in_kwargs:
                merged_kwargs[param.name] = value
            param_idx += 1

        # Fill variable-length keyword parameters.
        while _init_next_param(Parameter.VAR_KEYWORD):
            resolve = param in self._components
            values = _resolve_param(many=True, named=True) if resolve else kwargs
            merged_kwargs.update(values)
            if not resolve:
                kwargs.clear()
            param_idx += 1

        assert len(kwargs) == 0
        assert param_idx == len(self._parameters)

        return tuple(merged_args), merged_kwargs
