from .container import Container


class ContainerMeta(type):
    def __new__(mcs, name, bases, attrs):
        container = Container(name)
        attrs['_container'] = container
        attrs['provides'] = container.provides
        attrs['inject'] = container.inject
        return super(ContainerMeta, mcs).__new__(mcs, name, bases, attrs)


class DeclarativeContainer(metaclass=ContainerMeta):

    _container = None

    @classmethod
    def provides(cls, *args, **kwargs):
        pass

    @classmethod
    def inject(cls, *args, **kwargs):
        pass
