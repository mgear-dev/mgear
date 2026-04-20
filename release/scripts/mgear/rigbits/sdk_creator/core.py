"""SDK Creator - Core logic.

Reads keyframed poses from the timeline, creates SDK transform nodes,
animCurve/blendWeighted graphs, and UIHost driver attributes.
Supports export/import of ``.sdkc`` configurations and mirroring.
"""

import json

import mgear
from maya import cmds

from mgear.core import attribute
from mgear.core import utils as core_utils

# Pre/post infinity mode constant
_INFINITY_LINEAR = 1

# Config format
CONFIG_VERSION = "1.0"
CONFIG_EXT = ".sdkc"

# Local transform channels
TRANSFORM_CHANNELS = (
    "tx", "ty", "tz",
    "rx", "ry", "rz",
    "sx", "sy", "sz",
)

# Rest values per channel
REST_VALUES = {
    "tx": 0.0, "ty": 0.0, "tz": 0.0,
    "rx": 0.0, "ry": 0.0, "rz": 0.0,
    "sx": 1.0, "sy": 1.0, "sz": 1.0,
}

SCALE_CHANNELS = ("sx", "sy", "sz")

# AnimCurve type per channel
CHANNEL_CURVE_TYPE = {
    "tx": "animCurveUL", "ty": "animCurveUL", "tz": "animCurveUL",
    "rx": "animCurveUA", "ry": "animCurveUA", "rz": "animCurveUA",
    "sx": "animCurveUU", "sy": "animCurveUU", "sz": "animCurveUU",
}

# Default channels to negate when mirroring (empty = none checked)
DEFAULT_MIRROR_CHANNELS = ()

# Node types to clean up during delete
_SDK_NODE_TYPES = (
    "animCurveUA", "animCurveUL", "animCurveUU",
    "blendWeighted", "addDoubleLinear",
)

# Tolerance for comparing to rest value
_EPSILON = 1e-6


# =============================================================
# POSE READING
# =============================================================


def get_keyed_frames(controls):
    """Get sorted list of frames where controls have keyframes.

    Intersects keyframe times across all controls. Warns if
    any control is missing keys on common frames.

    Args:
        controls (list): List of control names.

    Returns:
        list: Sorted list of frame numbers (floats).
    """
    if not controls:
        return []

    frame_sets = []
    for ctl in controls:
        times = cmds.keyframe(ctl, query=True, timeChange=True)
        if times:
            frame_sets.append(set(times))
        else:
            cmds.warning(
                "SDK Creator: 在 '{}' 上未找到关键帧".format(ctl)
            )
            frame_sets.append(set())

    if not frame_sets:
        return []

    common = frame_sets[0]
    for fs in frame_sets[1:]:
        common = common.intersection(fs)

    all_frames = set()
    for fs in frame_sets:
        all_frames = all_frames.union(fs)

    missing = all_frames - common
    if missing:
        cmds.warning(
            "SDK Creator: 部分控制器在"
            "不同帧上有关键帧。仅使用共同帧。"
            "缺少帧: {}".format(sorted(missing))
        )

    return sorted(common)


def get_keyed_channels(control, frames):
    """Find which channels have non-default values on any frame.

    Args:
        control (str): Control name.
        frames (list): List of frame numbers.

    Returns:
        list: Channel names with meaningful keys.
    """
    active = []
    for ch in TRANSFORM_CHANNELS:
        attr_path = "{}.{}".format(control, ch)
        rest = REST_VALUES[ch]
        for frame in frames:
            val = cmds.getAttr(attr_path, time=frame)
            if abs(val - rest) > _EPSILON:
                active.append(ch)
                break
    return active


def collect_pose_data(controls, frames, pose_names):
    """Collect delta values for all controls across all poses.

    Reads values at each frame and computes deltas from rest.
    Channel detection is inlined to avoid double-reading values.

    Args:
        controls (list): Control names.
        frames (list): Frame numbers (one per pose).
        pose_names (list): Pose name for each frame.

    Returns:
        dict: ``{pose_name: {control: {channel: delta}}}``.
    """
    poses = {}
    for frame, pose_name in zip(frames, pose_names):
        pose_data = {}
        for ctl in controls:
            ch_data = {}
            for ch in TRANSFORM_CHANNELS:
                val = cmds.getAttr(
                    "{}.{}".format(ctl, ch), time=frame
                )
                delta = val - REST_VALUES[ch]
                if abs(delta) > _EPSILON:
                    ch_data[ch] = delta
            if ch_data:
                pose_data[ctl] = ch_data
        poses[pose_name] = {"frame": frame, "channels": pose_data}
    return poses


