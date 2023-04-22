"""
Basic prop template:
Just a single CTL + main control. For simple props or as a starting point for custom setups.
"""
import rigbaukasten
from rigbaukasten.base import geobase
from rigbaukasten.core import modulecor
from rigbaukasten.puppet import mainpup, chainspup
from rigbaukasten.utils.typesutl import Jnt, Ctl


class RigBuild(modulecor.RigBuild):
    def __init__(self):
        super().__init__(asset_name=rigbaukasten.environment.get_asset_name())

        self.add_module(geobase.Model(
            path=rigbaukasten.environment.get_model_path(version=None)
        ))
        self.add_module(mainpup.MainControl(
            size=100,
            plumbob_hook=Jnt('C_base', -1)
        ))
        self.add_module(chainspup.SingleCtl(
            side='C',
            module_name='base',
            size=15,
            hook=Ctl('C_main', -1)
        ))
