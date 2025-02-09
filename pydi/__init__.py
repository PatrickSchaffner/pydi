__version__ = '0.0.0'

from .core import DependencyInjectionException
from .scopes import singleton
from .container import Container, Inject
from .qualifiers import qualifiers
