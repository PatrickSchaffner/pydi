from typing import Annotated, Callable
from pathlib import Path, WindowsPath

from pydi import inject, singleton, provides, qualifiers


@provides(name='y')
def get_y() -> float:
    return 5


@provides(name='y2', group='output')
@inject()
def twice_y(y: inject(float, name='y')) -> float:
    return 2 * y


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


@provides(name='f', group='output')
@singleton()
@inject()
def calculate_f_using_func(func: inject(Callable[[int, float, float], float])) -> float:
    return func(1, w=1, v=1)


@provides()
def home() -> WindowsPath:
    return Path.home()


@inject()
def main(h: inject(Path),
         x: inject(int, name='x'),
         **floats: inject(float, group='output'),
         ) -> None:
    print(f"x: {x}")
    for variable, value in floats.items():
        print(f"{variable}: {value}")
    print(h)


if __name__ == '__main__':
    main()
