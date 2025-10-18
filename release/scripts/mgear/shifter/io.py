# Shifter guides IO utility functions
import os
import json
import sys
import re
import logging

from typing import List, Tuple, Sequence, Optional

import mgear.pymaya as pm
from mgear import shifter
from mgear.shifter import utils as shifter_utils
from mgear.core import curve
from mgear.core import string

if sys.version_info[0] == 2:
    string_types = (basestring, )
else:
    string_types = (str,)


logger = logging.getLogger("mgear.shifter.io")
logger.setLevel(logging.INFO)


# -- Pair lists kept separate for readability and future edits
_MH_SPINE: List[Tuple[str, str]] = [("root_C0_root", "root"),
                                    ("body_C0_root", "pelvis"),
                                    ("spine_C0_spineBase", "spine_01"),
                                    ("spine_C0_tan0", "spine_02"),
                                    ("spine_C0_spineTop", "spine_04"),
                                    ("spine_C0_tan1", "spine_03"),
                                    ("spine_C0_chest", "spine_05")
                                    ]

_MH_LEG: List[Tuple[str, str]] = [("leg_L0_root", "thigh_l"),
                                  ("leg_L0_knee", "calf_l"),
                                  ("leg_L0_ankle", "foot_l"),
                                  ("foot_L0_0_loc", "ball_l")
                                  ]

_MH_ARM: List[Tuple[str, str]] = [("clavicle_L0_root", "clavicle_l"),
                                  ("clavicle_L0_tip", "upperarm_l"),
                                  ("arm_L0_elbow", "lowerarm_l"),
                                  ("arm_L0_wrist", "hand_l")
                                  ]

_MH_HAND: List[Tuple[str, str]] = [("index_metacarpal_L0_root", "index_metacarpal_l"),
                                   ("middle_metacarpal_L0_root", "middle_metacarpal_l"),
                                   ("ring_metacarpal_L0_root", "ring_metacarpal_l"),
                                   ("pinky_metacarpal_L0_root", "pinky_metacarpal_l"),
                                   ("thumb_L0_root", "thumb_01_l"),
                                   ("thumb_L0_0_loc", "thumb_02_l"),
                                   ("thumb_L0_1_loc", "thumb_03_l"),
                                   ("index_L0_root", "index_01_l"),
                                   ("index_L0_0_loc", "index_02_l"),
                                   ("index_L0_1_loc", "index_03_l"),
                                   ("middle_L0_root", "middle_01_l"),
                                   ("middle_L0_0_loc", "middle_02_l"),
                                   ("middle_L0_1_loc", "middle_03_l"),
                                   ("ring_L0_root", "ring_01_l"),
                                   ("ring_L0_0_loc", "ring_02_l"),
                                   ("ring_L0_1_loc", "ring_03_l"),
                                   ("pinky_L0_root", "pinky_01_l"),
                                   ("pinky_L0_0_loc", "pinky_02_l"),
                                   ("pinky_L0_1_loc", "pinky_03_l")
                                   ]

_MH_NECK: List[Tuple[str, str]] = [("neck_C0_root", "neck_01"),
                                   ("neck_C0_neck", "head"),
                                   ("neck_C0_tan0", "neck_02")
                                   ]

_MH_IKS: List[Tuple[str, str]] = [("ik_foot_L0_root", "foot_l"),
                                  ("ik_hand_gun_C0_root", "hand_r"),
                                  ("ik_hand_L0_root", "hand_l")
                                  ]


# -- Compiled once, used to discover skeleton root and mirroring
_RE_ROOT_NAME = re.compile(r"(^|_)root($|_|$)", re.IGNORECASE)
_RE_SUFFIX_FROM_ROOT = re.compile(r"root(_[A-Za-z0-9]+)?$", re.IGNORECASE)


def get_guide_template_dict(guide_node, meta=None):
    """Get the guide template dictionary from a guide node.

    Args:
        guide_node (PyNode): The guide node to start the parsing from.
        meta (dict, optional): Arbitraty metadata dictionary. This can
            be use to store any custom information in a dictionary format.

    Returns:
        dict: the parsed guide dictionary
    """
    try:
        rig = shifter.Rig()
        rig.guide.setFromHierarchy(guide_node)
        return rig.guide.get_guide_template_dict(meta)
    except TypeError:
        pm.displayWarning("The selected object is not a valid guide element")


