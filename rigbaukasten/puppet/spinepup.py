import pymel.core as pm
from rigbaukasten.core import modulecor, iocor
from rigbaukasten.functions import chainfunc
from rigbaukasten.library import controllib, jointlib, guidelib
from rigbaukasten.utils import attrutl


class Spine(modulecor.RigPuppetModule):
    def __init__(
            self,
            side='C',
            module_name='spine',
            size=1,
            nr_of_joints=5,
            hook=None,
            parent_joint=None
    ):
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.nr_of_joints = nr_of_joints

        self.ctls = []
        self.root_ctl = None
        self.ik_ctls = []
        self.fk_ctls = None
        self.fk_ik_plug = None
        self.fk_ik_rvs_plug = None
        self.fk_joints = None
        self.ik_joints = None
        self.ik_crv = None
        self.ikh = None

    # ---------------------- Skeleton ---------------------- #

    def create_guides(self):
        positions = [(0, i * (self.size / (self.nr_of_joints - 1)), 0) for i in range(self.nr_of_joints)]
        asset_root = self.get_asset_root_module()
        model = pm.listRelatives(asset_root.geo_grp)
        if model:
            height = pm.exactWorldBoundingBox(model)[4]
            hip = height * 0.5
            length = height * 0.2
            positions = [(0, hip + (i * (length / (self.nr_of_joints - 1))), 0) for i in range(self.nr_of_joints)]

        guide_chain = guidelib.create_oriented_guide_chain(
            side=self.side,
            module_name=self.module_name,
            labels=[f'{i:02d}' for i in range(self.nr_of_joints)],
            size=self.size,
            positions=positions,
            aim=(0, 1, 0),
            up=(1, 0, 0),
            world_up=(1, 0, 0),
            world_up_type=guidelib.WORLD_AXIS,
        )
        self.joints = guide_chain.joints
        self.joints[0].setParent(asset_root.skel_grp)
        guide_chain.grp.setParent(self.guides_grp)

        self.publish_nodes['guides'] += guide_chain.guides

    # ---------------------- Puppet ---------------------- #

    def create_root_ctl(self):
        self.root_ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label='root',
            ctl_shape='hexagon',
            size=self.size * 1.4,
            pos=self.puppet_joints[0],
            rot=self.puppet_joints[0]
        )
        self.root_ctl.grp.setParent(self.in_hooks_grp)
        self.ctls.append(self.root_ctl)
        self.publish_nodes['ctls'].append(self.root_ctl.trn)
        self.root_ctl.trn.rotateOrder.set(2)

    def duplicate_fkik_joints(self):
        attrutl.label_attr(self.root_ctl.trn, 'settings')
        self.fk_ik_plug = attrutl.add(self.root_ctl.trn, attr_name='fk_ik', mn=0, mx=1)
        self.fk_joints, self.ik_joints = jointlib.fk_ik_joints(
            joints=self.puppet_joints,
            fk_ik_plug=self.fk_ik_plug,
        )
        pm.parent(self.ik_joints[0], self.fk_joints[0], self.static_grp)
        rvs = self.fk_ik_plug.outputs(type='reverse')[0]
        self.fk_ik_rvs_plug = rvs.outputX

    def create_fk_setup(self):
        self.fk_ctls = chainfunc.fk_chain_from_joints(joints=self.fk_joints, label='', size=self.size)
        self.ctls += self.fk_ctls
        self.publish_nodes['ctls'] += [ctl.trn for ctl in self.fk_ctls]
        self.fk_ctls[0].grp.setParent(self.root_ctl.trn)

    def create_ik_setup(self):
        self.ik_ctls, self.ik_crv, self.ikh = chainfunc.simple_spline_ik_from_joints(
            joints=self.ik_joints,
            label='',
            size=self.size,
            fwd_axis='y',
            up_axis='x'
        )
        self.ctls += self.ik_ctls
        self.publish_nodes['ctls'] += [ctl.trn for ctl in self.ik_ctls]
        for ctl in self.ik_ctls:
            ctl.grp.setParent(self.root_ctl.trn)
        self.ik_crv.setParent(self.static_grp)
        self.ikh.setParent(self.static_grp)

    def fk_ik_visibility(self):
        for ctl in self.fk_ctls:
            self.fk_ik_rvs_plug >> ctl.grp.v
        self.fk_ik_rvs_plug >> self.fk_joints[0].v
        for ctl in self.ik_ctls:
            self.fk_ik_plug >> ctl.grp.v
        self.fk_ik_plug >> self.ik_joints[0].v

    def compose_output_ctls_dict(self):
        output_ctls = {'root': self.root_ctl.trn}
        for i, fk in enumerate(self.fk_ctls):
            output_ctls[f'fk{i}'] = fk.trn
        for i, ik in enumerate(self.ik_ctls):
            output_ctls[f'ik{i}'] = ik.trn
        return output_ctls

    def connect_to_hook(self):
        self.constraint_to_hook(self.root_ctl.grp)
        # if self.hook:
        #     mod, index = self.hook
        #     hook = mod.out_hook(index)
        #     # hook.wm[0] >> self.root_ctl.grp.offsetParentMatrix
        #     pm.parentConstraint(hook, self.root_ctl.grp, mo=True)
        #     pm.scaleConstraint(hook, self.root_ctl.grp)

    def out_hook(self, index):
        return self.puppet_joints[index]

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
        self.create_root_ctl()
        self.duplicate_fkik_joints()
        self.create_ik_setup()
        self.create_fk_setup()
        self.fk_ik_visibility()
        self.store_output_data(ctls=self.compose_output_ctls_dict())

    def puppet_build_post(self):
        super().puppet_build_post()
        self.load_rigdata('ctls', False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_to_hook()
        self.connect_puppet_joints()
        self.cleanup_joints(self.joints + self.puppet_joints + self.fk_joints + self.ik_joints)

    def finalize(self):
        super().finalize()
        self.delete_guides()
