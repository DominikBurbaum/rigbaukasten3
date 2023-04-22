from rigbaukasten.core import modulecor, iocor
import pymel.core as pm

from rigbaukasten.functions import chainfunc
from rigbaukasten.library import controllib, curvelib, guidelib


class AimCtl(modulecor.RigPuppetModule):
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            end_hook=None,
            size=1,
            twist=False,
            parent_joint=None
    ):
        """

        :param side:
        :param module_name:
        :param hook:
        :param size:
        :param twist: Use aim CTL as up object instead of hook.
        """
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.end_hook = end_hook
        self.twist = twist

        self.center_gde = None
        self.aim_gde = None
        self.center_ctl = None
        self.aim_ctl = None

    # ---------------------- Skeleton ---------------------- #

    def create_joint(self):
        jnt = pm.createNode('joint', p=self.grp, n=f'{self.module_key}_00_JNT')
        self.joints.append(jnt)
        jnt.displayLocalAxis.set(True)
        jnt.setParent(self.get_asset_root_module().skel_grp)

    def create_guides(self):
        self.center_gde = guidelib.create_guide(self.side, self.module_name, 'Center', self.size)
        self.aim_gde = guidelib.create_guide(self.side, self.module_name, 'aim', self.size)
        self.aim_gde.tx.set(self.size * 3)
        self.publish_nodes['guides'] += [self.center_gde, self.aim_gde]
        pm.parent(self.center_gde, self.aim_gde, self.guides_grp)

        pm.pointConstraint(self.center_gde, self.joints[0])
        pm.aimConstraint(
            self.aim_gde,
            self.joints[0],
            wut='objectrotation',
            wuo=self.aim_gde if self.twist else self.center_gde
        )
        crv = curvelib.curve_from_transforms(
            trns=(self.center_gde, self.aim_gde),
            name=f'{self.module_key}_guideAim_CRV'
        )
        crv.inheritsTransform.set(False)
        crv.setParent(self.guides_grp)
        crv.template.set(True)

    # ---------------------- Puppet ---------------------- #

    def create_ctls(self):
        self.center_ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label='center',
            ctl_shape='arrowBold',
            size=self.size,
            pos=self.puppet_joints[0],
            rot=self.puppet_joints[0]
        )
        self.center_ctl.grp.setParent(self.in_hooks_grp)
        self.publish_nodes['ctls'].append(self.center_ctl.trn)

        self.aim_ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label='aim',
            ctl_shape='circle',
            size=self.size,
            pos=self.aim_gde,
            rot=self.aim_gde
        )
        self.aim_ctl.grp.setParent(self.in_hooks_grp)
        self.publish_nodes['ctls'].append(self.aim_ctl.trn)

    def setup_aim(self):
        grp = pm.group(self.center_ctl.trn, p=self.center_ctl.grp, n=f'{self.module_key}_centerAim_GRP')
        pm.aimConstraint(
            self.aim_ctl.trn,
            grp,
            wut='objectrotation',
            wuo=self.aim_ctl.trn if self.twist else self.center_ctl.grp
        )
        crv = curvelib.curve_from_transforms(
            trns=(self.center_ctl.trn, self.aim_ctl.trn),
            name=f'{self.module_key}_connector_CRV'
        )
        # crv.inheritsTransform.set(False)
        crv.setParent(self.static_grp)
        crv.template.set(True)

    def connect_to_joint(self):
        pm.parentConstraint(self.center_ctl.trn, self.puppet_joints[0], mo=True)
        pm.scaleConstraint(self.center_ctl.trn, self.puppet_joints[0])

    def connect_to_hook(self):
        self.constraint_to_hook(self.center_ctl.grp)
        self.constraint_to_hook(self.aim_ctl.grp, hook=self.end_hook)
        # if self.hook:
        #     mod, index = self.hook
        #     hook = mod.out_hook(index)
        #     pm.parentConstraint(hook, self.center_ctl.grp, mo=True)
        #     pm.scaleConstraint(hook, self.center_ctl.grp)
        # if self.end_hook:
        #     mod, index = self.end_hook
        #     end_hook = mod.out_hook(index)
        #     pm.parentConstraint(end_hook, self.aim_ctl.grp, mo=True)
        #     pm.scaleConstraint(end_hook, self.aim_ctl.grp)

    def out_hook(self, index):
        """ Return a transform that other modules can hook to. """
        return [self.center_ctl.trn, self.aim_ctl.trn][index]

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_joint()
        self.store_output_data(jnts=self.joints)
        self.create_guides()

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
        self.create_ctls()
        self.store_output_data(ctls=[self.center_ctl.trn, self.aim_ctl.trn])
        self.setup_aim()
        self.connect_to_joint()

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
