from abc import abstractmethod
from typing import Callable, Any

from .component import Component, T
from .core import DependencyInjectionException
from .qualifiers import NAME
from .injection import InjectionContext


class ResolutionException(DependencyInjectionException):
    pass


class AmbiguousDependencyException(ResolutionException):
    pass


class UnsatisfiedDependencyException(ResolutionException):
    pass


Factory = Callable[[], T]


Constraint = Callable[[Component[Any]], bool]


def Unconstrained(_: Component[Any]) -> bool:
    return True


class Registry(InjectionContext):

    @abstractmethod
    def register(self, component: Component[T], factory: Factory[T]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def lookup(self, request: Component[T], *, constraint: Constraint = Unconstrained) -> dict[Component[T], Factory[T]]:
        raise NotImplementedError()

    def resolve(self, request: Component[T], *,
                many: bool = False,
                named: bool = False,
                constraint: Constraint = Unconstrained,
                ) -> T | tuple[T, ...] | dict[str, T]:
        factories = self.lookup(request, constraint=constraint)
        if many:
            if named:
                instances = {comp.qualifiers[NAME]: factory()
                             for (comp, factory) in factories.items() if NAME in comp.qualifiers}
            else:
                instances = tuple(factory() for factory in factories.values())
            return instances
        elif named:
            raise ValueError("Parameter 'named=True' can only be used with 'many=True'.")
        elif len(factories) == 0:
            raise UnsatisfiedDependencyException(f'Cannot resolve dependency {request}.')
        elif len(factories) > 1:
            raise AmbiguousDependencyException(
                f'Dependency resolution for {request} is ambiguous: {" | ".join(str(c) for c in factories.keys())}')
        return next(iter(factories.values()))()


class DictRegistry(Registry):

    def __init__(self):
        self._factories: dict[Component[T], Factory[T]] = dict()
        super(DictRegistry, self).__init__()

    def register(self, component: Component[T], factory: Factory[T]) -> None:
        if component in self._factories:
            raise ResolutionException(f"Cannot register multiple providers for '{component}'.")
        self._factories[component] = factory

    def lookup(self, request: Component[T], *, constraint: Constraint = Unconstrained) -> dict[Component[T], Factory[T]]:
        return {comp: factory for (comp, factory) in self._factories.items() if comp.satisfies(request) and constraint(comp)}


