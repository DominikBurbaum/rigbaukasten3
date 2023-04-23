from collections import namedtuple

import pymel.core as pm

from rigbaukasten.utils import errorutl, mathutl, attrutl


def create_guide(side, module_name, label, size, parent=None, lock_attrs='sv'):
    gde = pm.spaceLocator(n=f'{side}_{module_name}_{label}_GDE')
    gde.localScale.set(size, size, size)
    gde.overrideEnabled.set(True)
    gde.overrideColor.set({'C': 17, 'L': 6, 'R': 13}[side])
    for attr in lock_attrs:
        gde.attr(attr).set(lock=True)
    if parent:
        gde.setParent(parent)
    return gde


def get_guide_data(gde):
    """ Get the transform & user data from the given guide for rig data publish. """
    data = {
        'translate': list(gde.getTranslation('world')),
        'rotate': list(gde.getRotation('world')),
        'scale': list(gde.scale.get()),
        'localScale': list(gde.localScale.get()),
        'userAttrs': {attr: gde.attr(attr).get() for attr in pm.listAttr(gde, ud=True)}
    }
    return data


def set_guide_data(gde, data):
    """ Apply the data from a previous rig data publish to the given guide """
    gde.setTranslation(data['translate'], 'world')
    gde.setRotation(data['rotate'], 'world')
    for i, ax in enumerate('XYZ'):
        for attr in ('scale', 'localScale'):
            attrutl.safe_set(gde.attr(attr + ax), data[attr][i])
    # gde.scale.set(data['scale'])
    # gde.localScale.set(data['localScale'])
    for attr, val in data.get('userAttrs', {}).items():
        if hasattr(gde, attr):
            attrutl.safe_set(gde.attr(attr), val)
            # gde.attr(attr).set(val)


WORLD_AXIS = 0  # up vector is aligned using the world axis
ROOT_GUIDE = 1  # up vectors of all joints are aligned to the axis of the root guide of the chain
EACH_GUIDE = 2  # up vectors of each joint are aligned to their according guide axis


def create_oriented_guide_chain(
        side='C',
        module_name='chain',
        labels=('00', '01', '02', '03'),
        size=1,
        positions=(),
        aim=(1, 0, 0),
        up=(0, 1, 0),
        world_up=(0, 1, 0),
        world_up_type=WORLD_AXIS,
        flip_right_vectors=True,
        tip_joint_aim=False
):
    """
    Create a joint chain with guides, where each joint is oriented towards teh next one.
    :param side: C, L or R
    :param module_name: name of the module the china belongs to
    :param labels: labels for each joint that will be created
    :param size: Size of the guide locators. Will also affect default positions if positions is empty
    :param positions: default positions for the guides
    :param aim: aim vector for the joints
    :param up: up vector for the joints
    :param world_up: world up vector for the joints
    :param world_up_type: hwo should the up vector be driven, see constants above for options
    :param flip_right_vectors: invert the aim and up vectors if side is R (for easier usage in loops)
    :param tip_joint_aim: bool - Aim the tip joint based on its parent. If False the tip guide can be freely rotated
    :return:
    """
    if positions and len(positions) != len(labels):
        raise errorutl.RbkInvalidKeywordArgument(f'length of labels & positions must match, got {labels} & {positions}')

    grp = pm.group(em=True, n=f'{side}_{module_name}_guideChain_GRP')
    num_guides = len(labels)
    if not positions:
        seg_size = (size / (num_guides - 1)) if size > num_guides else 1
        positions = [(aim[0] * i * seg_size, aim[1] * i * seg_size, aim[2] * i * seg_size) for i in range(num_guides)]
    if flip_right_vectors and side == 'R':
        aim = [a * -1 for a in aim]
        up = [a * -1 for a in up]
    guides, joints = [], []
    for label, pos in zip(labels, positions):
        gde = create_guide(side=side, module_name=module_name, label=label, size=size, parent=grp)
        gde.attr('localScale' + mathutl.axis_from_vector(aim, 1)).set(size * 0.1)
        pm.xform(gde, ws=True, t=pos)
        jnt = pm.createNode('joint', n=f'{side}_{module_name}_{label}_JNT')
        jnt.displayLocalAxis.set(True)
        pm.pointConstraint(gde, jnt)
        if joints:
            jnt.setParent(joints[-1])
            if world_up_type == WORLD_AXIS:
                pm.aimConstraint(gde, joints[-1], aim=aim, u=up, wu=world_up, wut='vector')
            elif world_up_type == ROOT_GUIDE:
                pm.aimConstraint(gde, joints[-1], aim=aim, u=up, wu=world_up, wut='objectrotation', wuo=guides[0])
            elif world_up_type == EACH_GUIDE:
                pm.aimConstraint(gde, joints[-1], aim=aim, u=up, wu=world_up, wut='objectrotation', wuo=guides[-1])
            else:
                raise errorutl.RbkInvalidKeywordArgument(
                    'world_up_type must be one of: WORLD_AXIS, ROOT_GUIDE, EACH_GUIDE'
                )
        if label == labels[-1]:
            if tip_joint_aim:
                tip_aim = [a * -1 for a in aim]
                if world_up_type == WORLD_AXIS:
                    pm.aimConstraint(guides[-1], jnt, aim=tip_aim, u=up, wu=world_up, wut='vector')
                elif world_up_type == ROOT_GUIDE:
                    pm.aimConstraint(
                        guides[-1], jnt, aim=tip_aim, u=up, wu=world_up, wut='objectrotation', wuo=guides[0]
                    )
                elif world_up_type == EACH_GUIDE:
                    pm.aimConstraint(guides[-1], jnt, aim=tip_aim, u=up, wu=world_up, wut='objectrotation', wuo=gde)
            else:
                pm.orientConstraint(gde, jnt)
        guides.append(gde)
        joints.append(jnt)
    GuideChain = namedtuple('GuideChain', ['grp', 'guides', 'joints'])
    return GuideChain(grp, guides, joints)


