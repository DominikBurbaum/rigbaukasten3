from rigbaukasten.core import modulecor
import pymel.core as pm


class BlendShape(modulecor.RigModule):
    def __init__(
            self,
            side,
            module_name,
            geo='',
    ):
        super().__init__(side=side, module_name=module_name)
        self.geo = geo
        self.blendshape = None

    def create_blendshape(self):
        self.blendshape = pm.blendShape(self.geo, n=self.mk('shapes_BLS'))[0]
        self.publish_nodes['blendshapes'] += [self.blendshape]
        # immediately load the shapes
        self.load_rigdata('blendshapes', recursive=False)

    def deform_build(self):
        super().deform_build()
        self.create_blendshape()
