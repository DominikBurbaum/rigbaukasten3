import pymel.core as pm


def to_pynode(stuff):
    """ Return a PyNode for the given variable if it can be created.

        Lists, tuples and dicts are recursively converted, so every item of the iterable is converted. If
        this is a nested structure it will be converted all the way to the bottom.
        Tuples are converted to lists.
        Types that cannot be converted (e.g. float, int) will stay as they are.
    """
    if isinstance(stuff, (str, )) and pm.objExists(stuff):
        return pm.PyNode(stuff)
    elif isinstance(stuff, (list, tuple)):
        new = []
        for item in stuff:
            new.append(to_pynode(item))
        return new
    elif isinstance(stuff, dict):
        new = {}
        for key, value in stuff.items():
            new[to_pynode(key)] = to_pynode(value)
        return new
    else:
        return stuff


def to_str(stuff):
    """ Return the string anme for the given variable if it holds a PyNode.

        Lists, tuples and dicts are recursively converted, so every item of the iterable is converted. If
        this is a nested structure it will be converted all the way to the bottom.
        Tuples are converted to lists.
    """
    if isinstance(stuff, pm.PyNode):
        return stuff.name()
    elif isinstance(stuff, (list, tuple)):
        new = []
        for item in stuff:
            new.append(to_str(item))
        return new
    elif isinstance(stuff, dict):
        new = {}
        for key, value in stuff.items():
            new[to_str(key)] = to_str(value)
        return new
    else:
        return stuff
