import mgear.menu


def install():
    """Install Utilbits submenu"""
    commands = (
        ("xPlorer", str_open_xplorer, "xplorer_icon.svg"),
        ("Random Colors", str_open_random_colors, "mgear_random_colors.svg"),
        ("Bookmarks", str_open_bookmarks, "mgear_bookmark.svg"),
        ("Matcap Viewer", str_open_matcap_viewer, "mgear_circle.svg"),
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

str_open_bookmarks = """
from mgear.utilbits import bookmarks
bookmarks.show()
"""

str_open_matcap_viewer = """
from mgear.utilbits import matcap_viewer
matcap_viewer.show()
"""
