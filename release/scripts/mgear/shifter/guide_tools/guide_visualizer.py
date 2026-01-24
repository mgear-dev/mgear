"""Guide Visualizer Tool
"""

from __future__ import print_function

import sys
import json

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import mgear.pymaya as pm
from mgear.core import icon
from mgear.core import pyqt
from mgear.core.widgets import create_button, CollapsibleWidget

QtGui, QtCore, QtWidgets, wrapInstance = pyqt.qt_import()

if sys.version_info[0] >= 3:
    long_type = int
else:
    long_type = long


# ----------------------------------------------------------------------
# Curve Selection & Thickness Helpers
# ----------------------------------------------------------------------

CV_SCALE_ATTR = "shifterGuideCvScale"


def _get_cv_scale(transform):
    """Get the cumulative CV scale from the transform's custom attribute.

    Args:
        transform (str): Transform node name.

    Returns:
        float: Current CV scale value, or 1.0 if not set.
    """
    if not cmds.attributeQuery(CV_SCALE_ATTR, node=transform, exists=True):
        return 1.0
    try:
        return float(cmds.getAttr(transform + "." + CV_SCALE_ATTR))
    except Exception:
        return 1.0


def _set_cv_scale(transform, scale):
    """Set the cumulative CV scale on the transform's custom attribute.

    Args:
        transform (str): Transform node name.
        scale (float): Scale value to set.
    """
    if not cmds.attributeQuery(CV_SCALE_ATTR, node=transform, exists=True):
        cmds.addAttr(transform, ln=CV_SCALE_ATTR, at="double", dv=1.0)
        cmds.setAttr(transform + "." + CV_SCALE_ATTR, keyable=False)
    cmds.setAttr(transform + "." + CV_SCALE_ATTR, scale)


def get_selected_curves():
    """Get all selected curves (nurbs curves and their shapes).

    Returns:
        list[str]: List of nurbsCurve shape long names.
    """
    selection = cmds.ls(selection=True, long=True)
    curves = []
    for obj in selection:
        if cmds.nodeType(obj) == "nurbsCurve":
            curves.append(obj)
        else:
            shapes = cmds.listRelatives(
                obj, shapes=True, fullPath=True, type="nurbsCurve"
            ) or []
            curves.extend(shapes)
    return curves


def adjust_curve_thickness(increment):
    """Adjust the lineWidth of selected curves.

    Args:
        increment (float): Amount to add to current lineWidth.
    """
    curves = get_selected_curves()
    if not curves:
        cmds.warning("No curves selected.")
        return
    for curve in curves:
        current = cmds.getAttr(curve + ".lineWidth")
        if current < 0:
            current = 1.0
        cmds.setAttr(curve + ".lineWidth", max(1.0, current + increment))


def scale_curve_cvs(scale_factor):
    """Scale CVs of selected curves around each transform's pivot.

    Also updates the shifterGuideCvScale attribute to track cumulative scale.

    Args:
        scale_factor (float): Multiplier for scaling.
            Example: 1.25 to enlarge, 1.0/1.25 to shrink.

    Raises:
        RuntimeError: If nothing is selected.
    """
    sel = cmds.ls(sl=True, long=True)
    if not sel:
        raise RuntimeError("No objects selected.")

    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        if not shapes:
            continue

        has_curve = False
        # Get transform pivot in world space
        piv = cmds.xform(obj, q=True, ws=True, rp=True)

        for shp in shapes:
            if cmds.nodeType(shp) != "nurbsCurve":
                continue

            has_curve = True
            cv_list = cmds.ls(shp + ".cv[*]", fl=True) or []
            for cv in cv_list:
                pos = cmds.pointPosition(cv, w=True)
                vec = [
                    (pos[0] - piv[0]) * scale_factor,
                    (pos[1] - piv[1]) * scale_factor,
                    (pos[2] - piv[2]) * scale_factor
                ]
                new_pos = [piv[0] + vec[0],
                           piv[1] + vec[1],
                           piv[2] + vec[2]]

                cmds.xform(cv, ws=True, t=new_pos)

        # Update cumulative scale attribute on transform
        if has_curve:
            current_scale = _get_cv_scale(obj)
            _set_cv_scale(obj, current_scale * scale_factor)


# ----------------------------------------------------------------------
# Curve Color Helpers
# ----------------------------------------------------------------------

def short_name(node):
    """Get short name from a full path.

    Args:
        node (str): Node name or full DAG path.

    Returns:
        str: Short name.
    """
    if not node:
        return node
    return node.split("|")[-1]


def get_curve_shapes_from_transform(transform, name_filter):
    """Get curve shapes under transform whose name contains the filter.

    Args:
        transform (str): Transform node name.
        name_filter (str): Substring to look for in the shape name.

    Returns:
        list: List of shape node names.
    """
    shapes = cmds.listRelatives(
        transform,
        shapes=True,
        fullPath=True
    ) or []
    result = []
    for shape in shapes:
        node_type = cmds.nodeType(shape)
        if node_type not in ("nurbsCurve", "bezierCurve"):
            continue
        sname = shape.split("|")[-1]
        if not name_filter or name_filter in sname:
            result.append(shape)
    return result


def set_shape_color(shape, rgb):
    """Set the override RGB color on a shape.

    Args:
        shape (str): Shape node name.
        rgb (tuple[float, float, float]): RGB values in 0-1 range.
    """
    if not cmds.objExists(shape):
        return
    if not cmds.attributeQuery("overrideEnabled", node=shape, exists=True):
        return
    cmds.setAttr(shape + ".overrideEnabled", 1)
    if cmds.attributeQuery("overrideRGBColors", node=shape, exists=True):
        cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(
        shape + ".overrideColorRGB",
        rgb[0],
        rgb[1],
        rgb[2],
        type="double3",
    )


def get_shape_color(shape):
    """Get the override RGB color from a shape.

    Args:
        shape (str): Shape node name.

    Returns:
        tuple or None: (r, g, b) in 0-1 range, or None if not set.
    """
    if not cmds.objExists(shape):
        return None
    if not cmds.attributeQuery("overrideRGBColors", node=shape, exists=True):
        return None
    try:
        use_rgb = cmds.getAttr(shape + ".overrideRGBColors")
    except Exception:
        use_rgb = 0
    if not use_rgb:
        return None
    try:
        rgb = cmds.getAttr(shape + ".overrideColorRGB")[0]
    except Exception:
        return None
    return rgb


def reset_shape_color(shape):
    """Reset a curve shape color by disabling RGB and enabling index mode.

    Args:
        shape (str): Shape node name.

    Returns:
        bool: True if reset succeeded, False otherwise.
    """
    if not cmds.objExists(shape):
        return False

    try:
        if cmds.attributeQuery("overrideRGBColors", node=shape, exists=True):
            cmds.setAttr(shape + ".overrideRGBColors", 0)
        cmds.setAttr(shape + ".overrideEnabled", 1)
    except Exception:
        return False

    return True


# ----------------------------------------------------------------------
# Guide Label Helpers
# ----------------------------------------------------------------------

LABEL_TAG_ATTR = "mgearGuideLabel"
LABEL_RED_INDEX = 13
LABEL_YELLOW_INDEX = 17
LABEL_DEFAULT_OFFSET = (1.0, 1.0, 1.0)


def is_mgear_guide(node):
    """Check if node is an mGear guide.

    Args:
        node (str): Node name.

    Returns:
        bool: True if node has the isGearGuide attribute.
    """
    if not cmds.objExists(node):
        return False
    return cmds.attributeQuery("isGearGuide", node=node, exists=True)


def guide_label_text(node):
    """Return label text for guide.

    Args:
        node (str): Guide node name.

    Returns:
        str: Label text without _root suffix.
    """
    name = node.split("|")[-1]
    if name.endswith("_root"):
        return name[:-5]
    return name


def is_root_guide(node):
    """Check if guide is a root guide based on its name.

    Args:
        node (str): Guide node name.

    Returns:
        bool: True if name ends with _root.
    """
    sname = node.split("|")[-1]
    return sname.endswith("_root")


def find_root_shape(node):
    """Find first shape with _root in its name under node.

    Args:
        node (str): Guide node name.

    Returns:
        str or None: Shape name or None if not found.
    """
    shapes = cmds.listRelatives(
        node, shapes=True, noIntermediate=True
    ) or []
    for shp in shapes:
        if "_root" in shp:
            return shp
    return None