def build_config(ui_host, controls, poses, min_val, max_val):
    """Build a complete config dictionary.

    Args:
        ui_host (str): UIHost control name.
        controls (list): Control names.
        poses (dict): Pose data from ``collect_pose_data``.
        min_val (float): Min range for driver attributes.
        max_val (float): Max range for driver attributes.

    Returns:
        dict: Full configuration dictionary.
    """
    return {
        "version": CONFIG_VERSION,
        "ui_host": ui_host,
        "range": [min_val, max_val],
        "controls": list(controls),
        "poses": poses,
    }


# =============================================================
# SDK SETUP CREATION
# =============================================================


def insert_sdk_transform(control, suffix="_sdk"):
    """Insert a SDK transform node above a control.

    Creates a parent transform with the control's world matrix,
    then parents the control under it. Similar to ``addNPO``
    but with ``_sdk`` suffix.

    Args:
        control (str): Control name.
        suffix (str): Suffix for the SDK node name.

    Returns:
        str: The created SDK transform node name, or None if
            one already exists.
    """
    parent = cmds.listRelatives(control, parent=True, fullPath=True)
    if parent:
        short_parent = parent[0].split("|")[-1]
        if short_parent.endswith(suffix):
            cmds.warning(
                "SDK Creator: '{}' already has a '{}' parent, "
                "skipping".format(control, suffix)
            )
            return None

    matrix = cmds.xform(
        control, query=True, matrix=True, worldSpace=True
    )

    short_name = control.split("|")[-1].split(":")[-1]
    sdk_name = short_name + suffix

    if parent:
        sdk_node = cmds.createNode(
            "transform", name=sdk_name, parent=parent[0],
            skipSelect=True,
        )
    else:
        sdk_node = cmds.createNode(
            "transform", name=sdk_name, skipSelect=True
        )

    cmds.xform(sdk_node, matrix=matrix, worldSpace=True)
    cmds.parent(control, sdk_node)

    return sdk_node


def create_pose_attributes(ui_host, pose_names, min_val, max_val):
    """Create driver attributes on the UIHost control.

    Adds a separator and one float attribute per pose.

    Args:
        ui_host (str): UIHost control name.
        pose_names (list): Pose name strings.
        min_val (float): Minimum attribute value.
        max_val (float): Maximum attribute value.

    Returns:
        list: Full attribute paths created.
    """
    # Separator
    sep_name = "sdk_poses"
    if not cmds.attributeQuery(sep_name, node=ui_host, exists=True):
        cmds.addAttr(
            ui_host,
            longName=sep_name,
            attributeType="enum",
            enumName="________:",
            keyable=False,
        )
        cmds.setAttr(
            "{}.{}".format(ui_host, sep_name), channelBox=True
        )

    attrs = []
    for pose_name in pose_names:
        if cmds.attributeQuery(pose_name, node=ui_host, exists=True):
            mgear.log(
                "  Reusing existing attribute: {}.{}".format(
                    ui_host, pose_name
                ),
                mgear.sev_info,
            )
            attrs.append("{}.{}".format(ui_host, pose_name))
            continue

        attribute.addAttribute(
            ui_host,
            pose_name,
            "double",
            value=0.0,
            minValue=min_val,
            maxValue=max_val,
            keyable=True,
        )
        attrs.append("{}.{}".format(ui_host, pose_name))

    return attrs


def create_sdk_curve(
    driver_attr, sdk_node, channel, pose_name, delta_value
):
    """Create a linear SDK animCurve with pre/post infinity.

    Args:
        driver_attr (str): Driver attribute (e.g.
            ``"ctl.poseName"``).
        sdk_node (str): SDK transform node name.
        channel (str): Channel name (e.g. ``"rx"``).
        pose_name (str): Pose name for node naming.
        delta_value (float): Delta value at driver=1.

    Returns:
        str: The created animCurve node name.
    """
    curve_type = CHANNEL_CURVE_TYPE[channel]
    short_sdk = sdk_node.split("|")[-1].split(":")[-1]
    curve_name = "{}_{}_{}".format(short_sdk, pose_name, channel)

    curve_node = cmds.createNode(
        curve_type, name=curve_name, skipSelect=True
    )

    cmds.setKeyframe(
        curve_node,
        float=0.0,
        value=0.0,
        inTangentType="clamped",
        outTangentType="clamped",
    )
    cmds.setKeyframe(
        curve_node,
        float=1.0,
        value=delta_value,
        inTangentType="clamped",
        outTangentType="clamped",
    )

    # Linear infinity for overshooting beyond 0-1
    cmds.setAttr(curve_node + ".preInfinity", _INFINITY_LINEAR)
    cmds.setAttr(curve_node + ".postInfinity", _INFINITY_LINEAR)

    cmds.connectAttr(driver_attr, curve_node + ".input")

    return curve_node


