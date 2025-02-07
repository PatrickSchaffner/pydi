from inspect import Parameter
from typing import TypeVar, Generic

from .qualifiers import Qualifiers


class InjectionPoint(object):

    def __init__(self, func):
        self._name = func.__qualname__
        self._func = func

    @property
    def func(self):
        return self._func

    @property
    def name(self):
        return self._name


T = TypeVar("T")


class InjectionParameter(Generic[T]):

    def __init__(self, injection_point: InjectionPoint, parameter: Parameter, target: type[T], qualifiers: Qualifiers):
        self._injection_point = injection_point
        self._parameter = parameter
        self._target = target
        self._qualifiers = qualifiers
        self._name = injection_point.name + ':' + parameter.name

    @property
    def injection_point(self):
        return self._injection_point

    @property
    def name(self):
        return self._name

