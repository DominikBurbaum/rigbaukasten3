import pymel.core as pm

from rigbaukasten.core import modulecor, iocor
from rigbaukasten.functions import chainfunc, twistfunc
from rigbaukasten.library import controllib, jointlib, posereaderlib, guidelib, curvelib
from rigbaukasten.utils import attrutl, connectutl


class FKIkLimb(modulecor.RigPuppetModule):
    def __init__(
            self,
            side='L',
            module_name='arm',
            size=1,
            hook=None,
            ik_hook=None,
            collision_spread=0,
            as_leg=False,
            with_foot=False,
            parent_joint=None
    ):
        """

        :param side:
        :param module_name:
        :param size:
        :param hook:
        :param ik_hook:
        :param collision_spread: cheap double knee/elbow effect, push the lower twist joint chain away from the hinge.
        :param segment_names:
        """
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.ik_hook = ik_hook
        self.collision_spread = collision_spread
        self.as_leg = as_leg
        if as_leg:
            self.segment_names = ['hip', 'thigh', 'knee', 'ankle']
            if with_foot:
                self.segment_names += ['footBall', 'footTip']
        else:
            self.segment_names = ('clavicle', 'shoulder', 'elbow', 'wrist')
        self.with_foot = with_foot

        self.pole_position_trn = None
        self.position_trns = {}
        self.root_hook_grp = None
        self.end_hook_grp = None
        self.root_ctl = None
        self.ik_ctls = []
        self.fk_ctls = None
        self.twist_ctls = []
        self.foot_ctl = None
        self.ikh = None
        self.fk_ik_plug = None
        self.fk_ik_rvs_plug = None
        self.fk_joints = None
        self.ik_joints = None
        self.upper_twist_joints = []
        self.lower_twist_joints = []
        self.collision_spread_trn = None

    # ---------------------- Skeleton ---------------------- #

    def get_limb_positions(self):
        asset_root = self.get_asset_root_module()
        model = pm.listRelatives(asset_root.geo_grp)
        if model:
            height = pm.exactWorldBoundingBox(model)[4]
        else:
            height = self.size * 10
        hip = height * 0.5
        shoulder = height * 0.8
        if self.as_leg:
            positions = [
                (hip * 0.05 * self.inv, hip, 0),
                (hip * 0.15 * self.inv, hip, 0),
                (hip * 0.15 * self.inv, hip * 0.55, hip * 0.1),
                (hip * 0.15 * self.inv, hip * 0.1, 0)
            ]
            if self.with_foot:
                positions += [
                    (hip * 0.15 * self.inv, hip * 0.02, hip * 0.1),
                    (hip * 0.15 * self.inv, 0, hip * 0.2),
                ]
        else:
            positions = [
                (shoulder * 0.05 * self.inv, shoulder, 0),
                (shoulder * 0.15 * self.inv, shoulder, 0),
                (shoulder * 0.4 * self.inv, shoulder, hip * -0.1),
                (shoulder * 0.65 * self.inv, shoulder, 0),
            ]
        return positions

    def create_guides(self):
        guide_chain = guidelib.create_limb_guide_chain(
            side=self.side,
            module_name=self.module_name,
            labels=self.segment_names,
            size=self.size,
            as_leg=self.as_leg,
            with_foot=self.with_foot,
            positions=self.get_limb_positions(),
        )
        self.joints = guide_chain.joints
        self.joints[0].setParent(self.get_asset_root_module().skel_grp)
        guide_chain.grp.setParent(self.guides_grp)

        self.publish_nodes['guides'] += guide_chain.guides

    def create_pole_guide(self):
        gde = guidelib.create_guide(self.side, self.module_name, 'poleVector', self.size * 0.5)
        grp = pm.group(gde, n=self.mk('poleVectorGuide_GRP'))
        pm.parentConstraint(self.joints[1], grp)
        pm.parent(grp, self.guides_grp)
        pm.orientConstraint(self.static_grp, gde)
        attrutl.lock([gde.ty, gde.r])

        z_multiplier = 3 if self.as_leg else -3
        gde.tz.set(self.size * self.inv * z_multiplier)
        gde.tx.set(self.size * self.inv)

        self.position_trns['pole'] = pm.group(em=True, n=self.mk('PolePosition_TRN'), p=self.joints[1])
        pm.parentConstraint(gde, self.position_trns['pole'])

        crv = curvelib.curve_from_transforms(
            trns=(gde, self.joints[1]),
            name=f'{self.module_key}_guideConnector_CRV'
        )
        crv.inheritsTransform.set(False)
        crv.setParent(self.guides_grp)
        crv.template.set(True)

        self.publish_nodes['guides'] += [gde]

    def create_foot_guides(self):
        if not self.with_foot:
            return
        for label in ('In', 'Out', 'Heel'):
            gde = guidelib.create_guide(self.side, self.module_name, f'footRoll{label}', self.size * 0.25)
            pm.parent(gde, self.guides_grp)
            pm.orientConstraint(self.static_grp, gde)
            attrutl.lock([gde.r])

            jnt = self.joints[3] if label == 'Heel' else self.joints[4]
            pm.delete(pm.pointConstraint(jnt, gde))
            gde.ty.set(0)
            if label == 'Heel':
                gde.tz.set(gde.tz.get() + self.size * -0.5)
            elif label == 'In':
                gde.tx.set(gde.tx.get() + self.size * self.inv * -0.5)
            else:
                gde.tx.set(gde.tx.get() + self.size * self.inv * 0.5)

            position_trn = pm.group(em=True, n=self.mk(f'footRoll{label}_TRN'), p=jnt)
            pm.parentConstraint(gde, position_trn)
            self.position_trns[label] = position_trn

            crv = curvelib.curve_from_transforms(
                trns=(gde, jnt),
                name=f'{self.module_key}_guideConnectorFootRool{label}_CRV'
            )
            crv.inheritsTransform.set(False)
            crv.setParent(self.guides_grp)
            crv.template.set(True)

            self.publish_nodes['guides'] += [gde]

    # ---------------------- Puppet ---------------------- #

    def create_hook_grps(self):
        """ Create a group for each in_hook. """
        self.root_hook_grp = pm.group(em=True, p=self.in_hooks_grp, n=self.mk('rootHook_GRP'))
        self.end_hook_grp = pm.group(em=True, p=self.in_hooks_grp, n=self.mk('endHook_GRP'))

    def create_root_ctl(self):
        self.root_ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label=self.segment_names[0],
            ctl_shape='halfMoon',
            size=self.size,
            pos=self.puppet_joints[0],
            rot=self.puppet_joints[0]
        )
        self.root_ctl.grp.setParent(self.root_hook_grp)
        self.publish_nodes['ctls'].append(self.root_ctl.trn)
        pm.rotate(self.root_ctl.shp.cv, 90 * self.inv, 90 * self.inv, 0, r=True)
        pm.move(self.root_ctl.shp.cv, self.joints[1].tx.get() * 0.5, 0, 0, r=True)

        pm.parentConstraint(self.root_ctl.trn, self.puppet_joints[0])
        pm.scaleConstraint(self.root_ctl.trn, self.puppet_joints[0])

    def duplicate_joints(self):
        attrutl.label_attr(self.root_ctl.trn, 'settings')
        self.fk_ik_plug = attrutl.add(self.root_ctl.trn, attr_name='fk_ik', mn=0, mx=1, default=self.as_leg)
        self.fk_joints, self.ik_joints = jointlib.fk_ik_joints(
            joints=self.puppet_joints[1:4],
            fk_ik_plug=self.fk_ik_plug
        )
        pm.parent(self.ik_joints[0], self.fk_joints[0], self.root_ctl.trn)
        rvs = self.fk_ik_plug.outputs(type='reverse')[0]
        self.fk_ik_rvs_plug = rvs.outputX

    def create_fk_setup(self):
        self.fk_ctls = chainfunc.fk_chain_from_joints(joints=self.fk_joints, size=self.size, label='')
        self.publish_nodes['ctls'] += [ctl.trn for ctl in self.fk_ctls]
        self.fk_ctls[0].grp.setParent(self.root_ctl.trn)
        for ctl in self.fk_ctls:
            pm.rotate(ctl.shp.cv, 0, 0, 90, r=True)
            attrutl.lock(ctl.trn.t)

    def create_ik_setup(self):
        self.ik_ctls, self.ikh = chainfunc.ik_chain_from_joints(
            joints=self.ik_joints,
            label='',
            size=self.size,
            pole_position=self.position_trns['pole'].getTranslation('world'),
            maintain_offset=self.as_leg,
            offset=(180, 0, 0) if self.side == 'R' else (0, 0, 0)
        )
        self.publish_nodes['ctls'] += [ctl.trn for ctl in self.ik_ctls]
        pm.parent(self.ik_ctls[0].grp, self.root_hook_grp)
        pm.parent(self.ik_ctls[1].grp, self.end_hook_grp)
        attrutl.lock(self.ik_ctls[0].trn.r)
        if self.as_leg:
            self.ik_ctls[-1].trn.rotateOrder.set(2)

    def fk_ik_visibility(self):
        for ctl in self.fk_ctls:
            self.fk_ik_rvs_plug >> ctl.grp.v
        self.fk_ik_rvs_plug >> self.fk_joints[0].v

        self.fk_ik_plug >> self.ik_ctls[0].grp.v
        self.fk_ik_plug >> self.ik_ctls[1].shp.v
        self.fk_ik_plug >> self.ik_joints[0].v

    def create_twist_ctls(self):
        for i, n in enumerate(self.segment_names[1:], 1):
            ctl = controllib.AnimCtl(
                side=self.side,
                module_name=self.module_name,
                label=n + 'Twist',
                ctl_shape='plus',
                size=self.size,
                pos=self.joints[i],
                rot=self.joints[i],
                lock_attrs='tsv'
            )
            self.twist_ctls.append(ctl)
            self.publish_nodes['ctls'].append(ctl.trn)
            ctl.grp.setParent(self.root_hook_grp)

    def setup_twist_ctls(self):
        pm.parentConstraint(self.puppet_joints[0], self.twist_ctls[0].grp, mo=True)
        shoulder_correction_grp = pm.group(
            self.twist_ctls[0].trn,
            p=self.twist_ctls[0].grp,
            n=self.twist_ctls[0].grp.replace('_GRP', 'Driven_GRP')
        )
        shoulder_reader = posereaderlib.axis_reader(
            read_trn=self.puppet_joints[1],
            reference_trn=self.puppet_joints[0],
            module_key=self.module_key,
            label=f'{self.segment_names[1]}Twist'
        )
        connectutl.driven_keys(
            driver=shoulder_reader[2],
            driven=shoulder_correction_grp.rz,
            dv=(-180, 0, 180),
            v=(-180, 0, 180)
        )

        pm.pointConstraint(self.puppet_joints[2], self.twist_ctls[1].grp)
        orc = pm.orientConstraint(self.puppet_joints[1], self.puppet_joints[2], self.twist_ctls[1].grp)
        orc.interpType.set(2)

        pm.parentConstraint(self.puppet_joints[3], self.twist_ctls[2].grp, mo=True)
        if not self.as_leg:
            wrist_correction_grp = pm.group(
                self.twist_ctls[2].trn,
                p=self.twist_ctls[2].grp,
                n=self.twist_ctls[2].grp.replace('_GRP', 'Driven_GRP')
            )
            wrist_reader = posereaderlib.axis_reader(
                read_trn=self.puppet_joints[3],
                reference_trn=self.puppet_joints[2],
                module_key=self.module_key,
                label=f'{self.segment_names[3]}Twist'
            )
            connectutl.driven_keys(
                driver=wrist_reader[2],
                driven=wrist_correction_grp.rz,
                dv=(-180, 0, 180),
                v=(180, 0, -180)
            )

    def collision_spread_setup(self):
        self.collision_spread_trn = pm.group(em=True, p=self.twist_ctls[1].trn, n=self.mk('collisionSpread_TRN'))
        collision_reader = posereaderlib.axis_reader(
            read_trn=self.puppet_joints[2],
            reference_trn=self.puppet_joints[1],
            module_key=self.module_key,
            label='CollisionPoseReader',
            buffer=False  # collision should always happen in reference to a straight arm, no matter the default angle
        )
        connectutl.driven_keys(
            driver=collision_reader[1],
            driven=self.collision_spread_trn.tx,
            v=(0, self.collision_spread * self.inv),
            dv=(110, 140) if self.as_leg else (-110, -140)
        )

    def create_twist_joints(self):
        # trn = pm.group(em=True, p=self.twist_ctls[1].trn)
        upper_twist = twistfunc.straight_ikspline_twist(
            start_trn=self.twist_ctls[0].trn,
            # end_trn=trn,
            end_trn=self.twist_ctls[1].trn,
            module_key=self.module_key,
            label='upperTwist',
            fwd_axis='-x' if self.side == 'R' else 'x',
            up_axis='y',
            nr_jnts=6
        )
        pm.parent(upper_twist['joints'][0], self.joints[1])
        pm.parent(upper_twist['ikh'], upper_twist['crv'], self.static_grp)
        self.upper_twist_joints = upper_twist['joints']

        lower_twist = twistfunc.straight_ikspline_twist(
            start_trn=self.collision_spread_trn,
            end_trn=self.twist_ctls[2].trn,
            module_key=self.module_key,
            label='lowerTwist',
            fwd_axis='-x' if self.side == 'R' else 'x',
            up_axis='y',
            nr_jnts=6
        )
        pm.parent(lower_twist['joints'][0], self.joints[2])
        pm.parent(lower_twist['ikh'], lower_twist['crv'], self.static_grp)
        self.lower_twist_joints = lower_twist['joints']

    def twist_ctl_visibility(self):
        plug = attrutl.add(self.root_ctl.trn, 'showTwistCtls', 'bool', k=False)
        for ctl in self.twist_ctls:
            plug >> ctl.grp.v

    def foot_roll(self):
        if not self.with_foot:
            return
        inner_grp = pm.group(em=True, n=self.mk('footRollInner_GRP'), p=self.ik_ctls[1].trn)
        inner_trn = pm.group(em=True, n=self.mk('footRollInner_TRN'), p=inner_grp)
        pm.delete(pm.parentConstraint(self.position_trns['In'], inner_grp))
        outer_grp = pm.group(em=True, n=self.mk('footRollOuter_GRP'), p=inner_trn)
        outer_trn = pm.group(em=True, n=self.mk('footRollOuter_TRN'), p=outer_grp)
        pm.delete(pm.parentConstraint(self.position_trns['Out'], outer_grp))
        heel_grp = pm.group(em=True, n=self.mk('footRollHeel_GRP'), p=outer_trn)
        heel_trn = pm.group(em=True, n=self.mk('footRollHeel_TRN'), p=heel_grp)
        pm.delete(pm.parentConstraint(self.position_trns['Heel'], heel_grp))
        tip_grp = pm.group(em=True, n=self.mk('footRollTip_GRP'), p=heel_trn)
        tip_trn = pm.group(em=True, n=self.mk('footRollTip_TRN'), p=tip_grp)
        pm.delete(pm.parentConstraint(self.puppet_joints[5], tip_grp))
        roll_grp = pm.group(em=True, n=self.mk('footRollRoll_GRP'), p=tip_trn)
        roll_trn = pm.group(em=True, n=self.mk('footRollRoll_TRN'), p=roll_grp)
        pm.delete(pm.parentConstraint(self.puppet_joints[4], roll_grp))

        attrutl.label_attr(self.ik_ctls[1].trn, 'Foot')
        roll_plug = attrutl.add(self.ik_ctls[1].trn, 'roll')
        rock_plug = attrutl.add(self.ik_ctls[1].trn, 'rock')
        roll_trigger_plug = attrutl.add(self.ik_ctls[1].trn, 'rolltrigger', default=30)

        connectutl.create_node('clamp', ipr=rock_plug, mxr=180, mnr=0, opr=inner_trn.rz)
        connectutl.create_node('clamp', ipr=rock_plug, mxr=0, mnr=-180, opr=outer_trn.rz)
        connectutl.create_node('clamp', ipr=roll_plug, mxr=0, mnr=-180, opr=heel_trn.rx)
        connectutl.create_node('clamp', ipr=roll_plug, mxr=roll_trigger_plug, mnr=0, opr=roll_trn.ry)
        roll_pma = connectutl.create_node('plusMinusAverage', i1__0___=roll_plug, i1__1___=roll_trigger_plug, op=2)
        connectutl.create_node('clamp', ipr=roll_pma.o1, mxr=180, mnr=0, opr=tip_trn.ry)

        self.foot_ctl = controllib.AnimCtl(
            side=self.side,
            module_name=self.module_name,
            label='footTip',
            ctl_shape='square',
            size=self.size,
            pos=self.puppet_joints[4],
            rot=self.puppet_joints[4]
        )
        self.foot_ctl.grp.setParent(tip_trn)
        self.publish_nodes['ctls'].append(self.foot_ctl.trn)
        self.ikh.setParent(roll_trn)
        pm.rotate(self.foot_ctl.shp.cv, 0, 0, 90, r=True)
        tip_fk_buffer = pm.group(em=True, n=self.mk('footRollTipFkBuffer_TRN'), p=self.fk_joints[-1])
        pm.delete(pm.parentConstraint(tip_trn, tip_fk_buffer))

        pac = pm.parentConstraint(tip_fk_buffer, tip_trn, self.foot_ctl.grp, mo=True)
        plugs = pm.parentConstraint(pac, q=1, wal=1)
        self.fk_ik_plug >> plugs[1]
        self.fk_ik_rvs_plug >> plugs[0]

        roll_ikh = pm.ikHandle(
            sj=self.puppet_joints[3], ee=self.puppet_joints[4], sol='ikSCsolver', n=self.mk('footRoll_IKH'))[0]
        roll_ikh.setParent(self.foot_ctl.grp)
        tip_ikh = pm.ikHandle(
            sj=self.puppet_joints[4], ee=self.puppet_joints[5], sol='ikSCsolver', n=self.mk('footTip_IKH'))[0]
        tip_ikh.setParent(self.foot_ctl.trn)
        pm.hide(roll_ikh, tip_ikh)

    def compose_output_ctls_dict(self):
        output_ctls = {'root': self.root_ctl.trn}
        for i, fk in enumerate(self.fk_ctls):
            output_ctls[f'fk{i}'] = fk.trn
        for i, ik in enumerate(self.ik_ctls):
            output_ctls[f'ik{i}'] = ik.trn
        for i, twist in enumerate(self.twist_ctls):
            output_ctls[f'twist{i}'] = twist.trn
        if self.with_foot:
            output_ctls['foot'] = self.foot_ctl.trn
        return output_ctls

    def connect_to_hook(self):
        self.constraint_to_hook(driven=self.root_hook_grp)
        self.constraint_to_hook(driven=self.end_hook_grp, hook=self.ik_hook)

    def out_hook(self, index):
        """ Return a transform that other modules can hook to. """
        if index == 1:
            return self.upper_twist_joints[0]
        else:
            return self.joints[index]

    def delete_position_trns(self):
        pm.delete(self.position_trns.values())

    # def out_joint(self, hook):
    #     """ Overwrite RigPuppetModule.out_joint to make the string keys foot00 & foot01 work. """
    #     if isinstance(hook, (list, tuple)):
    #         index = hook[1]
    #         if index == 'foot00':
    #             return self.foot_joints[0]
    #         elif index == 'foot01':
    #             return self.foot_joints[1]
    #         else:
    #             return super().out_joint(hook)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_guides()
        self.create_pole_guide()
        self.create_foot_guides()
        self.store_output_data(jnts=self.joints)

    def skeleton_build_post(self):
        super().skeleton_build_post()
        self.load_rigdata('guides', False)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.free_joints_from_guides(joints=self.joints + list(self.position_trns.values()))
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_joints()
        self.create_hook_grps()
        self.create_root_ctl()
        self.duplicate_joints()
        self.create_fk_setup()
        self.create_ik_setup()
        self.fk_ik_visibility()

        self.foot_roll()
        self.store_output_data(ctls=self.compose_output_ctls_dict())

        self.create_twist_ctls()
        self.setup_twist_ctls()
        self.collision_spread_setup()
        self.create_twist_joints()
        self.twist_ctl_visibility()

    def puppet_build_post(self):
        super().puppet_build_post()
        self.load_rigdata('ctls', False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_to_hook()
        self.connect_puppet_joints()
        self.cleanup_joints(
            self.joints + self.puppet_joints + self.fk_joints + self.ik_joints +
            self.upper_twist_joints + self.lower_twist_joints
        )

    def finalize(self):
        super().finalize()
        self.delete_position_trns()
