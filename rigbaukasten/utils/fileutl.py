import os
import platform
import subprocess

import pymel.core as pm


def import_file(path, *args, **kwargs):
    """ Import the given file, return all new root nodes in the DAG. """
    before = pm.ls(assemblies=True)
    pm.importFile(path, *args, **kwargs)
    after = pm.ls(assemblies=True)
    new = [a for a in after if a not in before]
    return new


def open_in_script_editor(path):
    """ Open the given file in the script editor. """
    # make sure script editor is visible
    editor_panel = 'scriptEditorPanel1'  # default maya name
    editor_window = 'scriptEditorPanel1Window'  # default maya name
    if editor_panel not in pm.getPanel(vis=True):
        pm.scriptedPanel(editor_panel, e=True, tor=True)
        pm.showWindow(editor_window)

    # the rest is pretty much a copy of MELs global proc loadFileInNewTab()

    # If we already have this file opened in another tab, just make that tab active instead of loading the file again.
    if pm.mel.selectExecuterTabByName(path):
        return

    # Create a new tab and load the file in it.
    ext = path.rsplit('.', 1)[-1]
    if ext == 'mel':
        pm.mel.buildNewExecuterTab(-1, "MEL", "mel", 0)
    else:
        pm.mel.buildNewExecuterTab(-1, "Python", "python", 0)

    # select the last tab created
    editor_tabs = pm.melGlobals['gCommandExecuterTabs']
    pm.tabLayout(editor_tabs, e=True, selectTabIndex=pm.tabLayout(editor_tabs, q=True, numberOfChildren=True))
    pm.mel.selectCurrentExecuterControl()

    # Then load the file contents into the new field
    pm.mel.delegateCommandToFocusedExecuterWindow(f'-e -loadFile "{path}"', 0)

    # Get the filename and rename the tab.
    pm.mel.renameCurrentExecuterTab(path, 0)
    pm.mel.delegateCommandToFocusedExecuterWindow("-e -modificationChangedCommand executerTabModificationChanged", 0)
    pm.mel.delegateCommandToFocusedExecuterWindow("-e -fileChangedCommand executerTabFileChanged", 0)


def open_in_default_app(path):
    """ Open the given file with the systems default app. """
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', path))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(path)
    else:                                   # linux variants
        subprocess.call(('xdg-open', path))
