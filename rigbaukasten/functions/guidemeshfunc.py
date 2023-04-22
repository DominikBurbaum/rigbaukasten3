import json
import os

import pymel.core as pm
from maya.api import OpenMaya

import rigbaukasten
from rigbaukasten.library import skinlib
from rigbaukasten.utils import mathutl, errorutl, connectutl


def get_guide_to_mesh_mapping(gde, mesh):
    dag = OpenMaya.MSelectionList().add(mesh.name()).getDagPath(0)
    mfn = OpenMaya.MFnMesh(dag)

    mat = pm.xform(gde, q=True, ws=True, matrix=True)
    x_vec = OpenMaya.MFloatVector(mat[0:3])
    y_vec = OpenMaya.MFloatVector(mat[4:7])
    z_vec = OpenMaya.MFloatVector(mat[8:11])
    vectors = (x_vec, -x_vec, y_vec, -y_vec, z_vec, -z_vec)
    pos = OpenMaya.MFloatPoint(mat[12:15])

    bbx = pm.xform(mesh, q=True, ws=True, bb=True)
    diagonal = mathutl.distance(bbx[:3], bbx[3:])

    points = []
    params = []
    for vec in vectors:
        result = mfn.closestIntersection(
            pos,
            vec,
            OpenMaya.MSpace.kWorld,
            diagonal,
            False,
            tolerance=0.0
        )
        if result:
            points.append(OpenMaya.MFloatPoint(result[0]))
            params.append(result[1])
        else:
            points.append(None)
            params.append(diagonal * 10)  # use a high number, but not infinity

    if sum(x is None for x in points) > 2:  # that's like points.count(None), except it works
        # If this passes we have one axes with two intersection and at least one more intersection - enough to continue.
        raise errorutl.RbkInvalidObjectError(
            f'Object {gde} does not have enough intersections with {mesh}. '
            'Objects must be inside a closed mesh, or at least have two intersecting axes.'
        )

    distances = [params[0] + params[1], params[2] + params[3], params[4] + params[5]]
    distances_sorted = sorted(distances)
    pin_index = distances.index(distances_sorted[0])
    up_index = distances.index(distances_sorted[1])

    pin_points = [points[pin_index * 2], points[(pin_index * 2) + 1]]
    pin_params = [params[pin_index * 2], params[(pin_index * 2) + 1]]
    pin_vector = [i == pin_index for i in range(3)]

    up_point = points[up_index * 2]
    if up_point is None:
        up_point = points[(up_index * 2) + 1]
    up_vector = [i == up_index for i in range(3)]

    pin_uvs = [mfn.getUVAtPoint(OpenMaya.MPoint(pnt), OpenMaya.MSpace.kWorld) for pnt in pin_points]
    up_uv = mfn.getUVAtPoint(OpenMaya.MPoint(up_point), OpenMaya.MSpace.kWorld)

    mapping = {
        mesh.name(): {
            gde.name(): {
                'pin_points': [
                        [pin_points[0].x, pin_points[0].y, pin_points[0].z],
                        [pin_points[1].x, pin_points[1].y, pin_points[1].z],
                    ],
                'pin_params': pin_params,
                'pin_uvs': pin_uvs,
                'pin_vector': pin_vector,
                'up_point': [up_point.x, up_point.y, up_point.z],
                'up_uv': up_uv,
                'up_vector': up_vector,
            }
        }
    }
    return mapping


def get_guides_to_mesh_mapping(guides, mesh):
    mapping = {mesh.name(): {}}
    for gde in guides:
        new = get_guide_to_mesh_mapping(gde, mesh)
        mapping[mesh.name()].update(new[mesh.name()])
    return mapping


def write_json(path, mapping):
    if os.path.exists(path):
        raise errorutl.RbkInvalidPath(
            f'File already exists: "{path}". Will not overwrite to prevent errors. '
            'Delete file manually to force writing to this path.'
        )
    if not os.path.exists(os.path.split(path)[0]):
        raise errorutl.RbkInvalidPath(f'Given folder does not exist: "{path}"')
    with open(path, 'w') as f:
        json.dump(mapping, f, indent=4)
    print('SUCCESS')


def get_name_description(mesh):
    mesh_no_namespace = mesh.name().split(':')[-1]
    if mesh_no_namespace[0] not in 'CLR' or not mesh_no_namespace.endswith('_PLY'):
        raise errorutl.RbkInvalidName(f'Please check naming convention on {mesh}')
    description = mesh.name().split('_')[1]
    return description


def get_json_path_for_mesh(mesh, suffix='guides'):
    description = get_name_description(mesh)
    try:
        export_path = get_json_path(folder=description, suffix=suffix)
    except errorutl.RbkInvalidName:
        pm.warning(f'Check name on {mesh}. Should be named after the folder in resources/guide_meshes. ')
        raise
    return export_path


