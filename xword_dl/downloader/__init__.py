import importlib
import pkgutil

from .basedownloader import BaseDownloader as __bd

def __get_subclasses(cls, lst=[]):
    """Recursively returns a list of subclasses of `cls` in imported namespaces."""
    for s_cls in cls.__subclasses__():
        lst.append(s_cls)
        __get_subclasses(s_cls, lst)
    return lst

def get_plugins():
    """Returns all plugins available in the downloader package."""
    for _, mod, _ in pkgutil.walk_packages(__path__):
        importlib.import_module(f".{mod}", package=__name__)
    return __get_subclasses(__bd)
