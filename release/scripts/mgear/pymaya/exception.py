class MayaAttributeError(Exception):
    pass


class MayaNodeError(RuntimeError):
    """A node does not exist or can not be found.

    Subclasses RuntimeError so callers catching either the PyMEL-style
    ``pm.MayaNodeError`` or a plain ``RuntimeError`` both work.
    """

    pass


class MayaGeometryError(Exception):
    pass
