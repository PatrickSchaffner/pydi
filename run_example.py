from typing import Annotated, Callable
from pathlib import Path, WindowsPath

from pydi import Container, singleton, Inject, qualifiers as q
from pydi.qualifiers import ANY, ALTERNATIVE


container = Container(__name__)
internal = Container(__name__+'_internal')

internal.share_with(container, float)
internal.expose_to(container, int)

provides = container.provides
inject = container.inject


@internal.provides()
def get_internal_int() -> int:
    return -5


@internal.provides()
@internal.inject()
def get_y(i: Inject[int]) -> float:
    return float(i)


@provides(ALTERNATIVE)
def get_mock_y() -> float:
    return 4


@provides(name='y2')
@inject()
def twice_y(y: inject(float)) -> float:
    return 2 * y


@provides('x')
def get_x() -> int:
    return 10


@provides(function=True)
@inject()
def func(x: Inject[int],
         /,
         z: int,
         w: float = 0,
         *,
         y: Annotated[float, q(name='y2')],
         v: float,
         ) -> float:
    return x * y * z * w * v


@provides(name='f')
@singleton()
@inject()
def calculate_f_using_func(func: Inject[Callable[[int, float, float], float]]) -> float:
    return func(1, v=1)


@provides()
def home() -> WindowsPath:
    return Path.home()


@inject()
def main(h: Inject[Path],
         x: Inject[int],
         x2: inject(int, 'x'),
         *vfloats: inject(float, ANY),
         **floats: inject(float, ANY),
         ) -> None:
    print(f"x: {x}, {x2}")
    for variable, value in floats.items():
        print(f"{variable}: {value}")
    print(h)
    print(vfloats)


if __name__ == '__main__':
    main()
