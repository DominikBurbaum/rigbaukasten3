import os

import rigbaukasten
from rigbaukasten.core import modulecor

from rigbaukasten.utils import errorutl, fileutl


class FileLoader(modulecor.RigModule):
    """ Load the given file into the scene. """
    def __init__(
            self,
            path,
            side='C',
            module_name='geo',
            load_step='skeleton_build'
    ):
        """
        :param side: str - C, L or R
        :param module_name: str - unique name for the module
        :param path: str - path to the file
        :param load_step: str - At which build step should the file be loaded?
        """
        super().__init__(side=side, module_name=module_name)
        if os.path.exists(path):
            self.path = path
        else:
            raise errorutl.RbkInvalidPath(f'file does not exist: {path}')
        self.load_step = load_step

        self.root_nodes = None
        self.constraints_loaded = False

    def load_file(self):
        self.root_nodes = fileutl.import_file(self.path)
        for rn in self.root_nodes:
            rn.setParent(self.static_grp)
            self.publish_nodes['constraints'].append(rn)

    def skeleton_build_pre(self):
        super().skeleton_build_pre()
        if self.load_step == 'skeleton_build_pre':
            self.load_file()

    def skeleton_build(self):
        super().skeleton_build()
        if self.load_step == 'skeleton_build':
            self.load_file()

    def skeleton_build_post(self):
        super().skeleton_build_post()
        if self.load_step == 'skeleton_build_post':
            self.load_file()

    def skeleton_connect_pre(self):
        super().skeleton_connect_pre()
        if self.load_step == 'skeleton_connect_pre':
            self.load_file()

    def skeleton_connect(self):
        super().skeleton_connect()
        if self.load_step == 'skeleton_connect':
            self.load_file()

    def skeleton_connect_post(self):
        super().skeleton_connect_post()
        if self.load_step == 'skeleton_connect_post':
            self.load_file()

    def puppet_build_pre(self):
        super().puppet_build_pre()
        if self.load_step == 'puppet_build_pre':
            self.load_file()

    def puppet_build(self):
        super().puppet_build()
        if self.load_step == 'puppet_build':
            self.load_file()

    def puppet_build_post(self):
        super().puppet_build_post()
        if self.load_step == 'puppet_build_post':
            self.load_file()

    def puppet_connect_pre(self):
        super().puppet_connect_pre()
        if self.load_step == 'puppet_connect_pre':
            self.load_file()

    def puppet_connect(self):
        super().puppet_connect()
        if self.load_step == 'puppet_connect':
            self.load_file()

    def puppet_connect_post(self):
        super().puppet_connect_post()
        if self.load_step == 'puppet_connect_post':
            self.load_file()

    def deform_build_pre(self):
        super().deform_build_pre()
        if self.load_step == 'deform_build_pre':
            self.load_file()

    def deform_build(self):
        super().deform_build()
        if self.load_step == 'deform_build':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def deform_build_post(self):
        super().deform_build_post()
        if self.load_step == 'deform_build_post':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def deform_connect_pre(self):
        super().deform_connect_pre()
        if self.load_step == 'deform_connect_pre':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def deform_connect(self):
        super().deform_connect()
        if self.load_step == 'deform_connect':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def deform_connect_post(self):
        super().deform_connect_post()
        if self.load_step == 'deform_connect_post':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def finalize_pre(self):
        super().finalize_pre()
        if self.load_step == 'finalize_pre':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def finalize(self):
        super().finalize()
        if self.load_step == 'finalize':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)

    def finalize_post(self):
        super().finalize_post()
        if self.load_step == 'finalize_post':
            self.load_file()
        if self.root_nodes and not self.constraints_loaded:
            self.load_rigdata('constraints', recursive=False)


class Model(FileLoader):
    """ Load the model for the current asset into the rigs GEO_GRP. """
    def __init__(
            self,
            version=None,
            side='C',
            module_name='model',
            load_step='skeleton_build'
    ):
        """
        :param side: str - C, L or R - Should probably always be 'C'
        :param module_name: str - unique name for the module - Should probably always be 'Model'
        :param version: int - version of the model, None will load teh latest one
        :param load_step: str - At which build step should the model be loaded?
        """
        super().__init__(
            path=rigbaukasten.environment.get_model_path(version=version),
            side=side,
            module_name=module_name,
            load_step=load_step
        )

    def load_file(self):
        self.root_nodes = fileutl.import_file(self.path)
        grp = self.get_asset_root_module().geo_grp
        for rn in self.root_nodes:
            rn.setParent(grp)
            self.publish_nodes['constraints'].append(rn)
