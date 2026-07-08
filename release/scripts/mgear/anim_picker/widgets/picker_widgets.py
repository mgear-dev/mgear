"""Compatibility shim for the anim picker widgets.

The classes formerly defined here were split into focused modules during the
Phase 2 decomposition. This module re-exports the same objects so existing
imports (e.g. ``picker_widgets.PickerItem``,
``picker_widgets.select_picker_controls``, and
``isinstance(x, picker_widgets.PickerItem)``) keep working unchanged.
"""

from mgear.anim_picker.widgets.graphics import DefaultPolygon
from mgear.anim_picker.widgets.graphics import PointHandle
from mgear.anim_picker.widgets.graphics import Polygon
from mgear.anim_picker.widgets.graphics import PointHandleIndex
from mgear.anim_picker.widgets.graphics import GraphicText

from mgear.anim_picker.widgets.dialogs.script_dialog import SCRIPT_DOC_HEADER
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomScriptEditDialog,
)
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomMenuEditDialog,
)
from mgear.anim_picker.widgets.dialogs.search_replace_dialog import (
    SearchAndReplaceDialog,
)
from mgear.anim_picker.widgets.dialogs.handles_window import (
    HandlesPositionWindow,
)
from mgear.anim_picker.widgets.dialogs.item_options import ItemOptionsWindow
from mgear.anim_picker.widgets.dialogs.copy_paste_dialog import State
from mgear.anim_picker.widgets.dialogs.copy_paste_dialog import DataCopyDialog

from mgear.anim_picker.widgets.picker_item import select_picker_controls
from mgear.anim_picker.widgets.picker_item import PickerItem


__all__ = [
    "DefaultPolygon",
    "PointHandle",
    "Polygon",
    "PointHandleIndex",
    "GraphicText",
    "SCRIPT_DOC_HEADER",
    "CustomScriptEditDialog",
    "CustomMenuEditDialog",
    "SearchAndReplaceDialog",
    "HandlesPositionWindow",
    "ItemOptionsWindow",
    "State",
    "DataCopyDialog",
    "select_picker_controls",
    "PickerItem",
]
