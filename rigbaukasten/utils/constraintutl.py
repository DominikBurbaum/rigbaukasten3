import pymel.core as pm

from rigbaukasten.utils import errorutl


def get_driven_obj(constraint):
    """
    get the object that is driven by the constraint
    :param constraint: PyNode - the constraint
    :return: PyNode - driven object
    """
    return constraint.constraintParentInverseMatrix.listConnections(source=True, destination=False)[0]


def get_drivers(constraint):
    """
    get the driver objects of the constraint
    :param constraint: PyNode - the constraint
    :return: [PyNode, ] - list of drivers
    """
    drivers = []
    i = 0
    while True:
        driver = constraint.tg[i].tpm.listConnections(source=True, destination=False)
        if driver:
            drivers.append(driver[0])
            i += 1
        else:
            break
    return drivers


def get_weights(constraint):
    """
    get the weights of the constraint
    :param constraint: PyNode - the constraint
    :return: [float, ] - list of weights in order
    """
    weights = []
    i = 0
    while True:
        try:
            weights.append(constraint.attr(f'w{i}').get())
            i += 1
        except pm.general.MayaAttributeError:
            break
    return weights


def get_constraint_data(constraints):
    """ Compose a dict for constraint rigdata publish
    :param constraints: [PyNode, ] - list of constraints to read
    :return dict - the constraint data
    """
    data = {}
    supported_types = ('parentConstraint', 'scaleConstraint', 'pointConstraint', 'orientConstraint')
    for constraint in constraints:
        if pm.objectType(constraint) not in supported_types:
            raise errorutl.RbkInvalidObjectError(f'Cannot generate data for "{constraint}", type not supported.')
        driven = get_driven_obj(constraint)
        drivers = get_drivers(constraint)
        weights = get_weights(constraint)
        typ = pm.objectType(constraint)
        tmp = {'drivers': drivers, 'weights': weights, 'type': typ}
        if data.get(driven):
            data[driven].append(tmp)  # multiple constraints on the same object
        else:
            data[driven] = [tmp]
    return data


def create_constraints_from_data(data):
    for driven, dataList in data.items():
        if not pm.objExists(driven):
            pm.warning('Cannot create constraint, object missing: %s' % driven)
            continue
        for data in dataList:
            if not min([pm.objExists(a) for a in data['drivers']]):
                pm.warning(
                    'Cannot create constraint, one or more drivers missing: %s' % ','.join(data['drivers'])
                )
                continue
            constraints = {
                'pointConstraint': pm.pointConstraint,
                'orientConstraint': pm.orientConstraint,
                'parentConstraint': pm.parentConstraint,
                'scaleConstraint': pm.scaleConstraint,
             }
            create_constraint = constraints.get(data['type'])
            for driver, w in zip(data['drivers'], data['weights']):
                con = create_constraint(driver, driven, w=w, mo=True)[0]
                if pm.objExists(f'{con}.interpType'):
                    con.interpType.set(2)
