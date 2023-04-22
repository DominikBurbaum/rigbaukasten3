import pymel.core as pm

from rigbaukasten.utils import attrutl


def add_spaces(ctl, default_target=None, constraint=pm.parentConstraint, **spaces):
    """ Add space switches to the given ctl by creating a group with a blended constraint above it.

        :param ctl: PyNode, the ctl that should get the space switch
        :param default_name: str, name of the space target that should be active by default. All other targets
                            will be inactive. If the given name does not exist in 'spaces', the first given
                            space will be used as default.
        :param constraint: type, type of constraint to use, pm.pointConstraint, pm.orientConstraint, [...]
        :param spaces: PyNode, transform nodes that are used as space targets. E.g. main=PyNode('C_main_00_CTL')
    """
    if default_target not in spaces.values():
        default_target = spaces.values()[0]
    ctl_parent = ctl.getParent()
    space_grp = pm.duplicate(ctl, po=True, n=ctl.replace('_CTL', 'SpaceSwitch_GRP'))[0]
    attrutl.unlock_transforms(space_grp)
    ctl.setParent(space_grp)
    attrutl.label_attr(ctl, 'spaces')
    for name, trn in spaces.items():
        default = trn == default_target
        if trn is None:
            trn = ctl_parent
        tgt = pm.duplicate(ctl, po=True, n=ctl.replace('_CTL', f'SpaceTaret{name}_TRN'))[0]
        attrutl.unlock_transforms(tgt)
        tgt.setParent(trn)
        plug = attrutl.add(ctl, name, mn=0, mx=1, default=default)
        con = constraint(tgt, space_grp, mo=True, n=ctl.replace('_CTL', 'SpaceSwitch_PAC'))
        plug >> constraint(con, q=True, wal=True)[-1]
