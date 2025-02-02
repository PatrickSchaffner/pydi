

class Qualifiers(object):

    def __init__(self, *args: str, **kwargs: str):
        self._args: tuple[str, ...] = tuple(sorted(args))
        self._kwargs: dict[str, str] = kwargs
        self._sorted_kwargs: tuple[tuple[str, str], ...] = tuple((k, v) for (k, v) in sorted(kwargs.items()))
        self._hash: int = (301 + hash(tuple(sorted(self._args)))) ^ hash(self._sorted_kwargs)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Qualifiers):
            return False
        if type(self) != type(other) and issubclass(type(other), type(self)):
            return other == self
        return self._args == other._args and self._sorted_kwargs == other._sorted_kwargs

    def __str__(self):
        return ','.join(self._args + tuple('='.join(kw) for kw in self._sorted_kwargs))

    def __getitem__(self, key):
        if key not in self._kwargs and key in self._args:
            return None
        return self._kwargs[key]

    def contain(self, other: 'Qualifiers'):
        if self is other:
            return True
        if len(self._args) < len(other._args) or len(self._sorted_kwargs) < len(other._sorted_kwargs):
            return False
        idx_args: int = 0
        for arg in other._args:
            while idx_args < len(self._args) and self._args[idx_args] < arg:
                idx_args += 1
            if idx_args >= len(self._args) or arg != self._args[idx_args]:
                return False
            idx_args += 1
        idx_args = 0
        for kwarg in other._sorted_kwargs:
            while idx_args < len(self._sorted_kwargs) and self._sorted_kwargs[idx_args][0] < kwarg[0]:
                idx_args += 1
            if idx_args >= len(self._sorted_kwargs) or kwarg != self._sorted_kwargs[idx_args]:
                return False
            idx_args += 1
        return True

    def __contains__(self, qualifier: str):
        return qualifier in self._args or qualifier in self._kwargs


def qualifiers(*args, **kwargs) -> Qualifiers:
    return Qualifiers(*args, **kwargs)
