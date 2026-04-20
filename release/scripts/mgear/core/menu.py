from functools import partial
import mgear
import mgear.menu
from mgear.core import pyqt
from mgear.core import skin
from mgear.core import wmap
import mgear.pymaya as pm
from mgear.pymaya import versions


def install_skinning_menu():
    """安装蒙皮子菜单"""
    commands = (
        ("复制蒙皮", partial(skin.skinCopy, None, None), "mgear_copy.svg"),
        (
            "添加复制蒙皮",
            partial(skin.skin_copy_add, None, None),
            "mgear_copy-add.svg",
        ),
        (
            "部分复制蒙皮",
            partial(skin.skinCopyPartial, None, None),
            "mgear_copy-partial.svg",
        ),
        (
            "选择蒙皮变形器",
            skin.selectDeformers,
            "mgear_mouse-pointer.svg",
        ),
        ("-----", None),
        (
            "蒙皮簇选择器",
            str_openSkinClusterSelector,
            "mgear_list.svg",
        ),
        ("蒙皮簇重命名", skin.rename_skin_clusters, "mgear_edit-3.svg"),
        ("-----", None),
        ("导入蒙皮", partial(skin.importSkin, None), "mgear_log-in.svg"),
        (
            "导入蒙皮包",
            partial(skin.importSkinPack, None),
            "mgear_package_in.svg",
        ),
        ("-----", None),
        (
            "导出蒙皮",
            partial(skin.exportSkin, None, None),
            "mgear_log-out.svg",
        ),
        (
            "导出蒙皮包（二进制）",
            partial(skin.exportSkinPack, None, None),
            "mgear_package_out.svg",
        ),
        (
            "导出蒙皮包（ASCII）",
            partial(skin.exportJsonSkinPack, None, None),
            "mgear_package_out.svg",
        ),
        (
            "导出蒙皮包（ASCII，含位置数据）",
            partial(skin.exportJsonSkinPackWithPositions, None, None),
            "mgear_package_out_positions.svg",
        ),
        ("-----", None),
        ("获取gSkin文件中的名称", partial(skin.getObjsFromSkinFile, None)),
        ("-----", None),
        (
            "导入变形器权重贴图",
            partial(wmap.import_weights_selected, None),
            "mgear_log-in.svg",
        ),
        (
            "导出变形器权重贴图",
            partial(wmap.export_weights_selected, None),
            "mgear_log-out.svg",
        ),
    )

    mgear.menu.install("蒙皮和权重", commands, image="mgear_skin.svg")


def install_utils_menu(m):
    """安装核心工具子菜单"""
    if versions.current() < 20220000:
        pm.setParent(m, menu=True)
        pm.menuItem(divider=True)
        pm.menuItem(label="编译PyQt ui", command=pyqt.ui2py)


str_openSkinClusterSelector = """
from mgear.core import skin
skin.openSkinClusterSelector()
"""
