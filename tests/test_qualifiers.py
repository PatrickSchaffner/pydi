import pytest

from pydi.qualifiers import Qualifiers, qualifiers


args_sample = pytest.mark.parametrize('tags, params', [
    pytest.param(tuple(), dict(), id='empty'),
    pytest.param(('default',), dict(name='named'), id='single'),
    pytest.param(('any', 'preferred'), dict(name='named', label='str'), id='multiple'),
    pytest.param(('qualifier',), dict(qualifier='duplicate'), id='duplicate')
])


@args_sample
def test_Qualifiers_init(tags, params):
    q = Qualifiers(*tags, **params)
    assert q._args == tuple(sorted(tags))
    assert q._kwargs == params
    assert q._sorted_kwargs == tuple(sorted(params.items()))


@args_sample
def test_Qualifiers_equals(tags, params):
    q1 = Qualifiers(*tags, **params)
    assert q1 == q1
    assert hash(q1) == hash(q1)

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
def test_Qualifiers_contains(tags, params):
    q = Qualifiers(*tags, **params)
    assert q.contain(q)

    q1 = Qualifiers('default', *tags, **params)
    assert q1.contain(q)
    assert not q.contain(q1)

    q2 = Qualifiers('alternative', *tags, different='another', **params)
    assert q2.contain(q)
    assert not q.contain(q2)
    assert not q1.contain(q2)
    assert not q2.contain(q1)


@args_sample
def test_qualifiers(tags, params):
    assert qualifiers(*tags, **params) == Qualifiers(*tags, **params)
