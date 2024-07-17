import json
import pymel.core as pm

import os

import rigbaukasten
from rigbaukasten.utils import errorutl, attrutl


class AnimCtl(object):
    def __init__(
            self,
            side='C',
            module_name='myMod',
            label='00',
            suffix='CTL',
            ctl_shape='circle',
            pos=(0, 0, 0),
            rot=(0, 0, 0),
            lock_attrs=('sx', 'sy', 'sz', 'v'),
            color=None,
            size=1
    ):
        self.side = side
        self.module_name = module_name
        self.label = label
        self.suffix = suffix
        self.ctl_shape = ctl_shape
        self.pos = pos
        self.rot = rot
        self.lock_attrs = lock_attrs
        self.color = color or {'C': 17, 'L': 6, 'R': 13}[side]
        self.size = size

        self.trn = None
        self.grp = None
        self.shp = None

        self.run()

    def create_ctl(self):
        self.trn = create_curve(shape=self.ctl_shape, name=f'{self.side}_{self.module_name}_{self.label}_{self.suffix}')
        self.shp = self.trn.getShape()
        self.grp = pm.group(em=True, n=f'{self.side}_{self.module_name}_{self.label}Offset_GRP')
        self.trn.setParent(self.grp)  # important to create group empty at first, otherwise pivot might be off center

    def add_ctl_shape(self, shape, label, size=None, color=None):
        """ Add another shape node the the CTL.

            :param shape: str - name of the shape, must exist in resources/shapes
            :param label: str - label for the new shape (we cannot use self.label because the name must be unique)
            :param size: float - size of the new shape, if None will use self.size
            :param color: int - color of the new shape, if None will use self.color

            ATTENTION: If a ctl has multiple shapes, all shape nodes must be published separately. It's not enough to
                       add the ctl transform to RigModule.publish_nodes['ctls']. Instead don't add the transform and
                       add each shape node separately.
        """
        tmp = create_curve(shape=shape, name=f'{self.side}_{self.module_name}_{label}_{self.suffix}')
        shp = tmp.getShape()
        pm.parent(shp, self.trn, r=True, s=True)
        pm.delete(tmp)
        pm.scale(f'{shp}.cv[*]', size or self.size, size or self.size, size or self.size)
        shp.overrideEnabled.set(True)
        shp.overrideColor.set(color or self.color)
        return shp

    def place_ctl(self):
        if isinstance(self.pos, (pm.PyNode, str)):
            pos = pm.xform(self.pos, q=True, ws=True, t=True)
        else:
            pos = self.pos
        if isinstance(self.rot, (pm.PyNode, str)):
            rot = pm.xform(self.rot, q=True, ws=True, ro=True)
        else:
            rot = self.rot
        pm.xform(self.grp, ws=True, t=pos, ro=rot)

        pm.scale(f'{self.shp}.cv[*]', self.size, self.size, self.size)

    def set_color(self):
        self.shp.overrideEnabled.set(True)
        self.shp.overrideColor.set(self.color)

    def lock(self):
        attrutl.lock([self.trn.attr(attr) for attr in self.lock_attrs])

    def run(self):
        self.create_ctl()
        self.place_ctl()
        self.lock()
        self.set_color()


def get_ctl_shape_data(ctl):
    if isinstance(ctl, AnimCtl):
        ctl = ctl.shp
    elif isinstance(ctl, pm.nt.Transform):
        ctl = ctl.getShape()
    reset_plugs = {}
    for deformer in pm.findDeformers(ctl) or []:
        deformer = pm.PyNode(deformer)
        reset_plugs[deformer.en] = deformer.en.get()
        deformer.en.set(0)  # make sure we only read the local point data and not some deformed result (e.g. plumbob)
    data = {
        'degree': ctl.degree(),
        'positions': [list(pnt) for pnt in ctl.getCVs()],
        'spans': ctl.spans.get(),
        'form': int(ctl.form()),
        'color': ctl.overrideColor.get() if ctl.overrideEnabled.get() else None
    }
    for plug, value in reset_plugs.items():
        plug.set(value)
    return data


