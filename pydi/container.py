from typing import Callable, Annotated, TypeVar
from inspect import signature

from makefun import wraps

from .qualifiers import Qualifiers
from .component import Component, T
from .injection import InjectionContext, Injector
from .registry import DictRegistry


Inject = Annotated[TypeVar('T'), Qualifiers('default')]


class Container(InjectionContext):

    def __init__(self, name: str):
        self._name = name
        self._registry = DictRegistry()
        super(Container, self).__init__()

    @property
    def name(self) -> str:
        return self._name

    def provides(self, target: type[T] | None = None, *flags: str, function: bool = False, **params: str):
        if target is not None and isinstance(target, str):
            flags = (target, *flags)
            target = None
        qualifiers = Qualifiers.for_provider(*flags, **params)

        def _decorator(func: Callable[[], T]):
            nonlocal target
            provider: Callable[[], T]
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
            component = Component[T](target, qualifiers)
            self._registry.register(component, provider)
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

            @wraps(func, remove_args=injector.parameters)
            def _wrapper(*args, **kwargs):
                args, kwargs = injector(self, args, kwargs)
                return func(*args, **kwargs)

            return _wrapper

        return _decorator

    def resolve(self, request: Component[T], **kwargs) -> T:
        return self._registry.resolve(request, **kwargs)


class ContainerMeta(type):
    def __new__(mcs, name, bases, attrs):
        container = Container(name)
        attrs['_container'] = container
        attrs['provides'] = container.provides
        attrs['inject'] = container.inject
        return super(ContainerMeta, mcs).__new__(mcs, name, bases, attrs)


class DeclarativeContainer(metaclass=ContainerMeta):

    _container = None

    @classmethod
    def provides(cls, *args, **kwargs):
        pass

    @classmethod
    def inject(cls, *args, **kwargs):
        pass
