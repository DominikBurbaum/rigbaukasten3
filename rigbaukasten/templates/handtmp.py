import copy

from rigbaukasten.core import modulecor
import pymel.core as pm

from rigbaukasten.library import guidelib
from rigbaukasten.puppet import jointpup, chainspup
from rigbaukasten.utils import attrutl, connectutl, mathutl


class SimpleFkHand(modulecor.RigPuppetModule):
    def __init__(
            self,
            side,
            module_name,
            fingers=('Thumb', 'Index', 'Mid', 'Ring', 'Pinky'),
            hook=None,
            size=1,
            parent_joint=None,
    ):
        super().__init__(side=side, module_name=module_name, hook=hook, size=size, parent_joint=parent_joint)
        self.fingers = fingers

        for finger in self.fingers:
            self.add_module(chainspup.SimpleFk(
                side=self.side,
                module_name=f'{module_name}{finger}',
                size=size,
                nr_of_joints=5,
                hook=hook,
                world_up_type=guidelib.ROOT_GUIDE,
                tip_joint_aim=True,
                tip_has_ctl=False
            ))

    def get_default_finger_positions(self):
        """ Compose positions for the finger digits, so they look like a hand. """
        asset_root = self.get_asset_root_module()
        model = pm.listRelatives(asset_root.geo_grp)
        if model:
            height = pm.exactWorldBoundingBox(model)[4]
            shoulder = height * 0.8
        else:
            shoulder = self.size * 10
        spacing = self.size
        nr = len(self.fingers)
        thumb_root = (shoulder * 0.7 * self.inv, shoulder, spacing * 2)
        thumb_tip = (shoulder * 0.76 * self.inv, shoulder, spacing * 3)
        thumb_positions = [
            thumb_root,
            mathutl.position_between(thumb_root, thumb_tip, 0.1),
            mathutl.position_between(thumb_root, thumb_tip, 0.45),
            mathutl.position_between(thumb_root, thumb_tip, 0.8),
            thumb_tip
        ]
        index_root = (shoulder * 0.72 * self.inv, shoulder, spacing)
        index_tip = (shoulder * 0.82 * self.inv, shoulder, spacing)
        index_positions = [
            index_root,
            mathutl.position_between(index_root, index_tip, 0.45),
            mathutl.position_between(index_root, index_tip, 0.7),
            mathutl.position_between(index_root, index_tip, 0.85),
            index_tip
        ]
        hand_positions = [thumb_positions, index_positions]
        for i in range(nr - 2):
            x_offset = (spacing - (i * spacing)) * self.inv * 0.5
            z_offset = spacing * (i + 1)
            positions = [(p[0] + x_offset, p[1], p[2] - z_offset) for p in index_positions]
            hand_positions.append(positions)
        return hand_positions

    def apply_default_finger_positions(self):
        """ Move the guides to their default positions. """
        hand_positions = self.get_default_finger_positions()
        for mod, finger_positions in zip(self.modules.values(), hand_positions):
            for guide, pos in zip(mod.guides, finger_positions):
                guide.setTranslation(pos, 'world')

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        self.create_grps()
        super().skeleton_build_pre()

    def skeleton_build(self):
        super().skeleton_build()
        self.apply_default_finger_positions()


class SimpleFkToes(modulecor.RigPuppetModule):
    def __init__(
            self,
            side,
            module_name,
            toes=('Thumb', 'Index', 'Mid', 'Ring', 'Pinky'),
            hook=None,
            size=1,
            parent_joint=None,
    ):
        super().__init__(side=side, module_name=module_name, hook=hook, size=size, parent_joint=parent_joint)
        self.toes = toes

        for i, toe in enumerate(self.toes):
            self.add_module(chainspup.SimpleFk(
                side=self.side,
                module_name=f'{module_name}{toe}',
                size=size,
                nr_of_joints=4 if i else 3,
                hook=hook,
                world_up_type=guidelib.ROOT_GUIDE,
                tip_joint_aim=True,
                tip_has_ctl=False
            ))

    def get_default_toe_positions(self):
        """ Compose positions for the toe digits, so they look like a foot. """
        asset_root = self.get_asset_root_module()
        model = pm.listRelatives(asset_root.geo_grp)
        if model:
            foot = pm.exactWorldBoundingBox(model)[5]
        else:
            foot = self.size * 10
        spacing = self.size
        nr = len(self.toes)
        thumb_root = [foot * self.inv, 0, foot]
        thumb_tip = [foot * self.inv, 0, foot + spacing]
        thumb_positions = [
            thumb_root,
            mathutl.position_between(thumb_root, thumb_tip, 0.5),
            thumb_tip
        ]
        foot_positions = [thumb_positions]
        root = thumb_root
        tip = thumb_tip
        for i in range(nr - 1):
            root = copy.deepcopy(root)
            tip = copy.deepcopy(tip)
            root[0] += spacing * self.inv
            tip[0] += spacing * self.inv
            positions = [
                root,
                mathutl.position_between(root, tip, 0.333),
                mathutl.position_between(root, tip, 0.666),
                tip
            ]
            foot_positions.append(positions)
        return foot_positions

    def apply_default_toe_positions(self):
        """ Move the guides to their default positions. """
        foot_positions = self.get_default_toe_positions()
        for mod, toe_positions in zip(self.modules.values(), foot_positions):
            for guide, pos in zip(mod.guides, toe_positions):
                guide.setTranslation(pos, 'world')

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        self.create_grps()
        super().skeleton_build_pre()

    def skeleton_build(self):
        super().skeleton_build()
        self.apply_default_toe_positions()
