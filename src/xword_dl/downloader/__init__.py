import importlib
import pkgutil
from typing import TypeVar, Type

from .basedownloader import BaseDownloader as __bd


# FIXME: after Python 3.11 deprecation, switch to PEP 695 style generics
T = TypeVar("T")


def __get_subclasses(cls: Type[T]) -> list[Type[T]]:
    """Recursively returns a list of subclasses of `cls` in imported namespaces."""
    return [cls] + [
        r_cls for s_cls in cls.__subclasses__() for r_cls in __get_subclasses(s_cls)
    ]


def get_plugins():
    """Returns all plugins available in the downloader package."""
    for _, mod, _ in pkgutil.walk_packages(__path__):
        importlib.import_module(f".{mod}", package=__name__)
    return __get_subclasses(__bd)
