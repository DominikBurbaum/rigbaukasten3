from rigbaukasten.core import modulecor

import pymel.core as pm

from rigbaukasten.functions import guidemeshfunc
from rigbaukasten.utils import errorutl, pymelutl


class GuideMesh(modulecor.RigModule):
    """ Use a guide mesh to set guides and weights on the given mesh.

        This module is a pretty hard edge case, think of it more like a tool. It modifies data from other modules
        during the skeleton_build and deform_build steps (placing guides and setting weights). Although this kinda
        breaks the design, it's still a module (for now) for the following reasons:
            - we want to be able to use it in rig_build_templates without having loose code bits in there
            - there is no proper way to add tools in rigbaukasten so far, so it would be a bit of a mess anyway
            - Everything this module does can be published to rig data of other modules, so it'll be easy to get rid
              of it later if needed.
    """
    def __init__(
            self,
            mesh,
            side='C',
            module_name='guideMesh',
            folder='guideMeshSimpleBiped'
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param mesh: PyNode - the adjusted guide mesh that now fits the characters proportions. Must already exist in
                     the scene.
        :param folder: str - Which folder in resources/guide_meshes should be used for the mapping?
        """
        super().__init__(side=side, module_name=module_name)
        self.mesh = mesh
        self.folder = folder

    def check_mesh(self):
        """ Check the given mesh exists and is of type PyNode. """
        if not pm.objExists(self.mesh):
            raise errorutl.RbkNotFound(f'Mesh "{self.mesh}" does not exist!')
        self.mesh = pymelutl.to_pynode(self.mesh)

    def set_guide_positions(self):
        mapping = guidemeshfunc.load_guide_mapping(folder=self.folder)
        guidemeshfunc.set_guides_from_mapping(mapping, override_mesh=self.mesh)

    def load_skinning(self):
        guidemeshfunc.load_skin_for_mesh(mesh=self.mesh, folder=self.folder)

    def skeleton_build(self):
        super().skeleton_build()
        self.check_mesh()
        self.set_guide_positions()

    def deform_build(self):
        super().deform_build()
        self.load_skinning()
