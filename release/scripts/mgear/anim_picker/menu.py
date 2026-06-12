from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from maya import cmds
import mgear.pymaya as pm

import mgear
import mgear.menu
from mgear.core import pyqt


str_open_picker_mode = """
from mgear import anim_picker
anim_picker.load(False, False)
"""

str_open_edit_mode = """
from mgear import anim_picker
anim_picker.load(True, False)
"""


def force_disable_passthrough(*args):
    """force all the anim picker gui's to disable passthrough feature

    Args:
        *args: n/a
    """

    widgets = pyqt.get_top_level_widgets(class_name="MainDockWindow")
    for ap in widgets:
        if (
            hasattr(ap, "__OBJ_NAME__")
            and ap.__OBJ_NAME__ == "ctrl_picker_window"
        ):
            ap.set_mouseEvent_passthrough(False)


def get_option_var_passthrough_state():
    """set option var for the anim picker passthrough feature

    Returns:
        int: 0 or 1
    """
    if not cmds.optionVar(exists="mgear_ap_passthrough_OV"):
        cmds.optionVar(intValue=("mgear_ap_passthrough_OV", 0))

    return cmds.optionVar(query="mgear_ap_passthrough_OV")


def set_mgear_ap_passthrough_state(state):
    """set the override state with maya option variable

    Args:
        state (bool, int): 0, 1, True, False
    """
    cmds.optionVar(intValue=("mgear_ap_passthrough_OV", int(state)))
    if state:
        print("---------------------------------------------------")
        print("Anim Picker passthrough enabled. (Beta)")
        print("Hold 'Shift' while hovering over the Anim Picker UI")
    else:
        force_disable_passthrough()


def install():
    """Install Anim Picker gui menu"""
    pm.setParent(mgear.menu_id, menu=True)

    state = get_option_var_passthrough_state()

    cmds.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    cmds.menuItem(
        "mgear_ap_menuitem",
        label="Anim Picker",
        subMenu=True,
        tearOff=True,
        image="mgear_mouse-pointer.svg",
    )
    cmds.menuItem(label="Anim Picker", command=str_open_picker_mode)
    pm.menuItem(divider=True)
    cmds.menuItem(label="Edit Anim Picker", command=str_open_edit_mode)
    pm.menuItem(divider=True)
    msg = "Experimental passthrough click when auto opacity enabled."
    cmds.menuItem(
        "mgear_ap_passthrough_menuitem",
        label="Enable opacity passthrough (Beta)",
        command=set_mgear_ap_passthrough_state,
        checkBox=state,
        ann=msg,
    )
