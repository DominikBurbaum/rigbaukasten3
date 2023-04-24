import os
import sys
import time
from functools import partial

from maya import cmds
import pymel.core as pm

import rigbaukasten
from rigbaukasten.core import modulecor
from rigbaukasten.library import controllib, rigsetlib
from rigbaukasten.pipeline import reloadpip, newrigbuildpip
from rigbaukasten.utils import mathutl, errorutl, mirrorutl, fileutl, pysideutl


def rigbaukasten_menu():
    if 'Rigbaukasten' in cmds.lsUI(type='menu'):
        cmds.deleteUI('Rigbaukasten')

    maya_main_window = pm.melGlobals['gMainWindow']
    pm.menu('Rigbaukasten', p=maya_main_window, to=True)

    pm.menuItem(label='Set Environment', c=lambda _: set_environemtn())
    pm.menuItem(divider=True)
    pm.menuItem(label='Reload Rigbaukasten', c=reload_rigbaukasten)
    pm.menuItem(label='Rebuild Menu', c=lambda _: rigbaukasten_menu())
    try:
        asset_name = rigbaukasten.environment.get_asset_name()
    except errorutl.RbkEnvironmentError:
        asset_name = 'rig'
    pm.menuItem(divider=True, l=asset_name)
    rig_builds_menu()
    publish_menu()
    pm.menuItem(divider=True, label='Guides', p='Rigbaukasten')
    mirror_transforms_menu()
    pm.menuItem(divider=True, label='Rig Sets', p='Rigbaukasten')
    pm.menuItem(label='Make All Sets Active', c=make_sets_active_cmd, p='Rigbaukasten')
    pm.menuItem(label='Make All Sets Inactive', c=make_sets_inactive_cmd, p='Rigbaukasten')
    pm.menuItem(divider=True, label='Control Shapes', p='Rigbaukasten')
    pm.menuItem(label='Mirror CTL', c=mirror_ctl_cmd, p='Rigbaukasten')
    pm.menuItem(label='Store Selected shape', c=store_selected_shape_cmd, p='Rigbaukasten')
    change_ctl_shape_menu()


def set_environemtn():
    rigbaukasten.environment.set()
    if 'Rigbaukasten' in cmds.lsUI(type='menu'):
        cmds.deleteUI('Rigbaukasten')
    rigbaukasten_menu()


def reload_rigbaukasten(*_):
    reloadpip.reload_rigbaukasten()


def rig_builds_menu():
    """  """
    if pm.menuItem('Rigbaukasten_builds', q=True, ex=True):
        pm.deleteUI('Rigbaukasten_builds')
    pm.menuItem('Rigbaukasten_builds', subMenu=True, label='Build Rig', to=True, p='Rigbaukasten')
    try:
        asset_name = rigbaukasten.environment.get_asset_name()
    except errorutl.RbkEnvironmentError:
        pm.menuItem(
            label='Set environment first!',
            p='Rigbaukasten_builds',
            en=False
        )
        pm.menuItem('Rigbaukasten_edit_build_script', label='Edit Build_script', p='Rigbaukasten', en=False)
        return

    build_path = os.path.join(rigbaukasten.environment.get_rig_builds_path(), asset_name, f'{asset_name}_build.py')
    if os.path.exists(build_path):
        rig_steps_menu(parent_menu='Rigbaukasten_builds', file=f'{asset_name}.{asset_name}_build')
        open_script_menu(parent_menu='Rigbaukasten', script_file_path=build_path)
    else:
        pm.menuItem(
            label=f'Create new rig build for {asset_name}...',
            p='Rigbaukasten_builds',
            c=create_new_rig_build
        )
        pm.menuItem('Rigbaukasten_edit_build_script', label='Edit Build_script', p='Rigbaukasten', en=False)


def open_script_menu(parent_menu, script_file_path):
    pm.menuItem('Rigbaukasten_edit_build_script', subMenu=True, label='Edit Build_script', p=parent_menu)
    pm.menuItem(
        label='Open in Script Editor',
        p='Rigbaukasten_edit_build_script',
        c=lambda _: fileutl.open_in_script_editor(script_file_path)
    )
    pm.menuItem(
        label='Open in Default Editor',
        p='Rigbaukasten_edit_build_script',
        c=lambda _: fileutl.open_in_default_app(script_file_path)
    )
    pm.menuItem(
        label='Copy file path to clipboard',
        p='Rigbaukasten_edit_build_script',
        c=lambda _: pysideutl.set_clipboard_text(script_file_path)
    )


