from typing import Callable, Annotated, TypeVar, Any
from inspect import signature

from makefun import wraps

from .qualifiers import Qualifiers
from .component import Component, T
from .injection import InjectionContext, Injector
from .registry import DictRegistry, Unconstrained, Constraint, AmbiguousDependencyException, UnsatisfiedDependencyException


Inject = Annotated[TypeVar('T'), Qualifiers('default')]


class Container(InjectionContext):

    def __init__(self, name: str):
        self._name = name
        self._registry = DictRegistry()
        self._dependencies: dict[Container, list[Component[T], ...]] = dict()
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

    def resolve(self, request: Component[T], *, many: bool = False, named: bool = False,
                constraint: Constraint = Unconstrained,
                _resolve_stack: set['Container'] = set(),
                ) -> T:
        _resolve_stack = _resolve_stack.union({self})
        if many:
            instances = self._registry.resolve(request, many=True, named=named, constraint=constraint)
            for (container, container_constraint) in self._dependencies.items():
                if container in _resolve_stack:
                    continue
                dependencies = container.resolve(request, many=True, named=named,
                                                 constraint=lambda c: constraint(c) and container_constraint(c),
                                                 _resolve_stack=_resolve_stack)
                if named:
                    duplicates = set(instances.keys()).intersection(set(dependencies.keys()))
                    if len(duplicates):
                        raise AmbiguousDependencyException(f"Multiple components with same name resolved: {','.join(duplicates)}")
                    instances.update(dependencies)
                else:
                    instances += dependencies
            return instances
        elif named:
            raise ValueError("Parameter 'named=True' can only be used with 'many=True'.")
        instance = None
        origin = None
        try:
            instance = self._registry.resolve(request, many=False, named=False, constraint=constraint)
            origin = self
        except UnsatisfiedDependencyException:
            pass
        for (container, container_constraints) in self._dependencies.items():
            if container in _resolve_stack:
                continue
            try:
                instance = container.resolve(request, many=False, named=False,
                                             constraint=lambda c: constraint(c) and container_constraints(c),
                                             _resolve_stack=_resolve_stack)
                if origin is not None:
                    raise AmbiguousDependencyException(f"Ambiguous dependency {request} received from containers {origin.name} and {container.name}.")
                origin = container
            except UnsatisfiedDependencyException:
                pass
        if instance is None:
            raise UnsatisfiedDependencyException(f"Cannot resolve dependency {request}")
        return instance

    def expose_to(self, other: 'Container', target: type[T], *tags: str, **params: str) -> None:
        other.require_from(self, target, *tags, **params)

    def require_from(self, other: 'Container', target: type[T], *tags: str, **params: str) -> None:
        request = Component(target, Qualifiers(*tags, **params))
        constraint: Constraint = lambda c: c.satisfies(request)
        if other not in self._dependencies:
            self._dependencies[other] = constraint
        else:
            other_constraints = self._dependencies[other]
            self._dependencies[other] = lambda c: other_constraints(c) or constraint(c)
        #for (component, factory) in other._registry.lookup(request).items():  # TODO: Delay to resolve phase.
        #    self._registry.register(component, factory)

    def share_with(self, other: 'Container', target: type[T], *tags: str, **params: str) -> None:
        self.require_from(other, target, *    tags, **params)
        self.expose_to(other, target, *tags, **params)


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
