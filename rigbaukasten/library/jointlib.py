import pymel.core as pm
from rigbaukasten.utils import connectutl, attrutl, mathutl


def fk_ik_joints(joints, fk_ik_plug, names=('Fk', 'Ik'), constraint=True):
    fk_joints = []
    ik_joints = []
    rvs = connectutl.create_node(
        'reverse',
        inputX=fk_ik_plug,
    )
    for j in joints:
        for i, lst in enumerate((fk_joints, ik_joints)):
            dup = pm.duplicate(j, n=j.replace('_JNT', f'{names[i]}_JNT'), po=True)[0]
            dup.radius.set(dup.radius.get() * 0.5)
            if lst:
                dup.setParent(lst[-1])
            lst.append(dup)
        if constraint:
            pac = pm.parentConstraint(fk_joints[-1], ik_joints[-1], j)
            plugs = pm.parentConstraint(pac, q=1, wal=1)
            fk_ik_plug >> plugs[1]
            rvs.outputX >> plugs[0]
            scc = pm.scaleConstraint(fk_joints[-1], ik_joints[-1], j)
            plugs = pm.scaleConstraint(scc, q=1, wal=1)
            fk_ik_plug >> plugs[1]
            rvs.outputX >> plugs[0]
        else:
            bm = connectutl.create_node(
                'blendMatrix',
                inputMatrix=fk_joints[-1].matrix,
                envelope=fk_ik_plug
            )
            ik_joints[-1].matrix >> bm.tgt[0].tmat
            connectutl.create_node(
                'decomposeMatrix',
                inputMatrix=bm.outputMatrix,
                outputTranslate=j.t,
                outputRotate=j.r,
                outputScale=j.s
            )

    return fk_joints, ik_joints


def duplicate_joint_chain(joint_chain, root_parent=None, search='_JNT', replace='Puppet_JNT'):
    """ Duplicate the given joint chain.
        :param joint_chain: [PyNode, ...] - list of joints to duplicate, must be parented in the same order.
        :param root_parent: PyNode - parent for the new root joint
        :param search: str - name substring for search & replace
        :param replace: str - name substring for search & replace
    """
    new_chain = []
    for i, jnt in enumerate(joint_chain):
        new = pm.duplicate(jnt, po=True, n=jnt.replace(search, replace))[0]
        new_chain.append(new)
        new.radius.set(new.radius.get() * 1.5)
        if i == 0 and root_parent:
            new.setParent(root_parent)
        if i:
            new.setParent(new_chain[-1])
    return new_chain


def driven_joint(name, parent, **attr_keys):
    """
    Create a joint with driven keys
    :param name: full name for the new joint
    :param parent: parent node for the joint
    :param attr_keys: use attribute name as keyword and a dict of driven_key settings as value, e.g.
                      tx={'driver': driver_jnt.rx, 'dv': (0, 90), 'v': (0, -10)}
    :return: the joint
    """
    jnt = pm.createNode('joint', n=name, p=parent, ss=True)
    for attr, settings in attr_keys.items():
        connectutl.driven_keys(driven=jnt.attr(attr), **settings)
    return jnt


