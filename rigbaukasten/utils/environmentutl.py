
import os
import pathlib
import sys
import abc
import glob

from PySide2 import QtWidgets, QtCore
import pymel.core as pm
from rigbaukasten.utils import errorutl, pysideutl


class AbstractEnvironment(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_resources_path(self, resource=None):
        """ Return the path to the resources folder.
            :param resource: (str) Immediately get the path to the given resource (e.g. 'shapes') instead of the
                                   root directory of the resources.
        """
        pass

    @abc.abstractmethod
    def get_asset_name(self):
        """ Get the name of the asset that is currently worked on.
            Rigbaukasten requires to set a single asset in teh environment.
        """
        pass

    @abc.abstractmethod
    def get_rigdata_path(self):
        """ Return the path to the 'rigdata' directory of the current asset.
            All rigdata will be saved and loaded from subfolders of this directory.
        """
        pass

    @abc.abstractmethod
    def get_model_path(self, version=None):
        """ Return the file path to the model of the current asset.
            :param version: (int) If a version is provided get the according version path instead of the latest.
        """
        pass

    @abc.abstractmethod
    def get_rig_builds_path(self):
        """ Return the path of the folder where the rig builds (python packages) are located.
        """
        pass

    @abc.abstractmethod
    def set(self, *args, **kwargs):
        """ Set the environment so all the methods above have enough data to work properly. """
        pass


class Environment(AbstractEnvironment):
    def __init__(self):
        self.ui = 'rigbaukasten_set_env'
        self.proj_text = self.ui + '_project_path'
        self.name_menu = self.ui + '_asset_name'

        self._project_path = None
        self._asset_name = None

    @property
    def asset_name(self):
        if self._asset_name is None:
            raise errorutl.RbkEnvironmentError('Cannot get asset name, set environment first.')
        return self._asset_name

    @asset_name.setter
    def asset_name(self, name):
        self._asset_name = name

    @property
    def project_path(self):
        if self._project_path is None:
            raise errorutl.RbkEnvironmentError('Cannot get project path, set environment first.')
        return self._project_path

    @project_path.setter
    def project_path(self, path):
        self._project_path = path

    def get_resources_path(self, resource=None):
        rigbaukasten_path = pathlib.Path(__file__).parent.parent.resolve()
        resources_path = os.path.join(rigbaukasten_path, 'resources')
        if resource:
            resources_path = os.path.join(resources_path, resource)
        return resources_path

    def get_asset_name(self):
        return self.asset_name

    def get_rigdata_path(self):
        return os.path.join(self.project_path, 'characters', self.asset_name, 'rigdata')

    def get_model_path(self, version=None):
        models_dir = os.path.join(self.project_path, 'characters', self.asset_name, 'model')
        if version:
            file_name = f'{self.asset_name}_mdl_body_{version:03d}_xx.mb'
            return os.path.join(models_dir, file_name)
        else:
            file_name = f'{self.asset_name}_mdl_body_*_xx.mb'
            glob_path = os.path.join(models_dir, file_name)
            versions = glob.glob(glob_path)
            versions.sort()
            return versions[-1]

    def get_rig_builds_path(self):
        project_scripts_path = os.path.join(self.project_path, 'scripts')
        rig_builds_path = os.path.join(project_scripts_path, 'rig_builds')
        if not os.path.exists(rig_builds_path):
            os.makedirs(rig_builds_path)
        if project_scripts_path not in sys.path:
            sys.path.append(project_scripts_path)
        return rig_builds_path

    def set(self, *args, **kwargs):
        x = ProjectSetterUi()
        if x.exec_():
            self._project_path, self._asset_name = x.results()

            print(f'Now working on {self.asset_name} in {self.project_path}')


class ProjectSetterUi(pysideutl.MayaDialog):
    def __init__(self):
        super().__init__()

        self.setModal(True)
        self.setWindowTitle('Rigbaukasten Project Setter')

        title_layout = QtWidgets.QVBoxLayout()
        self.setLayout(title_layout)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(pysideutl.TitleLabel('Set Project'))

        base_widget = QtWidgets.QWidget()
        base_lay = QtWidgets.QVBoxLayout()
        base_widget.setLayout(base_lay)
        title_layout.addWidget(base_widget)

        path_lbl = QtWidgets.QLabel('Project Path:')
        base_lay.addWidget(path_lbl)

        path_widget = QtWidgets.QWidget()
        path_lay = QtWidgets.QHBoxLayout()
        path_widget.setLayout(path_lay)
        self.path_lne = QtWidgets.QLineEdit()
        self.path_lne.setPlaceholderText('/my/fancy/project')
        self.path_lne.setText(pm.workspace(query=1, rootDirectory=1).replace('/', os.sep).replace('\\', os.sep))
        path_lay.addWidget(self.path_lne)
        path_btn = QtWidgets.QPushButton('...')
        path_btn.setFixedWidth(30)
        path_btn.clicked.connect(self.set_path)
        path_lay.addWidget(path_btn)
        base_lay.addWidget(path_widget)

        asset_lbl = QtWidgets.QLabel('Asset Name:')
        base_lay.addWidget(asset_lbl)

        self.asset_cmb = QtWidgets.QComboBox()
        self.update_asset_cmb()
        base_lay.addWidget(self.asset_cmb)

        btn = QtWidgets.QPushButton('OK')
        btn.clicked.connect(self.accept)
        base_lay.addWidget(btn)

    def results(self):
        return self.path_lne.text().strip(), self.asset_cmb.currentText().strip()

    def set_path(self):
        proj_path = pm.fileDialog2(fm=2, cap='Choose Project', okc='OK')[0].replace('/', os.sep).replace('\\', os.sep)
        self.path_lne.setText(proj_path)
        self.update_asset_cmb()

    def update_asset_cmb(self):
        self.asset_cmb.clear()
        folder = os.path.join(self.path_lne.text(), 'characters')
        if os.path.exists(folder):
            assets = [a for a in os.listdir(folder) if '.' not in a]
            for asset in assets:
                self.asset_cmb.addItem(asset)


#     maya_project_path = pm.workspace(query=1, rootDirectory=1).replace('/', os.sep).replace('\\', os.sep)
#
#     def set_path(*_):
#         project_path = pm.fileDialog2(fm=2, cap='Choose Project', okc='OK')[0].replace('/', os.sep).replace('\\', os.sep)
#         pm.textField(self.proj_text, e=True, text=project_path)
#         update_ui(project_path)
#
#     def update_ui(project_path):
#         clear_asset_names()
#         folder = os.path.join(project_path, 'characters')
#         if os.path.exists(folder):
#             pm.textField(self.proj_text, e=True, text=project_path)
#             assets = [a for a in os.listdir(folder) if not '.' in a]
#             set_asset_names(assets)
#
#     def clear_asset_names():
#         for item in pm.optionMenu(self.name_menu, q=True, itemListLong=True) or []:
#             pm.deleteUI(item)
#
#     def set_asset_names(assets):
#         for asset in assets:
#             pm.menuItem(l=asset, p=self.name_menu)
#
#     if pm.window(self.ui, ex=True):
#         pm.deleteUI(self.ui)
#     pm.window(self.ui, title='Rigbaukasten Environment Setter')
#     pm.columnLayout()
#     pm.separator()
#     pm.text(l='Set Environment', fn='boldLabelFont')
#     pm.separator()
#     pm.text(l='Project Path:')
#     pm.rowLayout(nc=2)
#     pm.textField(self.proj_text, placeholderText='/my/fancy/project/', w=300)
#     pm.button(l='...', c=set_path)
#     pm.setParent('..')
#     pm.separator()
#     pm.text(l='Asset name:')
#     pm.optionMenu(self.name_menu)
#     pm.separator()
#     pm.button(l='OK', c=self.set_env_from_ui)
#     update_ui(maya_project_path)
#     pm.showWindow(self.ui)
#
# def set_env_from_ui(self, *_):
#     self.project_path = pm.textField(self.proj_text, q=True, text=True)
#     self.asset_name = pm.optionMenu(self.name_menu, q=True, v=True)
#     pm.deleteUI(self.ui)
#     # rigbaukasten.environment = self