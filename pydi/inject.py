import inspect

from makefun import wraps





class Context:

    def __init__(self):
        self._singletons : dict[type,object] = dict()

    def register(self,
                 target : type,
                 component : object,
                 ):
        if target in self._singletons:
            raise ValueError(f"Cannot register multiple components for '{target}'")
        self._singletons[target] = component

    def resolve(self,
                target : type,
                ):
        if target in self._singletons:
            return self._singletons[target]
        raise ValueError(f"Cannot resolve dependency '{target}'.")



def inject(context : Context):
    def _decorator(target):
        sig = inspect.signature(target)
        for (idx, (varname, parameter)) in enumerate(sig.parameters.items()):
            ann = parameter.annotation
            print(idx, parameter.kind, parameter.name, parameter.annotation)
            if not hasattr(ann, '__metadata__') or inject not in ann.__metadata__:
                continue
            print(ann.__metadata__[0])
        @wraps(target, remove_args='x')
        def _wrapper(*args, **kwargs):
            return target(context.resolve(int), *args, **kwargs)
        return _wrapper
    return _decorator
