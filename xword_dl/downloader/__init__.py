import glob
import importlib
import inspect
import os
import sys

# This code runs through the modules in its directory and imports the ones
# that end in .py (but that aren't __init__.py). It then adds any classes
# from those modules to its own namespace.

modules = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
modules = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f) and not f.endswith('__init__.py')]

for mod in modules:
    mdl = importlib.import_module('.' + mod, package=__name__)
    if '__all__' in mdl.__dict__:
        names = mdl.__dict__['__all__']
    else:
        names = [x for x in mdl.__dict__ if not x.startswith('_')
                 and inspect.isclass(mdl.__dict__[x])]
    
    globals().update({k: getattr(mdl, k) for k in names})
    globals().pop(mod)
