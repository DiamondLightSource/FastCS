class FastCSError(Exception):
    """Base class for general problems in the running of a FastCS transport."""


class LaunchError(FastCSError):
    """For when there is an error in launching FastCS with the given
    transports and controller.
    """
