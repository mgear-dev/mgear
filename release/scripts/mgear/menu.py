from maya import cmds
import mgear.pymaya as pm
import mgear
import os

menuId = "mGear"


def create(menuId=menuId):
    """Create mGear main menu

    Args:
        menuId (str, optional): Main menu name

    Returns:
        str: main manu name
    """

    if cmds.menu(menuId, exists=True):
        try:
            pm.deleteUI(menuId)
        except RuntimeError:
            pm.displayInfo("Tried to delete {}, but it was not found".format(menuId))

    project_name = os.environ.get("MGEAR_PROJECT_NAME", None)
    if project_name:
        menuLabel = "mGear ({})".format(project_name)
    else:
        menuLabel = menuId

    pm.menu(menuId,
            parent="MayaWindow",
            tearOff=True,
            allowOptionBoxes=True,
            label=menuLabel)

    return menuId


def install_help_menu(menuId=menuId):
    """Install help menu section

    Args:
        menuId (str, optional): Main menu name
    """

    # Help
    pm.setParent(menuId, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(parent=menuId,
                subMenu=True,
                tearOff=True,
                label="Help",
                image="mgear_help-circle.svg")
    pm.menuItem(label="Web", command=str_web, image="mgear_globe.svg")
    pm.menuItem(label="Forum",
                command=str_forum,
                image="mgear_message-circle.svg")
    pm.menuItem(divider=True)
    pm.menuItem(label="Documentation",
                command=str_docs,
                image="mgear_book.svg")
    pm.menuItem(divider=True)
    pm.menuItem(label="About", command=str_about, image="mgear_smile.svg")


def install_utils_menu():
    """Install Utilities submenu
    """
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    commands = [("Reload", str_reload, "mgear_refresh-cw.svg")]

    m = install("Utilities", commands, image="mgear_tool.svg")
    return m


def install(label, commands, parent=menuId, image=""):
    """Installer Function for sub menus

    Args:
        label (str): Name of the sub menu
        commands (list): List of commands to install
        parent (str, optional): Parent menu for the submenu
    """
    try:
        m = pm.menuItem(parent=parent,
                        subMenu=True,
                        tearOff=True,
                        label=label,
                        image=image)
        for conf in commands:
            if len(conf) == 3:
                label, command, img = conf
            else:
                label, command = conf
                img = ""
            if not command:
                pm.menuItem(divider=True)
                continue
            if not label:
                command(m)
                pm.setParent(m, menu=True)
                continue

            pm.menuItem(label=label, command=command, image=img)

        return m

    except Exception as ex:
        template = ("An exception of type {0} occured. "
                    "Arguments:\n{1!r}")
        message = template.format(type(ex).__name__, ex.args)
        pm.displayError(message)


def install_main_menu():
    """Create top level mGear menu"""

    # Install mGear Menu
    import mgear
    mgear.install()

    # Install Shifter Menu
    import mgear.shifter.menu
    mgear.shifter.menu.install()

    # Install ueGear Menu
    import mgear.uegear.menu
    mgear.uegear.menu.install()

    # Install Simple Rig Menu
    import mgear.simpleRig.menu
    mgear.simpleRig.menu.install()

    # Install Skinning Menu
    import mgear.core.menu
    mgear.core.menu.install_skinning_menu()

    # Install Rigbits Menu
    import mgear.rigbits.menu
    mgear.rigbits.menu.install()

    # Install Animbits Menu
    import mgear.animbits.menu
    mgear.animbits.menu.install()

    # Install CFXbits Menu
    import mgear.cfxbits.menu
    mgear.cfxbits.menu.install()

    # Install Utilsbits Menu
    import mgear.utilbits.menu
    mgear.utilbits.menu.install()

    # Install Crank Menu
    import mgear.crank.menu
    mgear.crank.menu.install()

    # Install Anim Picker Menu
    import mgear.anim_picker.menu
    mgear.anim_picker.menu.install()

    # Install Flex Menu
    import mgear.flex.menu
    mgear.flex.menu.install()

    # Install Utilities Menu
    import mgear.menu
    m = mgear.menu.install_utils_menu()
    mgear.core.menu.install_utils_menu(m)
    mgear.rigbits.menu.install_utils_menu(m)

    # install dragdrop override in utilities
    import mgear.core.dragdrop
    mgear.core.dragdrop.install_utils_menu(m)

    # Install Help Menu
    mgear.menu.install_help_menu()

    # Install Dag Menu option
    import mgear.core.dagmenu
    mgear.core.dagmenu.install()

    # from cvwrap.menu import create_menuitems
    # create_menuitems()


str_web = """
import webbrowser
webbrowser.open("http://www.mgear-framework.com/")
"""

str_forum = """
import webbrowser
webbrowser.open("http://forum.mgear-framework.com/")
"""

str_docs = """
import webbrowser
webbrowser.open("https://mgear4.readthedocs.io/en/master/")
"""

str_about = """
import mgear
mgear.core.aboutMgear()
"""


str_reload = """
import mgear
mgear.reloadModule("mgear")
"""
