from typing import Annotated
from pydi.inject import inject, Context, singleton, provides


ctx = Context()


@provides(ctx)
@singleton()
def get_y() -> float:
    return 5


@provides(ctx)
def get_x() -> int:
    return 10


@inject(ctx)
def func(x: Annotated[int, inject],
         z: int,
         /,
         w: float = 0,
         *,
         y: Annotated[float, inject],
         v: float,
         ) -> float:
    return x * y * z * w * v


print(func(1, w=1, v=1))

