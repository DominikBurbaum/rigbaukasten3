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


def soft_clip_single(
        input_plug,
        clip_start=6,
        clip_end=10,
        output_plug=None,
        attrs_holder=None,
        module_key='C_mod',
        label='softClip',
):
    """
    Create a soft clip setup to limit the given input_plug above or below a certain threshold.
    The setup has three states:
    - if the inout is less than clip_start it is unchanged
    - if the inout is higher than clip_end, it is clip_end
    - if it's between clip_start and clip_end it will softly fade out with the following function:
                    (x/(n*1.5))^3
      (x/(n*1.5)) - ------------- * n * 1.5
                          3
      where x is the input_plug and n is the clip range (clip_end - clip_start). The power & divide by 3 is there to
      make the soft clip. The multiplication by 1.5 is there to make sure the output actually hits the clip_end value
      and isn't clipped 2/3 below it.
      :param input_plug: pm.Attribute - the attribute that sold be clipped
      :param clip_start: float - default start value for the clip, nothing's clipped below this value
      :param clip_end: float - default end value for the clip, no values above this are possible
      :param output_plug: pm.Attribute - optional, plug to feed the clipped result into
      :param attrs_holder: PyNode - Node to hold the clip start and end attributes
      :param module_key: str - <side>_<name> prefix for all nodes
      :param label: str - additional label to avoid name clashes for multiple soft clips in the same module
      :return: pm.Attribute - plug with the clipped output
    """
    attrs_holder = attrs_holder or input_plug.node()
    pm.addAttr(attrs_holder, ln=f'{label}Start', at='float', dv=clip_start, k=True)
    pm.addAttr(attrs_holder, ln=f'{label}End', at='float', dv=clip_end, k=True)
    start_plug = attrs_holder.attr(f'{label}Start')
    end_plug = attrs_holder.attr(f'{label}End')

    clip_range_pma = create_node(
        'plusMinusAverage', i1__0___=end_plug, i1__1___=start_plug, op=2, n=f'{module_key}_{label}ClipRange_PMA')
    offset_inout_pma = create_node(
        'plusMinusAverage', i1__0___=input_plug, i1__1___=start_plug, op=2, n=f'{module_key}_{label}OffsetInput_PMA')
    scale_range_mdl = create_node(
        'multDoubleLinear', i1=clip_range_pma.o1, i2=1.5, n=f'{module_key}_{label}RangeScale_MDL')
    normalize_mlt = create_node(
        'multiplyDivide', i1x=offset_inout_pma.o1, i2x=scale_range_mdl.o, op=2, n=f'{module_key}_{label}Normalize_MDL')
    power_3_mlt = create_node(
        'multiplyDivide', i1x=normalize_mlt.ox, i2x=3, op=3, n=f'{module_key}_{label}Power3_MDL')
    div_3_mlt = create_node(
        'multiplyDivide', i1x=power_3_mlt.ox, i2x=3, op=2, n=f'{module_key}_{label}Divide3_MDL')
    minus_pma = create_node(
        'plusMinusAverage', i1__0___=normalize_mlt.ox, i1__1___=div_3_mlt.ox, op=2, n=f'{module_key}_{label}Minus_PMA')
    restore_range_mdl = create_node(
        'multDoubleLinear', i1=minus_pma.o1, i2=scale_range_mdl.o, n=f'{module_key}_{label}RangeRestore_MDL')
    clip_range_cnd = create_node(
        'condition',
        ft=normalize_mlt.ox,
        st=1,
        op=4,
        ctr=restore_range_mdl.o,
        cfr=clip_range_pma.o1,
        n=f'{module_key}_{label}ClipRange_CND'
    )
    offset_output_adl = create_node(
        'addDoubleLinear', i1=start_plug, i2=clip_range_cnd.ocr, n=f'{module_key}_{label}OffsetOutput_ADL')
    swap_op_cnd = create_node(
        'condition',
        ft=start_plug,
        st=end_plug,
        op=4,
        ctr=4,
        cfr=2,
        n=f'{module_key}_{label}SwapOperation_CND'
    )
    full_range_cnd = create_node(
        'condition',
        ft=input_plug,
        st=start_plug,
        op=swap_op_cnd.ocr,
        ctr=input_plug,
        cfr=offset_output_adl.o,
        n=f'{module_key}_{label}FullRange_CND'
    )
    if output_plug:
        full_range_cnd.ocr >> output_plug
    return full_range_cnd.ocr


def soft_clip_double(
        input_plug,
        upper_clip_start=6,
        upper_clip_end=10,
        lower_clip_start=-6,
        lower_clip_end=-10,
        output_plug=None,
        attrs_holder=None,
        module_key='C_mod',
        label='SoftClip',
):
    """
    Create two soft clip setups, to clip teh given input plug in both directions (upper & lower bound).
    """
    upper_clip_output = soft_clip_single(
        input_plug=input_plug,
        clip_start=upper_clip_start,
        clip_end=upper_clip_end,
        output_plug=None,
        attrs_holder=attrs_holder,
        module_key=module_key,
        label=f'upper{label}'
    )
    lower_clip_output = soft_clip_single(
        input_plug=upper_clip_output,
        clip_start=lower_clip_start,
        clip_end=lower_clip_end,
        output_plug=output_plug,
        attrs_holder=attrs_holder,
        module_key=module_key,
        label=f'lower{label}'
    )
    return lower_clip_output


def soft_clip_pos_neg(
        input_plug,
        clip_start=6,
        clip_end=10,
        output_plug=None,
        attrs_holder=None,
        module_key='C_mod',
        label='softClip',
):
    """
    Create a soft clip setup, that clips at the same values in positive and negative direction.
    I.e. if clip_end is 10 then values below -10 will also be clipped.
    This requires less inout attributes and fewer nodes than having a soft_clip_double that does the same.
    """
    invert_swap_cnd = create_node(
        'condition',
        ft=input_plug,
        st=0,
        op=4,
        ctr=-1,
        cfr=1,
        n=f'{module_key}_{label}InvertSwap_CND'
    )
    invert_mdl = create_node(
        'multDoubleLinear', i1=input_plug, i2=invert_swap_cnd.ocr, n=f'{module_key}_{label}Invert_MDL')
    clip_output = soft_clip_single(
        input_plug=invert_mdl.o,
        clip_start=clip_start,
        clip_end=clip_end,
        output_plug=None,
        attrs_holder=attrs_holder,
        module_key=module_key,
        label=label
    )
    revert_mdl = create_node(
        'multDoubleLinear', i1=clip_output, i2=invert_swap_cnd.ocr, n=f'{module_key}_{label}Revert_MDL')
    if output_plug:
        revert_mdl.o >> output_plug
    return revert_mdl.o
