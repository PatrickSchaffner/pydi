from typing import Annotated, Callable
from pathlib import Path, WindowsPath

from pydi import inject, singleton, provides, qualifiers as q, Inject


@provides(name='y')
def get_y() -> float:
    return 5


@provides(name='y2', group='output')
@inject()
def twice_y(y: inject(float, name='y')) -> float:
    return 2 * y


@provides()
def get_x() -> int:
    return 10


@provides(function=True)
@inject()
def func(x: Inject[int],
         /,
         z: int,
         w: float = 0,
         *,
         y: Annotated[float, q(name='y')],
         v: float,
         ) -> float:
    return x * y * z * w * v


@provides(name='f', group='output')
@singleton()
@inject()
def calculate_f_using_func(func: Inject[Callable[[int, float, float], float]]) -> float:
    return func(1, w=1, v=1)


@provides()
def home() -> WindowsPath:
    return Path.home()


@inject()
def main(h: Inject[Path],
         x: Inject[int],
         **floats: inject(float, 'any'),
         ) -> None:
    print(f"x: {x}")
    for variable, value in floats.items():
        print(f"{variable}: {value}")
    print(h)


if __name__ == '__main__':
    main()