def get_json_path(folder, suffix='guides'):
    resources_path = rigbaukasten.environment.get_resources_path()
    folder_path = os.path.join(resources_path, 'guide_meshes', folder)
    if not os.path.exists(folder_path):
        raise errorutl.RbkInvalidName(
            f'Invalid folder name "{folder}". Should be a folder in resources/guide_meshes. '
            f'{folder_path} does not exist!'
        )
    export_path = os.path.join(folder_path, f'{folder}_{suffix}.json')
    return export_path


def export_mapping(mesh, guides):
    export_path = get_json_path_for_mesh(mesh)
    mapping = get_guides_to_mesh_mapping(guides, mesh)
    write_json(path=export_path, mapping=mapping)


def export_selected_guide_to_mesh_mapping():
    sel = pm.ls(sl=True)
    meshes = []
    guides = []
    for s in sel:
        if s.endswith('_PLY'):
            meshes.append(s)
        else:
            guides.append(s)
    export_mapping(mesh=meshes[0], guides=guides)


def set_guides_from_mapping(mapping, override_mesh=None):
    for mesh, guide_data in mapping.items():
        if override_mesh:
            mesh = override_mesh

        for gde, settings in guide_data.items():
            if not pm.objExists(gde):
                pm.warning(f'Skipping {gde} from mapping, does not exist in scene!')
                continue
            gde = pm.PyNode(gde)
            pin_trns = []
            for uv in settings['pin_uvs']:
                u, v, face_id = uv
                trn = create_transform_at_uv(u, v, face_id, mesh, gde)
                pin_trns.append(trn)
            pm.pointConstraint(pin_trns[0], gde, w=settings['pin_params'][1])
            pm.pointConstraint(pin_trns[1], gde, w=settings['pin_params'][0])

            u, v, face_id = settings['up_uv']
            up_trn = create_transform_at_uv(u, v, face_id, mesh, gde)
            skip = []
            for ax in 'xyz':
                if gde.attr(f'r{ax}').get(l=True):
                    skip.append(ax)
            if len(skip) < 3:
                pm.aimConstraint(
                    pin_trns[0],
                    gde,
                    aim=settings['pin_vector'],
                    wut='object',
                    wuo=up_trn,
                    u=settings['up_vector'],
                    skip=skip
                )
            pm.delete(pin_trns, up_trn)


def create_transform_at_uv(u, v, face_id, mesh, gde):
    dag = OpenMaya.MSelectionList().add(mesh.name()).getDagPath(0)
    mfn = OpenMaya.MFnMesh(dag)
    try:
        pnt = mfn.getPointAtUV(face_id, u, v, OpenMaya.MSpace.kWorld)
    except RuntimeError:
        pm.warning(
            f'Unable to create transform at uv position {u}, {v} for {gde}. Using closest UV as fallback solution.'
        )
        uv_index = mfn.getClosestUVs(u, v)[0]
        pnt = OpenMaya.MPoint(pm.pointPosition(mesh.map[uv_index]))
        # pm.warning(f'Unable to create transform at uv position {u}, {v}. Using face center as fallback solution.')
        # face = mesh.f[face_id]
        # pnt = face.__apimfn__().center(OpenMaya.MSpace.kWorld)
    trn = connectutl.create_node('transform', tx=pnt.x, ty=pnt.y, tz=pnt.z)
    return trn


def load_guide_mapping(folder):
    import_path = get_json_path(folder)
    with open(import_path, 'r') as f:
        mapping = json.load(f)
    return mapping


def load_guide_mapping_for_mesh(mesh):
    description = get_name_description(mesh)
    try:
        mapping = get_json_path(folder=description)
    except errorutl.RbkInvalidName:
        pm.warning(f'Check name on {mesh}. Should be named after the folder in resources/guide_meshes. ')
        raise
    return mapping


def set_guide_mapping_to_selected_mesh():
    sel = pm.ls(sl=True)
    mesh = [a for a in sel if a.endswith('_PLY')][0]
    mapping = load_guide_mapping_for_mesh(mesh)
    set_guides_from_mapping(mapping=mapping, override_mesh=mesh)


def load_skin_for_mesh(mesh, folder=None):
    if folder:
        import_path = get_json_path(folder=folder, suffix='skin')
    else:
        import_path = get_json_path_for_mesh(mesh, suffix='skin')
    with open(import_path, 'r') as f:
        data = json.load(f)
    # for x in data['deformerWeight']['weights']:
    #     x['shape'] = mesh.getShape().name()
    # skinlib.create_skin_from_data(data)
    joint_names = skinlib.get_joint_names_from_skin_data(data)
    joints = skinlib.ensure_all_joints_exist(joint_names)

    try:
        skn = skinlib.get_skin(mesh)
        skinlib.ensure_skin_cluster_is_connected_to_all_joints(skn, joints)
    except errorutl.RbkNotFound:
        deformer_name = skinlib.get_deformer_name_from_skin_data(data)
        skn = pm.skinCluster(joints, mesh, tsb=True, n=deformer_name, weightDistribution=1)

    skinlib.apply_weights_from_file(import_path, skn)


def load_skin_for_selected_mesh():
    sel = pm.ls(sl=True)
    mesh = [a for a in sel if a.endswith('_PLY')][0]
    load_skin_for_mesh(mesh)