def apply_rgb_from_shape(dst_shape, src_shape):
    """Apply RGB override from source shape to destination shape.

    Args:
        dst_shape (str): Destination shape name.
        src_shape (str): Source shape name.
    """
    if not cmds.getAttr(src_shape + ".overrideEnabled"):
        return

    use_rgb = False
    if cmds.attributeQuery("overrideRGBColors", node=src_shape, exists=True):
        if cmds.getAttr(src_shape + ".overrideRGBColors"):
            use_rgb = True

    if not use_rgb:
        return

    rgb = cmds.getAttr(src_shape + ".overrideColorRGB")[0]
    cmds.setAttr(dst_shape + ".overrideEnabled", 1)
    cmds.setAttr(dst_shape + ".overrideRGBColors", 1)
    cmds.setAttr(dst_shape + ".overrideColorRGB", *rgb)


def color_label(label_shape, guide):
    """Color label based on guide/root shape.

    Args:
        label_shape (str): Annotation shape name.
        guide (str): Guide node name.
    """
    root_shape = find_root_shape(guide)
    if root_shape:
        apply_rgb_from_shape(label_shape, root_shape)
        return

    root = is_root_guide(guide)
    color_index = LABEL_RED_INDEX if root else LABEL_YELLOW_INDEX
    cmds.setAttr(label_shape + ".overrideEnabled", 1)
    cmds.setAttr(label_shape + ".overrideRGBColors", 0)
    cmds.setAttr(label_shape + ".overrideColor", color_index)


def tag_label(label_transform):
    """Tag label transform so it can be found later.

    Args:
        label_transform (str): Transform name.
    """
    if not cmds.attributeQuery(LABEL_TAG_ATTR, node=label_transform,
                               exists=True):
        cmds.addAttr(
            label_transform,
            ln=LABEL_TAG_ATTR,
            at="bool"
        )
        cmds.setAttr(label_transform + "." + LABEL_TAG_ATTR, True)


def get_label_for_guide(guide):
    """Return label transform under guide, if any.

    Args:
        guide (str): Guide node name.

    Returns:
        str or None: Label transform name or None.
    """
    children = cmds.listRelatives(guide, children=True, type="transform")
    if not children:
        return None

    for child in children:
        if not cmds.attributeQuery(LABEL_TAG_ATTR, node=child, exists=True):
            continue
        shapes = cmds.listRelatives(
            child, shapes=True, noIntermediate=True
        ) or []
        for shp in shapes:
            if cmds.nodeType(shp) == "annotationShape":
                return child
    return None


def create_label(guide, offset):
    """Create label for a guide.

    Existing label is removed first.

    Args:
        guide (str): Guide node name.
        offset (tuple[float, float, float]): Offset vector.

    Returns:
        str: Label transform name.
    """
    if not is_mgear_guide(guide):
        return None

    existing = get_label_for_guide(guide)
    if existing:
        cmds.delete(existing)

    text = guide_label_text(guide)
    anno = cmds.annotate(guide, tx=text)
    if cmds.nodeType(anno) == "annotationShape":
        label_transform = cmds.listRelatives(anno, parent=True)[0]
        label_shape = anno
    else:
        label_transform = anno
        shapes = cmds.listRelatives(
            label_transform, shapes=True, noIntermediate=True
        ) or []
        if not shapes:
            cmds.delete(label_transform)
            return None
        label_shape = shapes[0]

    cmds.parent(label_transform, guide)

    guide_pos = cmds.xform(guide, q=True, ws=True, t=True)
    target_pos = [
        guide_pos[0] + offset[0],
        guide_pos[1] + offset[1],
        guide_pos[2] + offset[2],
    ]
    cmds.xform(label_transform, ws=True, t=target_pos)

    color_label(label_shape, guide)
    tag_label(label_transform)

    return label_transform


def remove_label_from_guide(guide):
    """Remove label from given guide.

    Args:
        guide (str): Guide node name.
    """
    label = get_label_for_guide(guide)
    if label and cmds.objExists(label):
        cmds.delete(label)


def list_all_labels():
    """List all label transforms in the scene.

    Returns:
        list[str]: List of label transform node names.
    """
    plugs = cmds.ls("*.{0}".format(LABEL_TAG_ATTR)) or []
    labels = []
    for plug in plugs:
        node = plug.split(".", 1)[0]
        if not cmds.attributeQuery(LABEL_TAG_ATTR, node=node, exists=True):
            continue
        if not cmds.getAttr(plug):
            continue
        shapes = cmds.listRelatives(
            node, shapes=True, noIntermediate=True
        ) or []
        valid = False
        for shp in shapes:
            if cmds.nodeType(shp) == "annotationShape":
                valid = True
                break
        if valid:
            labels.append(node)
    return labels


def compute_label_offset(guide, label):
    """Compute offset from guide to label.

    Args:
        guide (str): Guide node name.
        label (str): Label transform node name.

    Returns:
        tuple[float, float, float]: Offset vector.
    """
    g_pos = cmds.xform(guide, q=True, ws=True, t=True)
    l_pos = cmds.xform(label, q=True, ws=True, t=True)
    return (
        l_pos[0] - g_pos[0],
        l_pos[1] - g_pos[1],
        l_pos[2] - g_pos[2],
    )


def get_label_color_data(label_shape):
    """Get color data from label shape.

    Args:
        label_shape (str): Annotation shape name.

    Returns:
        dict: Color data with keys:
            use_rgb (bool),
            color_rgb (list[float, float, float]),
            color_index (int).
    """
    use_rgb = False
    color_rgb = [1.0, 1.0, 1.0]
    color_index = 0

    if cmds.getAttr(label_shape + ".overrideEnabled"):
        if cmds.getAttr(label_shape + ".overrideRGBColors"):
            use_rgb = True
            color_rgb = list(
                cmds.getAttr(label_shape + ".overrideColorRGB")[0]
            )
        else:
            color_index = cmds.getAttr(label_shape + ".overrideColor")

    return {
        "use_rgb": use_rgb,
        "color_rgb": color_rgb,
        "color_index": int(color_index),
    }


def set_label_color_from_data(label_shape, color_data):
    """Apply color to label shape using color data.

    Args:
        label_shape (str): Annotation shape name.
        color_data (dict): Color data as from get_label_color_data().
    """
    use_rgb = bool(color_data.get("use_rgb", False))
    if use_rgb:
        rgb = color_data.get("color_rgb", [1.0, 1.0, 1.0])
        cmds.setAttr(label_shape + ".overrideEnabled", 1)
        cmds.setAttr(label_shape + ".overrideRGBColors", 1)
        cmds.setAttr(label_shape + ".overrideColorRGB", *rgb)
    else:
        index = int(color_data.get("color_index", 0))
        cmds.setAttr(label_shape + ".overrideEnabled", 1)
        cmds.setAttr(label_shape + ".overrideRGBColors", 0)
        cmds.setAttr(label_shape + ".overrideColor", index)


def export_labels_to_json(file_path):
    """Export all labels to a JSON file.

    Args:
        file_path (str): Destination file path.
    """
    labels = list_all_labels()
    data = {"labels": []}

    for lbl in labels:
        parent = cmds.listRelatives(lbl, parent=True)
        if not parent:
            continue
        guide = parent[0]
        if not is_mgear_guide(guide):
            continue

        shapes = cmds.listRelatives(
            lbl, shapes=True, noIntermediate=True
        ) or []
        if not shapes:
            continue
        shp = shapes[0]
        if cmds.nodeType(shp) != "annotationShape":
            continue

        offset = compute_label_offset(guide, lbl)
        text = cmds.getAttr(shp + ".text") or ""
        color_data = get_label_color_data(shp)

        data["labels"].append(
            {
                "guide": guide,
                "label": text,
                "offset": list(offset),
                "color": color_data,
            }
        )

    with open(file_path, "w") as fobj:
        json.dump(data, fobj, indent=4)


def import_labels_from_json(file_path):
    """Import labels from a JSON file.

    Existing labels for imported guides are replaced.

    Args:
        file_path (str): JSON file path.
    """
    with open(file_path, "r") as fobj:
        data = json.load(fobj)

    for item in data.get("labels", []):
        guide = item.get("guide")
        if not guide or not cmds.objExists(guide):
            continue
        if not is_mgear_guide(guide):
            continue

        offset = item.get("offset", list(LABEL_DEFAULT_OFFSET))
        offset = (
            float(offset[0]),
            float(offset[1]),
            float(offset[2]),
        )

        remove_label_from_guide(guide)
        anno = cmds.annotate(guide, tx=item.get("label", ""))

        if cmds.nodeType(anno) == "annotationShape":
            label_transform = cmds.listRelatives(anno, parent=True)[0]
            label_shape = anno
        else:
            label_transform = anno
            shapes = cmds.listRelatives(
                label_transform, shapes=True, noIntermediate=True
            ) or []
            if not shapes:
                cmds.delete(label_transform)
                continue
            label_shape = shapes[0]

        cmds.parent(label_transform, guide)

        g_pos = cmds.xform(guide, q=True, ws=True, t=True)
        target_pos = [
            g_pos[0] + offset[0],
            g_pos[1] + offset[1],
            g_pos[2] + offset[2],
        ]
        cmds.xform(label_transform, ws=True, t=target_pos)

        color_data = item.get("color", {})
        set_label_color_from_data(label_shape, color_data)
        tag_label(label_transform)


