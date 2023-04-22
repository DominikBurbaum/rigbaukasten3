import pymel.core as pm


def create_node(*args, **kwargs):
    """
    This creates a node and set/connects all inputs that are passed as arguments.
    Usage:
    connectiutl.create_node('multiplyDivide', i1x=.5, i2x='pCube1.tx', ox='locator1.ty')
    # in array attributes use double underscore for open brackets and triple underscore for close brackets
    connectiutl.create_node('blendTwoAttr', i__0___=.5, i__1___='pCube1.tx')
    """
    # separate the original flags from the create_node() function from the attributes
    flags = {}
    attrs = {}
    for k, v in kwargs.items():
        if k in ('name', 'n', 'parent', 'p', 'shared', 's', 'skipSelect', 'ss'):
            flags[k] = v
        else:
            attrs[k] = v

    # create
    node = pm.createNode(*args, **flags)

    # set/connect attrs
    for attrName, val in attrs.items():
        if val is None:
            # This is for when you want to use one of the xxxconnect functions but ignore one input
            continue
        # convert characters for array attributes
        attr = node.attr(attrName.replace('___', ']').replace('__', '['))
        # attr or value
        if pm.objExists(str(val).replace('->', '').replace('<-', '')):
            # check if it's an input- or output attribute, then connect attribute
            if val.startswith('->'):
                is_input_attr = False
                val = val[2:]
            elif val.startswith('<-'):
                is_input_attr = True
                val = val[2:]
            else:
                is_input_attr = pm.attributeQuery(attr.attrName().split('[')[0], node=node, w=True)
            if is_input_attr:
                pm.connectAttr(val, attr, force=True)
            else:
                pm.connectAttr(attr, val, force=True)
        else:
            # set value(s)
            if not isinstance(val, (list, tuple)):
                val = [val]
            attr.set(*val)
            # pm.setAttr('%s.%s' % (node, attr), *val)

    return node


def driven_keys(driver, driven=(), v=(), dv=(), tangents='linear'):
    """
    Creates driven keys in less lines.
    """
    if not isinstance(driven, (list, tuple)):
        driven = [driven]
    anim_crv_nodes = []
    for drivenAttr in driven:
        dn, at = drivenAttr.split('.')
        for value, driverValue in zip(v, dv):
            pm.setDrivenKeyframe(dn, cd=driver, at=at, v=value, dv=driverValue, ott=tangents, itt=tangents)
        acn = pm.listConnections(drivenAttr, s=True, d=False, p=False)
        anim_crv_nodes += acn
    return anim_crv_nodes


def simple_matrix_constraint(driver, driven):
    """ Simple world matrix matching connections. """
    parent = pm.listRelatives(driven, p=True)[0]
    mmx = create_node(
        'multMatrix',
        matrixIn__0___=driver.wm[0],
        matrixIn__1___=parent.wim[0],
    )
    create_node(
        'decomposeMatrix',
        inputMatrix=mmx.matrixSum,
        outputTranslate=driven.t,
        outputRotate=driven.r,
        outputScale=driven.s,
        outputShear=driven.shear
    )
    if hasattr(driven, 'jointOrient'):
        # create extra network for rotation that takes joint orient into account
        com = create_node(
            'composeMatrix',
            inputRotateX=driven.jointOrientX.get(),
            inputRotateY=driven.jointOrientY.get(),
            inputRotateZ=driven.jointOrientZ.get(),
        )
        mmx2 = create_node(
            'multMatrix',
            matrixIn__0___=com.outputMatrix,
            matrixIn__1___=parent.wm[0],
        )
        ivm = create_node(
            'inverseMatrix',
            inputMatrix=mmx2.matrixSum
        )
        mmx3 = create_node(
            'multMatrix',
            matrixIn__0___=driver.wm[0],
            matrixIn__1___=ivm.outputMatrix,
        )
        create_node(
            'decomposeMatrix',
            inputMatrix=mmx3.matrixSum,
            outputRotate=driven.r,
        )
