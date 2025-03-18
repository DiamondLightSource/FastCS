class FastCSException(Exception):
    """Base class for general problems in the running of a FastCS transport."""


class LaunchError(FastCSException):
    """For when there is an error in launching FastCS with the given
    transports and controller.
    """
