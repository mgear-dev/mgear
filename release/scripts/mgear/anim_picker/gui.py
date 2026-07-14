"""Compatibility shim for the anim picker gui.

The classes and constants formerly defined here were split into focused
modules during the Phase 2 decomposition (constants, scene, view, tab_widget,
main_window). This module re-exports the same objects so existing imports keep
working unchanged -- notably
``from mgear.anim_picker.gui import MAYA_OVERRIDE_COLOR`` (used by Shifter).
"""

from mgear.anim_picker.constants import ANIM_PICKER_TITLE
from mgear.anim_picker.constants import MAYA_OVERRIDE_COLOR
from mgear.anim_picker.constants import GROUPBOX_BG_CSS
from mgear.anim_picker.constants import PICKER_EXTRACTION_NAME
from mgear.anim_picker.constants import ANIM_PICKER_RELATIVE_IMAGES
from mgear.anim_picker.constants import DEFAULT_RELATIVE_IMAGES_PATH

from mgear.anim_picker.scene import OrderedGraphicsScene
from mgear.anim_picker.view import GraphicViewWidget
from mgear.anim_picker.tab_widget import ContextMenuTabWidget
from mgear.anim_picker.main_window import MainDockWindow
from mgear.anim_picker.main_window import MainDockableWindow
from mgear.anim_picker.main_window import load


__all__ = [
    "ANIM_PICKER_TITLE",
    "MAYA_OVERRIDE_COLOR",
    "GROUPBOX_BG_CSS",
    "PICKER_EXTRACTION_NAME",
    "ANIM_PICKER_RELATIVE_IMAGES",
    "DEFAULT_RELATIVE_IMAGES_PATH",
    "OrderedGraphicsScene",
    "GraphicViewWidget",
    "ContextMenuTabWidget",
    "MainDockWindow",
    "MainDockableWindow",
    "load",
]