def create_new_rig_build(*_):
    """ Create a new rig build for the current asset and update the menu. """
    if newrigbuildpip.choose_template_and_create_new_rig_build():
        time.sleep(.5)
        rigbaukasten_menu()
        print('SUCCESS')


def rig_steps_menu(parent_menu, file):
    """ Create the menu that executes the build steps.

        The actual steps are created in an own function, because we have to be able to delete and recreate them
        easily to allow the sub steps toggle.
        :param parent_menu: (str) name of the parent menu, e.g. 'Rigbaukasten_builds'
        :param file: (str) name of the rig_build file (python module), e.g. 'spiderman_build'
    """
    pm.menuItem(
        l='Show Sub Steps',
        p=parent_menu,
        cb=False,
        c=partial(rig_steps_menu_toggle, parent_menu=parent_menu, file=file)
    )
    pm.menuItem(divider=True, p=parent_menu)
    rig_steps_menu_toggle(sub_steps=False, parent_menu=parent_menu, file=file)


def rig_steps_menu_toggle(sub_steps, parent_menu, file):
    """ Create the actual steps for the rig build.

        This will clear all existing steps before creating new ones, so it can be called ovr and over again (when
        the user uses the toggle sub steps).
        :param sub_steps: (bool) Create all steps (True) or just the main ones (False). This will be automatically
                                 set to the checkbox value when called from the 'Show Sub Steps' menuItem (maya passes
                                 the checkbox value as first argument).
        :param parent_menu: (str) name of the parent menu, e.g. 'Rigbaukasten_builds'
        :param file: (str) name of the rig_build file (python module), e.g. 'spiderman_build'
    """
    step_itmes = cmds.menu(parent_menu, q=1, itemArray=1)[2:]
    if step_itmes:
        pm.deleteUI(step_itmes)

    step_icons = {
        'skeleton_build': 'kinDisconnect.png',
        'skeleton_connect': 'kinConnect.png',
        'puppet_build': 'kinReroot.png',
        'puppet_connect': 'humanIK_CharCtrl.png',
        'deform_build': 'detachSkin.png',
        'deform_connect': 'smoothSkin.png',
        'finalize': 'SE_FavoriteStar.png'
    }
    for step, icon in step_icons.items():
        if sub_steps:
            pm.menuItem(
                f'{step}_pre',
                c=partial(build_rig, file=file, stop_after_step=step, stop_after_sub_step='pre'),
                p=parent_menu,
                i=icon
            )
            pm.menuItem(
                step,
                c=partial(build_rig, file=file, stop_after_step=step, stop_after_sub_step=''),
                p=parent_menu,
                i=icon
            )
            pm.menuItem(
                f'{step}_post',
                c=partial(build_rig, file=file, stop_after_step=step, stop_after_sub_step='post'),
                p=parent_menu,
                i=icon
            )
        else:
            pm.menuItem(
                step,
                c=partial(build_rig, file=file, stop_after_step=step, stop_after_sub_step='post'),
                p=parent_menu,
                i=icon
            )


def build_rig(*_, file='myRig_build', stop_after_step='finalize_post', stop_after_sub_step='post'):
    """ Wrapper for modulecor.build_rig(). Uses modifier keys to force a rebuild. """
    force_rebuild = bool(pm.getModifiers())  # Pressing any modifier key will force a rebuild.
    modulecor.build_rig(
        file=file,
        stop_after_step=stop_after_step,
        stop_after_sub_step=stop_after_sub_step,
        force_rebuild=force_rebuild
    )


def publish_menu():
    if pm.menuItem('Rigbaukasten_publish', q=True, ex=True):
        pm.deleteUI('Rigbaukasten_publish')

    try:
        rigbaukasten.environment.get_asset_name()  # Check if environment is set
    except errorutl.RbkEnvironmentError:
        pm.menuItem('Rigbaukasten_publish', label='Rig Data Publish', p='Rigbaukasten', en=False)
    else:
        pm.menuItem('Rigbaukasten_publish', subMenu=True, label='Rig Data Publish', to=True, p='Rigbaukasten')
        for which, cmd in (('All', publish_all_cmd), ('Selected', publish_selected_cmd)):
            pm.menuItem(divider=True, label=which)
            for io_type in ['guides', 'ctls', 'constraints', 'skinClusters', 'blendshapes', 'rigsets', 'drivenKeys']:
                pm.menuItem(label=f'{which} {io_type}', c=partial(cmd, io_type=io_type))


def publish_all_cmd(*_, io_type):
    sys.modules['__main__'].rig.publish_rigdata(io_type)