def toggle_labels_visibility():
    """Toggle visibility of all label transforms.

    If any label is visible, all labels are hidden. Otherwise all labels
    are shown.
    """
    labels = list_all_labels()
    if not labels:
        return

    any_visible = False
    for lbl in labels:
        if cmds.objExists(lbl) and cmds.getAttr(lbl + ".visibility"):
            any_visible = True
            break

    new_state = not any_visible
    for lbl in labels:
        if cmds.objExists(lbl):
            cmds.setAttr(lbl + ".visibility", new_state)


# ----------------------------------------------------------------------
# Display Curve Core Helpers
# ----------------------------------------------------------------------

# Default pale pink color for display curves (RGB 0-1 range)
DISPLAY_CURVE_DEFAULT_COLOR = (1.0, 0.7, 0.8)


def _find_curve_cns_node(curve_transform):
    """Find the mgear_curveCns node driving the display curve.

    Args:
        curve_transform (pm.nt.Transform): Display curve transform.

    Returns:
        pm.PyNode or None: mgear_curveCns node or None.
    """
    shape = curve_transform.getShape()
    if not shape:
        return None

    history = shape.listHistory(future=False)
    for node in history:
        try:
            if node.type() == "mgear_curveCns":
                return node
        except Exception:
            continue

    return None


def _get_inputs_in_order(curve_cns_node):
    """Get inputs of mgear_curveCns.inputs in logical index order.

    Args:
        curve_cns_node (pm.PyNode): mgear_curveCns node.

    Returns:
        list[pm.PyNode]: Connected input transforms in order.
    """
    plug = "{}.inputs".format(curve_cns_node.name())
    indices = cmds.getAttr(plug, multiIndices=True) or []
    inputs = []

    for idx in indices:
        plug_idx = "{}[{}]".format(plug, idx)
        srcs = cmds.listConnections(plug_idx, s=True, d=False) or []
        if not srcs:
            continue
        try:
            inputs.append(pm.PyNode(srcs[0]))
        except Exception:
            continue

    return inputs


def _mirror_input_node(node):
    """Return mirrored node for a given transform.

    Args:
        node (pm.PyNode): Input transform.

    Returns:
        pm.PyNode or None: Mirrored or same node, or None on failure.
    """
    name = node.name()

    if "_L" in name:
        mirrored_name = name.replace("_L", "_R", 1)
        if cmds.objExists(mirrored_name):
            return pm.PyNode(mirrored_name)
        return None

    return node


def _build_mirrored_curve_name(curve_transform, has_l_input):
    """Build name for the mirrored display curve.

    Args:
        curve_transform (pm.nt.Transform): Original display curve.
        has_l_input (bool): True if any input contains "_L".

    Returns:
        str or None: Mirrored curve name or None.
    """
    name = curve_transform.name()

    if "_L" in name:
        return name.replace("_L", "_R", 1)

    if has_l_input:
        return name

    return None


def _center_mirror_already_exists(disp_crv, mirrored_inputs):
    """Check if a mirrored center curve already exists.

    Args:
        disp_crv (pm.nt.Transform): Original display curve.
        mirrored_inputs (list[pm.PyNode]): Mirrored inputs list.

    Returns:
        bool: True if a matching mirrored curve already exists.
    """
    base_name = disp_crv.name()
    pattern = "{}*".format(base_name)
    candidates = pm.ls(pattern, type="transform") or []

    target_names = [n.name() for n in mirrored_inputs]

    for crv in candidates:
        if crv.name() == base_name:
            continue

        curve_cns = _find_curve_cns_node(crv)
        if not curve_cns:
            continue

        other_inputs = _get_inputs_in_order(curve_cns)
        other_names = [n.name() for n in other_inputs]

        if other_names == target_names:
            return True

    return False


# ----------------------------------------------------------------------
# Shape Color Config Helpers (for display curves)
# ----------------------------------------------------------------------

def _get_shape_color_config(curve_transform):
    """Get color configuration for all shapes under a display curve.

    Args:
        curve_transform (pm.nt.Transform): Display curve transform.

    Returns:
        list[dict]: One entry per shape with color/type data.
    """
    shapes = curve_transform.getShapes(noIntermediate=True) or []
    cfg = []

    for shp in shapes:
        try:
            ov_enabled = bool(shp.overrideEnabled.get())
        except Exception:
            ov_enabled = False

        color_type = "none"
        index_val = None
        rgb_val = None

        if ov_enabled:
            try:
                use_rgb = bool(shp.overrideRGBColors.get())
            except Exception:
                use_rgb = False

            if use_rgb:
                color_type = "rgb"
                try:
                    r = shp.overrideColorR.get()
                    g = shp.overrideColorG.get()
                    b = shp.overrideColorB.get()
                    rgb_val = [float(r), float(g), float(b)]
                except Exception:
                    rgb_val = None
            else:
                color_type = "index"
                try:
                    index_val = int(shp.overrideColor.get())
                except Exception:
                    index_val = None

        cfg.append(
            {
                "shape": shp.name(),
                "overrideEnabled": ov_enabled,
                "colorType": color_type,
                "index": index_val,
                "rgb": rgb_val,
            }
        )

    return cfg


def _apply_shape_color_config(curve_transform, shapes_cfg):
    """Apply color configuration to shapes of a display curve.

    Args:
        curve_transform (pm.nt.Transform): Display curve transform.
        shapes_cfg (list[dict]): Color configuration entries.
    """
    if not shapes_cfg:
        return

    shapes = curve_transform.getShapes(noIntermediate=True) or []
    if not shapes:
        return

    count = min(len(shapes), len(shapes_cfg))

    for i in range(count):
        shp = shapes[i]
        cfg = shapes_cfg[i]

        ov_enabled = bool(cfg.get("overrideEnabled", False))
        color_type = cfg.get("colorType", "none")
        index_val = cfg.get("index")
        rgb_val = cfg.get("rgb")

        try:
            shp.overrideEnabled.set(ov_enabled)
        except Exception:
            continue

        if not ov_enabled or color_type == "none":
            continue

        if color_type == "rgb" and rgb_val is not None:
            try:
                shp.overrideRGBColors.set(True)
                shp.overrideColorR.set(rgb_val[0])
                shp.overrideColorG.set(rgb_val[1])
                shp.overrideColorB.set(rgb_val[2])
            except Exception:
                continue
        elif color_type == "index" and index_val is not None:
            try:
                shp.overrideRGBColors.set(False)
                shp.overrideColor.set(index_val)
            except Exception:
                continue


# ----------------------------------------------------------------------
# Main Operations
# ----------------------------------------------------------------------

def mirror_connection_display_curves():
    """Mirror all *_disp_crv* curves according to naming rules.

    Copies:
        * inputs
        * lineWidth
        * shape colors
        * shape overrideDisplayType (toggle state)
        * keeps transform overrideEnabled off
    """
    disp_crvs = pm.ls("*_disp_crv*", type="transform") or []

    if not disp_crvs:
        print("mirror_connection_display_curves: No *_disp_crv* found.")
        return

    for disp_crv in disp_crvs:
        curve_cns = _find_curve_cns_node(disp_crv)
        if not curve_cns:
            print("No mgear_curveCns for curve: {}".format(disp_crv))
            continue

        inputs = _get_inputs_in_order(curve_cns)
        if not inputs:
            print("No inputs on mgear_curveCns: {}".format(curve_cns))
            continue

        all_center = all("_C" in n.name() for n in inputs)
        has_l_input = any("_L" in n.name() for n in inputs)

        if all_center:
            print(
                "All inputs are center (_C) on '{}', skipping '{}'."
                .format(curve_cns, disp_crv)
            )
            continue

        mirrored_inputs = []
        failed = False
        for node in inputs:
            mirrored = _mirror_input_node(node)
            if mirrored is None:
                print(
                    "Missing mirrored object for '{}' on curve '{}', "
                    "skipping.".format(node, disp_crv)
                )
                failed = True
                break
            mirrored_inputs.append(mirrored)

        if failed:
            continue

        new_name = _build_mirrored_curve_name(disp_crv, has_l_input)
        if not new_name:
            continue

        if new_name != disp_crv.name():
            if cmds.objExists(new_name):
                print(
                    "Mirror curve '{}' already exists, skipping."
                    .format(new_name)
                )
                continue
        else:
            if _center_mirror_already_exists(disp_crv, mirrored_inputs):
                print(
                    "Center mirror for '{}' with same inputs already "
                    "exists. Skipping.".format(disp_crv)
                )
                continue

        # Store source visual config before creating the new curve
        src_shapes_cfg = _get_shape_color_config(disp_crv)
        src_shapes = disp_crv.getShapes(noIntermediate=True) or []

        # Create mirrored curve
        new_disp_crv = icon.connection_display_curve(
            new_name,
            mirrored_inputs,
            1
        )

        # Copy lineWidth
        try:
            src_width = disp_crv.attr("lineWidth").get()
            new_disp_crv.attr("lineWidth").set(src_width)
        except Exception:
            pass

        # Transform override disabled
        try:
            new_disp_crv.overrideEnabled.set(False)
        except Exception:
            pass

        # Copy color config to shapes
        _apply_shape_color_config(new_disp_crv, src_shapes_cfg)

        # Copy overrideDisplayType (toggle state) on shapes
        new_shapes = new_disp_crv.getShapes(noIntermediate=True) or []
        count = min(len(src_shapes), len(new_shapes))
        for i in range(count):
            src_shape = src_shapes[i]
            dst_shape = new_shapes[i]
            try:
                val = int(src_shape.overrideDisplayType.get())
                dst_shape.overrideEnabled.set(True)
                dst_shape.overrideDisplayType.set(val)
            except Exception:
                continue

        print(
            "Created mirrored display curve '{}' from '{}'.".format(
                new_disp_crv, disp_crv
            )
        )


