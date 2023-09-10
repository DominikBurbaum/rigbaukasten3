from rigbaukasten.core import modulecor
import pymel.core as pm

from rigbaukasten.library import guidelib, curvelib, posereaderlib
from rigbaukasten.utils import attrutl, connectutl, mathutl


class StretchyJoint(modulecor.RigPuppetModule):
    """ A joint that 'stretches' (distance based scale) between the given hook and end_hook. """
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            end_hook=None,
            size=1,
            parent_joint=None
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param size: float - default size for the guides and joints
        :param hook: OutDataPointer or PyNode - What should the origin/start joint be attached to?
        :param end_hook: OutDataPointer or PyNode - What should the insertion/end joint be attached to?
        """
        super().__init__(side=side, module_name=module_name, size=size, hook=hook, parent_joint=parent_joint)
        self.end_hook = end_hook

        self.position_trns = {}
        self.start_trn = None
        self.aim_trn = None
        self.end_trn = None
        self.offset_plugs = []
        self.guide_offset_plugs = []
        self.guides = []
        self.joints = []
        self.crv = None
        self.stretch_length_pma = None
        self.guide_curve_info = None
        self.global_scale_read_dcm = None

    # ---------------------- Skeleton ---------------------- #

    def create_joints(self):
        for i in range(2):
            jnt = pm.createNode('joint', p=self.get_asset_root_module().skel_grp, n=f'{self.module_key}_{i:02}_JNT')
            jnt.radius.set(self.size * .3)
            self.joints.append(jnt)
        self.joints[0].displayLocalAxis.set(True)
        self.joints[1].setParent(self.joints[0])
        self.joints[1].tx.set(self.size)

    def create_guides(self):
        for i in range(2):
            gde = guidelib.create_guide(self.side, self.module_name, f'{i:02}', self.size)
            self.guides.append(gde)
            pm.parent(gde, self.guides_grp)
        self.publish_nodes['guides'] += self.guides
        self.guides[1].tx.set(self.size)
        self.guides[0].displayLocalAxis.set(True)

    def create_guide_aim_setup(self):
        # start_trn = pm.group(em=True, n=f'{self.module_key}_guideStart_TRN', p=self.guides_grp)
        aim_trn = pm.group(em=True, n=f'{self.module_key}_guideAim_TRN', p=self.guides[0])
        start_offset_trn = pm.group(em=True, n=f'{self.module_key}_guideStartOffset_TRN', p=aim_trn)
        end_offset_trn = pm.group(em=True, n=f'{self.module_key}_guideEndOffset_TRN', p=start_offset_trn)
        # end_trn = pm.group(em=True, n=f'{self.module_key}_guideEnd_TRN', p=self.guides_grp)
        crv = curvelib.curve_from_transforms(
            trns=(self.guides[0], self.guides[1]),
            name=f'{self.module_key}_guideConnector'
        )
        crv.inheritsTransform.set(False)
        crv.setParent(self.guides_grp)
        crv.template.set(True)

        self.position_trns['start'] = pm.group(em=True, n=self.mk('startPosition_TRN'), p=self.joints[0])
        pm.parentConstraint(self.guides[0], self.position_trns['start'])
        self.position_trns['end'] = pm.group(em=True, n=self.mk('endPosition_TRN'), p=self.joints[1])
        pm.parentConstraint(self.guides[1], self.position_trns['end'])

        pm.aimConstraint(self.guides[1], aim_trn, wut='objectrotation', wuo=self.guides[0])
        self.offset_plugs.append(attrutl.add(self.position_trns['start'], 'offset'))
        self.offset_plugs.append(attrutl.add(self.position_trns['end'], 'offset'))
        self.offset_plugs[0] >> start_offset_trn.tx
        self.guide_curve_info = pm.arclen(crv, ch=True)
        connectutl.create_node(
            'plusMinusAverage',
            i1__0___=self.guide_curve_info.arcLength,
            i1__1___=self.offset_plugs[0],
            i1__2___=self.offset_plugs[1],
            op=2,
            o1=end_offset_trn.tx
        )
        pm.parentConstraint(start_offset_trn, self.joints[0])
        pm.parentConstraint(end_offset_trn, self.joints[1])

    def connect_joints_to_guides(self):
        for gde, plug in zip(self.guides, self.offset_plugs):
            guide_plug = attrutl.add(gde, 'offset')
            self.guide_offset_plugs.append(guide_plug)
            guide_plug >> plug

    def free_joints_from_guides(self):
        super().free_joints_from_guides(joints=self.joints + list(self.position_trns.values()))
        for src, dst in zip(self.guide_offset_plugs, self.offset_plugs):
            src // dst

    # ---------------------- Puppet ---------------------- #

    def create_aim_setup(self):
        self.start_trn = pm.group(em=True, n=f'{self.module_key}_start_TRN', p=self.in_hooks_grp)
        self.aim_trn = pm.group(em=True, n=f'{self.module_key}_aim_TRN', p=self.start_trn)
        self.end_trn = pm.group(em=True, n=f'{self.module_key}_end_TRN', p=self.in_hooks_grp)
        self.crv = curvelib.curve_from_transforms(
            trns=(self.start_trn, self.end_trn), name=f'{self.module_key}_connector')
        self.crv.setParent(self.static_grp)
        self.crv.template.set(True)
        pm.delete(pm.parentConstraint(self.position_trns['start'], self.start_trn))
        pm.delete(pm.parentConstraint(self.position_trns['end'], self.end_trn))
        pm.aimConstraint(self.end_trn, self.aim_trn, wut='objectrotation', wuo=self.start_trn)
        self.puppet_joints[0].setParent(self.aim_trn)
        self.puppet_joints[0].resetFromRestPosition()
        self.offset_plugs[0] >> self.puppet_joints[0].tx

    def get_length_with_global_scale(self):
        """ Get the length between start and end and prepare a setup to read the global scale from the hook.
            Only prepare the global scale node and don't connect before the build step is done.
            This relies on uniform scale of the hook.
        """
        cvi = pm.arclen(self.crv, ch=True)
        self.global_scale_read_dcm = connectutl.create_node('decomposeMatrix', n=f'{self.module_key}_globalScale_DCM')
        global_scale_apply_mlt = connectutl.create_node(
            'multiplyDivide',
            i1x=cvi.arcLength,
            i2x=self.global_scale_read_dcm.outputScaleY,
            op=2,
            n=f'{self.module_key}_globalScaleDiv_MDL',
        )
        self.stretch_length_pma = connectutl.create_node(
            'plusMinusAverage',
            i1__0___=global_scale_apply_mlt.ox,
            i1__1___=self.offset_plugs[0],
            i1__2___=self.offset_plugs[1],
            op=2,
            o1=self.puppet_joints[1].tx,
            n=f'{self.module_key}_stretchLengthOffset_MDL',
        )

    def setup_stretch(self):
        self.stretch_length_pma.o1 // self.puppet_joints[1].tx
        connectutl.create_node(
            'multiplyDivide',
            i1x=self.stretch_length_pma.o1,
            i2x=self.stretch_length_pma.o1.get(),
            op=2,
            n=f'{self.module_key}_stretch_MDL',
            ox=self.puppet_joints[0].sx
        )

    def connect_to_hook(self):
        if self.hook:
            hook = self.get_hook(self.hook)
            if pm.objExists(f'{hook}.puppet_joint_equivalent'):
                hook = hook.puppet_joint_equivalent.listConnections(s=False, d=True)[0]
            buffer = pm.group(em=True, n=f'{self.module_key}_startHookBuffer_TRN', p=hook)
            pm.delete(pm.parentConstraint(self.start_trn, buffer))
            pm.parentConstraint(buffer, self.start_trn, mo=True)
            pm.scaleConstraint(buffer, self.start_trn)

            hook.wm[0] >> self.global_scale_read_dcm.inputMatrix

        if self.end_hook:
            end_hook = self.get_hook(self.end_hook)
            if pm.objExists(f'{end_hook}.puppet_joint_equivalent'):
                end_hook = end_hook.puppet_joint_equivalent.listConnections(s=False, d=True)[0]
            end_buffer = pm.group(em=True, n=f'{self.module_key}_endHookBuffer_TRN', p=end_hook)
            pm.delete(pm.parentConstraint(self.end_trn, end_buffer))
            pm.parentConstraint(end_buffer, self.end_trn, mo=True)
            pm.scaleConstraint(end_buffer, self.end_trn)

    def out_hook(self, index):
        """ Return a transform that other modules can hook to. """
        return self.joints[index]
    
    def delete_guides(self):
        pm.delete(self.guide_curve_info)
        super().delete_guides()
        pm.delete(self.position_trns.values())

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()
        self.create_guides_grp()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_joints()
        self.store_output_data(jnts=self.joints)
        self.create_guides()
        self.create_guide_aim_setup()
        self.connect_joints_to_guides()

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
        self.create_aim_setup()
        self.get_length_with_global_scale()
        self.setup_stretch()

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_to_hook()
        self.connect_puppet_joints()
        self.cleanup_joints(self.joints + self.puppet_joints)

    def finalize(self):
        super().finalize()
        self.delete_guides()


class SimpleHingeHelpers(modulecor.RigPuppetModule):
    """ Deformation joints that are driven by the angle between hook and parent_hook. For elbows, knees, etc. """
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            parent_hook=None,
            size=1,
            down_axis='x',
            out_axis='y',
            limit=120,
            push_distance=10,
            side_volume=False,
            parent_joint=None
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param size: float - default size and position multiplier for the guides and joints
        :param hook: OutDataPointer or PyNode - The hinge joint, e.g. elbow joint
        :param parent_hook: OutDataPointer or PyNode - The parent joint, e.g. shoulder joint
        :param down_axis: str - x, y, z, -x, -y or -z. Axis that goes down from the hinge, e.g. towards the wrist
        :param out_axis: str - x, y, z, -x, -y or -z. Axis that goes out from the hinge, e.g. back to get a pointy elbow
        :param limit: float - Default rotation value at which the joints should stop pushing further.
        :param push_distance: float - Default distance the joints should be pushed at max.
        :param side_volume: bool - Create two joints that push out sideways to mimic collision volume.
        :param parent_joint: OutDataPointer or PyNode - Parent joint for this modules joint. If the value for this
                             is None, the system will attempt to find the joint based on the given hook.
        """
        super().__init__(side=side, module_name=module_name, parent_joint=parent_joint)
        self.hook = hook
        self.parent_hook = parent_hook
        self.size = size
        self.down_axis = down_axis
        self.out_axis = out_axis
        self.side_axis = 'xyz'.replace(out_axis[-1], '').replace(down_axis[-1], '')
        self.limit = limit
        self.push_distance = push_distance
        self.side_volume = side_volume

        self.upper_jnts_grp = None
        self.lower_jnts_grp = None
        self.avg_jnt = None
        self.push_out_jnt = None
        self.push_up_jnt = None
        self.push_down_jnt = None
        self.avg_pup_jnt = None
        self.push_out_pup_jnt = None
        self.push_up_pup_jnt = None
        self.push_down_pup_jnt = None
        self.side_volume_pup_jnts = []

        self.axis_reader = None

    def create_jnts(self):
        """
        Create the main skin joints.
        For simplicity, they will all be parented under the parent or hook joint if possible. That means they'll have a
        different hierarchy than the puppet joints. They also won't be in the bind pose in this stage, because the
        correct initial positions are not defined yet (the axis reader and driven keys don't exist yet). This will all
        be resolved once the joints are constrained to the puppet joints.
        :TO DO: can we put the joints in the correct positions? Or at least better positions than all in one spot?
        """
        parent = self.get_asset_root_module().skel_grp
        self.avg_jnt = pm.createNode('joint', n=self.mk('average_JNT'), p=parent)
        self.push_up_jnt = pm.createNode('joint', n=self.mk('pushUp_JNT'), p=self.avg_jnt)
        self.push_down_jnt = pm.createNode('joint', n=self.mk('pushDown_JNT'), p=self.avg_jnt)
        self.push_out_jnt = pm.createNode('joint', n=self.mk('pushOut_JNT'), p=self.avg_jnt)

        self.joints = [self.avg_jnt, self.push_up_jnt, self.push_down_jnt, self.push_out_jnt]

        if self.side_volume:
            for i in range(2):
                jnt = pm.createNode('joint', n=self.mk(f'sideVolume{i:02}_JNT'), p=self.avg_jnt)
                self.joints.append(jnt)

        for jnt in self.joints:
            jnt.radius.set(self.size * 0.1)

    def connect_to_main_skeleton(self):
        """ Do the normal connect_to_main_skeleton(), then move the joints to their parent.
            This doesn't have any effect on the rig, because the positions will change again when the pose readers
            are applied. All it does is avoid bones form being drawn frm the hinge to the origin.
        """
        super().connect_to_main_skeleton()
        self.avg_jnt.t.set(0, 0, 0)
        self.avg_jnt.r.set(0, 0, 0)

    def create_puppet_jnts(self):
        self.upper_jnts_grp = pm.group(em=True, n=self.mk('upperJoints_GRP'), p=self.in_hooks_grp)
        self.push_up_pup_jnt = pm.createNode('joint', n=self.mk('pushUpPuppet_JNT'), p=self.upper_jnts_grp)
        self.lower_jnts_grp = pm.group(em=True, n=self.mk('lowerJoints_GRP'), p=self.in_hooks_grp)
        self.push_down_pup_jnt = pm.createNode('joint', n=self.mk('pushDownPuppet_JNT'), p=self.lower_jnts_grp)
        self.avg_pup_jnt = pm.createNode('joint', n=self.mk('averagePuppet_JNT'), p=self.lower_jnts_grp)
        self.push_out_pup_jnt = pm.createNode('joint', n=self.mk('pushOutPuppet_JNT'), p=self.avg_pup_jnt)

        self.puppet_joints = [self.avg_pup_jnt, self.push_up_pup_jnt, self.push_down_pup_jnt, self.push_out_pup_jnt]

        if self.side_volume:
            for i in range(2):
                jnt = pm.createNode('joint', n=self.mk(f'sideVolume{i:02}Puppet_JNT'), p=self.avg_pup_jnt)
                self.side_volume_pup_jnts.append(jnt)
                self.puppet_joints.append(jnt)

        for jnt in self.puppet_joints:
            jnt.radius.set(self.size * 0.1)

    def create_axis_reader(self):
        self.axis_reader = posereaderlib.axis_reader(
            read_trn=self.lower_jnts_grp,
            reference_trn=self.upper_jnts_grp,
            module_key=self.module_key,
            label='pose'
        )

    def setup_jnts(self):
        side_index = 'xyz'.index(self.side_axis[-1])
        connectutl.create_node(
            'multDoubleLinear',
            i1=self.axis_reader[side_index],
            i2=-0.5,
            o=self.avg_pup_jnt.attr(f'r{self.side_axis[-1]}')
        )

        out_vec = mathutl.vector_from_axis(self.out_axis)
        out_pos_start = [a * self.size for a in out_vec]
        out_pos_end = [a * self.push_distance for a in out_vec]
        out_index = 'xyz'.index(self.out_axis[-1])
        connectutl.driven_keys(
            driver=self.axis_reader[side_index],
            driven=self.push_out_pup_jnt.attr(f't{self.out_axis[-1]}'),
            v=(out_pos_start[out_index], out_pos_end[out_index]),
            dv=(0, self.limit)
        )
        self.publish_nodes['drivenKeys'].append(self.push_out_pup_jnt)
        for jnt in self.side_volume_pup_jnts:
            inv = 1 if jnt.endswith('sideVolume01Puppet_JNT') else -1
            connectutl.driven_keys(
                driver=self.axis_reader[side_index],
                driven=jnt.attr(f't{self.side_axis[-1]}'),
                v=(self.size * inv, self.push_distance * inv * 0.5),
                dv=(self.limit * 0.5, self.limit)
            )
            self.publish_nodes['drivenKeys'].append(jnt)

        self.push_down_pup_jnt.attr(f't{self.out_axis[-1]}').set(out_pos_start[out_index] * -1)
        self.push_up_pup_jnt.attr(f't{self.out_axis[-1]}').set(out_pos_start[out_index] * -1)

        down_vec = mathutl.vector_from_axis(self.down_axis)
        down_pos_start = [a * self.size for a in down_vec]
        down_pos_end = [a * self.push_distance for a in down_vec]
        down_index = 'xyz'.index(self.down_axis[-1])
        connectutl.driven_keys(
            driver=self.axis_reader[side_index],
            driven=self.push_down_pup_jnt.attr(f't{self.down_axis[-1]}'),
            v=(down_pos_start[down_index], down_pos_end[down_index]),
            dv=(0, self.limit)
        )
        connectutl.driven_keys(
            driver=self.axis_reader[side_index],
            driven=self.push_up_pup_jnt.attr(f't{self.down_axis[-1]}'),
            v=(down_pos_start[down_index] * -1, down_pos_end[down_index] * -1),
            dv=(0, self.limit)
        )
        self.publish_nodes['drivenKeys'] += [self.push_down_pup_jnt, self.push_up_jnt]

    def connect_to_hooks(self):
        hook = self.get_hook(self.hook)
        parent_hook = self.get_hook(self.parent_hook)

        pm.parentConstraint(hook, self.lower_jnts_grp)
        pm.scaleConstraint(hook, self.lower_jnts_grp)

        pm.delete(pm.pointConstraint(hook, self.upper_jnts_grp))
        pm.delete(pm.orientConstraint(parent_hook, self.upper_jnts_grp))
        pm.parentConstraint(parent_hook, self.upper_jnts_grp, mo=True)
        pm.scaleConstraint(parent_hook, self.upper_jnts_grp)

        posereaderlib.update_axis_reader_buffer(self.axis_reader)

    def cleanup_joints_side_aware(self):
        """ Do normal cleanup, then set the side labels properly for the left/right side joints (if needed). """
        self.cleanup_joints(self.joints + self.puppet_joints)
        if self.side == 'C' and self.side_volume:
            side_jnts = self.joints[-2:]
            x_pos_0 = pm.xform(side_jnts[0], q=True, ws=True, t=True)[0]
            x_pos_1 = pm.xform(side_jnts[1], q=True, ws=True, t=True)[0]
            for jnts in (side_jnts, self.side_volume_pup_jnts):
                if x_pos_0 > x_pos_1:
                    jnts[0].side.set(1)
                    jnts[1].side.set(2)
                else:
                    jnts[0].side.set(2)
                    jnts[1].side.set(1)
                label = jnts[0].name()[2:-6]
                jnts[0].otherType.set(label)
                jnts[1].otherType.set(label)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_jnts()
        self.store_output_data(jnts=self.joints)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_jnts()
        self.create_axis_reader()
        self.setup_jnts()

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_puppet_joints()
        self.connect_to_hooks()
        self.cleanup_joints_side_aware()
        self.load_rigdata(io_type='drivenKeys', recursive=False)


