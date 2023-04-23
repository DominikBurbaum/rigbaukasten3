import pymel.core as pm

from rigbaukasten.utils import attrutl, errorutl


def axis_reader(read_trn, reference_trn, module_key, label, buffer=True):
    """
        Create an axis reader to read rotation values from a transform.
        The calculated values will always be between -180 and 180 degrees. There won't be any gimbal flips.
        :param read_trn: The transform node from which you want to read rotations
        :param reference_trn: The transform node to use as space reference, usually the parent.
        :param module_key: <side>_<module_name> key for naming stuff
        :param label: additional label for naming stuff
        :param buffer: Create a buffer transform node, so the default output is (0, 0, 0).
        :return: [attrX, attrY, attrZ]
        """
    attr_name = f'poseRead_{reference_trn.name()}'
    if buffer:
        attr_name = f'{attr_name}_buffered'
    if hasattr(read_trn, attr_name + 'X'):
        return [read_trn.attr(attr_name + xyz) for xyz in 'XYZ']

    mmx = pm.createNode('multMatrix', n=f'{module_key}_{label}_MMX')
    read_trn.wm[0] >> mmx.matrixIn[0]
    if buffer:
        buffer_trn = pm.group(em=True, p=reference_trn, n=f'{module_key}_{label}Buffer_TRN')
        pm.delete(pm.parentConstraint(read_trn, buffer_trn))
        buffer_trn.wim[0] >> mmx.matrixIn[1]
    else:
        reference_trn.wim[0] >> mmx.matrixIn[1]

    dcm = pm.createNode('decomposeMatrix', n=f'{module_key}_{label}_DCM')
    mmx.matrixSum >> dcm.inputMatrix

    output_plugs = []
    for ax in 'XYZ':
        qte = pm.createNode('quatToEuler', n=f'{module_key}_{label}{ax}_QTE')
        dcm.attr(f'outputQuat{ax}') >> qte.attr(f'inputQuat{ax}')
        dcm.outputQuatW >> qte.inputQuatW
        if ax == 'Y':
            # keep outputs inbetween -180 and 180
            adl = pm.createNode('addDoubleLinear', n=f'{module_key}_{label}ClampTo180_ADL')
            qte.outputRotateY >> adl.i1
            adl.i2.set(-360)
            cnd = pm.createNode('condition', n=f'{module_key}_{label}ClampTo180_CND')
            cnd.operation.set(2)
            qte.outputRotateY >> cnd.firstTerm
            cnd.secondTerm.set(180)
            qte.outputRotateY >> cnd.colorIfFalseR
            adl.o >> cnd.colorIfTrueR
            pm.addAttr(read_trn, ln=f'{attr_name}{ax}', pxy=cnd.outColorR)
        else:
            pm.addAttr(read_trn, ln=f'{attr_name}{ax}', pxy=qte.attr(f'outputRotate{ax}'))
        output_plugs.append(read_trn.attr(f'{attr_name}{ax}'))

    return output_plugs


def update_axis_reader_buffer(reader_output):
    """  """
    y_output = reader_output[1]
    if not y_output.name().endswith('_bufferedY'):
        raise errorutl.RbkValueError('given axis reader is not buffered')
    cnd = y_output.connections(s=1, d=0)[0]
    buffer = pm.PyNode(cnd.name().replace('poseClampTo180', 'poseBuffer').replace('_CND', '_TRN'))
    pm.delete(pm.parentConstraint(y_output.node(), buffer))
