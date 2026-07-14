from . import mode_handlers
from . import maya_handlers

# INIT HANDLERS INSTANCES
__EDIT_MODE__ = mode_handlers.EditMode()
__SELECTION__ = maya_handlers.SelectionCheck()