def connect_curves_to_channel(curves, sdk_node, channel):
    """Connect SDK curves to a channel on the SDK transform.

    Single curve connects directly. Multiple curves go through
    a blendWeighted node. Scale channels add an addDoubleLinear
    to offset from 0 back to rest=1.0 when using blendWeighted.

    Args:
        curves (list): List of animCurve node names.
        sdk_node (str): SDK transform node name.
        channel (str): Channel name.
    """
    dst_attr = "{}.{}".format(sdk_node, channel)
    is_scale = channel in SCALE_CHANNELS

    if len(curves) == 1:
        # Single curve — connect directly
        # For scale: curve has rest=1.0 at driver=0 (absolute)
        cmds.connectAttr(curves[0] + ".output", dst_attr)
    else:
        # Multiple curves — use blendWeighted
        short_sdk = sdk_node.split("|")[-1].split(":")[-1]
        bw_name = "{}_{}_bwn".format(short_sdk, channel)
        bw_node = cmds.createNode(
            "blendWeighted", name=bw_name, skipSelect=True
        )

        for i, curve in enumerate(curves):
            cmds.connectAttr(
                curve + ".output",
                "{}.input[{}]".format(bw_node, i),
            )

        if is_scale:
            # Add rest offset: bw.output + 1.0 → sdk_node.channel
            adl_name = "{}_{}_adl".format(short_sdk, channel)
            # Maya 2026+ renamed addDoubleLinear to addDL
            version = int(cmds.about(version=True))
            node_type = "addDL" if version >= 2026 else "addDoubleLinear"
            adl_node = cmds.createNode(
                node_type, name=adl_name, skipSelect=True
            )
            cmds.connectAttr(bw_node + ".output", adl_node + ".input1")
            cmds.setAttr(adl_node + ".input2", 1.0)
            cmds.connectAttr(adl_node + ".output", dst_attr)
        else:
            cmds.connectAttr(bw_node + ".output", dst_attr)


def lock_sdk_transform(sdk_node):
    """Lock and hide all transform channels on the SDK node.

    Args:
        sdk_node (str): SDK transform node name.
    """
    attribute.setKeyableAttributes(sdk_node, params=[])


