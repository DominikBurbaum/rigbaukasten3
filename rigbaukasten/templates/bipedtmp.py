import pymel.core as pm


from rigbaukasten.core import modulecor
from rigbaukasten.puppet import spinepup, chainspup, limbspup
from rigbaukasten.templates import handtmp
from rigbaukasten.utils.typesutl import Jnt


class SimpleBiped(modulecor.RigPuppetModule):
    def __init__(
            self,
            side='C',
            module_name='biped',
            fingers=('Thumb', 'Index', 'Mid', 'Ring', 'Pinky'),
            toes=(),
            hook=None,
            size=1,
            parent_joint=None,
    ):
        super().__init__(side=side, module_name=module_name, hook=hook, size=size, parent_joint=parent_joint)
        self.fingers = fingers
        self.toes = toes

        self.add_module(spinepup.Spine(
            side='C',
            module_name='spine',
            size=size * 3,
            hook=hook
        ))
        # self.add_module(chainspup.SimpleFk(
        #     side='C',
        #     module_name='spine',
        #     size=size * 3,
        #     nr_of_joints=5,
        #     hook=hook,
        #     aim=(0, 1, 0),
        #     up=(1, 0, 0),
        #     world_up=(1, 0, 0),
        # ))
        self.add_module(chainspup.SingleCtl(
            side='C',
            module_name='chest',
            size=size * 1.5,
            hook=Jnt('C_spine', -1)
        ))
        self.add_module(chainspup.SimpleFk(
            side='C',
            module_name='neck',
            size=size * 1.5,
            nr_of_joints=3,
            hook=Jnt('C_chest', -1),
            aim=(0, 1, 0),
            up=(1, 0, 0),
            world_up=(1, 0, 0),
        ))
        for s in 'LR':
            self.add_module(limbspup.FKIkLimb(
                side=s,
                module_name='arm',
                size=size * 1.5,
                hook=Jnt('C_chest', -1),
                ik_hook=hook,
                collision_spread=1,
            ))
            if fingers:
                self.add_module(handtmp.SimpleFkHand(
                    side=s,
                    module_name='hand',
                    size=size * 0.3,
                    hook=Jnt(f'{s}_arm', -1),
                    fingers=fingers
                ))
            self.add_module(limbspup.FKIkLimb(
                side=s,
                module_name='leg',
                size=size * 1.5,
                hook=Jnt('C_spine', 0),
                ik_hook=hook,
                collision_spread=3,
                as_leg=True,
                with_foot=True
            ))
            if toes:
                self.add_module(handtmp.SimpleFkToes(
                    side=s,
                    module_name='foot',
                    size=size * 0.3,
                    hook=Jnt(f'{s}_leg', -1),
                    toes=toes
                ))

    def get_default_chest_and_neck_position(self):
        """ Compose positions for the chest and neck guide based on the characters height. """
        asset_root = self.get_asset_root_module()
        model = pm.listRelatives(asset_root.geo_grp)
        if model:
            height = pm.exactWorldBoundingBox(model)[4]
            shoulder = height * 0.8
        else:
            shoulder = self.size * 10
        positions = [
            (0, shoulder * 0.95, 0),  # chest
            (0, shoulder * 1.05, 0),  # neck root
            (0, shoulder * 1.1, 0),  # neck mid
            (0, shoulder * 1.15, 0),  # head
        ]
        return positions

    def apply_default_chest_and_neck_position(self):
        """ Move the guides to their default positions. """
        positions = self.get_default_chest_and_neck_position()

        chest_position = positions.pop(0)
        self.modules['C_chest'].gde.setTranslation(chest_position, 'world')

        for guide, pos in zip(self.modules['C_neck'].guides, positions):
            guide.setTranslation(pos, 'world')

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        self.create_grps()
        super().skeleton_build_pre()

    def skeleton_build(self):
        super().skeleton_build()
        self.apply_default_chest_and_neck_position()
