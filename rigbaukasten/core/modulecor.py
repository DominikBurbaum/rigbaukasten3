import importlib
import sys

import pymel.core as pm

import rigbaukasten
from rigbaukasten.core import iocor
from rigbaukasten.library import jointlib
from rigbaukasten.utils import errorutl, attrutl, mathutl, connectutl
from rigbaukasten.utils.typesutl import BuildStep, Ctl, Jnt, Trn, OutputDataPointer


ALL_MODULES = {}


class RigModule(object):
    def __init__(self, side, module_name):
        self.side = side
        self.module_name = module_name
        self.module_key = f'{side}_{module_name}'
        self.parent_module = None

        self.modules = {}
        self.publish_nodes = {
            'guides': [],
            'ctls': [],
            'constraints': [],
            'skinClusters': [],
            'blendshapes': [],
            'rigsets': [],
            'drivenKeys': [],
        }

        self.build_steps = {
            BuildStep('skeleton_build_pre'): self.skeleton_build_pre,
            BuildStep('skeleton_build'): self.skeleton_build,
            BuildStep('skeleton_build_post'): self.skeleton_build_post,
            BuildStep('skeleton_connect_pre'): self.skeleton_connect_pre,
            BuildStep('skeleton_connect'): self.skeleton_connect,
            BuildStep('skeleton_connect_post'): self.skeleton_connect_post,
            BuildStep('puppet_build_pre'): self.puppet_build_pre,
            BuildStep('puppet_build'): self.puppet_build,
            BuildStep('puppet_build_post'): self.puppet_build_post,
            BuildStep('puppet_connect_pre'): self.puppet_connect_pre,
            BuildStep('puppet_connect'): self.puppet_connect,
            BuildStep('puppet_connect_post'): self.puppet_connect_post,
            BuildStep('deform_build_pre'): self.deform_build_pre,
            BuildStep('deform_build'): self.deform_build,
            BuildStep('deform_build_post'): self.deform_build_post,
            BuildStep('deform_connect_pre'): self.deform_connect_pre,
            BuildStep('deform_connect'): self.deform_connect,
            BuildStep('deform_connect_post'): self.deform_connect_post,
            BuildStep('finalize_pre'): self.finalize_pre,
            BuildStep('finalize'): self.finalize,
            BuildStep('finalize_post'): self.finalize_post,
        }

        self.grp = None
        self.in_hooks_grp = None
        self.static_grp = None
        self.modules_grp = None
        self.guides_grp = None

        self.inv = -1 if side == 'R' else 1

    def skeleton_build_pre(self):
        for key, mod in self.modules.items():
            mod.skeleton_build_pre()

    def skeleton_build(self):
        for key, mod in self.modules.items():
            mod.skeleton_build()

    def skeleton_build_post(self):
        for key, mod in self.modules.items():
            mod.skeleton_build_post()

    def skeleton_connect_pre(self):
        for key, mod in self.modules.items():
            mod.skeleton_connect_pre()

    def skeleton_connect(self):
        for key, mod in self.modules.items():
            mod.skeleton_connect()

    def skeleton_connect_post(self):
        for key, mod in self.modules.items():
            mod.skeleton_connect_post()

    def puppet_build_pre(self):
        for key, mod in self.modules.items():
            mod.puppet_build_pre()

    def puppet_build(self):
        for key, mod in self.modules.items():
            mod.puppet_build()

    def puppet_build_post(self):
        for key, mod in self.modules.items():
            mod.puppet_build_post()

    def puppet_connect_pre(self):
        for key, mod in self.modules.items():
            mod.puppet_connect_pre()

    def puppet_connect(self):
        for key, mod in self.modules.items():
            mod.puppet_connect()

    def puppet_connect_post(self):
        for key, mod in self.modules.items():
            mod.puppet_connect_post()

    def deform_build_pre(self):
        for key, mod in self.modules.items():
            mod.deform_build_pre()

    def deform_build(self):
        for key, mod in self.modules.items():
            mod.deform_build()

    def deform_build_post(self):
        for key, mod in self.modules.items():
            mod.deform_build_post()

    def deform_connect_pre(self):
        for key, mod in self.modules.items():
            mod.deform_connect_pre()

    def deform_connect(self):
        for key, mod in self.modules.items():
            mod.deform_connect()

    def deform_connect_post(self):
        for key, mod in self.modules.items():
            mod.deform_connect_post()

    def finalize_pre(self):
        for key, mod in self.modules.items():
            mod.finalize_pre()

    def finalize(self):
        for key, mod in self.modules.items():
            mod.finalize()

    def finalize_post(self):
        for key, mod in self.modules.items():
            mod.finalize_post()

    def create_grps(self):
        if self.parent_module:
            self.grp = pm.group(em=True, n=f'{self.module_key}_module_GRP', p=self.parent_module.modules_grp)
        else:
            self.grp = pm.group(em=True, n=f'{self.module_key}_module_GRP')
        self.grp.useOutlinerColor.set(True)
        self.grp.outlinerColor.set(mathutl.rgb_int_to_float([76, 205, 211]))
        self.in_hooks_grp = pm.group(em=True, n=f'{self.module_key}_inHooks_GRP', p=self.grp)
        self.static_grp = pm.group(em=True, n=f'{self.module_key}_static_GRP', p=self.grp)
        self.static_grp.inheritsTransform.set(False)
        self.modules_grp = pm.group(em=True, n=f'{self.module_key}_modules_GRP', p=self.grp)

    def create_guides_grp(self):
        self.guides_grp = pm.group(em=True, n=f'{self.module_key}_guides_GRP', p=self.grp)

    def delete_guides(self):
        if self.guides_grp:
            pm.delete(self.guides_grp)

    def mk(self, name):
        """ Prefix the given name with <side>_<module_name>_. I.e. sm('00_JNT') -> 'C_mod_00_JNT' """
        return f'{self.module_key}_{name}'

    def out_hook(self, *_):
        raise errorutl.RbkNotFound(f'Rig module "{type(self)}" does not provide out hooks.')

    def get_hook(self, hook):
        if isinstance(hook, OutputDataPointer):  # Jnt('C_spine', 0)
            return self.get_output_data(hook)
        elif isinstance(hook, (list, tuple)):  # ['C_spine', 0]
            mod, index = hook
            if isinstance(mod, str):
                return ALL_MODULES[mod].out_hook(index)
            else:
                return mod.out_hook(index)
        elif pm.objExists(hook):  # 'C_spine_0_JNT'
            return pm.PyNode(hook)
        else:
            raise errorutl.RbkNotFound(f'Module {self.module_key} is unable to find provided hook {hook}.')

    def get_asset_root_module(self):
        """ Get the root module of the rig module hierarchy (usually this will be the RigBuild). """
        if ALL_MODULES:
            return list(ALL_MODULES.values())[0].parent_module
        else:
            # try crawling up
            mod = self
            while True:
                if mod.parent_module:
                    mod = mod.parent_module
                else:
                    break
            return mod

    def add_module(self, mod):
        if mod.module_key in ALL_MODULES:
            raise errorutl.RbkNotUnique(f'Module name must be unique: {mod.module_key}')
        self.modules[mod.module_key] = mod
        ALL_MODULES[mod.module_key] = mod
        mod.parent_module = self

    def publish_rigdata(self, io_type):
        for key, mod in self.modules.items():
            mod.publish_rigdata(io_type)
        io = iocor.RigDataIo(module_key=self.module_key)
        io.publish_rigdata(io_type, nodes=self.publish_nodes[io_type])

    def load_rigdata(self, io_type, recursive=True):
        if recursive:
            for key, mod in self.modules.items():
                mod.load_rigdata(io_type)
        io = iocor.RigDataIo(module_key=self.module_key)
        io.load_rigdata(io_type)

    def store_output_data(self, jnts=(), ctls=(), trns=()):
        """ Write output data onto the module group. """
        for typ, data in {Jnt: jnts, Ctl: ctls, Trn: trns}.items():
            if data:
                keys = data.keys() if isinstance(data, dict) else range(len(data))
                compound_plug, child_plugs = attrutl.add_compound(
                    obj=self.grp,
                    attr_name=f'rbkOutput{typ.suffix}',
                    typ='message',
                    child_names=[f'{typ.suffix}_{key}' for key in keys]
                )
                nodes = data.values() if isinstance(data, dict) else data
                for node, plug in zip(nodes, child_plugs):
                    src_plug = attrutl.add_message(node, 'rbk_output')
                    src_plug >> plug

    @staticmethod
    def get_output_data(pointer):
        """ Get the output data (node) that the given pointer points at.

            The pointer must be a OutputDataPointer subtype instance from typesutl. E.g. Jnt('C_spine', 0)
        """
        if not isinstance(pointer, OutputDataPointer):
            raise errorutl.RbkInvalidKeywordArgument('Given pointer is not a subclass of typesutl.OutputDataPointer!')

        try:
            mod = ALL_MODULES[pointer.module_key]
        except IndexError:
            raise errorutl.RbkNotFound(f'Module "{pointer.module_key}" does not exist.')

        try:
            plug = mod.grp.attr(f'{pointer.suffix}_{pointer.index}')
        except pm.MayaAttributeError:
            outputs = []
            if pm.attributeQuery(f"rbkOutput{pointer.suffix}", n=mod.grp, ex=True):
                attrs = pm.attributeQuery(f"rbkOutput{pointer.suffix}", n=mod.grp, lc=True)  # [Jnt_top, Jnt_00, Jnt_01]
                outputs = [a.replace(pointer.suffix + '_', '', 1) for a in attrs]  # ['top', '00', '01']
                numeric_outputs = [a for a in outputs if a.isnumeric()]  # ['00', '01']
                if isinstance(pointer.index, (int, float)) and pointer.index < 0:
                    positive_index = outputs.index(numeric_outputs[pointer.index])
                    plug = mod.grp.attr(attrs[positive_index])
                    node = pm.listConnections(plug, s=True, d=False, p=False)[0]
                    return node
            raise errorutl.RbkNotFound(
                f'Module {pointer.module_key} has no output "{pointer.index}"! '
                f'Available {pointer.suffix} outputs: {outputs}'
            )
        node = pm.listConnections(plug, s=True, d=False, p=False)[0]
        return node


