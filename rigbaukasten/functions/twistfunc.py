import pymel.core as pm
from rigbaukasten.library import controllib, curvelib
from rigbaukasten.utils import mathutl, connectutl, attrutl


def straight_ikspline_twist(start_trn, end_trn, module_key, fwd_axis='x', up_axis='y', label='twist', nr_jnts=5):
    crv = curvelib.curve_from_transforms(trns=(start_trn, end_trn), name=f'{module_key}_{label}')
    length = crv.length()
    joints = []
    dist = length / (nr_jnts - 1)
    if fwd_axis.startswith('-'):
        dist *= -1
    for i in range(nr_jnts):
        jnt = pm.createNode('joint', n=f'{module_key}_{label}{i:02}_JNT', ss=True)
        if i:
            jnt.setParent(joints[-1])
            jnt.attr(f't{fwd_axis[-1]}').set(dist)
        joints.append(jnt)

    ikh = pm.ikHandle(
        sj=joints[0],
        ee=joints[-1],
        sol='ikSplineSolver',
        ccv=False,
        c=crv,
        n=f'{module_key}_{label}_IKH'
    )[0]
    ikh.dTwistControlEnable.set(True)
    ikh.dForwardAxis.set(['x', '-x', 'y', '-y', 'z', '-z'].index(fwd_axis))
    ikh.dWorldUpType.set(4)
    ikh.dWorldUpAxis.set(['y', '-y', '_', 'z', '-z', '_', 'x', '-x'].index(up_axis))
    ikh.dWorldUpVector.set(mathutl.vector_from_axis(up_axis))
    ikh.dWorldUpVectorEnd.set(mathutl.vector_from_axis(up_axis))
    start_trn.wm[0] >> ikh.dWorldUpMatrix
    end_trn.wm[0] >> ikh.dWorldUpMatrixEnd

    pm.hide(crv, ikh)
    return {'joints': joints, 'crv': crv, 'ikh': ikh}