def motion_path_joints_uniform(
        crv,
        start_ctl,
        end_ctl,
        nr_jnts,
        aim_vec=(1, 0, 0),
        up_vec=(0, 1, 0),
        name='C_spine_ik',
        attrs_holder=None,
        global_scale_plug='C_main_00_CTL.globalScale'
    ):
    aim_axis = mathutl.axis_from_vector(aim_vec, upper_case=True)
    up_axis = mathutl.axis_from_vector(up_vec, upper_case=True)
    side_axis = 'XYZ'.replace(aim_axis[-1], '').replace(up_axis[-1], '')
    up_plug = attrutl.add_enum(attrs_holder or start_ctl, 'upAxis', enum_names=[up_axis[-1], side_axis])
    rvs_up_plug = connectutl.create_node("reverse", ix=up_plug, n=f"{name}UpAxis_RVS").ox

    u_plugs = []
    jnts = []
    for i in range(nr_jnts):
        u_value_noop = connectutl.create_node("addDoubleLinear", n=f"{name}UValueNoOp{i}_ADL")
        u_plug = attrutl.add(u_value_noop, 'uValue', default=i / (nr_jnts - 1))
        rvs_u_plug = connectutl.create_node("reverse", ix=u_plug, n=f"{name}UValue{i}_RVS").ox
        u_plugs.append(u_plug)

        add_up_vecs = connectutl.create_node('plusMinusAverage', n=f'{name}AddUpVec{i}_PMA')
        for x, trn in enumerate((start_ctl, end_ctl)):
            suffix = 'End' if x else 'Start'
            vec_from_matrix = connectutl.create_node(
                'vectorProduct',
                matrix=trn.wm[0],
                operation=3,
                **{f'input1{aim_axis[-1]}': 0, f'input1{up_axis[-1]}': rvs_up_plug, f'input1{side_axis}': up_plug},
                n=f'{name}VectorFromWorldMatrix{i}{suffix}_VEC'
            )
            vec_from_matrix_weighted = connectutl.create_node(
                'multiplyDivide',
                i1=vec_from_matrix.o,
                i2x=u_plug if x else rvs_u_plug,
                i2y=u_plug if x else rvs_u_plug,
                i2z=u_plug if x else rvs_u_plug,
                n=f'{name}VectorFromWorldMatrixWeighted{i}{suffix}_MDL'
            )
            vec_from_matrix_weighted.o >> add_up_vecs.i3[x]
        normalize_up_vec = connectutl.create_node(
            'vectorProduct',
            operation=0,
            i1=add_up_vecs.o3,
            normalizeOutput=True,
            n=f'{name}NormalizedUpVector{i}_VEC'
        )

        jnt = pm.createNode('joint', name=f'{name}{i:02d}')
        jnts.append(jnt)
        mop = connectutl.create_node(
            'motionPath',
            geometryPath=crv.ws[0],
            u=u_plug,
            fractionMode=True,
            worldUpType=3,
            frontAxis=0 if aim_vec[0] else 1 if aim_vec[1] else 2,
            inverseFront=min(aim_vec) < 0,
            upAxis=0 if up_vec[0] else 1 if up_vec[1] else 2,
            inverseUp=min(up_vec) < 0,
            worldUpVector=normalize_up_vec.o,
            allCoordinates=jnt.t,
            rotate=jnt.r,
            n=f'{name}CurveAttachment{i}_MOP'
        )
        connectutl.driven_keys(
            driver=up_plug,
            driven=mop.upAxis,
            dv=(0, 1),
            v=('XYZ'.index(up_axis[-1]), 'XYZ'.index(side_axis))
        )
        jnt.displayLocalAxis.set(True)

    stretch_plug = attrutl.add(attrs_holder or start_ctl, 'stretch', mn=0, mx=1, default=1)
    anchor_plug = attrutl.add(attrs_holder or start_ctl, 'anchor', mn=0, mx=1)

    arclen = connectutl.create_node('curveInfo', inputCurve=crv.worldSpace[0], n=f'{name}Length_CVI')
    mlt_global_scale = connectutl.create_node(
        'multiplyDivide',
        i1x=arclen.arcLength,
        i2x=pm.PyNode(global_scale_plug),
        operation=2
    )
    mlt_stretch = connectutl.create_node(
        'multiplyDivide',
        i1x=mlt_global_scale.ox,
        i2x=mlt_global_scale.ox.get(),
        operation=2
    )
    bta_enable = connectutl.create_node(
        'blendTwoAttr',
        i__0___=mlt_stretch.ox,
        i__1___=1,
        attributesBlender=stretch_plug,
        n=f'{name}EnableStretch_BTA'
    )

    anchor_offset_plug = None
    for i in range(nr_jnts - 1, -1, -1):
        mlt_no_stretch = connectutl.create_node(
            'multiplyDivide',
            i1x=u_plugs[i].get(),
            i2x=bta_enable.o,
            op=2,
            n=f'{name}EnableStretch_MDL'
        )
        if not anchor_offset_plug:
            pma = connectutl.create_node(
                'plusMinusAverage',
                i1__0___=1,
                i1__1___=mlt_no_stretch.ox,
                operation=2,
                n=f'{name}AnchorOffsetValue_PMA'
            )
            mdl = connectutl.create_node(
                'multDoubleLinear',
                i1=pma.o1,
                i2=anchor_plug,
                n=f'{name}WeightedAnchorOffsetValue_MDL'
            )
            anchor_offset_plug = mdl.o
        connectutl.create_node(
            'addDoubleLinear',
            i1=anchor_offset_plug,
            i2=mlt_no_stretch.ox,
            o=u_plugs[i],
            n=f'{name}AnchorOffset_ADL'
        )

        return crv, jnts
