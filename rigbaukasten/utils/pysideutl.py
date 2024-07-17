import shiboken2
from PySide2 import QtWidgets
from PySide2 import QtGui
from PySide2 import QtCore
from maya import OpenMayaUI


def get_maya_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QDialog)


class MayaDialog(QtWidgets.QDialog):
    """ Empty QDialog with mayas main window set as parent. """
    def __init__(self):
        super().__init__(get_maya_window())
        self.setWindowFlags(QtCore.Qt.Tool)


class TitleLabel(QtWidgets.QLabel):
    """ Blue ribaukasten title label. """
    def __init__(self, label):
        super().__init__(label)
        self.setContentsMargins(10, 5, 10, 5)
        self.setStyleSheet("font: bold 18px; background-color: rgb(76,205,211); color: rgb(46,50,55);")


class GroupBoxWithBorder(QtWidgets.QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        self.setStyleSheet((
            'QGroupBox{ border: 1px solid grey; border-radius: 5px; margin-top: 5px; padding-top: 5px;}'
            'QGroupBox::title {left: 20px; bottom: 6px}'
        ))


def get_clipboard_text():
    clip = QtGui.QClipboard()
    return clip.text()


def set_clipboard_text(text):
    clip = QtGui.QClipboard()
    clip.setText(text)
    print(f'Copied to clipboard: "{text}"')
