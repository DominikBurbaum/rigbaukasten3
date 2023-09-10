
import os

import pymel.core as pm

import rigbaukasten
from rigbaukasten.utils import errorutl, pymelutl


def create_skin(side, module_name, joints, geo):
    label = geo.split(':')[-1].replace('_', '')
    skn = pm.skinCluster(joints, geo, tsb=True, n=f'{side}_{module_name}_{label}_SKN', weightDistribution=1)
    return skn


def get_geo_name_from_skin_data(data):
    """ Get the geo name from data that was previously exported via pm.deformerWeights. """
    shapes = list(set([x['shape'] for x in data['deformerWeight']['weights']]))
    if len(shapes) > 1:
        pm.warning('More than one shape in skinWeights file, not sure what to do here. Only using first.')
    geo = shapes[0]
    return geo


def get_deformer_name_from_skin_data(data):
    """ Get the deformer name from data that was previously exported via pm.deformerWeights. """
    deformers = list(set([x['deformer'] for x in data['deformerWeight']['weights']]))
    if len(deformers) > 1:
        pm.warning('More than one deformers in skinWeights file, not sure what to do here. Only using first.')
    deformer_name = deformers[0]
    return deformer_name


def get_joint_names_from_skin_data(data):
    """ Get the joint names from data that was previously exported via pm.deformerWeights. """
    joint_names = list(set([x['source'] for x in data['deformerWeight']['weights']]))
    return joint_names


def get_path_from_skin_data(data):
    """ Get the file path from the skin data that was previously exported via pm.deformerWeights.

        This may seem stupid, because it we have the data we already read the file and should know the path. The
        problem is that the iocor interface doesn't allow to pass the path on, so we need to find it again. Usually
        we wouldn't need the file again once we read the content, thus iocor doesn't pass the path on. But in this
        case we want to use pm.deformerWeights instead of setting the weights manually, so we do need the file path
        again.
        As if this confusion wasn't enough, we also have to make sure the path is still valid in the current system.
        It may have been written on another workstation where the project is in a different folder. It may even been
        written with a different OS.
    """
    path = data['deformerWeight']['headerInfo']['fileName']
    path = path.replace('/', os.sep).replace('\\', os.sep)
    if not os.path.exists(path):
        head = rigbaukasten.environment.get_rigdata_path()
        splitter = f'{os.sep}rigdata{os.sep}'
        tail = path.split(splitter)[-1]
        path = os.path.join(head, tail)
    return path


def ensure_all_joints_exist(joint_names):
    """ Check if all joints form the given list of names exist, create a joint at the origin for any missing ones. """
    joints = []
    for jnt in joint_names:
        if pm.objExists(jnt):
            joints.append(pm.PyNode(jnt))
        else:
            joints.append(pm.createNode('joint', n=jnt, ss=True))
    return joints


def ensure_skin_cluster_exists(deformer_name, geo, joints):
    """ Check if a skinCluster with the given name exists, create if not. """
    if pm.objExists(deformer_name):
        skn = pm.PyNode(deformer_name)
    else:
        skn = pm.skinCluster(joints, geo, tsb=True, n=deformer_name, weightDistribution=1)
    return skn


def ensure_skin_cluster_is_connected_to_all_joints(skn, joints):
    """ Check if the given skinCluster is connected to all joints, connect any missing ones. """
    inf = skn.getInfluence()
    for jnt in joints:
        if jnt not in inf:
            skn.addInfluence(jnt)


def create_skin_from_data(data):
    geo = get_geo_name_from_skin_data(data)
    deformer_name = get_deformer_name_from_skin_data(data)
    joint_names = get_joint_names_from_skin_data(data)
    path = get_path_from_skin_data(data)

    if pm.objExists(geo):
        geo = pm.PyNode(geo)
    else:
        raise errorutl.RbkNotFound(f'Geometry "{geo}" does not exist.')

    joints = ensure_all_joints_exist(joint_names)
    skn = ensure_skin_cluster_exists(deformer_name, geo, joints)
    ensure_skin_cluster_is_connected_to_all_joints(skn, joints)

    apply_weights_from_file(path, skn)


