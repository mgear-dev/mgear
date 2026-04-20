import mgear.pymaya as pm
import mgear


def install():
    """Install Simple Rig submenu
    """
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="简易绑定工具", command=str_open_simple_rig)
    pm.menuItem(divider=True)


str_open_simple_rig = """
from mgear.simpleRig import simpleRigTool
simpleRigTool.openSimpleRigUI()
"""
