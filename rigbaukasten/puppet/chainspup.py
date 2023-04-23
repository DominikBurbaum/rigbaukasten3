from rigbaukasten.core import modulecor
import pymel.core as pm

from rigbaukasten.functions import chainfunc
from rigbaukasten.library import controllib, guidelib, jointlib


class SingleCtl(modulecor.RigPuppetModule):
    def __init__(
            self,
            side,
            module_name,
            size=1,
            hook=None,
            with_joint=True,
            lock_attrs=('sx', 'sy', 'sz', 'v'),
            parent_joint=None
    ):
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.lock_attrs = lock_attrs
        self.with_joint = with_joint

        self.ctls = []
        self.gde = None

    # ---------------------- Skeleton ---------------------- #

    def create_joint(self):
        jnt = pm.createNode('joint', p=self.get_asset_root_module().skel_grp, n=f'{self.module_key}_00_JNT')
        self.joints = [jnt]
        jnt.displayLocalAxis.set(True)

    def create_guides(self):
        self.gde = guidelib.create_guide(self.side, self.module_name, '00', self.size)
        self.publish_nodes['guides'] += [self.gde]
        pm.parent(self.gde, self.guides_grp)

    def connect_joints_to_guides(self):
        pm.parentConstraint(self.gde, self.joints[0])

    def hide_guides(self):
        self.guides_grp.v.set(False)

    # ---------------------- Puppet ---------------------- #

    def create_ctl(self):
        ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            ctl_shape='circle',
            size=self.size,
            lock_attrs=self.lock_attrs,
            pos=self.puppet_joints[0] if self.with_joint else self.gde,
            rot=self.puppet_joints[0] if self.with_joint else self.gde
        )
        ctl.grp.setParent(self.in_hooks_grp)
        self.ctls.append(ctl)
        self.publish_nodes['ctls'].append(ctl.trn)

    def connect_to_joint(self):
        if self.with_joint:
            pm.parentConstraint(self.ctls[0].trn, self.puppet_joints[0], mo=True)
            pm.scaleConstraint(self.ctls[0].trn, self.puppet_joints[0])

    def connect_to_hook(self):
        self.constraint_to_hook(self.ctls[0].grp)

    def out_hook(self, _):
        """ Return a transform that other modules can hook to. """
        return self.ctls[0].trn

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_guides()
        if self.with_joint:
            self.create_joint()
            self.store_output_data(jnts=self.joints)
            self.connect_joints_to_guides()

    def skeleton_build_post(self):
        super().skeleton_build_post()
        self.load_rigdata('guides', False)

    def skeleton_connect(self):
        super().skeleton_connect()
        if self.with_joint:
            self.free_joints_from_guides()
            self.connect_to_main_skeleton()
        else:
            self.hide_guides()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_joints()
        self.create_ctl()
        self.connect_to_joint()
        self.store_output_data(ctls=[c.trn for c in self.ctls])

    def puppet_build_post(self):
        super().puppet_build_post()
        self.load_rigdata('ctls', False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_to_hook()
        if self.with_joint:
            self.connect_puppet_joints()
            self.cleanup_joints(self.joints + self.puppet_joints)

    def finalize(self):
        super().finalize()
        self.delete_guides()


class SimpleFk(modulecor.RigPuppetModule):
    def __init__(
            self,
            side,
            module_name,
            nr_of_joints,
            size=1,
            joint_labels=None,
            hook=None,
            aim=(1, 0, 0),
            up=(0, 1, 0),
            world_up=(0, 1, 0),
            world_up_type=guidelib.WORLD_AXIS,
            flip_right_vectors=True,
            tip_joint_aim=False,
            tip_has_ctl=True,
            lock_attrs=('sx', 'sy', 'sz', 'v'),
            parent_joint=None,
    ):
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.nr_of_joints = nr_of_joints
        self.joint_labels = joint_labels or [f'{i:02d}' for i in range(self.nr_of_joints)]
        self.aim = aim
        self.up = up
        self.world_up = world_up
        self.world_up_type = world_up_type
        self.flip_right_vectors = flip_right_vectors
        self.tip_joint_aim = tip_joint_aim
        self.tip_has_ctl = tip_has_ctl
        self.lock_attrs = lock_attrs

        self.guides = []
        self.ctls = []

    # ---------------------- Skeleton ---------------------- #

    def create_guides(self):
        guide_chain = guidelib.create_oriented_guide_chain(
            side=self.side,
            module_name=self.module_name,
            labels=self.joint_labels,
            size=self.size,
            aim=self.aim,
            up=self.up,
            world_up=self.world_up,
            world_up_type=self.world_up_type,
            flip_right_vectors=self.flip_right_vectors,
            tip_joint_aim=self.tip_joint_aim
        )
        self.joints = guide_chain.joints
        self.joints[0].setParent(self.get_asset_root_module().skel_grp)
        guide_chain.grp.setParent(self.guides_grp)

        self.publish_nodes['guides'] += guide_chain.guides
        self.guides += guide_chain.guides

    # ---------------------- Puppet ---------------------- #

    def create_fk_setup(self):
        ctl_joints = self.puppet_joints
        if not self.tip_has_ctl and self.nr_of_joints > 1:
            ctl_joints = self.puppet_joints[:-1]
        self.ctls = chainfunc.fk_chain_from_joints(
            joints=ctl_joints,
            label='',
            size=self.size,
            lock_attrs=self.lock_attrs
        )
        self.ctls[0].grp.setParent(self.in_hooks_grp)
        self.publish_nodes['ctls'] += [ctl.trn for ctl in self.ctls]
        for ctl in self.ctls:
            if self.aim == (1, 0, 0):
                pm.rotate(ctl.shp.cv, 0, 0, 90, r=True)
            elif self.aim == (0, 0, 1):
                pm.rotate(ctl.shp.cv, 90, 0, 0, r=True)

    def connect_to_hook(self):
        self.constraint_to_hook(self.ctls[0].grp)

    def out_hook(self, index):
        """ Return a transform that other modules can hook to. """
        return self.ctls[index].trn

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_guides()
        self.store_output_data(jnts=self.joints)

    def skeleton_build_post(self):
        super().skeleton_build_post()
        self.load_rigdata('guides', False)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.free_joints_from_guides()
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_joints()
        self.create_fk_setup()
        self.store_output_data(ctls=[c.trn for c in self.ctls])

    def puppet_build_post(self):
        super().puppet_build_post()
        self.load_rigdata('ctls', False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_to_hook()
        self.connect_puppet_joints()
        self.cleanup_joints(self.joints + self.puppet_joints)

    def finalize(self):
        super().finalize()
        self.delete_guides()
