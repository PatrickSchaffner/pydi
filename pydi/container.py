from typing import Callable, Annotated, TypeVar, Any
import inspect

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

    @property
    def registry(self) -> str:
        return self._registry

    def provides(self, target: type[T] | None = None, *flags: str, function: bool = False, **params: str):
        if target is not None and isinstance(target, str):
            flags = (target, *flags)
            target = None
        qualifiers = Qualifiers.for_provider(*flags, **params)

        def _register_provider(t: type[T], q: Qualifiers, p: Callable[[], T]) -> None:
            c = Component[T](t, q)
            self.registry.register(c, p)

        if function:
            def _func_decorator(func: Callable[[Any,...], T]) -> Callable[[Any,...], T]:
                nonlocal target
                if target is None:
                    sig = inspect.signature(func)
                    return_type = sig.return_annotation
                    param_types = [p.annotation for p in sig.parameters.values()]
                    target = Callable[[*param_types], return_type]
                _register_provider(target, qualifiers, lambda: func)
                return func
            return _func_decorator

        def _provider_decorator(provider: Callable[[], T]):
            nonlocal target
            if target is None:
                target = provider.__annotations__['return']
            _register_provider(target, qualifiers, provider)
            return provider

        def _register_method(owner: type, provider: Callable[[], T]) -> None:
            nonlocal target
            if target is None:
                target = provider.__annotations__['return']
            inj = self.inject

            @inj()
            def _method_provider(instance: inj(owner)) -> target:
                return provider(instance)
            _register_provider(target, qualifiers, _method_provider)

        class _ProviderDescriptor:

            def __init__(self, provider: Callable[[], T]):
                wraps(provider)(self)
                self._provider = provider

                n_params: int = len(inspect.signature(provider).parameters)
                if n_params == 0:  # Function or staticmethod
                    _provider_decorator(provider)
                elif n_params > 1:  # Not a provider function
                    raise ValueError(f'Provider {provider} has unfilled parameters.')

            def __set_name__(self, owner, name):
                setattr(owner, name, self._provider)
                _register_method(owner, self._provider)

            def __call__(self, *args, **kwargs):
                return self._provider(*args, **kwargs)

        return _ProviderDescriptor

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

    def resolve(self, request: Component[T], *, many: bool = False, named: bool = False, constraint: Constraint = Unconstrained) -> T:
        if many:
            instances = self.registry.resolve(request, many=True, named=named, constraint=constraint)
            for (container, container_constraint) in self._dependencies.items():
                dependencies = container.registry.resolve(request, many=True, named=named,
                                                          constraint=lambda c: constraint(c) and container_constraint(c))
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
        usdexc = None
        try:
            instance = self.registry.resolve(request, many=False, named=False, constraint=constraint)
            origin = self
        except UnsatisfiedDependencyException as e:
            usdexc = e
        for (container, container_constraints) in self._dependencies.items():
            try:
                instance = container.registry.resolve(request, many=False, named=False,
                                                      constraint=lambda c: constraint(c) and container_constraints(c))
                if origin is not None:
                    raise AmbiguousDependencyException(f"Ambiguous dependency {request} received from containers {origin.name} and {container.name}.")
                origin = container
            except UnsatisfiedDependencyException as e:
                usdexc = e
        if instance is None:
            raise UnsatisfiedDependencyException(f"Cannot resolve dependency {request}") from usdexc
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

    def share_with(self, other: 'Container', target: type[T], *tags: str, **params: str) -> None:
        self.require_from(other, target, *    tags, **params)
        self.expose_to(other, target, *tags, **params)
