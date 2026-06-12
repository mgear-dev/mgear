from maya import cmds

print(r"""
 ____________________________________
|             _____                  |
|            / ____|                 |
|  _ __ ___ | |  __  ___  __ _ _ __  |
| | '_ ` _ \| | |_ |/ _ \/ _` | '__| |
| | | | | | | |__| |  __/ (_| | |    |
| |_| |_| |_|\_____|\___|\__,_|_|    |
|____________________________________|

""")


if not cmds.about(batch=True):
    import maya.utils
    import mgear.menu
    maya.utils.executeDeferred(mgear.menu.install_main_menu)
