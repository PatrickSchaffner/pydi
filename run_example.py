from typing import Annotated, Callable

from pydi.inject import inject, Context
from pydi.api import Provide, Inject

import inspect


ctx = Context()
ctx.register(int, 10)

def injected[T](x:type[T]) -> type[T]:
    return Annotated[x, inject]


@inject(ctx)
def func(x: injected(int), /, y: injected(float), *args : None, **kwargs) -> float:
    return 2 * x * y


print(func(5, 0, 0, 0))
print(func.__annotations__)
print(inspect.signature(func))