def create_display_curve_from_selection(line_width=2.0):
    """Create a connection_display_curve from current selection.

    Transform overrideEnabled is turned off.
    Shapes are set to overrideEnabled = True and displayType = 1.
    """
    sel = pm.selected() or []
    if not sel:
        print("No selection. Please select at least one object.")
        return None

    base_name = sel[0].name()
    crv_name = "{}_disp_crv".format(base_name)

    if cmds.objExists(crv_name):
        print(
            "Display curve '{}' already exists. Skipping."
            .format(crv_name)
        )
        return None

    disp_crv = icon.connection_display_curve(crv_name, sel, 1)

    try:
        disp_crv.attr("lineWidth").set(line_width)
    except Exception:
        pass

    try:
        disp_crv.overrideEnabled.set(False)
    except Exception:
        pass

    shapes = disp_crv.getShapes(noIntermediate=True) or []
    for shp in shapes:
        try:
            shp.overrideEnabled.set(True)
            shp.overrideDisplayType.set(1)
            # Apply default pale pink color
            shp.overrideRGBColors.set(True)
            shp.overrideColorRGB.set(*DISPLAY_CURVE_DEFAULT_COLOR)
        except Exception:
            continue

    print("Created display curve '{}'.".format(disp_crv))
    return disp_crv


def set_all_display_curves_thickness(line_width):
    """Set lineWidth on all *_disp_crv* curves."""
    disp_crvs = pm.ls("*_disp_crv*", type="transform") or []

    if not disp_crvs:
        print("No *_disp_crv* curves found.")
        return

    count = 0
    for crv in disp_crvs:
        try:
            crv.attr("lineWidth").set(line_width)
            count += 1
        except Exception:
            continue

    print(
        "Updated lineWidth to {} on {} curves."
        .format(line_width, count)
    )


def select_all_display_curves():
    """Select all *_disp_crv* transforms in the scene."""
    disp_crvs = pm.ls("*_disp_crv*", type="transform") or []
    if not disp_crvs:
        print("No *_disp_crv* curves found.")
        return

    pm.select(disp_crvs, r=True)
    print("Selected {} display curves.".format(len(disp_crvs)))


def toggle_display_type_all_curves():
    """Toggle overrideDisplayType on shapes, disable transform override.

    Behaviour:
        * All display curve transforms: overrideEnabled = False.
        * Shapes: overrideDisplayType toggled between 0 and 1.
    """
    disp_crvs = pm.ls("*_disp_crv*", type="transform") or []

    if not disp_crvs:
        print("No *_disp_crv* curves found.")
        return

    ref_val = None
    for crv in disp_crvs:
        shapes = crv.getShapes(noIntermediate=True) or []
        for shp in shapes:
            try:
                ref_val = int(shp.overrideDisplayType.get())
                break
            except Exception:
                continue
        if ref_val is not None:
            break

    if ref_val is None:
        ref_val = 0

    new_val = 0 if ref_val == 1 else 1

    for crv in disp_crvs:
        try:
            crv.overrideEnabled.set(False)
        except Exception:
            pass

        shapes = crv.getShapes(noIntermediate=True) or []
        for shp in shapes:
            try:
                shp.overrideEnabled.set(True)
                shp.overrideDisplayType.set(new_val)
            except Exception:
                continue

    print(
        "Set shapes overrideDisplayType to {} on all display curves."
        .format(new_val)
    )


# ----------------------------------------------------------------------
# Export / Import Configuration
# ----------------------------------------------------------------------

def export_display_curve_configuration():
    """Build a JSON-serializable config for all *_disp_crv* curves."""
    config = []
    disp_crvs = pm.ls("*_disp_crv*", type="transform") or []

    for crv in disp_crvs:
        curve_cns = _find_curve_cns_node(crv)
        inputs = []
        if curve_cns:
            inputs = _get_inputs_in_order(curve_cns)

        try:
            width = crv.attr("lineWidth").get()
        except Exception:
            width = None

        # Get CV scale if set
        cv_scale = _get_cv_scale(crv.name())

        shapes_cfg = _get_shape_color_config(crv)

        entry = {
            "curve": crv.name(),
            "inputs": [n.name() for n in inputs],
            "lineWidth": width,
            "cvScale": cv_scale,
            "shapes": shapes_cfg,
        }
        config.append(entry)

    return config


def _apply_cv_scale_to_curve(curve_name, target_scale):
    """Apply CV scale to a curve, computing delta from current scale.

    Args:
        curve_name (str): Curve transform name.
        target_scale (float): Desired cumulative CV scale.
    """
    if target_scale is None or target_scale == 1.0:
        return

    current_scale = _get_cv_scale(curve_name)
    if abs(current_scale - target_scale) < 0.0001:
        return

    # Compute delta scale factor needed
    delta = target_scale / current_scale

    shapes = cmds.listRelatives(curve_name, shapes=True, fullPath=True) or []
    piv = cmds.xform(curve_name, q=True, ws=True, rp=True)

    for shp in shapes:
        if cmds.nodeType(shp) != "nurbsCurve":
            continue

        cv_list = cmds.ls(shp + ".cv[*]", fl=True) or []
        for cv in cv_list:
            pos = cmds.pointPosition(cv, w=True)
            vec = [
                (pos[0] - piv[0]) * delta,
                (pos[1] - piv[1]) * delta,
                (pos[2] - piv[2]) * delta
            ]
            new_pos = [piv[0] + vec[0], piv[1] + vec[1], piv[2] + vec[2]]
            cmds.xform(cv, ws=True, t=new_pos)

    _set_cv_scale(curve_name, target_scale)


def import_display_curve_configuration(config):
    """Create/update curves from a configuration."""
    if not isinstance(config, list):
        cmds.warning("Invalid configuration format.")
        return

    created = 0
    updated = 0

    for entry in config:
        curve_name = entry.get("curve")
        inputs_names = entry.get("inputs") or []
        line_width = entry.get("lineWidth", None)
        cv_scale = entry.get("cvScale", None)
        shapes_cfg = entry.get("shapes") or []

        if not curve_name:
            continue

        input_nodes = []
        missing = False
        for name in inputs_names:
            if not cmds.objExists(name):
                cmds.warning(
                    "Missing input '{}' for curve '{}', skipping."
                    .format(name, curve_name)
                )
                missing = True
                break
            input_nodes.append(pm.PyNode(name))

        if missing or not input_nodes:
            continue

        if cmds.objExists(curve_name):
            try:
                crv = pm.PyNode(curve_name)
            except Exception:
                continue

            if line_width is not None:
                try:
                    crv.attr("lineWidth").set(line_width)
                except Exception:
                    pass

            # Apply CV scale delta
            _apply_cv_scale_to_curve(curve_name, cv_scale)

            _apply_shape_color_config(crv, shapes_cfg)
            updated += 1
            continue

        try:
            new_crv = icon.connection_display_curve(
                curve_name,
                input_nodes,
                1
            )
        except Exception as exc:
            cmds.warning(
                "Failed to create curve '{}': {}".format(
                    curve_name, exc
                )
            )
            continue

        if line_width is not None:
            try:
                new_crv.attr("lineWidth").set(line_width)
            except Exception:
                pass

        # Apply CV scale to newly created curve
        _apply_cv_scale_to_curve(new_crv.name(), cv_scale)

        _apply_shape_color_config(new_crv, shapes_cfg)
        created += 1

    print(
        "Import configuration: created {}, updated {} curves."
        .format(created, updated)
    )