def get_template_from_selection(meta=None):
    """Get the guide template dictionary from a selected guide element.

    Args:
        meta (dict, optional): Arbitraty metadata dictionary. This can
            be use to store any custom information in a dictionary format.

    Returns:
        dict: the parsed guide dictionary

    """
    if pm.selected():
        return get_guide_template_dict(pm.selected()[0], meta)
    else:
        pm.displayWarning("Guide root or guide component must be selected")


def _get_file(write=False):
    """Convinience function to retrive the guide file in at export or import.

    Args:
        write (bool, optional): If true, will set the dialog to write.
            If false will se the dialog to read.

    Returns:
        str: the file path
    """
    if write:
        mode = 0
    else:
        mode = 1
    filePath = pm.fileDialog2(
        fileMode=mode,
        fileFilter='Shifter Guide Template .sgt (*%s)' % ".sgt")

    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    return filePath


def export_guide_template(filePath=None, meta=None, conf=None, *args):
    """Export the guide templata to a file

    Args:
        filePath (str, optional): Path to save the file
        meta (dict, optional): Arbitraty metadata dictionary. This can
            be use to store any custom information in a dictionary format.
    """
    if not conf:
        conf = get_template_from_selection(meta)
    if conf:
        data_string = json.dumps(conf, indent=4, sort_keys=True)
        if not filePath:
            filePath = _get_file(True)
            if not filePath:
                return

        with open(filePath, 'w') as f:
            f.write(data_string)


def _import_guide_template(filePath=None):
    """Summary

    Args:
        filePath (str, optional): Path to the template file to import

    Returns:
        dict: the parsed guide dictionary
    """
    if not filePath:
        filePath = _get_file()
    if not filePath:
        pm.displayWarning("File path to template is None")
        return
    conf = None
    with open(filePath, 'r') as f:
        if f:
            conf = json.load(f)

    return conf


def import_partial_guide(
        filePath=None, partial=None, initParent=None, conf=None):
    """Import a partial part of a template

    Limitations:
        - The UI host and space switch references are not updated. This may
        affect the configuration if the index change. I.e. Import 2 times same
        componet with internal UI host in the childs. the second import will
        point to the original UI host.

    Args:
        filePath (str, optional): Path to the template file to import
        partial (str or list of str, optional): If Partial starting
            component is defined, will try to add the guide to a selected
            guide part of an existing guide.
        initParent (dagNode, optional): Initial parent. If None, will
            create a new initial heirarchy
    """
    if not conf:
        conf = _import_guide_template(filePath)
    if conf:
        rig = shifter.Rig()
        rig.guide.set_from_dict(conf)
        partial_names, partial_idx = rig.guide.draw_guide(partial, initParent)

        # controls shapes buffer
        if not partial and conf["ctl_buffers_dict"]:
            curve.create_curve_from_data(conf["ctl_buffers_dict"],
                                         replaceShape=True,
                                         rebuildHierarchy=True,
                                         model=rig.guide.model)

        elif partial and conf["ctl_buffers_dict"]:
            # we need to match the ctl buffer names with the new
            # component index
            for crv in conf["ctl_buffers_dict"]["curves_names"]:
                if crv.startswith(tuple(partial_names)):
                    comp_name = "_".join(crv.split("_")[:2])
                    i = partial_names.index(comp_name)
                    pi = partial_idx[i]
                    scrv = crv.split("_")
                    crv = "_".join(scrv)
                    scrv[1] = scrv[1][0] + str(pi)
                    ncrv = "_".join(scrv)
                    curve.create_curve_from_data_by_name(
                        crv,
                        conf["ctl_buffers_dict"],
                        replaceShape=True,
                        rebuildHierarchy=True,
                        rplStr=[crv, ncrv],
                        model=rig.guide.model)


def import_guide_template(filePath=None, conf=None, **kwargs):
    """Import a guide template

    Args:
        filePath (str, optional): Path to the template file to import
    """
    import_partial_guide(filePath, conf=conf, **kwargs)


def build_from_file(filePath=None, conf=False, *args):
    """Build a rig from a template file.
    The rig will be build from a previously exported guide template, without
    creating the guide in the scene.

    Args:
        filePath (None, optional): Guide template file path

    """
    if not conf:
        conf = _import_guide_template(filePath)
    if conf:
        rig = shifter.Rig()
        rig.buildFromDict(conf)

        # controls shapes buffer
        if conf["ctl_buffers_dict"]:
            curve.update_curve_from_data(conf["ctl_buffers_dict"],
                                         rplStr=["_controlBuffer", ""])
        return rig