class RigBuild(RigModule):
    def __init__(self):
        super().__init__(side='C', module_name='assetRootModule')

        self.asset_name = rigbaukasten.environment.get_asset_name()
        self.reset_all_modules()

        self.modules_grp = None
        self.geo_grp = None
        self.skel_grp = None
        self.current_step = None
        self.current_step_completed = False

        self.scene_prep()

    def reset_all_modules(self):
        global ALL_MODULES
        ALL_MODULES = {}

    def scene_prep(self):
        pm.newFile(f=True)
        self.create_grps()

    def create_grps(self):
        self.grp = pm.group(em=True, n=self.asset_name)
        attrutl.add_tag(self.grp, 'asset_name', self.asset_name)
        self.modules_grp = pm.group(em=True, n='MODULES_GRP', p=self.grp)
        self.geo_grp = pm.group(em=True, n='GEO_GRP', p=self.grp)
        self.skel_grp = pm.group(em=True, n='SKEL_GRP', p=self.grp)

        for grp in (self.geo_grp, self.skel_grp):
            attrutl.lock([grp.attr(a) for a in 'trsv'])
            grp.overrideEnabled.set(True)
            attrutl.unlock(grp.overrideDisplayType, k=False, cb=True)
            grp.overrideDisplayType.set(2)

    def run(self, stop_after_step='finalize', stop_after_sub_step='post'):
        fit_cam = self.current_step is None
        for step_name, step_method in self.build_steps.items():
            if self.current_step and self.current_step >= step_name:
                continue
            self.current_step = BuildStep(step_name)
            self.current_step_completed = False
            # print(f'Running {step_name}...')
            step_method()
            # print(f'...{step_name} completed')
            full_stop_step = f'{stop_after_step}_{stop_after_sub_step}' if stop_after_sub_step else stop_after_step
            if step_name == full_stop_step:
                if fit_cam:
                    pm.viewFit('persp', self.geo_grp)
                break
        self.current_step_completed = True


