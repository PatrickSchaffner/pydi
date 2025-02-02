from typing import Annotated, Callable
from pydi.inject import inject, singleton, provides, qualifiers


@provides(name='y')
@singleton()
def get_y() -> float:
    return 5


@provides(name='x')
def get_x() -> int:
    return 10


@provides(function=True)
@inject()
def func(x: Annotated[int, inject, qualifiers(name='x')],
         /,
         z: int,
         w: float = 0,
         *,
         y: inject(float, name='y'),
         v: float,
         ) -> float:
    return x * y * z * w * v


@provides(name='f')
@inject()
def calculate(f: Annotated[Callable[[int, float, float], float], inject]) -> float:
    return f(1, w=1, v=1)


@inject()
def main(f: inject(float, name='f')):
    print(f)


if __name__ == '__main__':
    main()


