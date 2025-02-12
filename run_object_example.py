from pydi import Container, qualifiers as q, Inject

container = Container(__name__)
provides = container.provides
inject = container.inject


@provides()
def get_x() -> int:
    return -2


class A:

    @inject()
    def __init__(self, base: Inject[float]):
        self._base = base

    @inject()
    def do_a(self, x: Inject[int]) -> float:
        return self._base*x

    @staticmethod
    @provides()
    def get_base() -> float:
        return 5.0


class B:

    @provides()
    def create_A(self) -> A:
        return A()


@provides()
def create_B() -> B:
    return B()


@inject()
def main(a: Inject[A]) -> None:
    print(a.do_a())


if __name__ == '__main__':
    main()
    x = create_B()
    print(x)
