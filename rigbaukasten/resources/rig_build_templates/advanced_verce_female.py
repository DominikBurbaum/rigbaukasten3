"""
Advanced Verce Female template:
Biped rig with space switches and some extra joints for advanced deformation.
Expects the mesh to be standard verce female topology and will automatically set guides
and skinning accordingly.
"""
import pymel.core as pm
import rigbaukasten
from rigbaukasten.base import geobase, hikbase, guidemeshbase
from rigbaukasten.core import modulecor
from rigbaukasten.deform import skindef
from rigbaukasten.library import spacelib, posereaderlib
from rigbaukasten.puppet import mainpup, jointpup, chainspup
from rigbaukasten.templates import bipedtmp, torsotmp
from rigbaukasten.utils import pymelutl, connectutl
from rigbaukasten.utils.typesutl import Jnt, Ctl


class RigBuild(modulecor.RigBuild):
    def __init__(self):
        super().__init__()

        self.add_module(geobase.Model(
            version=None
        ))

        ################################################################################
        # puppet
        ################################################################################
        self.add_module(mainpup.MainControl(
            size=100,
            plumbob_hook=Jnt('C_neck', -1)
        ))
        self.add_module(bipedtmp.SimpleBiped(
            fingers=('Thumb', 'Index', 'Mid', 'Ring', 'Pinky'),
            toes=(),
            hook=Ctl('C_main', -1),
            size=10
        ))
        for s in 'LR':
            self.add_module(chainspup.SingleCtl(
                side=s,
                module_name='boob',
                size=5,
                hook=Jnt('C_sternum', 0)
            ))
        self.add_module(
            hikbase.HumanIkCustomRig()
        )
        ################################################################################
        # stretchy joints
        ################################################################################
        self.add_module(torsotmp.Ribcage(
            side='C',
            module_name='ribcage',
            breathing_attrs_holder=Ctl('C_spine', 'root'),
            lower_chest_hook=Jnt('C_spine', -1),
            upper_chest_hook=Jnt('C_chest', 0),
            left_clavicle_hook=Jnt('L_arm', 0),
            left_shoulder_hook=Jnt('L_arm', 1),
            right_clavicle_hook=Jnt('R_arm', 0),
            right_shoulder_hook=Jnt('R_arm', 1),
        ))
        for s in 'LR':
            self.add_module(jointpup.StretchyJoint(
                side=s,
                module_name='trapezius',
                hook=Jnt('C_neck', 0),
                end_hook=Jnt(f'{s}_arm', 0),
            ))

        ################################################################################
        # hinges
        ################################################################################
        for i in (1, 2, 3):
            self.add_module(jointpup.VolumePushers(
                side='C',
                module_name=f'spineVolume{i:02}',
                hook=Jnt('C_spine', i),
                parent_hook=Jnt('C_spine', i - 1),
                aim_axis='y',
                size=2,
                push_distance=50,
                limit=40
            ))
        for s in 'LR':
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='armElbowHinge',
                hook=Jnt(f'{s}_arm', 2),
                parent_hook=Jnt(f'{s}_arm', 1),
                size=3,
                down_axis='x' if s == 'L' else '-x',
                out_axis='-z' if s == 'L' else 'z',
                push_distance=30,
                limit=-130,
                side_volume=True
            ))
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='armWristUpperHinge',
                hook=Jnt(f'{s}_arm', 3),
                parent_hook=f'{s}_arm_lowerTwist05_JNT',
                size=1.5,
                down_axis='x' if s == 'L' else '-x',
                out_axis='-y' if s == 'L' else 'y',
                push_distance=15,
                limit=90
            ))
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='armWristLowerHinge',
                hook=Jnt(f'{s}_arm', 3),
                parent_hook=f'{s}_arm_lowerTwist05_JNT',
                size=1.5,
                down_axis='x' if s == 'L' else '-x',
                out_axis='y' if s == 'L' else '-y',
                push_distance=15,
                limit=-90
            ))
            for finger in ('Index', 'Mid', 'Ring', 'Pinky'):
                for i in [1, 2]:
                    self.add_module(jointpup.SimpleHingeHelpers(
                        side=s,
                        module_name=f'hand{finger}{i:02}Hinge',
                        hook=Jnt(f'{s}_hand{finger}', i),
                        parent_hook=Jnt(f'{s}_hand{finger}', i - 1),
                        size=.7,
                        down_axis='x' if s == 'L' else '-x',
                        out_axis='y' if s == 'L' else '-y',
                        push_distance=5,
                        limit=-90
                    ))
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='legHipFrontHinge',
                hook=Jnt(f'{s}_leg', 1),
                parent_hook=f'{s}_leg_hingeDriver_TRN',
                size=5,
                down_axis='x' if s == 'L' else '-x',
                out_axis='-z' if s == 'L' else 'z',
                push_distance=40,
                limit=-90
            ))
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='legHipSideHinge',
                hook=Jnt(f'{s}_leg', 1),
                parent_hook=f'{s}_leg_hingeDriver_TRN',
                size=5,
                down_axis='x' if s == 'L' else '-x',
                out_axis='y' if s == 'L' else '-y',
                push_distance=40,
                limit=90
            ))
            self.add_module(jointpup.SimpleHingeHelpers(
                side=s,
                module_name='legKneeHinge',
                hook=Jnt(f'{s}_leg', 2),
                parent_hook=Jnt(f'{s}_leg', 1),
                size=4,
                down_axis='x' if s == 'L' else '-x',
                out_axis='z' if s == 'L' else '-z',
                push_distance=40,
                limit=140
            ))

        ################################################################################
        # deform
        ################################################################################
        self.add_module(skindef.SimpleSkin(
            side='C',
            module_name='bodySkin',
            joints=Jnt('C_spine', 0),
            geo=self.geo_grp
        ))

        self.add_module(guidemeshbase.GuideMesh(
            mesh=f'{rigbaukasten.environment.get_asset_name()}_body_mdl',
            folder='guideMeshVerceAdvancedFemale'
        ))

    def hip_hinge_reference(self):
        """ Create a reference transform for the hip hinges
            (hip joint cannot be used because it has the wrong orientation)
        """
        for s in 'LR':
            jnt = self.modules['C_biped'].modules[f'{s}_leg'].upper_twist_joints[0]
            trn = pm.group(em=True, p=jnt, n=f'{s}_leg_hingeDriver_TRN')
            pm.orientConstraint(self.modules['C_biped'].modules['C_spine'].joints[0], trn, mo=True)

    def boob_psd(self):
        """ Add some driven keys to make boobs more fleshy. """
        for s in 'LR':
            inv = -1 if s == 'R' else 1
            ctl = pm.PyNode(f'{s}_boob_00_CTL')
            grp = pm.PyNode(f'{s}_boob_00Offset_GRP')
            y_grp = pm.group(ctl, n=f'{s}_boob_00DrivenY_GRP', p=grp)
            z_grp = pm.group(ctl, n=f'{s}_boob_00DrivenZ_GRP', p=y_grp)
            reader = posereaderlib.axis_reader(
                read_trn=self.modules['C_biped'].modules[f'{s}_arm'].joints[0],
                reference_trn=self.modules['C_biped'].modules['C_chest'].joints[0],
                module_key=f'{s}_boob',
                label='pose'
            )
            connectutl.driven_keys(driver=reader[1], driven=y_grp.tx, dv=(-40, 0, 40), v=(-1 * inv, 0, .5 * inv))
            connectutl.driven_keys(driver=reader[1], driven=y_grp.tz, dv=(-40, 0, 40), v=(1 * inv, 0, -.5 * inv))
            connectutl.driven_keys(driver=reader[1], driven=y_grp.rx, dv=(-40, 0, 40), v=(1.5, 0, -3))
            connectutl.driven_keys(driver=reader[1], driven=y_grp.ry, dv=(-40, 0, 40), v=(-10, 0, 7))

            connectutl.driven_keys(driver=reader[2], driven=z_grp.ty, dv=(-20, 0, 40), v=(-0.5 * inv, 0, 1.7 * inv))
            connectutl.driven_keys(driver=reader[2], driven=z_grp.sy, dv=(-20, 0, 40), v=(.9, 1, 1.3))

    @staticmethod
    def space_switches():
        ctl_spaces = {
            'C_neck_02_CTL': {
                'constraint': pm.orientConstraint,
                'Neck': None,
                'Chest': 'C_spine_04_JNT',
                'Hips': 'C_spine_00_JNT',
                'Main': 'C_main_01_CTL',
            }
        }
        for s in 'LR':
            ctl_spaces.update({
                f'{s}_arm_wristIk_CTL': {
                    'Main': None,
                    'Clavicle': f'{s}_arm_clavicle_CTL',
                    'Chest': 'C_spine_04_JNT',
                    'Hips': 'C_spine_00_JNT',
                    'Head': 'C_neck_02_CTL'
                },
                f'{s}_arm_wristIkPole_CTL': {
                    'Main': 'C_main_01_CTL',
                    'Clavicle': f'{s}_arm_clavicle_CTL',
                    'Chest': None,
                    'Hips': 'C_spine_00_JNT',
                    'Root': 'C_spine_root_CTL',
                },
                f'{s}_arm_shoulderFk_CTL': {
                    'constraint': pm.orientConstraint,
                    'Clavicle': None,
                    'Chest': 'C_spine_04_JNT',
                },
                f'{s}_leg_ankleIk_CTL': {
                    'Main': None,
                    'Hips': 'C_spine_00_JNT',
                    'Root': 'C_spine_root_CTL',
                },
                f'{s}_leg_ankleIkPole_CTL': {
                    'Main': 'C_main_01_CTL',
                    'Hips': None,
                    'Root': 'C_spine_root_CTL',
                    'Foot': f'{s}_leg_ankleIk_CTL'
                }
            })
        ctl_spaces = pymelutl.to_pynode(ctl_spaces)
        for ctl, spaces in ctl_spaces.items():
            spacelib.add_spaces(ctl=ctl, **spaces)

    ################################################################################
    # build steps
    ################################################################################

    def puppet_build(self):
        super().puppet_build()
        self.hip_hinge_reference()

    def puppet_build_post(self):
        super().puppet_build_post()
        self.boob_psd()
        self.space_switches()
