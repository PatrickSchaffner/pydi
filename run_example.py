from typing import Annotated
from pydi.inject import inject, Context

import inspect


ctx = Context()
ctx.register(int, 10)
ctx.register(float, 5)


@inject(ctx)
def func(x: Annotated[int, inject], z: int, /, w: float = 0, *, y: Annotated[float, inject], v: float) -> float:
    return x * y * z * w * v


print(func(1, w=1, v=1))
print(func.__annotations__)
print(inspect.signature(func))