def publish_selected_cmd(*_, io_type):
    done = []
    for obj in pm.ls(sl=1):
        if io_type == 'skinClusters' and isinstance(obj.getShape(), pm.nt.Mesh):
            skn = pm.listHistory(obj, type='skinCluster')
            if skn:
                obj = skn[0]
        elif io_type == 'blendshapes' and isinstance(obj.getShape(), pm.nt.Mesh):
            bs = pm.listHistory(obj, type='blendshapes')
            if bs:
                obj = bs[0]
        module_key = '_'.join(obj.name().split('_')[:2])
        if module_key not in done:
            modulecor.ALL_MODULES[module_key].publish_rigdata(io_type)
        done.append(module_key)


def mirror_transforms_menu():
    """ Build a menu item for transform mirroring (e.g. guide mirroring). """
    if pm.menuItem('Rigbaukasten_mirror_transforms', q=True, ex=True):
        pm.deleteUI('Rigbaukasten_mirror_transforms')
    pm.menuItem('Rigbaukasten_mirror_transforms', subMenu=True, label='Mirror Transforms', to=True, p='Rigbaukasten')

    pm.menuItem(label='Pos Only', c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=False))
    pm.menuItem(divider=True, p='Rigbaukasten_mirror_transforms')
    pm.menuItem(
        label='Pos/Rot, Flip All',
        c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=True, flip_axis='all')
    )
    pm.menuItem(
        label='Pos/Rot, Flip X',
        c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=True, flip_axis='x')
    )
    pm.menuItem(
        label='Pos/Rot, Flip Y',
        c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=True, flip_axis='y')
    )
    pm.menuItem(
        label='Pos/Rot, Flip Z',
        c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=True, flip_axis='z')
    )
    pm.menuItem(
        label='Pos/Rot, Flip None',
        c=lambda _: mirrorutl.world_mirror(None, pos=True, rot=True, flip_axis=None)
    )
    pm.menuItem(divider=True, p='Rigbaukasten_mirror_transforms')
    pm.menuItem(
        label='Rot Only, Flip All',
        c=lambda _: mirrorutl.world_mirror(None, pos=False, rot=True, flip_axis='all')
    )
    pm.menuItem(
        label='Rot Only, Flip X',
        c=lambda _: mirrorutl.world_mirror(None, pos=False, rot=True, flip_axis='x')
    )
    pm.menuItem(
        label='Rot Only, Flip Y',
        c=lambda _: mirrorutl.world_mirror(None, pos=False, rot=True, flip_axis='y')
    )
    pm.menuItem(
        label='Rot Only, Flip Z',
        c=lambda _: mirrorutl.world_mirror(None, pos=False, rot=True, flip_axis='z')
    )
    pm.menuItem(
        label='Rot Only, Flip None',
        c=lambda _: mirrorutl.world_mirror(None, pos=False, rot=True, flip_axis=None)
    )


def make_sets_active_cmd(*_):
    missing = rigsetlib.update_all_rigsets()
    if missing:
        pm.warning(f'Could not make all sets active, missing objects: {missing}')


def make_sets_inactive_cmd(*_):
    for rigset in rigsetlib.get_all_rigsets():
        rigsetlib.make_all_members_inactive(rigset)


def mirror_ctl_cmd(*_):
    mirrored = []
    for ctl in pm.ls(sl=1):
        other = controllib.mirror_side_control(ctl)
        mirrored.append(other)
    pm.select(mirrored)


def change_ctl_shape_menu():
    """ Build a menu item to change the selected CTL to each available shape. """
    if pm.menuItem('Rigbaukasten_ctls', q=True, ex=True):
        pm.deleteUI('Rigbaukasten_ctls')
    pm.menuItem('Rigbaukasten_ctls', subMenu=True, label='Change CTL Shape to', to=True, p='Rigbaukasten')
    for shape in controllib.get_available_shapes():
        pm.menuItem(label=shape, c=partial(change_ctl_shape_to_cmd, shape=shape))


def change_ctl_shape_to_cmd(*_, shape):
    ctls = pm.ls(sl=1)
    for ctl in ctls:
        scale_before = mathutl.distance(*ctl.boundingBox())
        controllib.set_ctl_shape(ctl=ctl, shape=shape)
        scale_after = mathutl.distance(*ctl.boundingBox())
        factor = scale_before / scale_after
        pm.scale(ctl.cv[:], factor, factor, factor)
    pm.select(ctls)


def store_selected_shape_cmd(*_):
    """ Store the selected curve as ctl shape and rebuild the menu. """
    controllib.store_selected_curve_shape()
    change_ctl_shape_menu()


def main():
    """ Run this at maya startup after you added rigbaukasten3 to PYTHONPATH. """
    rigbaukasten_menu()