class HingeSidePush(modulecor.RigPuppetModule):
    """
    Two joints that push out to the side of a hinge. Simple standalone version of SimpleHingeHelpers side_volume.
    Primary use case is a cheek squash when opening the mouth.
    """
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            parent_hook=None,
            size=1,
            hinge_axis='y',
            limit=120,
            push_distance=10,
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param size: float - default size and position multiplier for the guides and joints
        :param hook: OutDataPointer or PyNode - The hinge joint, e.g. jaw joint
        :param parent_hook: OutDataPointer or PyNode - The parent joint, e.g. head joint
        :param hinge_axis: str - x, y, z, -x, -y or -z. rotation axis of the hinge
        :param limit: float - Default rotation value at which the joints should stop pushing further.
        :param push_distance: float - Default distance the joints should be pushed at max.
        """
        super().__init__(side=side, module_name=module_name)
        self.hook = hook
        self.parent_hook = parent_hook
        self.size = size
        self.hinge_axis = hinge_axis
        self.limit = limit
        self.push_distance = push_distance

        self.jnts_grp = None
        self.parent_ref_trn = None
        self.avg_jnt = None
        self.pos_jnt = None
        self.neg_jnt = None
        self.avg_pup_jnt = None
        self.pos_pup_jnt = None
        self.neg_pup_jnt = None

        self.axis_reader = None

    def create_jnts(self):
        """
        Create the main skin joints.
        For simplicity, they will all be parented under the parent or hook joint if possible. That means they'll have a
        different hierarchy than the puppet joints. They also won't be in the bind pose in this stage, because the
        correct initial positions are not defined yet (the axis reader and driven keys don't exist yet). This will all
        be resolved once the joints are constrained to the puppet joints.
        :TO DO: can we put the joints in the correct positions? Or at least better positions than all in one spot?
        """
        parent = self.get_asset_root_module().skel_grp
        self.avg_jnt = pm.createNode('joint', n=self.mk('average_JNT'), p=parent)
        self.pos_jnt = pm.createNode('joint', n=self.mk('pushPos_JNT'), p=self.avg_jnt)
        self.neg_jnt = pm.createNode('joint', n=self.mk('pushNeg_JNT'), p=self.avg_jnt)

        self.joints = [self.avg_jnt, self.neg_jnt, self.pos_jnt]

        for jnt in self.joints:
            jnt.radius.set(self.size * 0.1)

    def connect_to_main_skeleton(self):
        """ Do the normal connect_to_main_skeleton(), then move the joints to their parent.
            This doesn't have any effect on the rig, because the positions will change again when the pose readers
            are applied. All it does is avoid bones form being drawn frm the hinge to the origin.
        """
        super().connect_to_main_skeleton()
        self.avg_jnt.t.set(0, 0, 0)
        self.avg_jnt.r.set(0, 0, 0)

    def create_puppet_jnts(self):
        self.jnts_grp = pm.group(em=True, n=self.mk('joints_GRP'), p=self.in_hooks_grp)
        self.parent_ref_trn = pm.group(em=True, n=self.mk('parentReference_TRN'), p=self.in_hooks_grp)
        self.avg_pup_jnt = pm.createNode('joint', n=self.mk('averagePuppet_JNT'), p=self.jnts_grp)
        self.pos_pup_jnt = pm.createNode('joint', n=self.mk('pushPosPuppet_JNT'), p=self.avg_pup_jnt)
        self.neg_pup_jnt = pm.createNode('joint', n=self.mk('pushNegPuppet_JNT'), p=self.avg_pup_jnt)

        self.puppet_joints = [self.avg_pup_jnt, self.pos_pup_jnt, self.neg_pup_jnt]

        for jnt in self.puppet_joints:
            jnt.radius.set(self.size * 0.1)

    def create_axis_reader(self):
        self.axis_reader = posereaderlib.axis_reader(
            read_trn=self.jnts_grp,
            reference_trn=self.parent_ref_trn,
            module_key=self.module_key,
            label='pose'
        )

    def setup_jnts(self):
        side_index = 'xyz'.index(self.hinge_axis[-1])
        driver_plug = self.axis_reader[side_index]
        connectutl.create_node(
            'multDoubleLinear',
            i1=driver_plug,
            i2=-0.5,
            o=self.avg_pup_jnt.attr(f'r{self.hinge_axis[-1]}')
        )

        connectutl.driven_keys(
            driver=driver_plug,
            driven=self.pos_pup_jnt.attr(f't{self.hinge_axis[-1]}'),
            v=(self.size, self.push_distance + self.size),
            dv=(0, self.limit)
        )
        connectutl.driven_keys(
            driver=driver_plug,
            driven=self.neg_pup_jnt.attr(f't{self.hinge_axis[-1]}'),
            v=(-self.size, -(self.push_distance + self.size)),
            dv=(0, self.limit)
        )
        self.publish_nodes['drivenKeys'] += [self.pos_pup_jnt, self.neg_pup_jnt]

    def connect_to_hooks(self):
        hook = self.get_hook(self.hook)
        parent_hook = self.get_hook(self.parent_hook)

        pm.parentConstraint(hook, self.jnts_grp)
        pm.scaleConstraint(hook, self.jnts_grp)

        pm.delete(pm.pointConstraint(hook, self.parent_ref_trn))
        pm.delete(pm.orientConstraint(parent_hook, self.parent_ref_trn))
        pm.parentConstraint(parent_hook, self.parent_ref_trn, mo=True)
        pm.scaleConstraint(parent_hook, self.parent_ref_trn)

        posereaderlib.update_axis_reader_buffer(self.axis_reader)

    def cleanup_joints_side_aware(self):
        """ Do normal cleanup, then set the side labels properly for the left/right side joints (if needed). """
        self.cleanup_joints(self.joints + self.puppet_joints)
        if self.side == 'C':
            side_jnts = self.joints[-2:]
            x_pos_0 = pm.xform(side_jnts[0], q=True, ws=True, t=True)[0]
            x_pos_1 = pm.xform(side_jnts[1], q=True, ws=True, t=True)[0]
            for jnts in (side_jnts, self.puppet_joints[-2:]):
                if x_pos_0 > x_pos_1:
                    jnts[0].side.set(1)
                    jnts[1].side.set(2)
                else:
                    jnts[0].side.set(2)
                    jnts[1].side.set(1)
                label = jnts[0].name()[2:-6]
                jnts[0].otherType.set(label)
                jnts[1].otherType.set(label)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_jnts()
        self.store_output_data(jnts=self.joints)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_jnts()
        self.create_axis_reader()
        self.setup_jnts()

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_puppet_joints()
        self.connect_to_hooks()
        self.cleanup_joints_side_aware()
        self.load_rigdata(io_type='drivenKeys', recursive=False)


class VolumePushers(modulecor.RigPuppetModule):
    """
    Volume push joints to support anatomical joints that rotate in all directions (e.g. spine).

    Four joints will be created, towards the out directions (i.e. along all axes except the aim_axis). When the
    driver rotates towards one of the joints, it will push out. On a spine this can be used to simulate belly
    fat/ love handles.
    """
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            parent_hook=None,
            size=1,
            aim_axis='x',
            limit=120,
            push_distance=10
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param size: float - default size and position multiplier for the guides and joints
        :param hook: OutDataPointer or PyNode - The hinge joint, e.g. jaw joint
        :param parent_hook: OutDataPointer or PyNode - The parent joint, e.g. head joint
        :param aim_axis: str - x, y, z, -x, -y or -z. aim axis of the driver joint (hook)
        :param limit: float - Default rotation value at which the joints should stop pushing further.
        :param push_distance: float - Default distance the joints should be pushed at max.
        """
        super().__init__(side=side, module_name=module_name)
        self.hook = hook
        self.parent_hook = parent_hook
        self.size = size
        self.aim_axis = aim_axis
        self.limit = limit
        self.push_distance = push_distance

        self.push_axes = 'xyz'.replace(self.aim_axis[-1], '')
        self.jnts_grp = None
        self.ref_grp = None
        self.joints = []

        self.axis_reader = None

    def create_jnts(self):
        """
        Create the main skin joints.
        For simplicity, they will all be parented under the parent or hook joint if possible. That means they'll have a
        different hierarchy than the puppet joints. They also won't be in the bind pose in this stage, because the
        correct initial positions are not defined yet (the axis reader and driven keys don't exist yet). This will all
        be resolved once the joints are constrained to the puppet joints.
        :TO DO: can we put the joints in the correct positions? Or at least better positions than all in one spot?
        """
        parent = self.get_asset_root_module().skel_grp
        for ax in self.push_axes:
            for label, inv in (('Pos', 1), ('Neg', -1)):
                jnt = pm.createNode('joint', n=self.mk(f'volume{label}{ax.upper()}_JNT'), p=parent)
                jnt.radius.set(self.size * 0.1)
                self.joints.append(jnt)

    def connect_to_main_skeleton(self):
        """ Parent ALL joint to the main skeleton, not just the first one as in modulecor.RigPuppetModule.
            After parenting, move the joints to their parent.
            This doesn't have any effect on the rig, because the positions will change again when the pose readers
            are applied. All it does is avoid bones form being drawn from the hinge to the origin.
        """
        skeleton_parent = self.parent_joint or self.get_joint_from_hook(self.hook)
        if skeleton_parent:
            for jnt in self.joints:
                jnt.setParent(skeleton_parent)
                jnt.t.set(0, 0, 0)
                jnt.r.set(0, 0, 0)

    def create_hook_groups(self):
        self.jnts_grp = pm.group(em=True, n=self.mk('volumeJoints_GRP'), p=self.in_hooks_grp)
        self.ref_grp = pm.group(em=True, n=self.mk('reference_GRP'), p=self.in_hooks_grp)

    def create_axis_reader(self):
        self.axis_reader = posereaderlib.axis_reader(
            read_trn=self.jnts_grp,
            reference_trn=self.ref_grp,
            module_key=self.module_key,
            label='pose'
        )

    def create_puppet_jnts(self):
        for ax in self.push_axes:
            for label, inv in (('Pos', 1), ('Neg', -1)):
                jnt = pm.createNode('joint', n=self.mk(f'volume{label}{ax.upper()}Puppet_JNT'), p=self.jnts_grp)
                jnt.radius.set(self.size * 0.1)
                self.puppet_joints.append(jnt)

                start = self.size * inv
                end = self.push_distance * inv + start
                driver_ax = self.push_axes.replace(ax, '')
                direction = {'xz': -1, 'xy': 1, 'zy': -1, 'zx': 1, 'yx': -1, 'yz': 1}[ax + driver_ax]
                connectutl.driven_keys(
                    driver=self.axis_reader['xyz'.index(driver_ax)],
                    driven=jnt.attr(f't{ax}'),
                    v=(start, end),
                    dv=(0, self.limit * direction * inv)
                )
                self.publish_nodes['drivenKeys'].append(jnt)

    def connect_to_hooks(self):
        hook = self.get_hook(self.hook)
        parent_hook = self.get_hook(self.parent_hook)

        pm.parentConstraint(hook, self.jnts_grp)
        pm.scaleConstraint(hook, self.jnts_grp)

        pm.parentConstraint(parent_hook, self.ref_grp)
        pm.scaleConstraint(parent_hook, self.ref_grp)

        posereaderlib.update_axis_reader_buffer(self.axis_reader)

    def cleanup_joints_side_aware(self):
        """ Do normal cleanup, then set the side labels properly for the left/right side joints (if needed). """
        self.cleanup_joints(self.joints + self.puppet_joints)
        if self.side == 'C':
            x_pos = [pm.xform(j, q=True, ws=True, t=True)[0] for j in self.joints]
            right_index = x_pos.index(min(x_pos))
            left_index = x_pos.index(max(x_pos))
            self.joints[right_index].side.set(2)
            self.joints[left_index].side.set(1)
            label = self.joints[right_index].name()[2:-8]
            self.joints[right_index].otherType.set(label)
            self.joints[left_index].otherType.set(label)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_jnts()
        self.store_output_data(jnts=self.joints)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_hook_groups()
        self.create_axis_reader()
        self.create_puppet_jnts()

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_puppet_joints()
        self.connect_to_hooks()
        self.cleanup_joints_side_aware()
        self.load_rigdata(io_type='drivenKeys', recursive=False)


class ShearHinge(modulecor.RigPuppetModule):
    """ Deformation joints that shear around a corner, to maintain volume for wrist, fingers, etc. """
    def __init__(
            self,
            side,
            module_name,
            hook=None,
            parent_hook=None,
            size=1,
            aim_axis='x',
            shear_clip_start=2,
            shear_clip_end=3,
            push_distance=10,
            parent_joint=None
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param size: float - default size and position multiplier for the guides and joints
        :param hook: OutDataPointer or PyNode - The hinge joint, e.g. elbow joint
        :param parent_hook: OutDataPointer or PyNode - The parent joint, e.g. shoulder joint
        :param aim_axis: str - x, y, z, -x, -y or -z. Aim axis of the joint chain
        :param shear_clip_start: float - If shear values get too big, it usually causes too extreme deformations.
                                         Thus, we create a soft clip setup. This is the start value for the soft clip.
                                         Below this value the clip has no effect.
        :param shear_clip_end: float - End value for the soft clip setup, no values above this are possible.
        :param push_distance: float - Default distance the joints should be towards the inside of the hinge.
        :param parent_joint: OutDataPointer or PyNode - Parent joint for this modules joint. If the value for this
                             is None, the system will attempt to find the joint based on the given hook.
        """
        super().__init__(side=side, module_name=module_name, parent_joint=parent_joint)
        self.hook = hook
        self.parent_hook = parent_hook
        self.size = size
        self.aim_axis = aim_axis
        self.shear_clip_start = shear_clip_start
        self.shear_clip_end = shear_clip_end
        self.push_distance = push_distance

        self.upper_hook_grp = None
        self.lower_hook_grp = None
        self.upper_jnt_grp = None
        self.lower_jnt_grp = None
        self.upper_jnt = None
        self.lower_jnt = None
        self.avg_trn = None
        self.push_trn = None
        self.upper_pup_jnt = None
        self.lower_pup_jnt = None
        self.clipped_shear_output_plugs = {}

    def create_jnts(self):
        """
        Create the main skin joints.
        :TO DO: can we put the joints in the correct positions? Or at least better positions than all in one spot?
        """
        parent = self.get_asset_root_module().skel_grp
        self.upper_jnt = pm.createNode('joint', n=self.mk('upperShear_JNT'), p=parent)
        self.lower_jnt = pm.createNode('joint', n=self.mk('lowerShear_JNT'), p=parent)

        self.joints = [self.upper_jnt, self.lower_jnt]

        for jnt in self.joints:
            jnt.radius.set(self.size)

    def connect_to_main_skeleton(self):
        """ Do the normal connect_to_main_skeleton(), then move the joints to their parent.
            This doesn't have any effect on the rig, because the positions will change again when the pose readers
            are applied. All it does is avoid bones form being drawn frm the hinge to the origin.
            Second joint needs to be parented manually, because we have two floating joints and not a chain here.
        """
        super().connect_to_main_skeleton()
        self.joints[1].setParent(self.joints[0].getParent())
        for jnt in self.joints:
            jnt.t.set(0, 0, 0)
            jnt.r.set(0, 0, 0)

    def create_puppet_jnts(self):
        self.upper_hook_grp = pm.group(em=True, n=self.mk('upperHook_TRN'), p=self.in_hooks_grp)
        self.lower_hook_grp = pm.group(em=True, n=self.mk('lowerHook_TRN'), p=self.in_hooks_grp)
        self.avg_trn = pm.group(em=True, n=self.mk('average_TRN'), p=self.lower_hook_grp)
        self.push_trn = pm.group(em=True, n=self.mk('push_TRN'), p=self.avg_trn)
        self.upper_jnt_grp = pm.group(em=True, n=self.mk('upperJoint_GRP'), p=self.push_trn)
        self.upper_pup_jnt = pm.createNode('joint', n=self.mk('upperPuppet_JNT'), p=self.upper_jnt_grp)
        self.lower_jnt_grp = pm.group(em=True, n=self.mk('lowerJoint_GRP'), p=self.push_trn)
        self.lower_pup_jnt = pm.createNode('joint', n=self.mk('ulowrPuppet_JNT'), p=self.lower_jnt_grp)

        self.puppet_joints = [self.upper_pup_jnt, self.lower_pup_jnt]

        aim_vec = [a * self.size for a in mathutl.vector_from_axis(self.aim_axis)]
        for i, ax in enumerate('xyz'):
            self.upper_pup_jnt.attr(f't{ax}').set(aim_vec[i] * -1)
            self.lower_pup_jnt.attr(f't{ax}').set(aim_vec[i])
        for jnt in self.puppet_joints:
            jnt.radius.set(self.size * 0.5)

    def compute_shear(self):
        for i, grp in enumerate((self.upper_hook_grp, self.lower_hook_grp)):
            jnt = self.puppet_joints[i]
            matrix_vectors = []
            for ax in 'xyz':
                driver = grp if ax == self.aim_axis[-1].lower() else self.avg_trn
                vec_from_matrix = connectutl.create_node(
                    'vectorProduct',
                    matrix=driver.wm[0],
                    operation=3,
                    input1=mathutl.vector_from_axis(ax),
                    n=self.mk(f'{ax}VectorFromWorldMatrix_VEC')
                )
                matrix_vectors.append(vec_from_matrix)
            shear_mat = connectutl.create_node(
                'fourByFourMatrix',
                n=self.mk("shear_MAT"),
                in00=matrix_vectors[0].outputX,
                in01=matrix_vectors[0].outputY,
                in02=matrix_vectors[0].outputZ,
                in10=matrix_vectors[1].outputX,
                in11=matrix_vectors[1].outputY,
                in12=matrix_vectors[1].outputZ,
                in20=matrix_vectors[2].outputX,
                in21=matrix_vectors[2].outputY,
                in22=matrix_vectors[2].outputZ,
            )
            shear_dcm = connectutl.create_node(
                'decomposeMatrix',
                n=self.mk("shear_DCM"),
                inputMatrix=shear_mat.output
            )
            for ax, shear in zip('XYZ', ('shearXY', 'shearXZ', 'shearYZ')):
                plug = connectutl.soft_clip_pos_neg(
                    input_plug=shear_dcm.attr(f'outputShear{ax}'),
                    clip_start=self.shear_clip_start,
                    clip_end=self.shear_clip_end,
                    output_plug=jnt.attr(shear),
                    attrs_holder=self.grp,
                    module_key=self.mk(''),
                    label=f'lowerSoftClip{ax}' if i else f'upperSoftCLip{ax}'
                )
                self.clipped_shear_output_plugs[ax] = plug  # will be overwritten in the 2nd loop but that's ok

    def push_in(self):
        for ax, plug in self.clipped_shear_output_plugs.items():
            push_index = ('XYZ'.index(ax) + 1) % 3
            push_ax = 'XYZ'[push_index]
            if push_ax == self.aim_axis[-1].upper():
                continue
            connectutl.driven_keys(
                driver=plug,
                driven=self.push_trn.attr(f'translate{push_ax}'),
                v=(-self.push_distance, 0, self.push_distance),
                dv=(-self.shear_clip_end, 0, self.shear_clip_end),
            )
        self.publish_nodes['drivenKeys'].append(self.push_trn)

    def connect_to_hooks(self):
        hook = self.get_hook(self.hook)
        parent_hook = self.get_hook(self.parent_hook)

        pm.pointConstraint(hook, self.avg_trn)
        avg_orc = pm.orientConstraint(hook, parent_hook, self.avg_trn)
        avg_orc.interpType.set(2)
        pm.orientConstraint(parent_hook, self.upper_hook_grp)
        pm.orientConstraint(hook, self.lower_hook_grp)

        pm.orientConstraint(self.upper_hook_grp, self.upper_jnt_grp)
        pm.orientConstraint(self.lower_hook_grp, self.lower_jnt_grp)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        self.create_grps()

    def skeleton_build(self):
        super().skeleton_build()
        self.create_jnts()
        self.store_output_data(jnts=self.joints)

    def skeleton_connect(self):
        super().skeleton_connect()
        self.connect_to_main_skeleton()

    def puppet_build(self):
        super().puppet_build()
        self.create_puppet_jnts()
        self.compute_shear()
        self.push_in()
        self.load_rigdata(io_type='drivenKeys', recursive=False)

    def puppet_connect(self):
        super().puppet_connect()
        self.connect_puppet_joints()
        self.connect_to_hooks()
