from rigbaukasten.utils import errorutl

ALL_STEPS = (
    'skeleton_build_pre',
    'skeleton_build',
    'skeleton_build_post',
    'skeleton_connect_pre',
    'skeleton_connect',
    'skeleton_connect_post',
    'puppet_build_pre',
    'puppet_build',
    'puppet_build_post',
    'puppet_connect_pre',
    'puppet_connect',
    'puppet_connect_post',
    'deform_build_pre',
    'deform_build',
    'deform_build_post',
    'deform_connect_pre',
    'deform_connect',
    'deform_connect_post',
    'finalize_pre',
    'finalize',
    'finalize_post'
)


class BuildStep(str):
    """ String subclass for the build steps.
        Checks if the given step has a valid name and allows comparison <, <=, >=, >.
    """
    def __new__(cls, value):
        if value not in ALL_STEPS:
            raise errorutl.RbkInvalidKeywordArgument(f'BuildStep must be one of {ALL_STEPS}')

        return str.__new__(cls, value)

    def step_index(self):
        return ALL_STEPS.index(self)

    def __lt__(self, other):
        return self.step_index() < BuildStep(other).step_index()

    def __le__(self, other):
        return self.step_index() <= BuildStep(other).step_index()

    def __gt__(self, other):
        return self.step_index() > BuildStep(other).step_index()

    def __ge__(self, other):
        return self.step_index() >= BuildStep(other).step_index()


class OutputDataPointer(object):
    suffix = None

    def __init__(self, module_key, index):
        self.module_key = module_key
        self.index = index


class Ctl(OutputDataPointer):
    suffix = 'Ctl'


class Jnt(OutputDataPointer):
    suffix = 'Jnt'


class Trn(OutputDataPointer):
    suffix = 'Trn'