def build_rig(file='myRig.myRig_build', stop_after_step='finalize', stop_after_sub_step='post', force_rebuild=False):
    """
    Start or continue a rig build.

    :param file: The name of the python module with the RigBuild class
    :param stop_after_step: stop after this main step
    :param stop_after_sub_step: stop after this pre/post step
    :param force_rebuild: Don't try to find an existing rig build and continue the build - force a new rig build.
    """
    if not force_rebuild:
        if hasattr(sys.modules['__main__'], 'rig'):  # rig variable exists
            if isinstance(sys.modules['__main__'].rig, RigBuild):  # rig variable is a rig build
                rig = sys.modules['__main__'].rig
                if rig.current_step:  # current step is not None, i.e. rig build has started before
                    end_step = f'{stop_after_step}_{stop_after_sub_step}' if stop_after_sub_step else stop_after_step
                    if rig.current_step < end_step:  # new end step hasn't already been executed
                        if rig.current_step_completed:  # last step was completed without errors
                            if pm.objExists(rig.grp):  # scene was not closed since last rig build
                                # Current scene and rig build valid, continue build
                                rig.run(
                                    stop_after_step=stop_after_step,
                                    stop_after_sub_step=stop_after_sub_step
                                )
                                return
                            else:
                                pm.warning('Cannot continue previous rig build: Asset root group node not found.')
                        else:
                            pm.warning('Cannot continue previous rig build: Last rig step was not completed.')
                    else:
                        pm.warning('Cannot continue previous rig build: New end step was already executed.')
                else:
                    pm.warning('Cannot continue previous rig build: Existing rig build was never started.')
            else:
                pm.warning(
                    "Cannot continue previous rig build: 'rig' variable is not of type modulecor.RigBuild "
                    "(or modulecor was reloaded since last build)"
                )
        else:
            pm.warning("Cannot continue previous rig build: 'rig' variable not found.")

    mod = importlib.import_module(f'rig_builds.{file}')
    importlib.reload(mod)
    if not hasattr(mod, 'RigBuild'):
        raise errorutl.RbkNotFound(
            f'cannot find a RigBuild in {file}! Need a modulecor.RigBuild subclass called "RigBuild".'
        )
    if not issubclass(mod.RigBuild, RigBuild):
        raise errorutl.RbkValueError(f'{file}.RigBuild is not a subclass of modulecor.RigBuild')
    rig = mod.RigBuild()
    sys.modules['__main__'].rig = rig
    rig.run(stop_after_step=stop_after_step, stop_after_sub_step=stop_after_sub_step)