def set_ctl_shape_data(ctl, data):
    if isinstance(ctl, AnimCtl):
        ctl = ctl.shp
    elif isinstance(ctl, pm.nt.Transform):
        ctl = ctl.getShape()
    if int(ctl.form()) != data['form']:
        pm.closeCurve(ctl, ch=False, replaceOriginal=True)
    pm.rebuildCurve(ctl, spans=data['spans'], degree=data['degree'], ch=False, replaceOriginal=True)
    ctl.setCVs(data['positions'])
    ctl.updateCurve()
    if data.get('color') is not None:
        ctl.overrideColor.set(data['color'])


def set_ctl_shape(ctl, shape):
    j = get_shape_json(shape)
    with open(j, 'r') as f:
        data = json.load(f)
    set_ctl_shape_data(ctl, data)


def create_curve(shape, name):
    crv = pm.curve(n=name, p=((0, 0, 0), (0, 1, 0), (0, 2, 0)), d=1)
    set_ctl_shape(ctl=crv, shape=shape)
    return crv


def get_available_shapes():
    """ Get a list of all available ctl shapes.
    :return: (list) names of all available ctl shapes
    """
    shapes_jsons = os.listdir(rigbaukasten.environment.get_resources_path('shapes'))
    available_shapes = [j.replace('.json', '') for j in shapes_jsons if j.endswith('.json')]
    return available_shapes


def get_shape_json(shape):
    shape_path = os.path.join(rigbaukasten.environment.get_resources_path('shapes'), f'{shape}.json')
    if not os.path.exists(shape_path):
        available = get_available_shapes()
        raise errorutl.RbkInvalidName(f'Given ctl_shape "{shape}" is unknown. Use one of {available}')
    return shape_path


def store_selected_curve_shape():
    """ Store the selected curve(s) as ctl shape json. """
    crvs = pm.ls(sl=True)
    for crv in crvs:
        shape = crv.getShape()
        if not pm.objectType(shape) == 'nurbsCurve':
            raise errorutl.RbkNotFound('Must select nurbs curve(s)!')
    for crv in crvs:
        message = f'Store curve shape as "{crv}"?\n\n'
        if crv in get_available_shapes():
            message += 'WARNING: This will overwrite an existing shape!\n'
        if '_' in crv:
            message += 'WARNING: Curve name should be lowerCamelCase!\n'
        if pm.confirmDialog(
                title='Export CTL shape',
                message=message,
                button=("Yes", "No"),
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No"
        ) == 'Yes':
            data = get_ctl_shape_data(crv)
            file_path = os.path.join(rigbaukasten.environment.get_resources_path('shapes'), f'{crv}.json')
            with open(file_path, 'w') as f:
                json.dump(data, f)
            print(f'Exported to: {file_path}')
        else:
            print(f'Shape "{crv}" not exported, canceled by user!')


def mirror_side_control(ctl):
    """
    Mirror the point positions of the given ctls CVs to its counterpart on the other side.
    :param ctl: control to mirror (transform node)
    """
    if not str(ctl)[0:2] in 'L_R_':
        raise errorutl.RbkInvalidName('Cannot mirror this control. Only "L_" or "R_" controls are valid!')
    other_ctl = str(ctl).replace('L_', 'X_', 1).replace('R_', 'L_', 1).replace('X_', 'R_', 1)
    if pm.objExists(other_ctl):
        other_ctl = pm.PyNode(other_ctl)
    else:
        raise errorutl.RbkInvalidName(f'The given control has no equivalent on the other side: "{other_ctl}" not found')

    data = get_ctl_shape_data(ctl)
    data['color'] = None
    set_ctl_shape_data(other_ctl, data)
    positions = [(-p[0], p[1], p[2]) for p in ctl.getCVs('world')]
    other_ctl.setCVs(positions, 'world')

    return other_ctl
