from .inject import inject
from typing import Annotated

class DependencyGenerator():

    def __getitem__[T](self, item: type[T]) -> type[T]:
        return Annotated[item, inject]

    def __call__(self, *args, **kwargs):
        self.depends_on(*args, **kwargs)

    def depends_on(self, target, name = str | None):
        return None


Provide = DependencyGenerator()
Inject = DependencyGenerator()
