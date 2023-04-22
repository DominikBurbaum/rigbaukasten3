import shiboken2
from PySide2 import QtWidgets
from PySide2 import QtGui
from maya import OpenMayaUI


def get_maya_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(ptr), QtWidgets.QDialog)


class MayaDialog(QtWidgets.QDialog):
    """ Empty QDialog with mayas main window set as parent. """
    def __init__(self):
        super().__init__(get_maya_window())


class TitleLabel(QtWidgets.QLabel):
    """ Blue ribaukasten title label. """
    def __init__(self, label):
        super().__init__(label)
        self.setContentsMargins(10, 5, 10, 5)
        self.setStyleSheet("font: bold 18px; background-color: rgb(76,205,211); color: rgb(46,50,55);")


def get_clipboard_text():
    clip = QtGui.QClipboard()
    return clip.text()


def set_clipboard_text(text):
    clip = QtGui.QClipboard()
    clip.setText(text)
    print(f'Copied to clipboard: "{text}"')
