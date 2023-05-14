import math
import os
from xml.etree import ElementTree

import rigbaukasten
from rigbaukasten.core import modulecor
from rigbaukasten.utils import attrutl

import pymel.core as pm
from maya import mel
from maya.app.hik import retargeter


def default_skeleton_t_pose_setter():
    """ Rotate the shoulder, elbow and wrist joints to a world space T pose based on default names. """
    xforms = {
        'L_arm_shoulder_JNT': (0, 1, 0),
        'L_arm_elbow_JNT': (0, -2, 0),
        'L_arm_wrist_JNT': (0, 1, 0),
        'R_arm_shoulder_JNT': (180, -1, 0),
        'R_arm_elbow_JNT': (180, 2, 0),
        'R_arm_wrist_JNT': (180, -1, 0),
    }
    for jnt_name, rot in xforms.items():
        pm.xform(jnt_name, ws=True, ro=rot)


def default_skeleton_bind_pose_setter():
    """ Rotate the shoulder, elbow and wrist joints to local 0, 0, 0 based on default names. """
    for s in 'LR':
        for n in ('shoulder', 'elbow', 'wrist'):
            jnt_name = f'{s}_arm_{n}_JNT'
            pm.xform(jnt_name, ro=(0, 0, 0))


def default_rig_t_pose_setter():
    """ Rotate the shoulder, elbow and wrist CTLs to a world space T pose based on default names. """
    xforms = {
        'L_arm_shoulderFk_CTL': (0, 1, 0),
        'L_arm_elbowFk_CTL': (0, -2, 0),
        'L_arm_wristFk_CTL': (0, 1, 0),
        'R_arm_shoulderFk_CTL': (180, -1, 0),
        'R_arm_elbowFk_CTL': (180, 2, 0),
        'R_arm_wristFk_CTL': (180, -1, 0),
    }
    for ctl_name, rot in xforms.items():
        pm.xform(ctl_name, ws=True, ro=rot)
    for s in 'LR':
        pm.matchTransform(f'{s}_arm_wristIk_CTL', f'{s}_arm_wristFk_CTL')
        pm.matchTransform(f'{s}_arm_wristIkPole_CTL', f'{s}_arm_elbowFk_CTL', pos=True, rot=False, scl=False)
    pm.xform(f'R_arm_wristIk_CTL', ro=(180, 0, 0), r=True)


def default_rig_bind_pose_setter():
    """ Rotate the shoulder, elbow and wrist CTLs to local 0, 0, 0 based on default names. """
    for s in 'LR':
        for n in ('shoulder', 'elbow', 'wrist'):
            ctl_name = f'{s}_arm_{n}Fk_CTL'
            pm.xform(ctl_name, ro=(0, 0, 0))
        pm.xform(f'{s}_arm_wristIk_CTL', t=(0, 0, 0), ro=(0, 0, 0))
        pm.xform(f'{s}_arm_wristIkPole_CTL', t=(0, 0, 0))


