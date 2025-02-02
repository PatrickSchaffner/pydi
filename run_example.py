from typing import Annotated, Callable
from pydi.inject import inject, singleton, provides


@provides()
@singleton()
def get_y() -> float:
    return 5


@provides()
def get_x() -> int:
    return 10


@provides(function=True)
@inject()
def func(x: Annotated[int, inject],
         z: int,
         /,
         w: float = 0,
         *,
         y: Annotated[float, inject],
         v: float,
         ) -> float:
    return x * y * z * w * v


@inject()
def main(f: Annotated[Callable[[int, float, float], float], inject]):
    print(f(1, w=1, v=1))


if __name__ == '__main__':
    main()


