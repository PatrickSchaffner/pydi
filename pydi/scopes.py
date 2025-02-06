from makefun import wraps


def singleton():
    def _decorator(func):
        instance = None

        @wraps(func)
        def _wrapper(*args, **kwargs):
            nonlocal instance
            if instance is None:
                instance = func(*args, **kwargs)
            return instance

        return _wrapper
    return _decorator

