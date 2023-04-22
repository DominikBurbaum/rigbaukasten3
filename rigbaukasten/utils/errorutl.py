class RbkBaseException(Exception):
    """ Exception base class.
        This should never be raised, use any of the more specific sub classes.
        Can be usd for catching errors in a try/except blocck tho.
    """
    pass


class RbkInvalidKeywordArgument(RbkBaseException):
    """ Raise this if a keyword arg is invalid or the combination of several keyword arguments is invalid. """
    pass


class RbkInvalidName(RbkBaseException):
    """ Raise this if a name does not match the naming convention. """
    pass


class RbkNotFound(RbkBaseException):
    """ Raise this if the requested node/file/folder/[...] does not exist in the given location. """
    pass


class RbkValueError(RbkBaseException):
    """ Raise this if the given value cannot be processed. """
    pass


class RbkNotUnique(RbkBaseException):
    """ Raise this if a name must be unique but isn't. """
    pass


class RbkInvalidPath(RbkBaseException):
    """ Raise this if a file path/disk location is not valid. """
    pass


class RbkEnvironmentError(RbkBaseException):
    """ Raise this if the environment is not set properly """
    pass


class RbkInvalidObjectError(RbkBaseException):
    """ Raise this if a given object doesn't meet the requirements. """
    pass
