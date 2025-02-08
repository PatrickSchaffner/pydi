__version__ = '0.0.0'

from .core import DependencyInjectionException
from .qualifiers import qualifiers
from .scopes import singleton
from .container import Container, Inject
