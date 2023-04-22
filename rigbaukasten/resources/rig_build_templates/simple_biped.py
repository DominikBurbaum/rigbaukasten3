"""
Simple biped template:
Basic puppet rig + skinCluster for a biped. No extra joints or advanced deformation.
"""
import rigbaukasten
from rigbaukasten.base import geobase
from rigbaukasten.core import modulecor
from rigbaukasten.deform import skindef
from rigbaukasten.puppet import mainpup
from rigbaukasten.templates import bipedtmp
from rigbaukasten.utils.typesutl import Jnt, Ctl


class RigBuild(modulecor.RigBuild):
    def __init__(self):
        super().__init__(asset_name=rigbaukasten.environment.get_asset_name())

        self.add_module(geobase.Model(
            path=rigbaukasten.environment.get_model_path(version=None)
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

        ################################################################################
        # deform
        ################################################################################
        self.add_module(skindef.SkinSet(
            side='C',
            module_name='bodySkin',
            joints=Jnt('C_spine', 0)
        ))
