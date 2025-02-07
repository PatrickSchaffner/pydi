DEFAULT: str = 'default'
ANY: str = 'any'
ALTERNATIVE: str = 'alternative'
NAME: str = 'name'


class Qualifiers(object):

    @classmethod
    def for_provider(cls, *tags: str, **params: str) -> 'Qualifiers':
        if len(tags) == 0 and len(params) == 0:
            tags = (DEFAULT, ANY)
        if ANY not in tags:
            tags += (ANY,)
        return cls(*tags, **params)

    @classmethod
    def for_injector(cls, *tags: str, **params: str) -> 'Qualifiers':
        if len(tags) == 0 and len(params) == 0:
            tags = (DEFAULT,)
        return cls(*tags, **params)

    def __init__(self, *tags: str, **params: str):
        tags = set(tags)
        for p in tags:
            if p in params.keys():
                raise ValueError(f"Duplicate qualifier '{p}' found in tags and parameters.")
        self._tags: tuple[str, ...] = tuple(sorted(set(tags)))
        self._params: dict[str, str] = params
        self._sorted_params: tuple[tuple[str, str], ...] = tuple((k, v) for (k, v) in sorted(params.items()))
        self._hash: int = (301 + hash(tuple(sorted(self._tags)))) ^ hash(self._sorted_params)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Qualifiers):
            return False
        if type(self) != type(other) and issubclass(type(other), type(self)):
            return other == self
        return self._tags == other._tags and self._sorted_params == other._sorted_params

    def __str__(self):
        return ','.join(self._tags + tuple('='.join(kw) for kw in self._sorted_params))

    def __getitem__(self, key):
        if key not in self._params and key in self._tags:
            return None
        return self._params[key]

    def is_subset(self, other: 'Qualifiers'):
        return other.is_superset(self)

    def is_superset(self, other: 'Qualifiers'):
        if self is other:
            return True
        if len(self._tags) < len(other._tags) or len(self._sorted_params) < len(other._sorted_params):
            return False
        idx_tag: int = 0
        for tag in other._tags:
            while idx_tag < len(self._tags) and self._tags[idx_tag] < tag:
                idx_tag += 1
            if idx_tag >= len(self._tags) or tag != self._tags[idx_tag]:
                return False
            idx_tag += 1
        idx_param = 0
        for param in other._sorted_params:
            while idx_param < len(self._sorted_params) and self._sorted_params[idx_param][0] < param[0]:
                idx_param += 1
            if idx_param >= len(self._sorted_params) or param != self._sorted_params[idx_param]:
                return False
            idx_param += 1
        return True

    def __contains__(self, qualifier: str):
        return qualifier in self._tags or qualifier in self._params


def qualifiers(*tags, **params) -> Qualifiers:
    return Qualifiers.for_injector(*tags, **params)
