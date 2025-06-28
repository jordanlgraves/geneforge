# Placeholder __init__ file for the `src.tools` package

# Re-export public tool classes so that importing from this package works transparently

from importlib import import_module

# Lazily import sub-modules to avoid circular dependencies when the registry in
# `src.functions` pulls in the classes.  Only the packages actually referenced
# via ``from src.tools import …`` will be imported.
__all__ = []

_modules = [
    "src.tools.cello_tools",
    "src.tools.promoter_tools",
    "src.tools.rbs_tools",
    "src.tools.synbiohub_tools",
    "src.tools.utility_tools",
    "src.tools.kinetic_model_tools",
]

for _mod_name in _modules:
    _mod = import_module(_mod_name)
    for _name in getattr(_mod, "__all__", []):
        globals()[_name] = getattr(_mod, _name)
        __all__.append(_name) 