import os
import importlib


def import_modules_from(package, module_name) -> list:
    """
    Recursively import all modules in the given package and its subpackages.
    """
    loaded_modules = []
    pkg = importlib.import_module(str(package))
    pkg_path = pkg.__path__[0]
    for root, _, files in os.walk(pkg_path):
        if f"{module_name}.py" in files:
            rel_path = os.path.relpath(root, pkg_path)
            if rel_path == ".":
                module_path = f"{package}.{module_name}"
            else:
                subpackage = rel_path.replace(os.sep, ".")
                module_path = f"{package}.{subpackage}.{module_name}"
            laded_module = importlib.import_module(module_path)
            loaded_modules.append(laded_module)
    return loaded_modules