def apply_weights_from_file(path, skn):
    """ Load the weights from the given file onto the given skinCluster.
        :param path: str, absolute file path to a file that was previously exported via pm.deformerWeights
        :param skn: PyNode, skinCluster to load weights, assuming all influences are already connected
    """
    pm.deformerWeights(
        os.path.basename(path),
        path=os.path.dirname(path),
        im=True,
        deformer=skn,
        method='index',
    )
    # vtx[0] is always broken...
    pm.select(skn.getGeometry()[0].vtx[0])
    skn.smoothWeights(0)
    pm.select(cl=True)
    skn.forceNormalizeWeights()


def get_skin(obj):
    """ Get the skinCluster on the given mesh. """
    skn = pm.listHistory(obj, type='skinCluster')
    if not skn:
        raise errorutl.RbkNotFound(f'No skinCluster found on {obj}')
    return skn[0]


def copy_skin(src, tgt, uv_based=False):
    """ Copy skin weights from source(s) to target.
    :param src: [PyNode, ], source mesh(es) with a skinCluster
    :param tgt: [PyNode, ] or [Component, ], Target mesh(es) with a skinCluster and same influences as src.
                                             If components are specified they must all be from the same object.
    :param uv_based: bool, transfer weights in uv space
    """
    if uv_based:
        kwargs = {'uv': [
                    pm.polyUVSet(src[0], cuv=True, q=True)[0],
                    pm.polyUVSet(tgt[0], cuv=True, q=True)[0]
            ]
        }
    else:
        kwargs = {}
    if isinstance(tgt[0], pm.general.Component):
        tgt = [tgt]
    for t in tgt:
        pm.copySkinWeights(
            src, t,
            noMirror=True,
            influenceAssociation=("name", "label", "oneToOne"),
            surfaceAssociation="closestPoint",
            **kwargs
        )


def transfer_skin(src=(), tgt=(), module_key='C_transferredSkin', uv_based=False):
    src_skin = get_skin(src[0])
    src_jnts = src_skin.getInfluence()
    src_is_comp = isinstance(src[0], pm.general.Component)
    tgt_is_comp = isinstance(tgt[0], pm.general.Component)

    tgt_objs = [tgt[0].node()] if tgt_is_comp else tgt
    for tgt_obj in tgt_objs:
        try:
            tgt_skin = get_skin(tgt_obj)
        except errorutl.RbkNotFound:
            label = tgt_obj.replace('_', '')
            pm.skinCluster(src_jnts, tgt_obj, tsb=True, n=f'{module_key}_{label}_SKN')
        else:
            tgt_jnts = tgt_skin.getInfluence()
            for jnt in src_jnts:
                if jnt not in tgt_jnts:
                    tgt_skin.addInfluence(jnt)

    if src_is_comp:
        src_obj = src[0].node()
        src_faces = pymelutl.to_pynode(pm.polyListComponentConversion(src, tf=True, internal=True))
        src_patch = pm.duplicate(src_obj, n=f'{module_key}_tempSkinTransfer_PLY')[0]
        src_patch_faces = []
        for src_face in src_faces:
            src_patch_faces += [pm.PyNode(f'{src_patch}.f[{i}]') for i in src_face.indices()]
        pm.select(src_patch.f)
        pm.select(src_patch_faces, tgl=True)
        pm.delete()
        pm.delete(src_patch, ch=True)
        pm.skinCluster(src_jnts, src_patch, tsb=True)
        copy_skin([src_obj], [src_patch], uv_based=True)
        src = [src_patch]

    copy_skin(src, tgt, uv_based=uv_based)

    if src_is_comp:
        pm.delete(src)
