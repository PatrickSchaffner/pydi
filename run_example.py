from typing import Annotated, Callable
from pathlib import Path, WindowsPath

from pydi import Container, singleton, Inject
from pydi.qualifiers import qualifiers as q, ANY, ALTERNATIVE

from pydi.container import DeclarativeContainer


class ExampleContainer(DeclarativeContainer):
    pass


container = Container(__name__)
internal = Container(__name__+'_internal')

provides = container.provides
inject = container.inject

"""
a = Container('a')

b = Container('b')
a.veto(Callable[[int, float, float], float], q('default'))
b.requires_from(a, int)
b.requires_from(a, Path, name='home')
b.requires_from(a, [(Path, q(name='home')), int])
b.exposes_to(a, Callable[[int, float, float], float], override=True)
b.shares_with(a, float)
"""


@provides()
def get_y() -> float:
    return 5


@provides(ALTERNATIVE)
def get_mock_y() -> float:
    return 4


@provides(name='y2')
@inject()
def twice_y(y: inject(float)) -> float:
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
         *vfloats: inject(float, ANY),
         **floats: inject(float, ANY),
         ) -> None:
    print(f"x: {x}")
    for variable, value in floats.items():
        print(f"{variable}: {value}")
    print(h)
    print(vfloats)


if __name__ == '__main__':
    main()