class HumanIkCustomRig(modulecor.RigModule):
    """
    Create a HumanIk characterization and a HumanIk custom rig, so the rig can be used with moCap data.

    The joint and CTL mapping will be read from xml files that were previously exported from the HumanIk window
    in maya. If the rig was created from a ribaukasten biped template, you can use a xml file from the
    hik_templates in the resources.
    If these get used a lot it might make sense to create publish and load functions so the mappings can be used
    as rig data. For now, I assume that the templates will be good enough for 95% of rigs, thus the stupid simple
    paths-as-arguments workflow - good enough to allow custom files where needed, but with no overhead.
    If you need to create a fresh mapping for a custom character, proceed as follows:
    - run the rig until skeleton_connect
    - create the mapping in hte HumanIk window and export it
    - run the rig until puppet_connect
    - create a custom rig mapping using the HumanIk window and export it as well
    - (optional) edit the custom rig xml manually to add more CTLs to the custom rig. In the HumanIK window you can
      only set very basic CTLs. But if you just add other ones to the xml (e.g. fingers or ik CTLs), they will
      work in the resulting HumanIk rig. See the hik_templates in the resources for examples.

    Also, we need to set the character to a proper T pose and back to bind pose during the characterization. For
    this please provide functions that set the given poses for your character. The default functions that are available
    in this file only set the arms to T pose - if the feet or spine also need to be posed please provide custom
    functions for your character.
    The T pose for the HumanIK system should be as straight as possible. Arms parallel to the world X axis, spine,
    neck and legs parallel to the world Y axis and feet parallel to the world Z axis. This is important to ensure that
    two characters can be matched without any baked-in offsets.
    """
    def __init__(
            self,
            skeleton_t_pose_setter=default_skeleton_t_pose_setter,
            skeleton_bind_pose_setter=default_skeleton_bind_pose_setter,
            rig_t_pose_setter=default_rig_t_pose_setter,
            rig_bind_pose_setter=default_rig_bind_pose_setter,
            skeleton_xml_path='simple_biped',
            rig_xml_path='simple_biped',
    ):
        """
        :param skeleton_t_pose_setter: Function that sets the joints to T pose in skeleton_connect_post.
        :param skeleton_bind_pose_setter: Function that resets the joints back to bind pose after T pose was set.
        :param rig_t_pose_setter: Function that sets the CTLs to T pose in puppet_connect_post. This is only required
                                  if the rig_xml is used from hik_templates or another character. If the rig_xml
                                  was created specifically for this character, the rig T pose & bind pose setters
                                  are not used.
        :param rig_bind_pose_setter: Function that resets the CTLs back to bind pose after T pose was set.
        :param skeleton_xml_path: Path to the xml file with the skeleton definition or template name.
        :param rig_xml_path: Path to the xml file with the custom rig definition or template name.
        """
        super().__init__(side='C', module_name=f'{rigbaukasten.environment.get_asset_name()}HumanIk')
        self.skeleton_t_pose_setter = skeleton_t_pose_setter
        self.skeleton_bind_pose_setter = skeleton_bind_pose_setter
        self.rig_t_pose_setter = rig_t_pose_setter
        self.rig_bind_pose_setter = rig_bind_pose_setter

        self.skeleton_xml_root = None
        self.rig_xml_root = None
        self.char_node = None
        self.skeleton_mapping = {}

        if os.path.exists(skeleton_xml_path):
            self.skeleton_xml_path = skeleton_xml_path
        else:
            skeleton_template = skeleton_xml_path
            self.skeleton_xml_path = os.path.join(
                rigbaukasten.environment.get_resources_path('hik_templates'),
                skeleton_template,
                f'{skeleton_template}_skeleton_definition.xml'
            )

        if os.path.exists(rig_xml_path):
            self.rig_xml_path = rig_xml_path
        else:
            rig_template = rig_xml_path
            self.rig_xml_path = os.path.join(
                rigbaukasten.environment.get_resources_path('hik_templates'),
                rig_template,
                f'{rig_template}_rig_definition.xml'
            )

        for plugin in ('mayaHIK', 'mayaCharacterization', 'retargeterNodes'):
            if not pm.pluginInfo(plugin, q=True, l=True):
                pm.loadPlugin(plugin)

    def read_skeleton_xml(self):
        tree = ElementTree.parse(self.skeleton_xml_path)
        self.skeleton_xml_root = tree.getroot()

    def skeleton_xml_to_dict(self):
        """ Reads the data from the skeleton definition file (xml) and saves it in the
            skeleton_mapping dict for further use.
        """
        for item in self.skeleton_xml_root[0]:
            hik_name = item.attrib['key']
            rbk_name = item.attrib['value']
            self.skeleton_mapping[hik_name] = rbk_name

    def create_character_node(self):
        """ guess what """
        self.char_node = pm.createNode('HIKCharacterNode', n=self.mk('00_HIK'))

    def define_skeleton(self):
        """ This is the actual characterization. Each joint gets connected to the character node. """
        for hik_name, rbk_name in self.skeleton_mapping.items():
            if pm.objExists(rbk_name):
                pm.connectAttr(f'{rbk_name}.message', f'{self.char_node}.{hik_name}')
                attrutl.add_string(rbk_name, 'Character', self.char_node)

    def lock_characterization(self):
        """ Lock the characterization, so we can set the rig back to bind pose.
            This is poorly wrapped MEL code, but it works :)
        """
        # make sure the HIK window is opened
        mel.eval('HIKCharacterControlsTool')
        # make sure the definition tab is active
        mel.eval('hikSelectDefinitionTab')
        # first update, to get the skeleton definition working
        mel.eval('hikUpdateDefinitionUI();')
        # lock characterization
        mel.eval(f'hikCharacterLock("{self.char_node}", 1, 1);')
        # second update, to get the lock working
        mel.eval('hikUpdateDefinitionUI();')

    def read_rig_xml(self):
        tree = ElementTree.parse(self.rig_xml_path)
        self.rig_xml_root = tree.getroot()

    def adjust_rig_xml(self):
        """
        Adjust the data in the rig xml file for the current character. Only used if the rig xml file was not
        specifically created for this character.
        Adjustments:
        - Put the current character name in the rig xml to avoid the popup warning that the wrong character is used.
        - While in T pose: Calculate and set offsets from joints to CTLs, to make sure ik CTLs are properly matched.
        """
        if self.rig_xml_root.attrib["dest"] == self.char_node.name():
            # If the custom rig xml was created for this character, don't change anything!
            return
        self.rig_xml_root.attrib["dest"] = self.char_node.name()
        self.rig_t_pose_setter()
        for mapped_retargeter in self.rig_xml_root:
            jnt = mapped_retargeter.attrib['destSkel']
            ctl = mapped_retargeter.attrib['destRig']
            typ = mapped_retargeter.attrib['type']
            if pm.objExists(jnt) and pm.objExists(ctl):
                jnt = pm.PyNode(jnt)
                ctl = pm.PyNode(ctl)
                offset_matrix = ctl.wm[0].get() * jnt.wim[0].get()
                if typ == 'T':
                    offset = offset_matrix.translate
                    if mapped_retargeter.attrib['body'] in ('LeftLeg', 'RightLeg', 'LeftForeArm', 'RightForeArm'):
                        if all([ctl.attr(f'r{ax}').get(l=True) for ax in 'xyz']):
                            # Knee or elbow ctl with no rotation - that's a pole vector and should not have any offset.
                            offset = (0, 0, 0)
                else:
                    radians = offset_matrix.rotate.asEulerRotation()
                    offset = [math.degrees(x) for x in radians]
                for ax, value in zip('XYZ', offset):
                    mapped_retargeter.attrib['offset' + ax] = value
        self.rig_bind_pose_setter()

    def define_custom_rig(self):
        """ Create the custom rig nodes and connections from the xml data. """
        ret = retargeter.HIKRetargeter(self.char_node.name())
        ret.fromXML(self.rig_xml_root, self.char_node.name())
        ret.toGraph()
        mel.eval('hikSelectCustomRigTab;')  # update the UI

    def skeleton_connect_post(self):
        super().skeleton_connect_post()
        self.read_skeleton_xml()
        self.skeleton_xml_to_dict()
        self.create_character_node()
        self.define_skeleton()
        self.skeleton_t_pose_setter()
        self.lock_characterization()
        self.skeleton_bind_pose_setter()

    def puppet_connect_post(self):
        super().puppet_connect_post()
        self.read_rig_xml()
        self.adjust_rig_xml()
        self.define_custom_rig()
