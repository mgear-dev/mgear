import mgear.pymaya as pm
import mgear

from mgear.core import string


menuID = "Rigbits"


def install():
    """Install Rigbits submenu"""
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    commands = (
        ("Add NPO", str_add_NPO),
        ("-----", None),
        (None, gimmick_submenu),
        # ("Gimmick Setup Tool", str_gimmick_tool),
        ("-----", None),
        ("Mirror Controls Shape", str_mirror_ctls),
        ("Replace Shape", str_replace_shape),
        ("-----", None),
        ("Match All Transform", str_matchWorldXform),
        ("Match Pos with BBox", str_matchPosfromBBox),
        ("Align Ref Axis", str_alignToPointsLoop),
        ("-----", None),
        (None, pCtl_sub),
        (None, cCtl_sub),
        ("-----", None),
        ("Duplicate symmetrical", str_duplicateSym),
        ("-----", None),
        ("RBF Manager 2.1", str_rbf_manager2_ui),
        ("SDK Manager", str_SDK_manager_ui),
        ("-----", None),
        ("Space Manager", str_space_manager),
        ("-----", None),
        ("Space Jumper", str_spaceJump),
        ("Interpolated Transform", str_createInterpolateTransform),
        (None, connect_submenu),
        ("-----", None),
        ("Channel Wrangler", str_openChannelWrangler),
        ("-----", None),
        ("Eyelid Rigger 2.0", str_eye_rigger),
        ("Facial Rigger 1.0 (Legacy)", str_facial_rigger),
        ("-----", None),
        ("Proxy Geo", str_proxyGeo, "mgear_proxyGeo_to_next.svg"),
        ("Proxy Slicer", str_proxySlicer),
        ("Proxy Slicer Parenting", str_proxySlicer_parent),
    )

    mgear.menu.install(menuID, commands, image="mgear_rigbits.svg")


def connect_submenu(parent_menu_id):
    """Create the connect local Scale, rotation and translation submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("Connect SRT", str_connect_SRT),
        ("Connect S", str_connect_S),
        ("Connect R", str_connect_R),
        ("Connect T", str_connect_T),
    )

    mgear.menu.install("Connect Local SRT", commands, parent_menu_id)


def gimmick_submenu(parent_menu_id):
    """Create the gimmick joint submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("Add Joint", str_addJnt),
        ("-----", None),
        ("Add Blended Joint", str_addBlendedJoint),
        ("Add Support Joint", str_addSupportJoint),
    )

    mgear.menu.install("Gimmick Joints", commands, parent_menu_id)


def _ctl_submenu(parent_menu_id, name, cCtl=False):
    """Create contol submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
        name (str): Menu name
        pCtl (bool, optional): If True, the new control will be child
                               of selected
    """
    ctls = [
        "Square",
        "Circle",
        "Cube",
        "Diamond",
        "Sphere",
        "Cross Arrow",
        "Pyramid",
        "Cube With Peak",
    ]
    commands = []
    for c in ctls:
        cm = string.removeInvalidCharacter(c).lower()
        commands.append(
            [
                c,
                "from mgear import rigbits\nrigbits.createCTL('{0}', {1})".format(
                    cm, str(cCtl)
                ),
            ]
        )
    mgear.menu.install(name, commands, parent_menu_id)


def pCtl_sub(parent_menu_id):
    """Create control as parent of selected elements

    Args:
        parent_menu_id (stro): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    _ctl_submenu(parent_menu_id, "CTL as Parent", cCtl=False)


def cCtl_sub(parent_menu_id):
    """Create control as child of selected elements

    Args:
        parent_menu_id (stro): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    _ctl_submenu(parent_menu_id, "CTL as Child", cCtl=True)


def install_utils_menu(m):
    """Install rigbit utils submenu"""
    pm.setParent(m, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Create mGear Hotkeys", command=str_createHotkeys)


# menu str commands

str_add_NPO = """
from mgear import rigbits
rigbits.addNPO()
"""

str_gimmick_tool = """
from mgear.rigbits.gimmick_tool import main
main.mainUI()
"""

str_mirror_ctls = """
from mgear.rigbits import mirror_controls
mirror_controls.show()
"""

str_replace_shape = """
from mgear import rigbits
rigbits.replaceShape()
"""

str_matchWorldXform = """
from mgear import rigbits
rigbits.matchWorldXform()
"""

str_matchPosfromBBox = """
from mgear import rigbits
rigbits.matchPosfromBBox()
"""

str_alignToPointsLoop = """
from mgear import rigbits
rigbits.alignToPointsLoop()
"""

str_duplicateSym = """
from mgear import rigbits
rigbits.duplicateSym()
"""

str_rbf_manager2_ui = """
from mgear.rigbits.rbf_manager2 import rbf_manager_ui
rbf_manager_ui.show()
"""

str_SDK_manager_ui = """
from mgear.rigbits.sdk_manager import SDK_manager_ui
SDK_manager_ui.show()
"""
str_space_manager = """
from mgear.rigbits.space_manager import spaceManagerUtils
spacemanager = spaceManagerUtils.SpaceManager()
"""

str_spaceJump = """
from mgear import rigbits
rigbits.spaceJump()
"""


str_createInterpolateTransform = """
from mgear import rigbits
rigbits.createInterpolateTransform()
"""

str_openChannelWrangler = """
from mgear.rigbits import channelWrangler
channelWrangler.openChannelWrangler()
"""

str_proxyGeo = """
from mgear.rigbits import proxyGeo
proxyGeo.openProxyGeo()
"""

str_proxySlicer = """
from mgear.rigbits import proxySlicer
proxySlicer.slice()
"""

str_proxySlicer_parent = """
from mgear.rigbits import proxySlicer
proxySlicer.slice(True)
"""

# connect str commands

str_connect_SRT = """
from mgear import rigbits
rigbits.connectLocalTransform(None, 1, 1, 1)
"""

str_connect_S = """
from mgear import rigbits
rigbits.connectLocalTransform(None, 1, 0, 0)
"""

str_connect_R = """
from mgear import rigbits
rigbits.connectLocalTransform(None, 0, 1, 0)
"""

str_connect_T = """
from mgear import rigbits
rigbits.connectLocalTransform(None, 0, 0, 1)
"""

str_facial_rigger = """
from mgear.rigbits import facial_rigger
facial_rigger.show()
"""

# eye rigger 2.0 str commands

str_eye_rigger = """
from mgear.rigbits import facial_rigger2
facial_rigger2.eye_riggerUI.show()
"""

# Gimmick joints str commands

str_addJnt = """
from mgear import rigbits
rigbits.addJnt()
"""

str_addBlendedJoint = """
from mgear import rigbits
rigbits.addBlendedJoint()
"""

str_addSupportJoint = """
from mgear import rigbits
rigbits.addSupportJoint()
"""


# hotkeys str command

str_createHotkeys = """
from mgear.rigbits import utils
utils.createHotkeys()
"""