@core_utils.one_undo
def delete_sdk_setup(controls, ui_host=None, suffix="_sdk"):
    """Delete SDK setup from controls.

    Removes ``_sdk`` transform parents, their upstream nodes
    (animCurves, blendWeighted, addDoubleLinear), and optionally
    the pose attributes from the UIHost.

    Args:
        controls (list): Control names.
        ui_host (str, optional): UIHost node. If provided,
            removes pose attributes created by SDK Creator.
        suffix (str): SDK node suffix to look for.

    Returns:
        int: Number of controls cleaned up.
    """
    mgear.log("SDK Creator: Deleting SDK setup...", mgear.sev_info)
    count = 0
    for ctl in controls:
        if not cmds.objExists(ctl):
            mgear.log(
                "  Control not found: {}".format(ctl),
                mgear.sev_warning,
            )
            continue

        parent = cmds.listRelatives(
            ctl, parent=True, fullPath=True
        )
        if not parent:
            continue

        short_parent = parent[0].split("|")[-1]
        if not short_parent.endswith(suffix):
            continue

        sdk_node = parent[0]

        to_delete = set()
        for ch in TRANSFORM_CHANNELS:
            attr_path = "{}.{}".format(sdk_node, ch)
            cmds.setAttr(attr_path, lock=False)
            conns = cmds.listConnections(
                attr_path, source=True, destination=False,
                skipConversionNodes=False,
            )
            if not conns:
                continue
            for node in conns:
                to_delete.add(node)
                upstream = cmds.listConnections(
                    node, source=True, destination=False,
                    skipConversionNodes=False,
                ) or []
                for up in upstream:
                    if cmds.nodeType(up) in _SDK_NODE_TYPES:
                        to_delete.add(up)

        mgear.log(
            "  Removing SDK node: {} from {}".format(sdk_node, ctl),
            mgear.sev_info,
        )

        grandparent = cmds.listRelatives(
            sdk_node, parent=True, fullPath=True
        )
        if grandparent:
            cmds.parent(ctl, grandparent[0])
        else:
            cmds.parent(ctl, world=True)

        to_delete.add(sdk_node)
        for node in to_delete:
            if cmds.objExists(node):
                cmds.delete(node)

        count += 1

    # Remove UIHost pose attributes that have no outputs
    if ui_host and cmds.objExists(ui_host):
        user_attrs = cmds.listAttr(ui_host, userDefined=True) or []
        for attr_name in user_attrs:
            if attr_name == "sdk_poses":
                continue
            full_attr = "{}.{}".format(ui_host, attr_name)
            out_conns = cmds.listConnections(
                full_attr, source=False, destination=True,
            )
            if not out_conns:
                try:
                    cmds.deleteAttr(full_attr)
                    mgear.log(
                        "  Removed UIHost attr: {}".format(
                            attr_name
                        ),
                        mgear.sev_info,
                    )
                except RuntimeError:
                    pass

        # Remove separator only if no SDK-connected attrs remain
        if cmds.attributeQuery(
            "sdk_poses", node=ui_host, exists=True
        ):
            remaining = cmds.listAttr(
                ui_host, userDefined=True
            ) or []
            has_sdk_attrs = False
            for a in remaining:
                if a == "sdk_poses":
                    continue
                full = "{}.{}".format(ui_host, a)
                # An SDK pose attr drives animCurve nodes
                out = cmds.listConnections(
                    full, source=False, destination=True,
                    type="animCurveUU",
                ) or cmds.listConnections(
                    full, source=False, destination=True,
                    type="animCurveUA",
                ) or cmds.listConnections(
                    full, source=False, destination=True,
                    type="animCurveUL",
                )
                if out:
                    has_sdk_attrs = True
                    break
            if not has_sdk_attrs:
                cmds.deleteAttr("{}.sdk_poses".format(ui_host))

    mgear.log(
        "SDK Creator: Deleted setup from {} control(s)".format(
            count
        ),
        mgear.sev_info,
    )
    return count


@core_utils.one_undo
def create_sdk_setup(config):
    """Create the full SDK setup from a configuration.

    Main orchestrator: validates inputs, inserts SDK transforms,
    creates UIHost attributes, builds animCurve/blendWeighted
    graphs, and locks SDK transform channels.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        list: Created SDK transform node names.
    """
    ui_host = config["ui_host"]
    controls = config["controls"]
    poses = config["poses"]
    min_val, max_val = config["range"]

    # Validate
    if not cmds.objExists(ui_host):
        cmds.warning(
            "SDK Creator: UIHost '{}' not found".format(ui_host)
        )
        return []

    for ctl in controls:
        if not cmds.objExists(ctl):
            cmds.warning(
                "SDK Creator: Control '{}' not found".format(ctl)
            )
            return []

    # Step 1: Insert SDK transforms
    mgear.log("SDK Creator: Inserting SDK transforms...", mgear.sev_info)
    sdk_nodes = {}
    for ctl in controls:
        sdk_node = insert_sdk_transform(ctl)
        if sdk_node:
            sdk_nodes[ctl] = sdk_node
            mgear.log(
                "  Created: {} -> {}".format(ctl, sdk_node),
                mgear.sev_info,
            )

    if not sdk_nodes:
        cmds.warning("SDK Creator: No SDK transforms created")
        return []

    # Step 2: Create UIHost attributes
    pose_names = list(poses.keys())
    mgear.log(
        "SDK Creator: Creating {} pose attributes on {}".format(
            len(pose_names), ui_host
        ),
        mgear.sev_info,
    )
    create_pose_attributes(ui_host, pose_names, min_val, max_val)

    # Step 3: For each control, collect per-channel curves and connect
    total_curves = 0
    for ctl, sdk_node in sdk_nodes.items():
        channel_curves = {}

        for pose_name, pose_data in poses.items():
            ctl_channels = pose_data.get("channels", {}).get(ctl, {})
            driver_attr = "{}.{}".format(ui_host, pose_name)

            for ch, delta in ctl_channels.items():
                curve = create_sdk_curve(
                    driver_attr, sdk_node, ch, pose_name, delta
                )
                if ch not in channel_curves:
                    channel_curves[ch] = []
                channel_curves[ch].append(curve)
                total_curves += 1

        # For single-curve scale channels, adjust to absolute values
        for ch, curves in channel_curves.items():
            if len(curves) == 1 and ch in SCALE_CHANNELS:
                cmds.keyframe(
                    curves[0],
                    floatChange=0.0,
                    valueChange=1.0,
                    float=(0.0,),
                )
                delta = cmds.keyframe(
                    curves[0], float=(1.0,),
                    query=True, valueChange=True,
                )[0]
                cmds.keyframe(
                    curves[0],
                    float=(1.0,),
                    valueChange=delta + 1.0,
                )

        # Connect all curves to their channels
        for ch, curves in channel_curves.items():
            connect_curves_to_channel(curves, sdk_node, ch)

        mgear.log(
            "  {}: {} channels connected".format(
                sdk_node, len(channel_curves)
            ),
            mgear.sev_info,
        )

        # Step 4: Lock and hide
        lock_sdk_transform(sdk_node)

    mgear.log(
        "SDK Creator: Done. {} controls, {} poses, "
        "{} SDK curves created".format(
            len(sdk_nodes), len(poses), total_curves
        ),
        mgear.sev_info,
    )

    return list(sdk_nodes.values())


