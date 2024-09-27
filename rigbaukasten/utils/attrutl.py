import pymel.core as pm


def add(obj, attr_name='attr', typ='float', mn=None, mx=None, default=0, k=True, cb=True, multi=False):
    # add attribute
    if typ.endswith('3'):
        pm.addAttr(obj, attributeType=typ, longName=attr_name, multi=multi)
        for ax in 'XYZ':
            pm.addAttr(obj, attributeType=typ[:-1], longName=attr_name + ax, p=attr_name, dv=default)
    else:
        pm.addAttr(obj, attributeType=typ, longName=attr_name, dv=default, multi=multi)
    plug = pm.PyNode(f'{obj}.{attr_name}')
    if mn is not None:
        pm.addAttr(plug, e=True, min=mn)
    if mx is not None:
        pm.addAttr(plug, e=True, max=mx)
    pm.setAttr(plug, keyable=k)
    if not k:
        pm.setAttr(plug, channelBox=cb)

    return plug


def add_compound(obj, attr_name, typ, child_names, k=True, cb=True, **kwargs):
    pm.addAttr(obj, attributeType='compound', longName=attr_name, nc=len(child_names))
    for cn in child_names:
        pm.addAttr(obj, attributeType=typ, longName=cn, p=attr_name, **kwargs)
    child_plugs = [pm.PyNode(f'{obj}.{cn}') for cn in child_names]
    compound_plug = pm.PyNode(f'{obj}.{attr_name}')
    for cp in child_plugs:
        pm.setAttr(cp, keyable=k)
        if not k:
            pm.setAttr(cp, channelBox=cb)
    return compound_plug, child_plugs


def add_string(obj, attr_name, default='', multi=False):
    plug_name = f'{obj}.{attr_name}'
    if pm.objExists(plug_name):
        return pm.PyNode(plug_name)
    pm.addAttr(obj, dt='string', longName=attr_name, multi=multi)
    plug = pm.PyNode(plug_name)
    plug.set(default)
    return plug


def add_message(obj, attr_name, multi=False):
    plug_name = f'{obj}.{attr_name}'
    if pm.objExists(plug_name):
        return pm.PyNode(plug_name)
    pm.addAttr(obj, at='message', longName=attr_name, multi=multi)
    plug = pm.PyNode(plug_name)
    return plug


def add_enum(obj, attr_name='enumAttr', enum_names=['one', 'two'], default=0, k=True, cb=True):
    pm.addAttr(obj, attributeType='enum', longName=attr_name, dv=default, enumName=enum_names)
    plug = pm.PyNode(f'{obj}.{attr_name}')
    pm.setAttr(plug, keyable=k)
    if not k:
        pm.setAttr(plug, channelBox=cb)
    return plug


def label_attr(obj, label):
    attr_name = "_"
    while pm.attributeQuery(attr_name, node=obj, exists=True):
        attr_name = attr_name + "_"
    pm.addAttr(obj, attributeType="enum", longName=attr_name, enumName=label)
    plug = pm.PyNode(f'{obj}.{attr_name}')
    pm.setAttr(plug, channelBox=True)
    pm.setAttr(plug, lock=True)
    return plug


def add_tag(obj, tag, value, typ='string'):
    if typ == 'string':
        pm.addAttr(obj, dt=typ, longName=tag)
    else:
        pm.addAttr(obj, at=typ, longName=tag)
    plug = pm.PyNode(f'{obj}.{tag}')
    pm.setAttr(plug, value)
    pm.setAttr(plug, lock=True)
    return plug


def _set_locked(attrs, locked=True, k=False, cb=False):
    """ Lock or unlock the given attributes. For internal use, lock(), unlock() should be preferred. """
    if not isinstance(attrs, (list, tuple)):
        attrs = [attrs]
    for attr in attrs:
        attr.set(lock=locked)
        attr.set(k=k)
        attr.set(cb=cb)
        for child in attr.iterDescendants():
            child.set(lock=locked)
            child.set(k=k)
            child.set(cb=cb)


def lock(attrs):
    """ Lock and hide the given attributes. """
    _set_locked(attrs, locked=True, k=False, cb=False)


def unlock(attrs, k=True, cb=True):
    """ Unlock the given attributes """
    _set_locked(attrs, locked=False, k=k, cb=cb)


def unlock_transforms(nodes):
    """ Unlock and show translate, rotate and scale. """
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    for node in nodes:
        unlock([node.t, node.r, node.s])


def safe_set(attr, val, ignore_errors=(RuntimeError, )):
    """ Set the attr to the given value, catch errors. """
    try:
        attr.set(val)
    except ignore_errors:
        if attr.get() != val:
            pm.warning(f'Cannot set {attr} to {val}!')
