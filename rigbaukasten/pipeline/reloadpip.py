import importlib
import sys


def reload_rigbaukasten():
    """ Reload all rigbaukasten modules in the correct order. """
    mods = {k: m for k, m in sys.modules.items() if 'rigbaukasten' in k}
    order = ['utils', 'library', 'functions', 'pipeline', 'core', 'base', 'puppet', 'deform', 'templates']
    for current in order:
        for k, mod in mods.items():
            if current in k:
                print(f'reloading {k}')
                importlib.reload(mod)
