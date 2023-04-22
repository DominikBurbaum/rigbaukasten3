import importlib
import os
import types


def force_list(var):
    if not isinstance(var, list):
        if isinstance(var, (tuple, set)):
            var = list(var)
        else:
            var = [var]  # avoid converting PyNode('pCube1') tp ['p', 'C', 'u', 'b', 'e', '1']
    return var


def import_module(path_to_module: str) -> types.ModuleType:
    """ Import the given file as python module. Doesn't have to be in PYTHONPATH to work.

        :param path_to_module: str - absolute path to the module, e.g. '/my/python/module.py'
    """
    file_name = os.path.split(path_to_module)[-1]
    loader = importlib.machinery.SourceFileLoader(
        file_name.replace('.py', ''),
        path_to_module
    )
    mod = types.ModuleType(loader.name)
    loader.exec_module(mod)
    return mod