# =============================================================
# CONFIG I/O
# =============================================================


def export_config(file_path, config):
    """Export configuration to a .sdkc JSON file.

    Args:
        file_path (str): Destination file path.
        config (dict): Configuration dictionary.

    Returns:
        bool: True if successful.
    """
    if not file_path.endswith(CONFIG_EXT):
        file_path += CONFIG_EXT

    try:
        with open(file_path, "w") as f:
            json.dump(config, f, indent=2)
        mgear.log(
            "SDK Creator: Exported config to {}".format(file_path),
            mgear.sev_info,
        )
        return True
    except IOError as e:
        cmds.warning(
            "SDK Creator: Failed to export: {}".format(e)
        )
        return False


def import_config(file_path):
    """Import configuration from a .sdkc JSON file.

    Args:
        file_path (str): Source file path.

    Returns:
        dict: Configuration dictionary, or None on failure.
    """
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
        mgear.log(
            "SDK Creator: Imported config from {}".format(file_path),
            mgear.sev_info,
        )
        return config
    except (IOError, ValueError) as e:
        cmds.warning(
            "SDK Creator: Failed to import: {}".format(e)
        )
        return None


def apply_from_file(file_path):
    """Load a config file and apply the SDK setup.

    Convenience function for Shifter custom steps.

    Args:
        file_path (str): Path to ``.sdkc`` file.

    Returns:
        list: Created SDK transform node names, or empty list.
    """
    config = import_config(file_path)
    if config:
        return create_sdk_setup(config)
    return []


# =============================================================
# MIRROR
# =============================================================


def mirror_config(
    config, search="_L", replace="_R", mirror_channels=None
):
    """Create a mirrored copy of a configuration.

    Swaps ``search``/``replace`` in control and UIHost names,
    and negates the specified channels.

    Args:
        config (dict): Source configuration.
        search (str): String to find (e.g. ``"_L"``).
        replace (str): String to replace with (e.g. ``"_R"``).
        mirror_channels (list, optional): Channels to negate.
            Defaults to ``("tx", "ry", "rz")``.

    Returns:
        dict: Mirrored configuration dictionary.
    """
    if mirror_channels is None:
        mirror_channels = list(DEFAULT_MIRROR_CHANNELS)

    def _swap(name):
        if search in name:
            return name.replace(search, replace)
        elif replace in name:
            return name.replace(replace, search)
        return name

    mirrored = {
        "version": config["version"],
        "ui_host": _swap(config["ui_host"]),
        "range": list(config["range"]),
        "controls": [_swap(c) for c in config["controls"]],
        "poses": {},
    }

    for pose_name, pose_data in config["poses"].items():
        new_channels = {}
        for ctl, ch_data in pose_data.get("channels", {}).items():
            new_ch = {}
            for ch, delta in ch_data.items():
                if ch in mirror_channels:
                    new_ch[ch] = -delta
                else:
                    new_ch[ch] = delta
            new_channels[_swap(ctl)] = new_ch

        mirrored["poses"][pose_name] = {
            "frame": pose_data.get("frame", 0),
            "channels": new_channels,
        }

    return mirrored


def mirror_sdk_setup(
    config, search="_L", replace="_R", mirror_channels=None
):
    """Mirror a config and apply the SDK setup.

    Args:
        config (dict): Source configuration.
        search (str): String to find.
        replace (str): String to replace with.
        mirror_channels (list, optional): Channels to negate.

    Returns:
        list: Created SDK transform node names.
    """
    mirrored = mirror_config(
        config, search, replace, mirror_channels
    )
    return create_sdk_setup(mirrored)
