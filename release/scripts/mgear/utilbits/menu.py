import mgear.menu


def install():
    """Install Utilbits submenu"""
    commands = (
        ("xPlorer", str_open_xplorer, "xplorer_icon.svg"),
        ("Random Colors", str_open_random_colors, "mgear_random_colors.svg"),
    )

    mgear.menu.install("Utilbits", commands, image="mgear_utilbits.svg")


str_open_xplorer = """
from mgear.utilbits import xplorer
xplorer_win = xplorer.XPlorer()
xplorer_win.show(dockable=True)
"""

str_open_random_colors = """
from mgear.utilbits import random_colors
random_colors.show()
"""
