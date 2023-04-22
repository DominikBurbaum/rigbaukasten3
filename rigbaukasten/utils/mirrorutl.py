import pymel.core as pm

from rigbaukasten.utils import errorutl, pythonutl


def get_mirror_transform(trn):
    if trn.startswith('C_'):
        raise errorutl.RbkInvalidName(f'{trn} cannot be mirrored, only L_ & R_ transforms are allowed.')
    other = trn.name().replace('L_', 'XXX_').replace('R_', 'L_').replace('XXX_', 'R_')
    if pm.objExists(other):
        return pm.PyNode(other)
    else:
        raise errorutl.RbkNotFound(f"Couldn't find {other} when trying to mirror {trn}")


def world_mirror_pos(transforms, mirror_axis='x'):
    if mirror_axis.lower() not in 'xyz':
        raise errorutl.RbkInvalidKeywordArgument(f'mirror_axis {mirror_axis} is invalid, need one of x, y, z')
    transforms = pythonutl.force_list(transforms)
    index = 'xyz'.index(mirror_axis.lower())
    for trn in transforms:
        other = get_mirror_transform(trn)
        pos = trn.getTranslation('world')
        pos[index] *= -1
        other.setTranslation(pos, 'world')


def world_mirror_rot(transforms, mirror_axis='x', keep_axis='y'):
    if mirror_axis.lower() not in 'xyz':
        raise errorutl.RbkInvalidKeywordArgument(f'mirror_axis {mirror_axis} is invalid, need one of x, y, z')
    if keep_axis.lower() not in [None, 'none', 'x', 'y', 'z', 'all']:
        raise errorutl.RbkInvalidKeywordArgument(f"keep_axis {mirror_axis} is invalid, need one of None, x, y, z, all")
    transforms = pythonutl.force_list(transforms)
    for trn in transforms:
        other = get_mirror_transform(trn)

        mtx = trn.wm[0].get()
        other_mtx = other.wm[0].get()

        x_vec, y_vec, z_vec, _ = mtx
        t_vec = other_mtx[3]

        index = 'xyz'.index(mirror_axis.lower())
        x_vec[index] *= -1
        y_vec[index] *= -1
        z_vec[index] *= -1

        if keep_axis.lower() in ['y', 'z', 'all']:
            x_vec[0] *= -1
            x_vec[1] *= -1
            x_vec[2] *= -1

        if keep_axis.lower() in ['x', 'z', 'all']:
            y_vec[0] *= -1
            y_vec[1] *= -1
            y_vec[2] *= -1

        if keep_axis.lower() in ['x', 'y', 'all']:
            z_vec[0] *= -1
            z_vec[1] *= -1
            z_vec[2] *= -1

        # if keep_axis == 'x':
        #     y_vec[0] *= -1
        #     y_vec[1] *= -1
        #     y_vec[2] *= -1
        #     z_vec[0] *= -1
        #     z_vec[1] *= -1
        #     z_vec[2] *= -1
        #
        # if keep_axis == 'y':
        #     x_vec[0] *= -1
        #     x_vec[1] *= -1
        #     x_vec[2] *= -1
        #     z_vec[0] *= -1
        #     z_vec[1] *= -1
        #     z_vec[2] *= -1
        #
        # if keep_axis == 'z':
        #     x_vec[0] *= -1
        #     x_vec[1] *= -1
        #     x_vec[2] *= -1
        #     y_vec[0] *= -1
        #     y_vec[1] *= -1
        #     y_vec[2] *= -1

        mirror_mat = pm.datatypes.Matrix(x_vec, y_vec, z_vec, t_vec)

        other.setTransformation(mirror_mat)


def world_mirror(trns, pos=True, rot=True, mirror_axis='x', keep_axis='all'):
    if not trns:
        trns = pm.ls(sl=True, type='transform')
    if pos:
        world_mirror_pos(transforms=trns, mirror_axis=mirror_axis)
    if rot:
        world_mirror_rot(transforms=trns, mirror_axis=mirror_axis, keep_axis=keep_axis)
