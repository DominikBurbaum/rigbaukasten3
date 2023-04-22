import pymel.core as pm
from rigbaukasten.library import controllib, curvelib
from rigbaukasten.utils import mathutl, connectutl, attrutl


def fk_chain_from_joints(joints, label='Fk', size=1):
    ctls = []
    for j in joints:
        side, module_name, jnt_label, suffix = j.name().split('_')
        if 'Puppet' in jnt_label:
            jnt_label = jnt_label.replace('Puppet', '')
        ctl = controllib.AnimCtl(
            side=side,
            module_name=module_name,
            label=jnt_label + label,
            pos=j,
            rot=j,
            size=size,
        )
        if ctls:
            ctl.grp.setParent(ctls[-1].trn)
        ctls.append(ctl)
        pm.parentConstraint(ctl.trn, j)
        pm.scaleConstraint(ctl.trn, j)
    return ctls


def ik_chain_from_joints(joints, label='Ik', size=1, pole_position=(0, 0, 0), maintain_offset=False, offset=(0, 0, 0)):
    side, module_name, jnt_label, suffix = joints[-1].name().split('_')
    if 'Puppet' in jnt_label:
        jnt_label = jnt_label.replace('Puppet', '')
    end_ctl = controllib.AnimCtl(
        side=side,
        module_name=module_name,
        label=jnt_label + label,
        pos=joints[-1],
        size=size,
        ctl_shape='box'
    )
    pole_ctl = controllib.AnimCtl(
        side=side,
        module_name=module_name,
        label=jnt_label + label + 'Pole',
        pos=pole_position,
        size=size * 0.5,
        ctl_shape='diamond'
    )
    ikh = pm.ikHandle(sj=joints[0], ee=joints[-1], sol='ikRPsolver', n=f'{side}_{module_name}_{label}_IKH')[0]
    ikh.setParent(end_ctl.trn)
    orc = pm.orientConstraint(end_ctl.trn, joints[-1], mo=maintain_offset)
    if not maintain_offset:
        orc.offset.set(offset)
    pm.poleVectorConstraint(pole_ctl.trn, ikh)
    crv = curvelib.curve_from_transforms(trns=(pole_ctl.trn, joints[1]), d=1, name=f'{side}_{module_name}_{label}Connector')
    crv.inheritsTransform.set(False)
    crv.setParent(pole_ctl.trn)
    crv.template.set(True)
    pm.hide(ikh)

    return (pole_ctl, end_ctl), ikh


def simple_spline_ik_from_joints(joints, label='Ik', size=1, fwd_axis='x', up_axis='y'):
    sj = pm.duplicate(joints[0], po=True, n=joints[0].replace('_JNT', 'IkStart_JNT'))[0]
    sj.setParent(joints[0])
    joints[1].setParent(sj)
    mj = joints[len(joints) // 2]
    ee = joints[-1]

    # ctls
    ctls = []
    for j in (sj, mj, ee):
        side, module_name, jnt_label, suffix = j.name().split('_')
        if 'Puppet' in jnt_label:
            jnt_label = jnt_label.replace('Puppet', '')
        ctl = controllib.AnimCtl(
            side=side,
            module_name=module_name,
            label=jnt_label + label,
            pos=j,
            rot=j,
            size=size,
            ctl_shape='circleGear'
        )
        ctls.append(ctl)
    pm.pointConstraint(ctls[0].trn, ctls[2].trn, ctls[1].grp, mo=True)
    pm.orientConstraint(ctls[-1].trn, joints[-1])
    pm.parentConstraint(ctls[0].trn, joints[0])
    pm.scaleConstraint(ctls[0].trn, joints[0])

    # tangents
    start_tangent = pm.group(em=True, n=ctls[0].trn.replace('_CTL', 'OutTangent_TRN'), p=ctls[0].trn)
    end_tangent = pm.group(em=True, n=ctls[2].trn.replace('_CTL', 'InTangent_TRN'), p=ctls[2].trn)
    attrutl.label_attr(ctls[0].trn, 'settings')
    start_tangent_plug = attrutl.add(ctls[0].trn, 'tangentWeight', default=0, mn=0, mx=1)
    attrutl.label_attr(ctls[-1].trn, 'settings')
    end_tangent_plug = attrutl.add(ctls[-1].trn, 'tangentWeight', default=0, mn=0, mx=1)
    dist = mathutl.distance(ctls[0].trn.getTranslation('world'), ctls[1].trn.getTranslation('world'))
    if fwd_axis.startswith('-'):
        dist *= -1
    attr = f't{fwd_axis[-1]}'
    connectutl.driven_keys(driver=start_tangent_plug, driven=start_tangent.attr(attr), dv=(0, 1), v=(0, dist))
    connectutl.driven_keys(driver=end_tangent_plug, driven=end_tangent.attr(attr), dv=(0, 1), v=(0, -dist))

    # ik curve
    crv = curvelib.curve_from_transforms(
        trns=(ctls[0].trn, start_tangent, ctls[1].trn, end_tangent, ctls[2].trn),
        name=f'{side}_{module_name}_{label}',
        d=2
    )
    crv.inheritsTransform.set(False)
    crv.v.set(False)

    # ik handle
    ikh = pm.ikHandle(sj=sj, ee=ee, sol='ikSplineSolver', ccv=False, c=crv, n=f'{side}_{module_name}_{label}_IKH')[0]
    ikh.v.set(False)
    ikh.dTwistControlEnable.set(True)
    ikh.dForwardAxis.set(['x', '-x', 'y', '-y', 'z', '-z'].index(fwd_axis))
    ikh.dWorldUpType.set(4)
    ikh.dWorldUpAxis.set(['y', '-y', '_', 'z', '-z', '_', 'x', '-x'].index(up_axis))
    up_vec = [a == up_axis[-1] * (-1 if up_axis.startswith('-') else 1) for a in 'xyz']
    ikh.dWorldUpVector.set(up_vec)
    ikh.dWorldUpVectorEnd.set(up_vec)
    ctls[0].trn.wm[0] >> ikh.dWorldUpMatrix
    ctls[-1].trn.wm[0] >> ikh.dWorldUpMatrixEnd

    return ctls, crv, ikh
