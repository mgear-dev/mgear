import mgear.pymaya as pm
import mgear

from mgear.core import string


menuID = "Rigbits"


def install():
    """Install Rigbits submenu"""
    pm.setParent(mgear.menu_id, menu=True)
    pm.menuItem(divider=True)
    commands = (
        ("添加NPO", str_add_NPO, "mgear_add_npo.svg"),
        ("-----", None),
        (None, gimmick_submenu),
        # ("Gimmick Setup Tool", str_gimmick_tool),
        ("-----", None),
        ("镜像控制器形状", str_mirror_ctls, "mgear_mirror_controls.svg"),
        ("替换形状", str_replace_shape, "mgear_replace_shape.svg"),
        ("-----", None),
        ("匹配所有变换", str_matchWorldXform, "mgear_match_transform.svg"),
        ("通过边界框匹配位置", str_matchPosfromBBox, "mgear_match_bbox.svg"),
        ("对齐参考轴", str_alignToPointsLoop, "mgear_align_ref_axis.svg"),
        ("-----", None),
        (None, pCtl_sub),
        (None, cCtl_sub),
        ("-----", None),
        ("对称复制", str_duplicateSym, "mgear_duplicate_sym.svg"),
        ("-----", None),
        ("RBF管理器 2.1", str_rbf_manager2_ui, "mgear_rbf_manager.svg"),
        ("SDK管理器", str_SDK_manager_ui, "mgear_sdk_manager.svg"),
        ("SDK创建器", str_sdk_creator, "mgear_sdk_creator.svg"),
        ("-----", None),
        ("空间管理器", str_space_manager, "mgear_space_manager.svg"),
        ("-----", None),
        ("空间跳跃", str_spaceJump, "mgear_space_jumper.svg"),
        ("插值变换", str_createInterpolateTransform, "mgear_interpolate_transform.svg"),
        (None, connect_submenu),
        ("-----", None),
        ("通道整理器", str_openChannelWrangler, "mgear_channel_wrangler.svg"),
        ("-----", None),
        ("眼睑绑定器 2.1", str_eye_rigger, "mgear_eye_rigger.svg"),
        ("面部绑定器 1.0（旧版）", str_facial_rigger, "mgear_facial_rigger.svg"),
        ("-----", None),
        ("线框到蒙皮", str_wire_to_skinning, "mgear_wire_to_skinning.svg"),
        ("评估分区", str_evaluation_partition, "mgear_evaluation_partition.svg"),
        ("混合形状设置传输", str_blendshape_transfer, "mgear_copy.svg"),
        ("-----", None),
        ("代理几何体", str_proxyGeo, "mgear_proxyGeo_to_next.svg"),
        ("代理切片器", str_proxySlicer, "mgear_proxy_slicer.svg"),
        ("代理切片器父子关系", str_proxySlicer_parent, "mgear_proxy_slicer.svg"),
    )

    mgear.menu.install(menuID, commands, image="mgear_rigbits.svg")


def connect_submenu(parent_menu_id):
    """Create the connect local Scale, rotation and translation submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("连接SRT", str_connect_SRT),
        ("连接S", str_connect_S),
        ("连接R", str_connect_R),
        ("连接T", str_connect_T),
    )

    mgear.menu.install("连接局部SRT", commands, parent_menu_id)


def gimmick_submenu(parent_menu_id):
    """Create the gimmick joint submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("添加关节", str_addJnt),
        ("-----", None),
        ("添加混合关节", str_addBlendedJoint),
        ("添加支撑关节", str_addSupportJoint),
    )

    mgear.menu.install("Gimmick关节", commands, parent_menu_id)


def _ctl_submenu(parent_menu_id, name, cCtl=False):
    """Create contol submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
        name (str): Menu name
        pCtl (bool, optional): If True, the new control will be child
                               of selected
    """
    ctls = [
        "方形",
        "圆形",
        "立方体",
        "菱形",
        "球体",
        "十字箭头",
        "金字塔",
        "带顶点的立方体",
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
    _ctl_submenu(parent_menu_id, "控制器作为父级", cCtl=False)


def cCtl_sub(parent_menu_id):
    """Create control as child of selected elements

    Args:
        parent_menu_id (stro): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    _ctl_submenu(parent_menu_id, "控制器作为子级", cCtl=True)


def install_utils_menu(m):
    """Install rigbit utils submenu"""
    pm.setParent(m, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="创建mGear快捷键", command=str_createHotkeys)


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

str_sdk_creator = """
from mgear.rigbits import sdk_creator
sdk_creator.show()
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

str_wire_to_skinning = """
from mgear.rigbits import wire_to_skinning
wire_to_skinning.show()
"""

str_evaluation_partition = """
from mgear.rigbits import evaluation_partition
evaluation_partition.show()
"""

str_blendshape_transfer = """
from mgear.rigbits import blendshape_transfer
blendshape_transfer.show()
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
