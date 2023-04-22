import pymel.core as pm
from rigbaukasten.utils import connectutl


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
