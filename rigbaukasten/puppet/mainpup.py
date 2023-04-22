import pymel.core as pm
from rigbaukasten.core import modulecor, iocor
from rigbaukasten.library import controllib, guidelib
from rigbaukasten.utils import attrutl, connectutl


class MainControl(modulecor.RigPuppetModule):
    def __init__(
            self,
            side='C',
            module_name='main',
            size=1,
            plumbob_hook=None
    ):
        super().__init__(side=side, module_name=module_name)
        self.size = size
        self.plumbob_hook = plumbob_hook

        self.plumbob_shp = None
        self.ctls = []
        self.global_scale_plug = None

    def create_joint(self):
        """ Create a joint in the origin. No guide for this joint, main CTL will always be in the origin """
        self.joints.append(
            pm.createNode('joint', n=self.mk('00_JNT'), p=self.get_asset_root_module().skel_grp)
        )
        self.joints[0].drawStyle.set(2)

    def create_ctl(self):
        main = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            ctl_shape='arrowBoldQuad',
            size=self.size,
            lock_attrs='v'
        )
        main.grp.setParent(self.in_hooks_grp)
        self.ctls.append(main)
        self.publish_nodes['ctls'].append(main.shp)

        if self.plumbob_hook:
            self.plumbob_shp = main.add_ctl_shape('diamond', 'plumbob', size=self.size * 0.15, color=23)
            self.publish_nodes['ctls'].append(self.plumbob_shp)
            asset_root = self.get_asset_root_module()
            model = pm.listRelatives(asset_root.geo_grp)
            if model:
                height = pm.exactWorldBoundingBox(model)[4] * 1.1
            else:
                height = self.size * 4
            pm.move(self.plumbob_shp.cv, 0, height, 0, r=True)

        sec = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label='01',
            ctl_shape='octagon',
            size=self.size * 0.5
        )
        sec.grp.setParent(main.trn)
        self.ctls.append(sec)
        self.publish_nodes['ctls'].append(sec.trn)

        for ctl in self.ctls:
            ctl.trn.rotateOrder.set(2)

    def constrain_joint(self):
        # pm.parentConstraint(self.ctls[-1].trn, self.joints[0])
        # pm.scaleConstraint(self.ctls[-1].trn, self.joints[0])
        self.ctls[-1].trn.wm[0] >> self.joints[0].offsetParentMatrix

    def add_attrs(self):
        attrutl.label_attr(self.ctls[0].trn, 'settings')
        self.global_scale_plug = attrutl.add(self.ctls[0].trn, 'globalScale', mn=0.001, default=1)

        mdt = attrutl.add_enum(
            self.ctls[0].trn,
            'modelDisplayType',
            enum_names=['normal', 'template', 'reference'],
            default=2
        )
        geo_grp = self.get_asset_root_module().geo_grp
        geo_grp.overrideEnabled.set(True)
        pm.connectAttr(mdt, geo_grp.overrideDisplayType)

        vis = attrutl.add(self.ctls[0].trn, 'showModel', typ='bool', default=True)
        attrutl.unlock(geo_grp.v)
        vis.connect(geo_grp.v)

        sdt = attrutl.add_enum(
            self.ctls[0].trn,
            'skeletonDisplayType',
            enum_names=['normal', 'template', 'reference'],
            default=2
        )
        skel_grp = self.get_asset_root_module().skel_grp
        skel_grp.overrideEnabled.set(True)
        pm.connectAttr(sdt, skel_grp.overrideDisplayType)

        skel_vis = attrutl.add(self.ctls[0].trn, 'showMainSkeleton', typ='bool', default=True)
        attrutl.unlock(skel_grp.v)
        skel_vis.connect(skel_grp.v)

        attrutl.add(self.ctls[0].trn, 'showHelperJoints', typ='bool', default=False)

    def connect_global_scale(self):
        for ax in 'XYZ':
            scale_plug = self.ctls[0].trn.attr(f'scale{ax}')
            self.global_scale_plug >> scale_plug
            scale_plug.set(l=True, k=False, cb=False)

    def connect_show_helper_joints_attr(self):
        mods_grp = self.get_asset_root_module().modules_grp
        jnts = pm.listRelatives(mods_grp, ad=True, type='joint')
        anim_crv = connectutl.driven_keys(
            driver=self.ctls[0].trn.showHelperJoints,
            driven=jnts[0].drawStyle,
            v=(2, 0),
            dv=(0, 1)
        )[0]
        for jnt in jnts[1:]:
            anim_crv.o >> jnt.drawStyle

    def connect_plumbob_to_hook(self):
        if self.plumbob_shp:
            hook = self.get_hook(self.plumbob_hook)
            cluster, handle = pm.cluster(self.plumbob_shp, n=self.mk('plumbob_CLS'))
            cluster.relative.set(True)
            pm.parent(handle, self.ctls[0].trn)
            pm.parentConstraint(hook, handle, mo=True)
            pm.scaleConstraint(hook, handle)
            pm.hide(handle)

    def out_hook(self, index):
        """ Return a transform that other modules can hook to. """
        return self.ctls[index].trn

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_joint()
        self.store_output_data(jnts=self.joints)

    def puppet_build(self):
        super().puppet_build()
        self.create_ctl()
        self.constrain_joint()
        self.store_output_data(ctls=[c.trn for c in self.ctls])
        self.add_attrs()
        self.connect_global_scale()

    def puppet_build_post(self):
        super().puppet_build_post()
        self.load_rigdata('ctls', False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_plumbob_to_hook()
        self.cleanup_joints(self.joints + self.puppet_joints)

    def puppet_connect_post(self):
        super().puppet_connect_post()
        self.connect_show_helper_joints_attr()
