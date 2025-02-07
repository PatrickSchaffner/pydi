from typing import Callable, Any, Annotated, TypeVar
from inspect import signature

from makefun import wraps

from .qualifiers import Qualifiers, NAME
from .component import Component, T
from .injection import InjectionContext, Injector


Inject = Annotated[TypeVar('T'), Qualifiers('default')]


class Container(InjectionContext):

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
            injector = Injector(func, self)

            @wraps(func, remove_args=injector.injected_params)
            def _wrapper(*args, **kwargs):
                args, kwargs = injector.inject_args(args, kwargs)
                return func(*args, **kwargs)

            return _wrapper

        return _decorator

    def register(self, component: Component[T], provider: Callable[[], T]) -> None:
        if component in self._providers:
            raise ValueError(f"Cannot register multiple providers for '{component}'.")
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
