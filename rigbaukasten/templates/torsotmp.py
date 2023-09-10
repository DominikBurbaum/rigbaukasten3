from rigbaukasten.core import modulecor
import pymel.core as pm

from rigbaukasten.puppet import jointpup
from rigbaukasten.utils import attrutl, connectutl, mathutl
from rigbaukasten.utils.typesutl import Ctl


class Ribcage(modulecor.RigModule):
    def __init__(
            self,
            side,
            module_name,
            breathing_attrs_holder=None,
            lower_chest_hook=None,
            upper_chest_hook=None,
            left_clavicle_hook=None,
            left_shoulder_hook=None,
            right_clavicle_hook=None,
            right_shoulder_hook=None,
    ):
        super().__init__(side=side, module_name=module_name)
        self.breathing_attrs_holder = breathing_attrs_holder
        self.lower_chest_hook = lower_chest_hook
        self.upper_chest_hook = upper_chest_hook

        self.upper_breathing_grp = self.mk('upperBreathingHook_GRP')
        self.upper_breathing_trn = self.mk('upperBreathingHook_TRN')
        self.lower_breathing_grp = self.mk('lowerBreathingHook_GRP')
        self.lower_breathing_trn = self.mk('lowerBreathingHook_TRN')
        self.left_outer_breathing_trn = f'L_{module_name}_outerBreathing_TRN'
        self.right_outer_breathing_trn = f'R_{module_name}_outerBreathing_TRN'

        self.lower_breathing_plug = None
        self.upper_breathing_plug = None

        self.add_module(jointpup.StretchyJoint(
            side='C',
            module_name='sternum',
            hook=self.lower_breathing_trn,
            end_hook=self.upper_breathing_trn,
            parent_joint=lower_chest_hook
        ))
        shoulder_hook = {'L': left_shoulder_hook, 'R': right_shoulder_hook}
        clavicle_hook = {'L': left_clavicle_hook, 'R': right_clavicle_hook}
        outer_breathing_hook = {'L': self.left_outer_breathing_trn, 'R': self.right_outer_breathing_trn}
        for s in 'LR':
            self.add_module(jointpup.StretchyJoint(
                side=s,
                module_name='clavicleBone',
                hook=['C_sternum', 0],
                end_hook=clavicle_hook[s],
                parent_joint=upper_chest_hook
            ))
            self.add_module(jointpup.StretchyJoint(
                side=s,
                module_name='pectoralisClavicular',
                hook=[f'{s}_clavicleBone', 0],
                end_hook=shoulder_hook[s],
                parent_joint=upper_chest_hook
            ))
            self.add_module(jointpup.StretchyJoint(
                side=s,
                module_name='pectoralisSternal',
                hook=['C_sternum', 0],
                end_hook=shoulder_hook[s],
                parent_joint=lower_chest_hook
            ))
            self.add_module(jointpup.StretchyJoint(
                side=s,
                module_name='pectoralisAbdominal',
                hook=outer_breathing_hook[s],
                end_hook=shoulder_hook[s],
                parent_joint=lower_chest_hook
            ))

    def create_breathing_hooks(self):
        """ Create transforms that get hooked between the hooks and sternum to create offsets for the breathing. """
        self.upper_breathing_grp = pm.group(em=True, n=self.upper_breathing_grp, p=self.grp)
        pm.delete(pm.pointConstraint(self.modules['C_sternum'].joints[1], self.upper_breathing_grp))
        self.upper_breathing_trn = pm.group(em=True, n=self.upper_breathing_trn, p=self.upper_breathing_grp)
        self.lower_breathing_grp = pm.group(em=True, n=self.lower_breathing_grp, p=self.grp)
        pm.delete(pm.pointConstraint(self.modules['C_sternum'].joints[0], self.lower_breathing_grp))
        self.lower_breathing_trn = pm.group(em=True, n=self.lower_breathing_trn, p=self.lower_breathing_grp)
        self.left_outer_breathing_trn = pm.group(em=True, n=self.left_outer_breathing_trn, p=self.lower_breathing_trn)
        self.right_outer_breathing_trn = pm.group(em=True, n=self.right_outer_breathing_trn, p=self.lower_breathing_trn)

    def connect_breathing_hooks(self):
        upper_chest_hook = self.get_hook(self.upper_chest_hook)
        pm.parentConstraint(upper_chest_hook, self.upper_breathing_grp, mo=True)
        pm.scaleConstraint(upper_chest_hook, self.upper_breathing_grp)
        lower_chest_hook = self.get_hook(self.lower_chest_hook)
        pm.parentConstraint(lower_chest_hook, self.lower_breathing_grp, mo=True)
        pm.scaleConstraint(lower_chest_hook, self.lower_breathing_grp)

    def create_breathing_attrs(self):
        if isinstance(self.breathing_attrs_holder, Ctl):
            self.breathing_attrs_holder = self.get_output_data(self.breathing_attrs_holder)
        attrs_holder = pm.PyNode(self.breathing_attrs_holder) if pm.objExists(self.breathing_attrs_holder) else self.grp
        attrutl.label_attr(attrs_holder, 'manualBreathing')
        upper_manual_plug = attrutl.add(attrs_holder, 'upperChestBreathing', mn=-10, mx=10)
        lower_manual_plug = attrutl.add(attrs_holder, 'lowerChestBreathing', mn=-10, mx=10)
        attrutl.label_attr(attrs_holder, 'autoBreathing')
        auto_enable_plug = attrutl.add(attrs_holder, 'enableAutoBreathing', typ='bool')
        auto_freq_plug = attrutl.add(attrs_holder, 'frequency', mn=0, mx=10, default=5)
        auto_amp_plug = attrutl.add(attrs_holder, 'amplitude', mn=0, mx=10, default=3)

        self.upper_breathing_plug = attrutl.add(attrs_holder, 'upperChestBreathingOut', k=False, cb=False)
        self.lower_breathing_plug = attrutl.add(attrs_holder, 'lowerChestBreathingOut', k=False, cb=False)

        pm.expression(n=self.mk('chestBreathing_EXP'), s=f'''
            if ({auto_enable_plug}){{
                $auto = sin(frame * {auto_freq_plug} * 0.03) * {auto_amp_plug};
                {self.upper_breathing_plug} = clamp(-10, 10, {upper_manual_plug} + $auto);
                {self.lower_breathing_plug} = clamp(-10, 10, {lower_manual_plug} + $auto);
            }}else{{
                {self.upper_breathing_plug} = {upper_manual_plug};
                {self.lower_breathing_plug} = {lower_manual_plug};
            }}
        ''')

        # upper_manual_plug >> self.upper_breathing_plug
        # lower_manual_plug >> self.lower_breathing_plug

    def create_breathing_keys(self):
        connectutl.driven_keys(
            driver=self.lower_breathing_plug,
            driven=self.lower_breathing_trn.tz,
            v=(-0.5, -0.2, 0, 0.4, 1),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.lower_breathing_plug,
            driven=self.lower_breathing_trn.ty,
            v=(-0.5, -0.2, 0, 0.4, 1),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.upper_breathing_trn.tz,
            v=(-1, -0.6, 0, 0.6, 1),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.upper_breathing_trn.ty,
            v=(-0.5, -0.2, 0, 0.6, 1.5),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.left_outer_breathing_trn.tx,
            v=(-1, -0.5, 0, 1, 2),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.left_outer_breathing_trn.tz,
            v=(0, 0, 0, 0.9, 1.5),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.right_outer_breathing_trn.tx,
            v=(1, 0.5, 0, -1, -2),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )
        connectutl.driven_keys(
            driver=self.upper_breathing_plug,
            driven=self.right_outer_breathing_trn.tz,
            v=(0, 0, 0, 0.9, 1.5),
            dv=(-10, -5, 0, 5, 10),
            tangents='auto'
        )

    # ---------------------- Build Steps ---------------------- #

    def skeleton_build_pre(self):
        self.create_grps()
        super().skeleton_build_pre()

    def puppet_build(self):
        super(Ribcage, self).puppet_build()
        self.create_breathing_hooks()
        self.create_breathing_attrs()
        self.create_breathing_keys()

    def puppet_connect(self):
        super(Ribcage, self).puppet_connect()
        self.connect_breathing_hooks()