class RigPuppetModule(RigModule):
    def __init__(
            self,
            side,
            module_name,
            size=1,
            hook=None,
            parent_joint=None
    ):
        """ A RigModule with some conventions & helpers for puppet rigging. """
        super().__init__(side=side, module_name=module_name)
        self.size = size
        self.hook = hook
        self.parent_joint = parent_joint

        self.joints = []
        self.puppet_joints = []

    def free_joints_from_guides(self, joints=None):
        """ Remove all constraints from the joints, zero out rotations using joint orient (if possible). """
        trns = joints or self.joints
        for trn in trns:
            pm.delete(pm.listHistory(trn, type='constraint'))
            trn.displayLocalAxis.set(False)
            if pm.objectType(trn) == 'joint':
                for ax in 'xyz':
                    r = trn.attr(f'r{ax}')
                    jo = trn.attr(f'jo{ax}')
                    jo.set(r.get() + jo.get())
                    r.set(0)
        self.guides_grp.v.set(False)

    def connect_to_main_skeleton(self):
        skeleton_parent = self.parent_joint or self.get_joint_from_hook(self.hook)
        if skeleton_parent:
            self.joints[0].setParent(skeleton_parent)

    def get_joint_from_hook(self, hook):
        """ Try to find the best fitting joint corresponding to the given hook. """
        if isinstance(hook, Jnt):  # Jnt('C_spine', 0)
            return self.get_output_data(hook)
        elif isinstance(hook, OutputDataPointer):
            try:
                return self.get_output_data(Jnt(hook.module_key, hook.index))
            except errorutl.RbkNotFound:
                try:
                    return self.get_output_data(Jnt(hook.module_key, 0))
                except errorutl.RbkNotFound:
                    pass
        return None

    def out_joint(self, hook):
        """ Get the joint that most closely matches the given hook. May be overwritten in the actual modules. """
        if isinstance(hook, (list, tuple)):
            index = hook[1]
            return self.joints[index]
        elif isinstance(hook, pm.nt.Transform):
            if hook in self.joints:
                return hook
        elif isinstance(hook, str):
            py_hook = pm.PyNode(hook)
            if py_hook in self.joints:
                return py_hook
        else:
            pm.warning(f'Cannot find a joint for given hook {hook}')
            return None

    def create_puppet_joints(self):
        self.puppet_joints = jointlib.duplicate_joint_chain(self.joints, root_parent=self.static_grp)
        for p, j in zip(self.puppet_joints, self.joints):
            src = attrutl.add_message(j, 'puppet_joint_equivalent')
            tgt = attrutl.add_message(p, 'skeleton_joint_equivalent')
            src >> tgt

    @staticmethod
    def cleanup_joints(joints):
        for jnt in joints:
            # disable segment scale compensate to allow global scale
            jnt.segmentScaleCompensate.set(False)

            # set joint label for easier weight mirroring
            side = 'CLR'.index(jnt.name()[0])
            other_type = jnt.name()[2:]
            jnt.side.set(side)
            jnt.attr('type').set(18)
            jnt.otherType.set(other_type)

    def connect_puppet_joints(self):
        for p, j in zip(self.puppet_joints, self.joints):
            connectutl.simple_matrix_constraint(p, j)

    def constraint_to_hook(self, driven, hook=None, prefer_puppet_joint=True):
        _hook = hook or self.hook
        if _hook:
            hook_trn = self.get_hook(_hook)
            if prefer_puppet_joint and pm.objExists(f'{hook_trn}.puppet_joint_equivalent'):
                hook_trn = hook_trn.puppet_joint_equivalent.listConnections(s=False, d=True)[0]
            pm.parentConstraint(hook_trn, driven, mo=True)
            pm.scaleConstraint(hook_trn, driven)
