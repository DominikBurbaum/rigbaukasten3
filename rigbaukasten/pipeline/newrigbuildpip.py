import os
import shutil
import rigbaukasten
from PySide2 import QtWidgets

from rigbaukasten.utils import errorutl, pysideutl, pythonutl


def new_rig_build_from_template(template_name='basic_prop'):
    """ Create a new folder for the current asset and copy the given rig build template into it.
        :param template_name: str - name of a template from resources/rig_build_templates
    """
    if not template_name.endswith('.py'):
        template_name = template_name + '.py'

    asset_name = rigbaukasten.environment.get_asset_name()
    rig_builds_path = rigbaukasten.environment.get_rig_builds_path()
    rig_build_package_path = os.path.join(rig_builds_path, asset_name)
    build_templates_path = os.path.join(rigbaukasten.environment.get_resources_path(), 'rig_build_templates')
    rig_template_src_path = os.path.join(build_templates_path, template_name)

    if os.path.exists(rig_build_package_path):
        folder_content = os.listdir(rig_build_package_path)
        if '__init__.py' in folder_content and f'{asset_name}_build.py' in folder_content:
            raise errorutl.RbkNotUnique(
                f'A rig build for {asset_name} already exists in {rig_builds_path}! '
                'Cannot have multiple rig builds per asset.'
            )
        else:
            raise errorutl.RbkNotUnique(
                f'A folder named {asset_name} already exists in {rig_builds_path}! '
                'Cannot create new rig build. Check if the environment is correctly set and if the existing folder '
                'is needed or can be removed.'
            )
    if not os.path.exists(rig_template_src_path):
        raise errorutl.RbkNotFound(
            f'A rig build template named {template_name} does not exist in {build_templates_path}.'
        )

    os.mkdir(rig_build_package_path)
    init_path = os.path.join(rig_build_package_path, '__init__.py')
    with open(init_path, 'w') as f:
        f.write('')
    rig_build_dst_path = os.path.join(rig_build_package_path, f'{asset_name}_build.py')
    shutil.copyfile(rig_template_src_path, rig_build_dst_path)
    return rig_build_package_path


class ChooseRigBuildFromTemplateUi(pysideutl.MayaDialog):
    """ Simple UI for choosing a rig build template from the resources folder. """
    def __init__(self):
        super().__init__()

        self.setModal(True)
        self.setWindowTitle('Rigbaukasten Project Setter')

        title_layout = QtWidgets.QVBoxLayout()
        self.setLayout(title_layout)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(pysideutl.TitleLabel('Create New Rig Build'))

        base_widget = QtWidgets.QWidget()
        base_lay = QtWidgets.QVBoxLayout()
        base_widget.setLayout(base_lay)
        title_layout.addWidget(base_widget)
        title_layout.addStretch()

        base_lay.addWidget(QtWidgets.QLabel('Choose Template:'))

        self.radio_btns = []
        build_templates_path = os.path.join(rigbaukasten.environment.get_resources_path(), 'rig_build_templates')
        build_templates = [a for a in os.listdir(build_templates_path) if a.endswith('.py')]
        for template_name in build_templates:
            mod = pythonutl.import_module(os.path.join(build_templates_path, template_name))
            radio = QtWidgets.QRadioButton(template_name[:-3])
            radio.description = mod.__doc__.strip()
            radio.toggled.connect(self.set_description)
            base_lay.addWidget(radio)
            self.radio_btns.append(radio)

        self.description_lbl = QtWidgets.QLabel('')
        self.description_lbl.setFixedWidth(300)
        self.description_lbl.setWordWrap(True)
        self.description_lbl.setStyleSheet("border: 1px solid black; padding: 5px;")
        base_lay.addWidget(self.description_lbl)

        self.radio_btns[0].toggle()

        btn = QtWidgets.QPushButton('OK')
        btn.clicked.connect(self.accept)
        base_lay.addWidget(btn)

    def set_description(self):
        radio = self.sender()
        self.description_lbl.setText(radio.description)

    def results(self):
        for radio in self.radio_btns:
            if radio.isChecked():
                return radio.text()


def choose_template_and_create_new_rig_build():
    """ Open the chooser UI and create a new rig build with the selected template. """
    x = ChooseRigBuildFromTemplateUi()
    if x.exec_():
        template_name = x.results()
        new_rig_build_from_template(template_name=template_name)
