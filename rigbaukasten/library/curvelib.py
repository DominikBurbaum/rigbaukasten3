import pymel.core as pm

from rigbaukasten.utils import connectutl


def curve_from_transforms(trns, name='C_mod_0', d=1):
    crv = pm.curve(p=[(0, 0, 0) for _ in trns], n=f'{name}_CRV', d=d)
    for i, trn in enumerate(trns):
        connectutl.create_node(
            'decomposeMatrix',
            inputMatrix=trn.wm[0],
            outputTranslate='->' + crv.controlPoints[i].name(),
            n=f'{name}cv{i:02}_DCM'
        )
    return crv
