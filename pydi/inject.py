from inspect import Parameter, signature
from typing import Callable, Dict, Tuple, Any, get_args

from makefun import wraps


class Context:

    def __init__(self):
        self._singletons : dict[type,object] = dict()

    def register(self,
                 target : type,
                 component : object,
                 ):
        if target in self._singletons:
            raise ValueError(f"Cannot register multiple components for '{target}'")
        self._singletons[target] = component

    def resolve(self,
                target : type,
                all : bool = False,
                named : bool = False,
                ):
        if all or named:
            raise NotImplementedError("Not implemented yet.")
        if target in self._singletons:
            return self._singletons[target]
        raise ValueError(f"Cannot resolve dependency '{target}'.")


def inject(context: Context):
    def _decorator(target):
        injector = Injector(target)

        @wraps(target, remove_args=injector.injected_params)
        def _wrapper(*args, **kwargs):
            args, kwargs = injector.inject_args(context, args, kwargs)
            return target(*args, **kwargs)

        return _wrapper
    return _decorator


class Injector:

    def __init__(self, injection_point: Callable, /):
        self._parameters = [p for p in signature(injection_point).parameters.values()]
        self._injects = {p: get_args(p.annotation)[0] for p in self._parameters
                         if hasattr(p.annotation, '__metadata__') and inject in p.annotation.__metadata__}

    @property
    def injected_params(self):
        return set(p.name for p in self._injects.keys())

    def inject_args(self, context: Context, args: Tuple[Any], kwargs: Dict[str, Any]) -> Tuple[Tuple[Any], Dict[str, Any]]:
        kwargs = kwargs.copy()
        param_idx = 0
        arg_idx = 0
        merged_args = list()
        merged_kwargs = dict()

        def _param_kind_is(kind) -> bool:
            if param_idx >= len(self._parameters):
                return False
            if not isinstance(kind, set):
                kind = {kind}
            return self._parameters[param_idx].kind in kind

        # Fill positional-only paramenters.
        while _param_kind_is(Parameter.POSITIONAL_ONLY):
            param = self._parameters[param_idx]
            if param in self._injects:
                merged_args.append(context.resolve(self._injects[param]))
            else:
                if arg_idx >= len(args):
                    raise ValueError("Not enough positional arguments.")
                merged_args.append(args[arg_idx])
                arg_idx += 1
            param_idx += 1

        # Fill positional-or-keyword parameters being used as positionals.
        while _param_kind_is(Parameter.POSITIONAL_OR_KEYWORD):
            param = self._parameters[param_idx]
            if param in self._injects:
                merged_args.append(context.resolve(self._injects[param]))
            elif arg_idx >= len(args):
                break
            else:
                if param.name in kwargs:
                    raise ValueError("Cannot provide argument twice.")
                merged_args.append(args[arg_idx])
                arg_idx += 1
            param_idx += 1

        # Fill variable-length positional parameters.
        while _param_kind_is(Parameter.VAR_POSITIONAL):
            if param in self._injects:
                merged_args.extend(context.resolve(self._injects[param], all=True))
            else:
                merged_args.extend(args[arg_idx:])
                arg_idx = len(args)
            param_idx += 1

        # Fill keyword-only parameters.
        while _param_kind_is({Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY}):
            param = self._parameters[param_idx]
            if param in self._injects:
                if param.name in kwargs:
                    raise ValueError("Cannot provide argument twice.")
                merged_kwargs[param.name] = context.resolve(self._injects[param])
            elif param.name in kwargs:
                merged_kwargs[param.name] = kwargs[param.name]
                del kwargs[param.name]
            else:
                pass
            param_idx += 1

        # Fill variable-length keyword parameters.
        while _param_kind_is(Parameter.VAR_KEYWORD):
            if param in self._injects:
                merged_kwargs.update(context.resolve(self._injects[param], all=True, named=True))
            else:
                merged_kwargs.update(kwargs)
                kwargs.clear()
            param_idx += 1

        return tuple(merged_args), merged_kwargs
