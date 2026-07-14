from maya import cmds
import mgear.pymaya as pm

import mgear
import mgear.menu


str_open_picker_mode = """
from mgear import anim_picker
anim_picker.load(False, False)
"""

str_open_dockable_mode = """
from mgear import anim_picker
anim_picker.load(False, True)
"""

str_open_edit_mode = """
from mgear import anim_picker
anim_picker.load(True, False)
"""


def install():
    """Install Anim Picker gui menu"""
    pm.setParent(mgear.menu_id, menu=True)

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
    cmds.menuItem(label="Anim Picker (Dockable)", command=str_open_dockable_mode)
    pm.menuItem(divider=True)
    cmds.menuItem(label="Edit Anim Picker", command=str_open_edit_mode)
