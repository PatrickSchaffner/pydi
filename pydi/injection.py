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


class Injector:

    @classmethod
    def _parse_parameters(cls, function) -> tuple[Parameter]:
        return tuple(p for p in signature(function).parameters.values())

    @classmethod
    def _parse_component(cls, parameter: Parameter) -> Component:
        args = get_args(parameter.annotation)
        target = args[0]
        qualifiers = next((arg for arg in args[1:] if isinstance(arg, Qualifiers)), None)
        if qualifiers is None:
            raise ValueError(f"Did not find qualifiers on injected parameter {parameter}.")
        return Component(target, qualifiers)

    @classmethod
    def _parse_components(cls, parameters: Sequence[Parameter]) -> dict[Parameter, Component]:
        return {p: cls._parse_component(p) for p in parameters
                if hasattr(p.annotation, '__metadata__') and
                any(isinstance(m, Qualifiers) for m in p.annotation.__metadata__)}

    def __init__(self, function: Callable, context: InjectionContext, /):
        self._parameters: tuple[Parameter] = self._parse_parameters(function)
        self._components: dict[Parameter, Component] = self._parse_components(self._parameters)
        self._context: InjectionContext = context

    @property
    def injected_params(self):
        return set(p.name for p in self._components.keys())

    def inject_args(self, args: Tuple[Any], kwargs: Dict[str, Any]) -> Tuple[Tuple[Any], Dict[str, Any]]:
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
            if param in self._components:
                merged_args.append(self._context.resolve(self._components[param]))
            else:
                if arg_idx >= len(args):
                    raise ValueError("Not enough positional arguments.")
                merged_args.append(args[arg_idx])
                arg_idx += 1
            param_idx += 1

        # Fill positional-or-keyword parameters being used as positionals.
        while _init_param(Parameter.POSITIONAL_OR_KEYWORD):
            if param in self._components:
                merged_args.append(self._context.resolve(self._components[param]))
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
            if param in self._components:
                merged_args.extend(self._context.resolve(self._components[param], many=True))
            else:
                remaining = args[arg_idx:]
                merged_args.extend(remaining)
                arg_idx += len(remaining)
            param_idx += 1

        # Fill keyword-only parameters.
        while _init_param({Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}):
            if param in self._components:
                if param.name in kwargs:
                    raise ValueError("Cannot provide argument twice.")
                merged_kwargs[param.name] = self._context.resolve(self._components[param])
            elif param.name in kwargs:
                merged_kwargs[param.name] = kwargs[param.name]
                del kwargs[param.name]
            else:
                pass
            param_idx += 1

        # Fill variable-length keyword parameters.
        while _init_param(Parameter.VAR_KEYWORD):
            if param in self._components:
                merged_kwargs.update(self._context.resolve(self._components[param], many=True, named=True))
            else:
                for key in list(kwargs.keys()):
                    merged_kwargs[key] = kwargs[key]
                    del kwargs[key]
            param_idx += 1

        assert arg_idx == len(args)
        assert len(kwargs) == 0

        return tuple(merged_args), merged_kwargs

