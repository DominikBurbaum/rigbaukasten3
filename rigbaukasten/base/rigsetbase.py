from rigbaukasten.core import modulecor
from rigbaukasten.library import rigsetlib

import pymel.core as pm


class RigSets(modulecor.RigModule):
    def __init__(
            self,
            side='C',
            module_name='rigsets',
    ):
        super().__init__(side=side, module_name=module_name)
        self.load_rigdata(io_type='rigsets')
        parent_set_name = self.mk('parent_RIGSET')
        if pm.objExists(parent_set_name):
            # parent set was already created by load_rigdata()
            self.parent_set = pm.PyNode(parent_set_name)
        else:
            self.parent_set = rigsetlib.create_rigset(parent_set_name)
        self.publish_nodes['rigsets'].append(self.parent_set)
