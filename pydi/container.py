from typing import Callable, Any, Union
from inspect import signature

from .qualifiers import Qualifiers
from .component import Component, T


class Container(object):

    def __init__(self, name: str):
        self._name = name
        self._providers: dict[type, Callable[[], Any]] = dict()

    @property
    def name(self) -> str:
        return self._name

    def provides(self, target: type | None = None, *flags: str, function: bool = False, **params: str):
        qualifiers = Qualifiers(*flags, **params)

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

    def register(self, component: Component[T], provider: Callable[[], T]) -> None:
        if component in self._providers:
            raise ValueError(f"Cannot register multiple providers for '{component}'")
        self._providers[component] = provider

    def resolve(self, request: Component[T], *, many: bool = False, named: bool = False) -> Union[T, tuple[T, ...]]:
        components = [comp for comp in self._providers.keys() if comp.satisfies(request)]
        if many:
            if named:
                instances = {comp.qualifiers['name']: self._providers[comp]() for comp in components if 'name' in comp.qualifiers}
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
