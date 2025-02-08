import pytest

from pydi.qualifiers import Qualifiers, qualifiers, ANY, DEFAULT, ALTERNATIVE


args_sample = pytest.mark.parametrize('tags, params', [
    pytest.param(tuple(), dict(), id='empty'),
    pytest.param((DEFAULT,), dict(), id='default'),
    pytest.param((ALTERNATIVE,), dict(), id='tag'),
    pytest.param(tuple(), dict(name='named'), id='parameter'),
    pytest.param((DEFAULT,), dict(name='named'), id='both'),
    pytest.param((ANY, 'preferred', 'preferred'), dict(name='named', label='str'), id='multiple'),
])


@args_sample
def test_Qualifiers_init(tags, params):
    q = Qualifiers(*tags, **params)
    assert q._tags == tuple(sorted(set(tags)))
    assert q._params == params
    assert q._sorted_params == tuple(sorted(params.items()))


def test_Qualifiers_init_duplicates():
    with pytest.raises(ValueError) as err:
        _ = Qualifiers('duplicate', 'duplicate', duplicate='here')
    assert type(err.value) == ValueError

    assert Qualifiers('duplicate', 'duplicate') == Qualifiers('duplicate')


@args_sample
def test_Qualifiers_equals(tags, params):
    q1 = Qualifiers(*tags, **params)
    assert q1 == q1
    assert hash(q1) == hash(q1)

    qr = Qualifiers(*reversed(tags), **params)
    assert qr == q1

    q2 = Qualifiers(*tags, **params)
    assert q1 == q2
    assert hash(q1) == hash(q2)

    q3 = Qualifiers('other', *tags, **params)
    assert q1 != q3
    assert hash(q1) != hash(q3)

    q4 = Qualifiers(*tags, other='added', **params)
    assert q1 != q4
    assert hash(q1) != hash(q4)

    q5 = Qualifiers(*tags, other='subtracted', **params)
    assert q4 != q5
    assert hash(q4) != hash(q5)


@args_sample
def test_Qualifiers_dict(tags, params):
    q = Qualifiers(*tags, **params)
    for t in tags:
        assert t in q
        if t not in params:
            assert q[t] is None
    for k, v in params.items():
        assert k in q
        assert q[k] == v
    assert 'notcontained' not in q
    with pytest.raises(KeyError) as exc:
        _ = q['notcontained']
    assert type(exc.value) == KeyError


@args_sample
def test_Qualifiers_is_superset(tags, params):
    q = Qualifiers(*tags, **params)
    assert q.is_superset(q)

    q1 = Qualifiers('default2', *tags, **params)
    assert q1.is_superset(q)
    assert not q.is_superset(q1)

    q2 = Qualifiers('alternative', *tags, different='another', **params)
    assert q2.is_superset(q)
    assert not q.is_superset(q2)
    assert not q1.is_superset(q2)
    assert not q2.is_superset(q1)


@args_sample
def test_qualifiers(tags, params):
    assert qualifiers(*tags, **params) == Qualifiers.for_injector(*tags, **params)
