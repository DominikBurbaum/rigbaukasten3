import time
from functools import partial

from PySide2 import QtWidgets, QtCore, QtGui
import pymel.core as pm
from maya import utils

from rigbaukasten.functions import animtoolsfunc
from rigbaukasten.utils import pysideutl


class FkIkSnapUI(pysideutl.MayaDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Rigbaukasten Fk Ik Snapper')

        title_layout = QtWidgets.QVBoxLayout()
        self.setLayout(title_layout)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(pysideutl.TitleLabel('Fk Ik Snapper'))

        base_widget = QtWidgets.QWidget()
        base_lay = QtWidgets.QVBoxLayout()
        base_widget.setLayout(base_lay)
        title_layout.addWidget(base_widget)

        rigs_widget = pysideutl.GroupBoxWithBorder('Rigs')
        rigs_lay = QtWidgets.QVBoxLayout()
        rigs_widget.setLayout(rigs_lay)
        base_lay.addWidget(rigs_widget)

        refresh_btn = QtWidgets.QPushButton('')
        try:
            pixmap = QtWidgets.QStyle.SP_BrowserReload
            icon = self.style().standardIcon(pixmap)
            refresh_btn.setIcon(icon)
            refresh_btn.setFixedWidth(20)
            refresh_btn.setFixedHeight(20)
            refresh_btn.setStyleSheet('background-color: rgba(255, 255, 255, 0); border: 0px;')
        except RuntimeError:
            refresh_btn.setText("refresh")
        rigs_lay.addWidget(refresh_btn, alignment=QtCore.Qt.AlignRight)
        refresh_btn.clicked.connect(self.refresh)

        networks = self.get_networks()
        self.network_checks = {}
        for asset_name, data in networks.items():
            asset_lbl = QtWidgets.QLabel(f'{asset_name}:')
            rigs_lay.addWidget(asset_lbl)
            for namespace, network_nodes in data.items():
                namespace_lbl = QtWidgets.QLabel(f'{namespace}:')
                namespace_lbl.setStyleSheet('margin-left: 20px')
                rigs_lay.addWidget(namespace_lbl)
                for network_node in network_nodes:
                    enable_cb = QtWidgets.QCheckBox(network_node.name().replace('_fkIkSnap_NET', '').split(':')[-1])
                    enable_cb.setStyleSheet('margin-left: 40px')
                    rigs_lay.addWidget(enable_cb)
                    self.network_checks[enable_cb] = network_node

        frame_range_widget = pysideutl.GroupBoxWithBorder('Frame Range')
        frame_range_lay = QtWidgets.QVBoxLayout()
        frame_range_widget.setLayout(frame_range_lay)
        frame_range_lay.setContentsMargins(0, 0, 0, 0)
        base_lay.addWidget(frame_range_widget)

        radio_widget = QtWidgets.QWidget()
        radio_lay = QtWidgets.QHBoxLayout()
        radio_widget.setLayout(radio_lay)
        frame_range_lay.addWidget(radio_widget)
        self.time_slider_btn = QtWidgets.QRadioButton('Time Slider')
        radio_lay.addWidget(self.time_slider_btn)
        self.time_slider_btn.setChecked(True)
        self.start_end_btn = QtWidgets.QRadioButton('Start/End')
        radio_lay.addWidget(self.start_end_btn)
        self.frame_btn = QtWidgets.QRadioButton('Current Frame')
        radio_lay.addWidget(self.frame_btn)

        self.start_end_btn.toggled.connect(self.hide_frames_fields)
        self.frame_btn.toggled.connect(self.hide_key_check)

        only_int_validator = QtGui.QIntValidator()
        self.frames_widget = QtWidgets.QWidget()
        frames_lay = QtWidgets.QHBoxLayout()
        self.frames_widget.setLayout(frames_lay)
        frame_range_lay.addWidget(self.frames_widget)
        self.frames_widget.hide()
        start_lbl = QtWidgets.QLabel('Start Frame:')
        start_lbl.setFixedWidth(60)
        frames_lay.addWidget(start_lbl)
        self.start_lne = QtWidgets.QLineEdit()
        self.start_lne.setFixedWidth(45)
        self.start_lne.setValidator(only_int_validator)
        frames_lay.addWidget(self.start_lne)
        end_lbl = QtWidgets.QLabel('End Frame:')
        end_lbl.setFixedWidth(60)
        frames_lay.addWidget(end_lbl)
        self.end_lne = QtWidgets.QLineEdit()
        self.end_lne.setFixedWidth(45)
        self.end_lne.setValidator(only_int_validator)
        frames_lay.addWidget(self.end_lne)
        self.hide_frames_fields()

        self.key_check = QtWidgets.QCheckBox('Set Keyframes')
        self.key_check.setStyleSheet('margin-left: 10px; margin-bottom: 10px')
        self.key_check.setChecked(True)
        frame_range_lay.addWidget(self.key_check)
        self.hide_key_check()

        button_widget = pysideutl.GroupBoxWithBorder('Bake')
        button_lay = QtWidgets.QHBoxLayout()
        button_widget.setLayout(button_lay)
        base_lay.addWidget(button_widget)

        self.to_fk_btn = QtWidgets.QPushButton('To FK')
        button_lay.addWidget(self.to_fk_btn)
        self.to_fk_btn.clicked.connect(self.bake)

        self.to_ik_btn = QtWidgets.QPushButton('To IK')
        button_lay.addWidget(self.to_ik_btn)
        self.to_ik_btn.clicked.connect(self.bake)

        self.show()

    @staticmethod
    def get_networks():
        networks = {}
        network_nodes = [a for a in pm.ls('::*_fkIkSnap_NET', type='network') if a.hasAttr('fkIkSnapNetwork')]
        for network_node in network_nodes:
            misc_ctrl = network_node.snapToFk0.listConnections(s=True, d=False)[0]
            top_node = misc_ctrl.getAllParents()[-1]
            asset_name = top_node.name().split(':')[-1]
            namespace = network_node.namespace()
            if asset_name in networks:
                if namespace in networks[asset_name]:
                    networks[asset_name][namespace].append(network_node)
                else:
                    networks[asset_name] = {namespace: [network_node]}
            else:
                networks[asset_name] = {namespace: [network_node]}
        return networks

    def refresh(self):
        self.close()
        FkIkSnapUI()

    def hide_frames_fields(self):
        if self.start_end_btn.isChecked():
            self.frames_widget.show()
        else:
            self.frames_widget.hide()
        utils.executeDeferred(partial(self.resize, 1, 1))  # shrink window to the smallest possible size

    def hide_key_check(self):
        if self.frame_btn.isChecked():
            self.key_check.show()
        else:
            self.key_check.hide()
        utils.executeDeferred(partial(self.resize, 1, 1))  # shrink window to the smallest possible size

    def bake(self):
        network_nodes = [node for check, node in self.network_checks.items() if check.isChecked()]
        if self.start_end_btn.isChecked():
            try:
                time_range = (int(self.start_lne.text()), int(self.end_lne.text()))
            except ValueError:
                self.start_lne.setStyleSheet('background-color: red')
                self.end_lne.setStyleSheet('background-color: red')
                def reset_style():
                    time.sleep(1)
                    self.start_lne.setStyleSheet('')
                    self.end_lne.setStyleSheet('')
                utils.executeDeferred(reset_style)
                raise ValueError('Please use a valid time range!')
        elif self.frame_btn.isChecked():
            time_range = (pm.currentTime(), pm.currentTime())
        else:
            time_range = None
        set_key = False if self.frame_btn.isChecked() and not self.key_check.isChecked() else True
        to_fk = self.sender() is self.to_fk_btn

        animtoolsfunc.fk_ik_bake(
            network_nodes=network_nodes,
            to_fk=to_fk,
            timerange=time_range,
            set_key=set_key
        )
