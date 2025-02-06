from typing import TypeVar, Generic, get_origin

from .qualifiers import Qualifiers


T = TypeVar('T')


class Component(Generic[T]):

    def __init__(self, target: type[T], qualifiers: Qualifiers):
        if target is None:
            raise ValueError('target cannot be none')
        if qualifiers is None:
            if not isinstance(qualifiers, Qualifiers):
                raise ValueError('qualifiers must be of type Qualifiers')
            else:
                qualifiers = Qualifiers()
        self._target = target
        self._qualifiers = qualifiers

    @property
    def target(self):
        return self._target

    @property
    def qualifiers(self):
        return self._qualifiers

    def __hash__(self):
        return (103 + hash(self.target)) ^ hash(self.qualifiers)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Component):
            return False
        return self.target == other.target and self.qualifiers == other.qualifiers

    def __str__(self):
        return f"{self.target.__module__}.{self.target.__qualname__}[{str(self.qualifiers)}]"

    def satisfies(self, request):
        def _get_origin(x): return get_origin(x) if hasattr(x, '__origin__') else x
        return issubclass(_get_origin(self.target), _get_origin(request.target)) \
            and request.qualifiers.is_subset(self.qualifiers)

