import mgear.pymaya as pm
import mgear


import mgear.menu


def install():
    """Install Crank submenu
    """
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Crank: Shot Sculpt",
                command=str_open_crank,
                image="mgear_crank.svg")


str_open_crank = """
from mgear.crank import crank_tool
crank_tool.openUI()
"""