# Sample import command
def import_sample_template(name, *args):
    """Import the sample guide templates from _template folder

    Args:
        name (str): Name of the guide template file. with extension.
        *args: Maya Dummy
    """
    shifter_path = os.path.dirname(shifter.__file__)
    path = os.path.join(shifter_path, "component", "_templates", name)
    import_guide_template(path)


def _find_guide_root_name() -> Optional[str]:
    """
    Return the mGear guide model name from utils.get_guide() or None.
    """
    _guide = shifter_utils.get_guide()
    if not _guide:
        logger.warning("No guide found. Select a guide root or component.")
        return None
    return _guide[0].node().name()


def _snap_translation(src: pm.PyNode, dst: pm.PyNode) -> None:
    """
    Snap source world translation to destination world translation.
    """
    src.setTranslation(dst.getTranslation(space="world"), space="world")


def _get_suffix(root_nodes: List) -> str:
    """
    Get the suffix (e.g. '_drv') from the first root joint in the list.

    :param list[str] root_nodes: List of joint names containing 'root'.
    :return: The detected suffix or an empty string if none is found.
    :rtype: str
    """
    root_short = root_nodes[0].split("|")[-1]
    m = _RE_SUFFIX_FROM_ROOT.search(root_short)

    return m.group(1) if (m and m.group(1)) else ""


def _set_roll_divisions_zero() -> None:
    """
    Set roll division to 0 on upper and lower leg and arm components.

    There is already rig logic from MetaHuman driving the twists, so there is
    no need for mGear to build its own twist logic when driving a built MetaHuman.

    :return: None
    """
    for side in "LR":
        for comp_name in ["arm", "leg"]:
            comp_roots = [f"{comp_name}_{side}0_root.div0",
                          f"{comp_name}_{side}0_root.div1"]

            for comp in comp_roots:
                if not pm.objExists(comp_name):
                    continue
                # -- Set upper and lower values to zero
                pm.setAttr(comp, 0)


# Epic Metahuman snap to skeleton utility function
def metahuman_snap():
    """
    Snap the MetaHuman guide to align with its corresponding skeleton.

    Finds the skeleton root to extract the suffix - if there is one (e.g., `_drv`),
    then snaps guide locators to their matching driver joints in world space.
    Left-side elements are mirrored to the right automatically. Finally, updates
    the joint naming rule and sets roll divisions for correct deformation.

    :return: None
    """

    guide_name = _find_guide_root_name()

    # -- Exit early, if no guide in the scene.
    if not guide_name:
        logger.error("No guide found in the scene.")
        return

    all_joints = pm.ls(long=True, type="joint")
    root_nodes = [n for n in all_joints if _RE_ROOT_NAME.search(n.split("|")[-1])]

    # -- Exit early if no root node is found
    if not root_nodes:
        logger.error("No root or root_drv found in the scene.")
        return

    # -- extract suffix if there is one (backwards compatibility)
    suffix = _get_suffix(root_nodes=root_nodes)

    # -- Create one list with all paired items to match
    # -- Build mapping once
    left_pairs: Sequence[Tuple[str, str]] = (_MH_SPINE + _MH_LEG + _MH_ARM + _MH_HAND + _MH_NECK + _MH_IKS)
    processed: List[Tuple[str, str]] = []

    for src_left, tgt_left in left_pairs:
        # -- Left pair - Adding the corrected suffix to the target skeleton
        processed.append((src_left, f"{tgt_left}{suffix}"))

        # -- Only mirror if the SOURCE actually has an L/R token
        src_right = string.convertRLName(src_left)
        if src_right != src_left:
            tgt_right = string.convertRLName(tgt_left) + suffix
            processed.append((src_right, tgt_right))

    # -- Snapping
    for src_name, dst_name in processed:
        try:
            src = pm.PyNode(src_name)
            dst = pm.PyNode(dst_name)
        except pm.MayaNodeError:
            logger.warning(f"Missing node. Skipping pair: {src_name} -> {dst_name}")
            continue

        try:
            _snap_translation(src, dst)
        except Exception as exc:
            logger.error(f"Failed to snap {src_name} to {dst_name}: {exc}")

    # -- Ensure to set the correct naming rule for mGear build.
    name_pattern = f"{{description}}{{side}}{suffix}"
    joint_name_rule = f"{guide_name}.joint_name_rule"

    if not pm.objExists(joint_name_rule):
        logger.error("Guide and attribute could not be found in the scene.")
        return

    # -- Set the value
    pm.setAttr(joint_name_rule, name_pattern)

    # -- Set the roll attributes
    _set_roll_divisions_zero()

    logger.info("Successfully aligned mGear guide to MetaHuman skeleton.")