def create_limb_guide_chain(
        side='C',
        module_name='arm',
        labels=('clavicle', 'shoulder', 'elbow', 'wrist'),
        size=1,
        positions=(),
        as_leg=False,
        with_foot=False
):
    expected = 6 if with_foot else 4
    if positions and len(positions) != expected:
        raise errorutl.RbkInvalidKeywordArgument(f'Need one position for each of: {labels},  got {positions}')
    if len(labels) != expected:
        raise errorutl.RbkInvalidKeywordArgument(f'need {expected} lables, got {labels}')

    grp = pm.group(em=True, n=f'{side}_{module_name}_guideChain_GRP')
    aim = (-1, 0, 0) if side == 'R' else (1, 0, 0)
    inv_aim = [a * -1 for a in aim]
    up = (0, 0, -1) if side == 'R' else (0, 0, 1)
    inv_up = [a * -1 for a in up]
    root_world_up = (0, 0, 1)
    foot_up = (0, 1, 0)
    foot_world_up = (1, 0, 0)

    if not positions:
        if as_leg:
            positions = [
                (size * aim[0], size * 6, 0),
                (size * aim[0] * 1.2, size * 6, 0),
                (size * aim[0] * 1.2, size * 3, size),
                (size * aim[0] * 1.2, 0, 0),
            ]
            if with_foot:
                positions += [
                    (size * aim[0] * 1.2, 0, size),
                    (size * aim[0] * 1.2, 0, size * 2)
                ]
        else:
            positions = [
                (size * aim[0], size * 6, 0),
                (size * aim[0] * 2, size * 6, 0),
                (size * aim[0] * 4, size * 6, -size),
                (size * aim[0] * 6, size * 6, 0),
            ]

    guides, joints = [], []
    for label, pos in zip(labels, positions):
        gde = create_guide(side=side, module_name=module_name, label=label, size=size, parent=grp)
        pm.xform(gde, ws=True, t=pos)
        jnt = pm.createNode('joint', n=f'{side}_{module_name}_{label}_JNT')
        jnt.displayLocalAxis.set(True)
        pm.pointConstraint(gde, jnt)
        if joints:
            jnt.setParent(joints[-1])
        guides.append(gde)
        joints.append(jnt)

    pm.aimConstraint(guides[1], joints[0], aim=aim, u=up, wu=root_world_up, wut='objectrotation', wuo=guides[0])
    mid_up_trn = pm.group(em=True, p=grp, n=f'{side}_{module_name}_midUp_TRN')
    pm.pointConstraint(guides[1], guides[3], mid_up_trn)
    pm.aimConstraint(guides[2], joints[1], aim=aim, u=inv_up if as_leg else up, wut='object', wuo=mid_up_trn)
    pm.aimConstraint(guides[3], joints[2], aim=aim, u=inv_up if as_leg else up, wut='object', wuo=mid_up_trn)
    if with_foot:
        pm.aimConstraint(
            guides[4], joints[3], aim=aim, u=foot_up, wu=foot_world_up, wut='objectrotation', wuo=guides[3]
        )
        pm.aimConstraint(
            guides[5], joints[4], aim=aim, u=foot_up, wu=foot_world_up, wut='objectrotation', wuo=guides[4]
        )
        pm.aimConstraint(
            guides[4], joints[5], aim=inv_aim, u=foot_up, wu=foot_world_up, wut='objectrotation', wuo=guides[4]
        )
    else:
        pm.orientConstraint(guides[3], joints[3])

    GuideChain = namedtuple('GuideChain', ['grp', 'guides', 'joints'])
    return GuideChain(grp, guides, joints)
