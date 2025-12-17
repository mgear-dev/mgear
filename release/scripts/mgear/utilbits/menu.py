import mgear.pymaya as pm
import mgear


import mgear.menu


def install():
    """Install Crank submenu
    """
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="xPlorer",
                command=str_open_crank,
                image="xplorer_icon.svg")


str_open_crank = """
from mgear.utilbits import xplorer
xplorer_win = xplorer.XPlorer()
xplorer_win.show(dockable=True)
"""
