from functools import partial
import mgear
import mgear.menu
from mgear.core import pyqt
from mgear.core import skin
from mgear.core import wmap
import mgear.pymaya as pm
from mgear.pymaya import versions


def install_skinning_menu():
    """Install Skinning submenu"""
    commands = (
        ("Copy Skin", partial(skin.skinCopy, None, None), "mgear_copy.svg"),
        (
            "Copy Skin Add",
            partial(skin.skin_copy_add, None, None),
            "mgear_copy-add.svg",
        ),
        (
            "Copy Skin Partial",
            partial(skin.skinCopyPartial, None, None),
            "mgear_copy-partial.svg",
        ),
        (
            "Select Skin Deformers",
            skin.selectDeformers,
            "mgear_mouse-pointer.svg",
        ),
        ("-----", None),
        (
            "Skin Cluster Selector",
            str_openSkinClusterSelector,
            "mgear_list.svg",
        ),
        ("Skin Cluster Rename", skin.rename_skin_clusters, "mgear_edit-3.svg"),
        ("-----", None),
        ("Import Skin", partial(skin.importSkin, None), "mgear_log-in.svg"),
        (
            "Import Skin Pack",
            partial(skin.importSkinPack, None),
            "mgear_package_in.svg",
        ),
        ("-----", None),
        (
            "Export Skin",
            partial(skin.exportSkin, None, None),
            "mgear_log-out.svg",
        ),
        (
            "Export Skin Pack Binary",
            partial(skin.exportSkinPack, None, None),
            "mgear_package_out.svg",
        ),
        (
            "Export Skin Pack ASCII",
            partial(skin.exportJsonSkinPack, None, None),
            "mgear_package_out.svg",
        ),
        ("-----", None),
        ("Get Names in gSkin File", partial(skin.getObjsFromSkinFile, None)),
        ("-----", None),
        (
            "Import Deformer Weight Map",
            partial(wmap.import_weights_selected, None),
            "mgear_log-in.svg",
        ),
        (
            "Export Deformer Weight Map",
            partial(wmap.export_weights_selected, None),
            "mgear_log-out.svg",
        ),
    )

    mgear.menu.install("Skin and Weights", commands, image="mgear_skin.svg")


def install_utils_menu(m):
    """Install core utils submenu"""
    if versions.current() < 20220000:
        pm.setParent(m, menu=True)
        pm.menuItem(divider=True)
        pm.menuItem(label="Compile PyQt ui", command=pyqt.ui2py)


str_openSkinClusterSelector = """
from mgear.core import skin
skin.openSkinClusterSelector()
"""