def export_guide_colors_configuration():
    """Build a JSON-serializable config for guide root colors.

    Returns:
        list[dict]: Color configuration entries for guide shapes.
    """
    config = []
    # Find all transforms with isGearGuide attribute
    guides = [n for n in cmds.ls(type="transform") or []
              if cmds.attributeQuery("isGearGuide", node=n, exists=True)]

    for guide in guides:
        shapes = cmds.listRelatives(
            guide, shapes=True, fullPath=True
        ) or []
        for shape in shapes:
            if cmds.nodeType(shape) not in ("nurbsCurve", "bezierCurve"):
                continue
            rgb = get_shape_color(shape)
            if rgb is None:
                continue
            config.append({
                "guide": guide,
                "shape": shape,
                "color": [rgb[0], rgb[1], rgb[2]],
            })

    return config


def import_guide_colors_configuration(config):
    """Apply guide colors from configuration.

    Args:
        config (list[dict]): Color configuration entries.
    """
    if not isinstance(config, list):
        return

    applied = 0
    for entry in config:
        shape = entry.get("shape")
        color = entry.get("color")
        if not shape or color is None:
            continue
        if not cmds.objExists(shape):
            continue
        if len(color) != 3:
            continue
        rgb = (float(color[0]), float(color[1]), float(color[2]))
        set_shape_color(shape, rgb)
        applied += 1

    print("Applied colors to {} shapes.".format(applied))


def export_guide_curves_configuration():
    """Build a JSON-serializable config for guide curve shapes.

    Exports lineWidth and CV scale for all curve shapes under guides
    (objects with isGearGuide attribute).

    Returns:
        list[dict]: Curve configuration entries with guide, shape,
            lineWidth, and cvScale.
    """
    config = []
    # Find all transforms with isGearGuide attribute
    guides = [n for n in cmds.ls(type="transform") or []
              if cmds.attributeQuery("isGearGuide", node=n, exists=True)]

    for guide in guides:
        # Get CV scale from the guide transform itself
        cv_scale = _get_cv_scale(guide)

        shapes = cmds.listRelatives(
            guide, shapes=True, fullPath=True
        ) or []
        for shape in shapes:
            if cmds.nodeType(shape) not in ("nurbsCurve", "bezierCurve"):
                continue

            # Get lineWidth from shape
            try:
                line_width = cmds.getAttr(shape + ".lineWidth")
            except Exception:
                line_width = -1.0

            # Only export if there's something to store
            if cv_scale == 1.0 and line_width <= 0:
                continue

            config.append({
                "guide": guide,
                "shape": shape,
                "lineWidth": line_width,
                "cvScale": cv_scale,
            })

    return config


def import_guide_curves_configuration(config):
    """Apply guide curve configuration.

    Args:
        config (list[dict]): Curve configuration entries.
    """
    if not isinstance(config, list):
        return

    applied_width = 0
    applied_scale = 0
    processed_guides = set()

    for entry in config:
        guide = entry.get("guide")
        shape = entry.get("shape")
        line_width = entry.get("lineWidth")
        cv_scale = entry.get("cvScale")

        if not guide or not cmds.objExists(guide):
            continue

        # Apply lineWidth to shape if it exists
        if shape and cmds.objExists(shape):
            if line_width is not None and line_width > 0:
                try:
                    cmds.setAttr(shape + ".lineWidth", line_width)
                    applied_width += 1
                except Exception:
                    pass

        # Apply CV scale to guide (only once per guide)
        if guide not in processed_guides and cv_scale is not None:
            _apply_cv_scale_to_curve(guide, cv_scale)
            processed_guides.add(guide)
            if cv_scale != 1.0:
                applied_scale += 1

    print("Applied lineWidth to {} shapes, CV scale to {} guides.".format(
        applied_width, applied_scale))


def export_labels_configuration():
    """Build a JSON-serializable config for all guide labels.

    Returns:
        list[dict]: Label configuration entries.
    """
    config = []
    labels = list_all_labels()

    for lbl in labels:
        parent = cmds.listRelatives(lbl, parent=True)
        if not parent:
            continue
        guide = parent[0]
        if not is_mgear_guide(guide):
            continue

        shapes = cmds.listRelatives(
            lbl, shapes=True, noIntermediate=True
        ) or []
        if not shapes:
            continue
        shp = shapes[0]
        if cmds.nodeType(shp) != "annotationShape":
            continue

        offset = compute_label_offset(guide, lbl)
        text = cmds.getAttr(shp + ".text") or ""
        color_data = get_label_color_data(shp)

        config.append({
            "guide": guide,
            "label": text,
            "offset": list(offset),
            "color": color_data,
        })

    return config


def import_labels_configuration(config):
    """Create labels from configuration.

    Args:
        config (list[dict]): Label configuration entries.
    """
    if not isinstance(config, list):
        return

    created = 0
    for item in config:
        guide = item.get("guide")
        if not guide or not cmds.objExists(guide):
            continue
        if not is_mgear_guide(guide):
            continue

        offset = item.get("offset", list(LABEL_DEFAULT_OFFSET))
        offset = (float(offset[0]), float(offset[1]), float(offset[2]))

        remove_label_from_guide(guide)
        anno = cmds.annotate(guide, tx=item.get("label", ""))

        if cmds.nodeType(anno) == "annotationShape":
            label_transform = cmds.listRelatives(anno, parent=True)[0]
            label_shape = anno
        else:
            label_transform = anno
            shapes = cmds.listRelatives(
                label_transform, shapes=True, noIntermediate=True
            ) or []
            if not shapes:
                cmds.delete(label_transform)
                continue
            label_shape = shapes[0]

        cmds.parent(label_transform, guide)

        g_pos = cmds.xform(guide, q=True, ws=True, t=True)
        target_pos = [
            g_pos[0] + offset[0],
            g_pos[1] + offset[1],
            g_pos[2] + offset[2],
        ]
        cmds.xform(label_transform, ws=True, t=target_pos)

        color_data = item.get("color", {})
        set_label_color_from_data(label_shape, color_data)
        tag_label(label_transform)
        created += 1

    print("Created {} labels.".format(created))


def export_full_configuration(file_path):
    """Export all guide visualizer configuration to a single JSON file.

    Includes:
        - Display curves configuration
        - Guide colors
        - Guide curves (lineWidth, CV scale)
        - Labels

    Args:
        file_path (str): Destination file path.
    """
    data = {
        "version": 2,
        "display_curves": export_display_curve_configuration(),
        "guide_colors": export_guide_colors_configuration(),
        "guide_curves": export_guide_curves_configuration(),
        "labels": export_labels_configuration(),
    }

    with open(file_path, "w") as fobj:
        json.dump(data, fobj, indent=4)

    counts = (
        len(data["display_curves"]),
        len(data["guide_colors"]),
        len(data["guide_curves"]),
        len(data["labels"]),
    )
    print(
        "Exported configuration: {} display curves, {} colors, "
        "{} guide curves, {} labels.".format(*counts)
    )


def import_full_configuration(file_path):
    """Import all guide visualizer configuration from a JSON file.

    Args:
        file_path (str): Source JSON file path.
    """
    with open(file_path, "r") as fobj:
        data = json.load(fobj)

    # Import display curves
    disp_curves = data.get("display_curves")
    if disp_curves:
        import_display_curve_configuration(disp_curves)

    # Import guide colors
    guide_colors = data.get("guide_colors")
    if guide_colors:
        import_guide_colors_configuration(guide_colors)

    # Import guide curves (lineWidth, CV scale)
    guide_curves = data.get("guide_curves")
    if guide_curves:
        import_guide_curves_configuration(guide_curves)

    # Import labels
    labels = data.get("labels")
    if labels:
        import_labels_configuration(labels)

    print("Import complete.")


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------

class GuideVisualizerUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """UI tool for guide visualization: display curves and curve editing."""

    SCALE_UP_FACTOR = 1.25
    SCALE_DOWN_FACTOR = 1.0 / 1.25
    toolName = "mgearGuideVisualizerTool"

    # Default values for settings
    DEFAULT_CURRENT_COLOR = (255, 255, 0)
    DEFAULT_COLOR_HISTORY = []
    DEFAULT_FILTER_TEXT = "_root"
    DEFAULT_THICKNESS = 2
    DEFAULT_OFFSET_X = LABEL_DEFAULT_OFFSET[0]
    DEFAULT_OFFSET_Y = LABEL_DEFAULT_OFFSET[1]
    DEFAULT_OFFSET_Z = LABEL_DEFAULT_OFFSET[2]

    def __init__(self, parent=None):
        super(GuideVisualizerUI, self).__init__(parent)
        self.setWindowTitle("Guide Visualizer")
        self.setObjectName(self.toolName)
        self.setMinimumWidth(200)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Color state (will be loaded from settings)
        self._current_color = QtGui.QColor(*self.DEFAULT_CURRENT_COLOR)
        self._color_history = []

        self._build_ui()
        self._create_connections()
        self._load_settings()
        self._update_color_preview()
        self._refresh_history_buttons()

    def _build_ui(self):
        """Build the Qt widgets and layout."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(1)

        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.file_menu = self.menu_bar.addMenu("File")
        self.export_action = self.file_menu.addAction(
            "Export Configuration..."
        )
        self.import_action = self.file_menu.addAction(
            "Import Configuration..."
        )

        # Edit menu
        self.edit_menu = self.menu_bar.addMenu("Edit")
        self.reset_defaults_action = self.edit_menu.addAction(
            "Reset to Defaults"
        )
        main_layout.setMenuBar(self.menu_bar)

        # Scroll area for collapsible sections
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(1)

        # ---- Display Curves Section ----
        self.display_curves_section = CollapsibleWidget("Display Curves")
        self.create_btn = QtWidgets.QPushButton("Create From Selection")
        self.select_btn = QtWidgets.QPushButton("Select All")
        self.mirror_btn = QtWidgets.QPushButton("Mirror Curves")
        self.display_curves_section.addWidget(self.create_btn)
        self.display_curves_section.addWidget(self.select_btn)
        self.display_curves_section.addWidget(self.mirror_btn)

        # Thickness row inside display curves
        thickness_widget = QtWidgets.QWidget()
        disp_thickness_layout = QtWidgets.QHBoxLayout(thickness_widget)
        disp_thickness_layout.setContentsMargins(0, 2, 0, 0)
        disp_thickness_layout.setSpacing(4)
        self.thickness_spin = QtWidgets.QSpinBox()
        self.thickness_spin.setMinimum(1)
        self.thickness_spin.setMaximum(50)
        self.thickness_spin.setSingleStep(1)
        self.thickness_spin.setValue(2)
        self.thickness_spin.setFixedWidth(50)
        self.apply_thickness_btn = QtWidgets.QPushButton("Apply to All")
        disp_thickness_layout.addWidget(QtWidgets.QLabel("Width:"))
        disp_thickness_layout.addWidget(self.thickness_spin)
        disp_thickness_layout.addWidget(self.apply_thickness_btn)
        self.display_curves_section.addWidget(thickness_widget)

        # Toggle display type
        toggle_widget = QtWidgets.QWidget()
        toggle_layout = QtWidgets.QHBoxLayout(toggle_widget)
        toggle_layout.setContentsMargins(0, 2, 0, 0)
        toggle_layout.setSpacing(4)
        toggle_layout.addWidget(QtWidgets.QLabel("Status:"))
        self.toggle_display_type_btn = QtWidgets.QPushButton("Toggle")
        toggle_layout.addWidget(self.toggle_display_type_btn)
        toggle_layout.addStretch()
        self.display_curves_section.addWidget(toggle_widget)

        scroll_layout.addWidget(self.display_curves_section)

        # ---- Selected Curves Section ----
        self.selected_curves_section = CollapsibleWidget("Selected Curves")

        # Combined row for thickness and CV scale
        sel_widget = QtWidgets.QWidget()
        sel_layout = QtWidgets.QGridLayout(sel_widget)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(4)

        # Thickness row
        sel_layout.addWidget(QtWidgets.QLabel("Thickness:"), 0, 0)
        self.thickness_minus_btn = create_button(
            size=24, icon="mgear_minus", toolTip="Decrease Thickness (-1)"
        )
        self.thickness_plus_btn = create_button(
            size=24, icon="mgear_plus", toolTip="Increase Thickness (+1)"
        )
        thickness_btn_widget = QtWidgets.QWidget()
        thickness_btn_layout = QtWidgets.QHBoxLayout(thickness_btn_widget)
        thickness_btn_layout.setContentsMargins(0, 0, 0, 0)
        thickness_btn_layout.setSpacing(2)
        thickness_btn_layout.addWidget(self.thickness_minus_btn)
        thickness_btn_layout.addWidget(self.thickness_plus_btn)
        thickness_btn_layout.addStretch()
        sel_layout.addWidget(thickness_btn_widget, 0, 1)

        # CV Scale row
        sel_layout.addWidget(QtWidgets.QLabel("CV Scale:"), 1, 0)
        self.scale_down_btn = create_button(
            size=24, icon="mgear_minus", toolTip="Scale CVs Down (0.8x)"
        )
        self.scale_up_btn = create_button(
            size=24, icon="mgear_plus", toolTip="Scale CVs Up (1.25x)"
        )
        scale_btn_widget = QtWidgets.QWidget()
        scale_btn_layout = QtWidgets.QHBoxLayout(scale_btn_widget)
        scale_btn_layout.setContentsMargins(0, 0, 0, 0)
        scale_btn_layout.setSpacing(2)
        scale_btn_layout.addWidget(self.scale_down_btn)
        scale_btn_layout.addWidget(self.scale_up_btn)
        scale_btn_layout.addStretch()
        sel_layout.addWidget(scale_btn_widget, 1, 1)

        self.selected_curves_section.addWidget(sel_widget)
        scroll_layout.addWidget(self.selected_curves_section)

        # ---- Curve Colors Section ----
        self.curve_colors_section = CollapsibleWidget("Curve Colors")

        # Filter row
        filter_widget = QtWidgets.QWidget()
        filter_layout = QtWidgets.QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        self.filter_line = QtWidgets.QLineEdit("_root")
        self.filter_line.setToolTip(
            "Only apply to shapes whose name contains this string"
        )
        filter_layout.addWidget(QtWidgets.QLabel("Filter:"))
        filter_layout.addWidget(self.filter_line)
        self.curve_colors_section.addWidget(filter_widget)

        # Color picker row
        color_widget = QtWidgets.QWidget()
        color_layout = QtWidgets.QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(4)
        self.color_button = QtWidgets.QPushButton("Pick Color")
        self.color_button.setFixedHeight(25)
        self.pick_from_sel_button = QtWidgets.QPushButton("Get From Sel")
        self.pick_from_sel_button.setFixedHeight(25)
        color_layout.addWidget(QtWidgets.QLabel("Color:"))
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.pick_from_sel_button)
        color_layout.addStretch()
        self.curve_colors_section.addWidget(color_widget)

        # History row
        history_widget = QtWidgets.QWidget()
        history_layout = QtWidgets.QHBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(4)
        self.history_container = QtWidgets.QWidget()
        self.history_layout = QtWidgets.QHBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(2)
        history_layout.addWidget(QtWidgets.QLabel("History:"))
        history_layout.addWidget(self.history_container)
        history_layout.addStretch()
        self.curve_colors_section.addWidget(history_widget)

        # Apply / Reset row
        apply_widget = QtWidgets.QWidget()
        apply_layout = QtWidgets.QHBoxLayout(apply_widget)
        apply_layout.setContentsMargins(0, 2, 0, 0)
        apply_layout.setSpacing(4)
        self.apply_color_button = QtWidgets.QPushButton("Apply")
        self.reset_color_button = QtWidgets.QPushButton("Reset")
        apply_layout.addWidget(self.apply_color_button)
        apply_layout.addWidget(self.reset_color_button)
        self.curve_colors_section.addWidget(apply_widget)

        scroll_layout.addWidget(self.curve_colors_section)

        # ---- Guide Labels Section ----
        self.guide_labels_section = CollapsibleWidget("Guide Labels")

        # Offset rows (3 separate rows for narrow UI)
        offset_grid = QtWidgets.QWidget()
        offset_layout = QtWidgets.QGridLayout(offset_grid)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(2)
        offset_layout.setColumnStretch(1, 1)

        self.offset_x_spin = QtWidgets.QDoubleSpinBox()
        self.offset_x_spin.setRange(-100.0, 100.0)
        self.offset_x_spin.setValue(LABEL_DEFAULT_OFFSET[0])
        self.offset_x_spin.setDecimals(2)

        self.offset_y_spin = QtWidgets.QDoubleSpinBox()
        self.offset_y_spin.setRange(-100.0, 100.0)
        self.offset_y_spin.setValue(LABEL_DEFAULT_OFFSET[1])
        self.offset_y_spin.setDecimals(2)

        self.offset_z_spin = QtWidgets.QDoubleSpinBox()
        self.offset_z_spin.setRange(-100.0, 100.0)
        self.offset_z_spin.setValue(LABEL_DEFAULT_OFFSET[2])
        self.offset_z_spin.setDecimals(2)

        offset_layout.addWidget(QtWidgets.QLabel("Offset X:"), 0, 0)
        offset_layout.addWidget(self.offset_x_spin, 0, 1)
        offset_layout.addWidget(QtWidgets.QLabel("Offset Y:"), 1, 0)
        offset_layout.addWidget(self.offset_y_spin, 1, 1)
        offset_layout.addWidget(QtWidgets.QLabel("Offset Z:"), 2, 0)
        offset_layout.addWidget(self.offset_z_spin, 2, 1)

        self.guide_labels_section.addWidget(offset_grid)

        # Add/Remove label buttons (stacked vertically for narrow UI)
        self.add_label_btn = QtWidgets.QPushButton("Add to Selected")
        self.remove_label_btn = QtWidgets.QPushButton("Remove from Selected")
        self.guide_labels_section.addWidget(self.add_label_btn)
        self.guide_labels_section.addWidget(self.remove_label_btn)

        # Remove all / Toggle visibility
        label_actions_widget = QtWidgets.QWidget()
        label_actions_layout = QtWidgets.QHBoxLayout(label_actions_widget)
        label_actions_layout.setContentsMargins(0, 2, 0, 0)
        label_actions_layout.setSpacing(4)
        self.remove_all_labels_btn = QtWidgets.QPushButton("Remove All")
        self.toggle_labels_btn = QtWidgets.QPushButton("Toggle Vis")
        label_actions_layout.addWidget(self.remove_all_labels_btn)
        label_actions_layout.addWidget(self.toggle_labels_btn)
        self.guide_labels_section.addWidget(label_actions_widget)

        scroll_layout.addWidget(self.guide_labels_section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _create_connections(self):
        """Wire up signals."""
        # Display curves actions
        self.create_btn.clicked.connect(self._on_create_from_sel)
        self.select_btn.clicked.connect(self._on_select_all)
        self.mirror_btn.clicked.connect(self._on_mirror_curves)
        self.apply_thickness_btn.clicked.connect(self._on_apply_thickness)
        self.toggle_display_type_btn.clicked.connect(
            self._on_toggle_display_type
        )

        # File menu
        self.export_action.triggered.connect(self._on_export_config)
        self.import_action.triggered.connect(self._on_import_config)

        # Edit menu
        self.reset_defaults_action.triggered.connect(self._on_reset_defaults)

        # Selected curves thickness
        self.thickness_minus_btn.clicked.connect(
            lambda: adjust_curve_thickness(-1)
        )
        self.thickness_plus_btn.clicked.connect(
            lambda: adjust_curve_thickness(1)
        )

        # CV scaling
        self.scale_down_btn.clicked.connect(self._on_scale_cvs_down)
        self.scale_up_btn.clicked.connect(self._on_scale_cvs_up)

        # Curve colors
        self.color_button.clicked.connect(self._on_pick_color)
        self.pick_from_sel_button.clicked.connect(self._on_pick_from_selection)
        self.apply_color_button.clicked.connect(self._on_apply_color)
        self.reset_color_button.clicked.connect(self._on_reset_color)

        # Guide labels
        self.add_label_btn.clicked.connect(self._on_add_label)
        self.remove_label_btn.clicked.connect(self._on_remove_label)
        self.remove_all_labels_btn.clicked.connect(self._on_remove_all_labels)
        self.toggle_labels_btn.clicked.connect(self._on_toggle_labels)

        # Auto-save settings when UI values change
        self.filter_line.editingFinished.connect(self._save_settings)
        self.thickness_spin.valueChanged.connect(self._save_settings)
        self.offset_x_spin.valueChanged.connect(self._save_settings)
        self.offset_y_spin.valueChanged.connect(self._save_settings)
        self.offset_z_spin.valueChanged.connect(self._save_settings)

    # ------------------------------------------------------------------
    # Display Curves Slots
    # ------------------------------------------------------------------
    def _on_create_from_sel(self):
        line_width = float(self.thickness_spin.value())
        create_display_curve_from_selection(line_width=line_width)

    def _on_select_all(self):
        select_all_display_curves()

    def _on_mirror_curves(self):
        mirror_connection_display_curves()

    def _on_apply_thickness(self):
        line_width = float(self.thickness_spin.value())
        set_all_display_curves_thickness(line_width)

    def _on_toggle_display_type(self):
        toggle_display_type_all_curves()

    def _on_scale_cvs_up(self):
        try:
            scale_curve_cvs(self.SCALE_UP_FACTOR)
        except RuntimeError as e:
            cmds.warning(str(e))

    def _on_scale_cvs_down(self):
        try:
            scale_curve_cvs(self.SCALE_DOWN_FACTOR)
        except RuntimeError as e:
            cmds.warning(str(e))

    def _on_export_config(self):
        """Export all configuration to a single JSON file."""
        file_path = cmds.fileDialog2(
            caption="Export Guide Visualizer Configuration",
            fileMode=0,
            fileFilter="JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            export_full_configuration(file_path[0])
        except Exception as exc:
            cmds.warning("Failed to export configuration: {}".format(exc))

    def _on_import_config(self):
        """Import all configuration from a JSON file."""
        file_path = cmds.fileDialog2(
            caption="Import Guide Visualizer Configuration",
            fileMode=1,
            fileFilter="JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            import_full_configuration(file_path[0])
        except Exception as exc:
            cmds.warning("Failed to import configuration: {}".format(exc))

    # ------------------------------------------------------------------
    # Color Helpers
    # ------------------------------------------------------------------
    def _update_color_preview(self):
        """Update color button background to match current color."""
        rgb = self._current_color
        template = (
            "background-color: rgb({r}, {g}, {b});"
            "border: 1px solid #444;"
        )
        style = template.format(
            r=rgb.red(),
            g=rgb.green(),
            b=rgb.blue(),
        )
        self.color_button.setStyleSheet(style)

    def _add_to_history(self, qcolor):
        """Add color to history, keeping last 10.

        Args:
            qcolor (QtGui.QColor): Color to add.
        """
        rgb_tuple = (qcolor.red(), qcolor.green(), qcolor.blue())
        cleaned = []
        for col in self._color_history:
            if col != rgb_tuple:
                cleaned.append(col)
        cleaned.insert(0, rgb_tuple)
        self._color_history = cleaned[:10]
        self._refresh_history_buttons()
        # Save settings when color/history changes
        self._save_settings()

    def _refresh_history_buttons(self):
        """Refresh small buttons showing color history."""
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for rgb in self._color_history:
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(18, 18)
            style = "background-color: rgb({0}, {1}, {2});".format(
                rgb[0],
                rgb[1],
                rgb[2],
            )
            btn.setStyleSheet(style)
            btn.clicked.connect(
                self._make_history_clicked_callback(rgb)
            )
            self.history_layout.addWidget(btn)

        self.history_layout.addStretch()

    def _make_history_clicked_callback(self, rgb):
        """Create callback when a history color button is clicked.

        Args:
            rgb (tuple[int, int, int]): Stored RGB 0-255.

        Returns:
            callable: Slot to set current color.
        """
        def callback():
            self._current_color = QtGui.QColor(
                rgb[0],
                rgb[1],
                rgb[2],
            )
            self._update_color_preview()
            self._add_to_history(self._current_color)

        return callback

    # ------------------------------------------------------------------
    # Color Slots
    # ------------------------------------------------------------------
    def _on_pick_color(self):
        """Open QColorDialog and set chosen color."""
        color = QtWidgets.QColorDialog.getColor(
            self._current_color,
            self,
            "Select Curve Color",
        )
        if not color.isValid():
            return
        self._current_color = color
        self._update_color_preview()
        self._add_to_history(color)

    def _on_pick_from_selection(self):
        """Pick color from first selected shape or child curve."""
        sel = cmds.ls(selection=True, long=True) or []
        if not sel:
            cmds.warning("Select an object to read the color from.")
            return

        shapes = []
        for node in sel:
            if cmds.nodeType(node) in ("nurbsCurve", "bezierCurve"):
                shapes.append(node)
            else:
                children = cmds.listRelatives(
                    node,
                    shapes=True,
                    fullPath=True,
                ) or []
                for child in children:
                    if cmds.nodeType(child) in (
                        "nurbsCurve",
                        "bezierCurve",
                    ):
                        shapes.append(child)

        if not shapes:
            cmds.warning("No curve shapes found in selection.")
            return

        picked_rgb = None
        pattern = self.filter_line.text().strip()
        for shape in shapes:
            if pattern in short_name(shape):
                rgb = get_shape_color(shape)
                if rgb:
                    picked_rgb = rgb
                    break

        if picked_rgb is None:
            cmds.warning("Selected curves have no RGB override color.")
            return

        qcolor = QtGui.QColor(
            int(picked_rgb[0] * 255.0),
            int(picked_rgb[1] * 255.0),
            int(picked_rgb[2] * 255.0),
        )
        self._current_color = qcolor
        self._update_color_preview()
        self._add_to_history(qcolor)

    def _on_apply_color(self):
        """Apply current color to filtered curve shapes in selection."""
        sel = cmds.ls(selection=True, long=True, type="transform") or []
        if not sel:
            cmds.warning("Select at least one transform.")
            return

        name_filter = self.filter_line.text()
        if name_filter is None:
            name_filter = ""

        r = self._current_color.redF()
        g = self._current_color.greenF()
        b = self._current_color.blueF()
        rgb = (r, g, b)

        affected = []
        for tr in sel:
            shapes = get_curve_shapes_from_transform(tr, name_filter)
            for shape in shapes:
                set_shape_color(shape, rgb)
                affected.append(shape)

        if not affected:
            cmds.warning("No matching curve shapes found.")
            return

        print(
            "Guide Visualizer: Colored {0} shapes.".format(
                len(affected)
            )
        )

        self._add_to_history(self._current_color)

    def _on_reset_color(self):
        """Reset color on filtered curve shapes in selection."""
        sel = cmds.ls(selection=True, long=True, type="transform") or []
        if not sel:
            cmds.warning("Select at least one transform.")
            return

        name_filter = self.filter_line.text()
        if name_filter is None:
            name_filter = ""

        affected = []
        for tr in sel:
            shapes = get_curve_shapes_from_transform(tr, name_filter)
            for shape in shapes:
                reset_shape_color(shape)
                affected.append(shape)

        if not affected:
            cmds.warning("No curve shapes found to reset.")
            return

        print(
            "Guide Visualizer: Reset color on {0} shapes.".format(
                len(affected)
            )
        )

    # ------------------------------------------------------------------
    # Guide Labels Helpers
    # ------------------------------------------------------------------
    def _get_label_offset(self):
        """Return offset from UI spinboxes.

        Returns:
            tuple[float, float, float]: Offset vector.
        """
        return (
            self.offset_x_spin.value(),
            self.offset_y_spin.value(),
            self.offset_z_spin.value(),
        )

    def _iter_selected_guides(self):
        """Iterate over selected mGear guides.

        Yields:
            str: Guide node name.
        """
        selection = cmds.ls(selection=True) or []
        for node in selection:
            if is_mgear_guide(node):
                yield node

    # ------------------------------------------------------------------
    # Guide Labels Slots
    # ------------------------------------------------------------------
    def _on_add_label(self):
        """Add labels to selected guides."""
        offset = self._get_label_offset()
        count = 0
        for guide in self._iter_selected_guides():
            create_label(guide, offset)
            count += 1
        if count:
            print("Guide Visualizer: Added labels to {} guides.".format(count))
        else:
            cmds.warning("No mGear guides selected.")

    def _on_remove_label(self):
        """Remove labels from selected guides."""
        count = 0
        for guide in self._iter_selected_guides():
            remove_label_from_guide(guide)
            count += 1
        if count:
            print(
                "Guide Visualizer: Removed labels from {} guides.".format(
                    count
                )
            )

    def _on_remove_all_labels(self):
        """Remove all labels from scene."""
        labels = list_all_labels()
        if labels:
            cmds.delete(labels)
            print(
                "Guide Visualizer: Removed {} labels.".format(len(labels))
            )

    def _on_toggle_labels(self):
        """Toggle visibility of all labels."""
        toggle_labels_visibility()

    # ------------------------------------------------------------------
    # Settings Persistence
    # ------------------------------------------------------------------
    def _get_settings(self):
        """Return QSettings instance with proper organization/app names.

        Returns:
            QtCore.QSettings: Settings object for persistent storage.
        """
        return QtCore.QSettings("mGear", "GuideVisualizer")

    def _load_settings(self):
        """Load persistent settings from QSettings."""
        settings = self._get_settings()

        # Current color
        color_r = settings.value("color_r", self.DEFAULT_CURRENT_COLOR[0])
        color_g = settings.value("color_g", self.DEFAULT_CURRENT_COLOR[1])
        color_b = settings.value("color_b", self.DEFAULT_CURRENT_COLOR[2])
        # Handle type - QSettings may return strings
        try:
            color_r = int(color_r)
            color_g = int(color_g)
            color_b = int(color_b)
        except (ValueError, TypeError):
            color_r, color_g, color_b = self.DEFAULT_CURRENT_COLOR
        self._current_color = QtGui.QColor(color_r, color_g, color_b)

        # Color history
        history_str = settings.value("color_history", "")
        if history_str:
            try:
                self._color_history = json.loads(history_str)
            except (ValueError, TypeError):
                self._color_history = list(self.DEFAULT_COLOR_HISTORY)
        else:
            self._color_history = list(self.DEFAULT_COLOR_HISTORY)

        # Filter text
        filter_text = settings.value("filter_text", self.DEFAULT_FILTER_TEXT)
        if filter_text:
            self.filter_line.setText(str(filter_text))

        # Display curves thickness
        thickness = settings.value("thickness", self.DEFAULT_THICKNESS)
        try:
            thickness = int(thickness)
        except (ValueError, TypeError):
            thickness = self.DEFAULT_THICKNESS
        self.thickness_spin.setValue(thickness)

        # Label offsets
        offset_x = settings.value("offset_x", self.DEFAULT_OFFSET_X)
        offset_y = settings.value("offset_y", self.DEFAULT_OFFSET_Y)
        offset_z = settings.value("offset_z", self.DEFAULT_OFFSET_Z)
        try:
            offset_x = float(offset_x)
            offset_y = float(offset_y)
            offset_z = float(offset_z)
        except (ValueError, TypeError):
            offset_x = self.DEFAULT_OFFSET_X
            offset_y = self.DEFAULT_OFFSET_Y
            offset_z = self.DEFAULT_OFFSET_Z
        self.offset_x_spin.setValue(offset_x)
        self.offset_y_spin.setValue(offset_y)
        self.offset_z_spin.setValue(offset_z)

    def _save_settings(self):
        """Save persistent settings to QSettings."""
        settings = self._get_settings()

        # Current color
        settings.setValue("color_r", self._current_color.red())
        settings.setValue("color_g", self._current_color.green())
        settings.setValue("color_b", self._current_color.blue())

        # Color history
        settings.setValue("color_history", json.dumps(self._color_history))

        # Filter text
        settings.setValue("filter_text", self.filter_line.text())

        # Display curves thickness
        settings.setValue("thickness", self.thickness_spin.value())

        # Label offsets
        settings.setValue("offset_x", self.offset_x_spin.value())
        settings.setValue("offset_y", self.offset_y_spin.value())
        settings.setValue("offset_z", self.offset_z_spin.value())

        # Force write to disk
        settings.sync()

    def _on_reset_defaults(self):
        """Reset all settings to their default values."""
        # Reset color state
        self._current_color = QtGui.QColor(*self.DEFAULT_CURRENT_COLOR)
        self._color_history = list(self.DEFAULT_COLOR_HISTORY)

        # Reset UI widgets
        self.filter_line.setText(self.DEFAULT_FILTER_TEXT)
        self.thickness_spin.setValue(self.DEFAULT_THICKNESS)
        self.offset_x_spin.setValue(self.DEFAULT_OFFSET_X)
        self.offset_y_spin.setValue(self.DEFAULT_OFFSET_Y)
        self.offset_z_spin.setValue(self.DEFAULT_OFFSET_Z)

        # Update UI
        self._update_color_preview()
        self._refresh_history_buttons()

        # Save to clear persistent settings
        self._save_settings()

        print("Guide Visualizer: Reset to defaults.")

    def closeEvent(self, event):
        """Save settings when the window is closed."""
        self._save_settings()
        super(GuideVisualizerUI, self).closeEvent(event)


def show(dockable=True):
    """Create and show the Guide Visualizer tool UI.

    Args:
        dockable (bool): If True, show as dockable window. Default True.

    Returns:
        GuideVisualizerUI: The dialog instance.
    """
    if not QtWidgets:
        cmds.warning("Qt bindings not available.")
        return None

    # Clean up existing workspace control if dockable
    control_name = GuideVisualizerUI.toolName + "WorkspaceControl"
    if cmds.workspaceControl(control_name, q=True, exists=True):
        cmds.workspaceControl(control_name, e=True, close=True)
        cmds.deleteUI(control_name, control=True)

    # Close any existing instances
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == GuideVisualizerUI.toolName:
            widget.close()

    parent = pyqt.maya_main_window()
    dlg = GuideVisualizerUI(parent=parent)

    if dockable:
        dlg.show(dockable=True)
    else:
        dlg.show()
        dlg.raise_()

    return dlg


if __name__ == "__main__":
    show()
