# Stdlib imports
import bisect
import re
import traceback
from contextlib import contextmanager
from functools import partial

PY2 = False

# Maya imports
from maya import cmds
import maya.api.OpenMaya as om2
import maya.mel as mel
import mgear.pymaya as pm
from mgear.pymaya import versions

# mGear imports
import mgear
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets
from mgear.core import pyqt
from mgear.core import dag
from mgear.core import transform
from mgear.core import utils
from mgear.core import attribute
from mgear.core import vector
from mgear.core.attribute import reset_selected_channels_value
# keyable_nodes moved to core.attribute, kept here for anim tools
from mgear.core.attribute import keyable_nodes
from mgear.core.pickWalk import get_all_tag_children

# =============================================================================
# constants
# =============================================================================
EXPR_LEFT_SIDE = re.compile("L(\d+)")
EXPR_RIGHT_SIDE = re.compile("R(\d+)")

CTRL_GRP_SUFFIX = "_controllers_grp"
PLOT_GRP_SUFFIX = "_PLOT_grp"

# spine FK/IK matching, naming ------------------------------------------------
TAN_TOKEN = "_tan_ctl"
TAN0_TOKEN = "_tan0_ctl"
TAN1_TOKEN = "_tan1_ctl"
START_IK_TOKEN = "_ik0_ctl"
END_IK_TOKEN = "_ik1_ctl"
POS_IK_TOKEN = "_spinePosition_ctl"

# No mirror attributes ------------------------------------------------
NO_MIRROR_ATTRIBUTES = ["isRig", "uiHost", "_ctl"]

##################################################
# util


def isSideElement(name):
    """Returns is name(str) side element?

    Arguments:
        name (str): Description

    Returns:
        bool

    """
    # try first wiht side labels if is a node. This will fail with attrs
    try:
        if isinstance(name, str):
            node = pm.PyNode(name)
        if node.hasAttr("side_label"):
            side = node.side_label.get()
            if side in "LR":
                return True
    except (pm.MayaNodeError, RuntimeError):
        pass

    # old logic for back compatibility
    if "_L_" in name or "_R_" in name:
        return True
    nameParts = stripNamespace(name).split("|")[-1]

    for part in nameParts.split("_"):
        if EXPR_LEFT_SIDE.match(part) or EXPR_RIGHT_SIDE.match(part):
            return True
    else:
        return False


def isSideNode(node):
    """Returns is name(str) side element?

    Arguments:
        name (node): PyNode

    Returns:
        bool
    """

    if node.hasAttr("side_label"):
        if node.side_label.get() in "LR":
            return True
        else:
            return False

    else:
        return isSideElement(node.name())


def swapSideLabel(name):
    """Returns fliped name

    Returns fliped name that replaced side label left to right or
    right to left

    Arguments:
        name(str): Name to swap the side

    Returns:
        str
    """

    for part in name.split("_"):
        if EXPR_LEFT_SIDE.match(part):
            return EXPR_LEFT_SIDE.sub(r"R\1", name)
        if EXPR_RIGHT_SIDE.match(part):
            return EXPR_RIGHT_SIDE.sub(r"L\1", name)

    else:
        if "_L_" in name:
            return name.replace("_L_", "_R_")
        elif "_R_" in name:
            return name.replace("_R_", "_L_")
        else:
            return name


def swapSideLabelNode(node):
    """Returns fliped name of a node

    Returns fliped name that replaced side label left to right or
    right to left

    Arguments:
        name(node): pyNode

    Returns:
        str
    """
    if isinstance(node, str):
        node = pm.PyNode(node)

    # first check default swapSideLabel. For defaul Shifter naming system
    name = node.stripNamespace()
    sw_name = swapSideLabel(name)
    if name != sw_name:
        return sw_name

    # try to find the mirror using custom side labels
    if node.hasAttr("side_label"):
        side = node.side_label.get()
        if side in "LR":
            # custom side label
            c_side = node.attr("{}_custom_side_label".format(side)).get()
            # mirror side label
            if side == "L":
                cm_side = node.attr("R_custom_side_label").get()
            elif side == "R":
                cm_side = node.attr("L_custom_side_label").get()
            return node.stripNamespace().replace(c_side, cm_side)
        else:
            return node.stripNamespace()

    else:
        return swapSideLabel(node.stripNamespace())


def getClosestNode(node, nodesToQuery):
    """return the closest node, based on distance, from the list provided

    Args:
        node (string): name of node
        nodesToQuery (list): of nodes to query

    Returns:
        string: name of the closest node
    """
    distance = None
    closestNode = None
    node = pm.PyNode(node)
    for index, nodeTQ in enumerate(nodesToQuery):
        nodeTQ = pm.PyNode(nodeTQ)
        tmpDist = vector.getDistance2(node, nodeTQ)
        if index == 0:
            distance = tmpDist
            closestNode = nodeTQ
        if distance > tmpDist:
            distance = tmpDist
            closestNode = nodeTQ
    return closestNode.name()


def recordNodesMatrices(nodes, desiredTime):
    """get the matrices of the nodes provided and return a dict of
    node:matrix

    Args:
        nodes (list): of nodes

    Returns:
        dict: node:node matrix
    """
    nodeToMat_dict = {}
    for fk in nodes:
        fk = pm.PyNode(fk)
        nodeToMat_dict[fk.name()] = fk.getAttr("worldMatrix", time=desiredTime)

    return nodeToMat_dict


def get_playback_range(start=None, end=None):
    """Return a frame range, defaulting to the playback range.

    Args:
        start (float, optional): First frame. Default: playback start.
        end (float, optional): Last frame. Default: playback end.

    Returns:
        tuple: ``(start, end)``.
    """
    if start is None:
        start = cmds.playbackOptions(query=True, minTime=True)
    if end is None:
        end = cmds.playbackOptions(query=True, maxTime=True)
    return start, end


def record_world_matrices(nodes, start=None, end=None, status="Recording", frames=None):
    """Read the world matrix of nodes on every frame of a range.

    The current time is restored afterwards. Esc stops the recording; the
    frames read so far are returned.

    Args:
        nodes (list): Transform names.
        start (float, optional): First frame. Default: playback start.
        end (float, optional): Last frame. Default: playback end.
        status (str, optional): Progress bar text.
        frames (list, optional): Read only these frames, in order, instead
            of the ``start`` to ``end`` range.

    Returns:
        dict: ``{frame: [world matrix as 16 floats, one per node]}``, frames
        as int (or as given in ``frames``).
    """
    if frames is None:
        start, end = (int(round(f)) for f in get_playback_range(start, end))
        frames = range(start, end + 1)
    frames = list(frames)
    paths = [utils.get_dag_path(node) for node in nodes]
    matrices = {}
    with utils.current_time_kept(), utils.viewport_suspended():
        with utils.main_progress_bar(status, len(frames), True) as step:
            for frame in frames:
                if step("{} frame {:g}".format(status, frame)):
                    break
                cmds.currentTime(frame, edit=True)
                matrices[frame] = [list(path.inclusiveMatrix()) for path in paths]
    return matrices


def key_world_matrices(nodes, frames, status="Keying"):
    """Set and key world matrices on nodes, frame by frame.

    Parents are set before their children on each frame, so a child lands
    on its world matrix after its parent moved. Only the settable
    translate, rotate and scale channels are keyed. The current time is
    restored afterwards; Esc stops.

    Args:
        nodes (list): Transform names, matching the matrices of each frame.
        frames (dict): ``{frame: [world matrix per node]}``, e.g. from
            :func:`record_world_matrices`.
        status (str, optional): Progress bar text.

    Returns:
        list: The keyed frames.
    """
    nodes = [cmds.ls(node, long=True)[0] for node in nodes]
    # parents first, by DAG depth
    order = sorted(range(len(nodes)), key=lambda index: nodes[index].count("|"))
    plugs = [
        "{}.{}".format(node, channel)
        for node in nodes
        for channel in attribute.get_unlocked_channels(node, settable=True)
    ]
    keyed = []
    with utils.current_time_kept(), utils.viewport_suspended():
        with utils.main_progress_bar(status, len(frames), True) as step:
            for frame in sorted(frames):
                if step("{} frame {:g}".format(status, frame)):
                    break
                cmds.currentTime(frame, edit=True)
                matrices = frames[frame]
                for index in order:
                    cmds.xform(nodes[index], worldSpace=True, matrix=matrices[index])
                if plugs:
                    cmds.setKeyframe(plugs)
                keyed.append(frame)
    return keyed


def get_keyframe_times(nodes):
    """Return the sorted, unique keyframe times found on a list of nodes.

    Missing nodes are ignored. All nodes are queried in a single
    ``cmds.keyframe`` call.

    Args:
        nodes (list): Node names to query.

    Returns:
        list: Sorted unique keyframe times (float). Empty when no keyframe
        is found.
    """
    nodes = cmds.ls(nodes) if nodes else []
    if not nodes:
        return []
    times = cmds.keyframe(nodes, query=True, timeChange=True) or []
    return sorted(set(times))


def is_anim_source(node):
    """Return True if the node is an anim curve or an anim layer blend.

    Args:
        node (str): Node name.

    Returns:
        bool: True for animCurve and animBlendNode types.
    """
    types = cmds.nodeType(node, inherited=True) or []
    return "animCurve" in types or "animBlendNodeBase" in types


# What drives a plug, see plug_state
PLUG_FREE = "free"
PLUG_KEYED = "keyed"
PLUG_LAYERED = "layered"
PLUG_DRIVEN = "driven"
# Animation curves driven by time: keyframes. Curves driven by another
# attribute are driven keys
_KEY_CURVE_TYPES = (
    om2.MFn.kAnimCurveTimeToAngular,
    om2.MFn.kAnimCurveTimeToDistance,
    om2.MFn.kAnimCurveTimeToUnitless,
    om2.MFn.kAnimCurveTimeToTime,
)


def plug_state(plug):
    """Tell what drives a plug, looking through unit conversions.

    The one rule the pose tools share: mirror and flip, pose blends and
    ``set_or_key`` set free plugs, key keyed and layered plugs, and leave
    driven plugs alone.

    Args:
        plug (str or om2.MPlug): The plug, e.g. ``"ctl.translateX"``.

    Returns:
        str: ``free`` (no input), ``keyed`` (keyframes), ``layered`` (an
            animation layer) or ``driven`` (a constraint, an expression, a
            driven key, a character set...).
    """
    if not isinstance(plug, om2.MPlug):
        selection = om2.MSelectionList()
        selection.add(plug)
        plug = selection.getPlug(0)
    if not plug.isDestination:
        return PLUG_FREE
    source = plug.source()
    while source.node().apiType() == om2.MFn.kUnitConversion:
        source = om2.MFnDependencyNode(source.node()).findPlug("input", False)
        if not source.isDestination:
            return PLUG_DRIVEN
        source = source.source()
    if source.node().apiType() in _KEY_CURVE_TYPES:
        return PLUG_KEYED
    if om2.MFnDependencyNode(source.node()).typeName.startswith("animBlendNode"):
        return PLUG_LAYERED
    return PLUG_DRIVEN


def is_animated(plug):
    """Return True if a plug is keyed or on an animation layer.

    Args:
        plug (str): Plug name, e.g. ``"ctl.translateX"``.

    Returns:
        bool: True if animated; a driven key isn't animation.
    """
    return plug_state(plug) in (PLUG_KEYED, PLUG_LAYERED)


def refresh_keyed(plugs):
    """Update the values of plugs keyed with a value on the current frame.

    Such a key doesn't change the evaluated value until the time changes,
    so the pose wouldn't update. Dirtying the plug is enough for a plain
    anim curve; on animation layers the layer blend nodes are dirtied too.

    Args:
        plugs (list): Plug names.
    """
    if not plugs:
        return
    dirty = list(plugs)
    if cmds.ls(type="animLayer"):
        seen = set()
        pending = list(plugs)
        while pending:
            sources = cmds.listConnections(
                pending.pop(),
                source=True,
                destination=False,
                skipConversionNodes=True,
                type="animBlendNodeBase",
            )
            for node in sources or ():
                if node not in seen:
                    seen.add(node)
                    pending.append(node)
        dirty.extend(seen)
    cmds.dgdirty(dirty)


def layer_base_plug(plug):
    """Return the plug feeding the base animation of a layered attribute.

    When animation layers drive the plug, the base input of the bottom
    layer blend node is returned (``inputA``, or ``inputAX`` for rotation
    blends). Otherwise the plug itself is returned.

    Args:
        plug (str): Attribute plug, e.g. ``"ctl.translateX"``.

    Returns:
        str: The plug to connect base animation to.
    """
    current = plug
    while True:
        inputs = (
            cmds.listConnections(current, source=True, destination=False, plugs=True)
            or []
        )
        if not inputs:
            return current
        node, attr = inputs[0].split(".", 1)
        types = cmds.nodeType(node, inherited=True) or []
        if "animBlendNodeBase" not in types or not attr.startswith("output"):
            return current
        current = "{}.inputA{}".format(node, attr[len("output") :])


def move_animation_curves(source, target, attrs=None):
    """Move the animation driving attributes of one node to another node.

    Anim curves and anim layer blend nodes connected to the source
    attributes, or to their children (e.g. ``translateX`` for
    ``translate``), are disconnected and connected to the same attribute
    on the target. Other connections, like constraints, are left as is.
    When the target attribute is driven by animation layers, the
    animation goes to the base input of the layers.

    Args:
        source (str): Node with the animation.
        target (str): Node that receives the animation.
        attrs (list, optional): Attribute names to move. Defaults to
            translate, rotate and scale.

    Returns:
        list: The target plugs that received animation.
    """
    attrs = attrs or ("translate", "rotate", "scale")
    moved = []
    for attr in attrs:
        if not cmds.attributeQuery(attr, node=source, exists=True):
            continue
        children = cmds.attributeQuery(attr, node=source, listChildren=True) or []
        for name in [attr] + children:
            source_plug = "{}.{}".format(source, name)
            inputs = (
                cmds.listConnections(
                    source_plug,
                    source=True,
                    destination=False,
                    plugs=True,
                    skipConversionNodes=True,
                )
                or []
            )
            for input_plug in inputs:
                if not is_anim_source(input_plug.split(".")[0]):
                    continue
                target_plug = layer_base_plug("{}.{}".format(target, name))
                cmds.disconnectAttr(input_plug, source_plug)
                cmds.connectAttr(input_plug, target_plug, force=True)
                moved.append(target_plug)
    return moved


def set_or_key(plug, value):
    """Set a plug, or key it at the current time when it is animated.

    Plugs driven by something other than animation are left unchanged.

    Args:
        plug (str): Plug name.
        value (object): New value.

    Returns:
        bool: True if the value was set or keyed.
    """
    settable, animated = _blend_plug_state(plug)
    if animated:
        cmds.setKeyframe(plug, value=value)
        refresh_keyed([plug])
        return True
    if not settable:
        mgear.log(
            "{} is driven by a connection, not changed".format(plug),
            mgear.sev_warning,
        )
        return False
    cmds.setAttr(plug, value)
    return True


def _bracket_keys(plug, time):
    """Return the keys of a plug strictly before and after a time.

    A key on ``time`` itself is skipped.

    Args:
        plug (str): Plug name.
        time (float): The frame.

    Returns:
        tuple: ``(prev_time, prev_value, next_time, next_value)``, or None
            when the plug has no key on one side.
    """
    try:
        data = cmds.keyframe(plug, query=True, timeChange=True, valueChange=True)
    except RuntimeError:
        return None
    if not data:
        return None
    times = data[0::2]
    prev_index = bisect.bisect_left(times, time) - 1
    next_index = bisect.bisect_right(times, time)
    if prev_index < 0 or next_index >= len(times):
        return None
    return (
        times[prev_index],
        data[2 * prev_index + 1],
        times[next_index],
        data[2 * next_index + 1],
    )


def get_tween_cache(nodes, time=None):
    """Return the previous and next key values of the animated attributes.

    Each keyable, unlocked attribute of the nodes that has keys strictly
    before and strictly after ``time`` gives one entry. Attributes that
    are not animated, or that miss a key on either side, are skipped.
    Collect the cache once and pass it to :func:`apply_tween` as often as
    needed, e.g. on every mouse move of a slider drag.

    Args:
        nodes (list): Node names.
        time (float, optional): Frame to tween at. Defaults to the current
            time.

    Returns:
        list: ``(plug, prev_value, next_value)`` tuples.
    """
    if time is None:
        time = cmds.currentTime(query=True)
    cache = []
    for node in nodes:
        for attr in cmds.listAttr(node, keyable=True, unlocked=True) or []:
            plug = "{}.{}".format(node, attr)
            keys = _bracket_keys(plug, time)
            if keys:
                cache.append((plug, keys[1], keys[3]))
    return cache


def apply_tween(cache, fraction, time=None):
    """Key the tween of the cached attributes at a fraction between keys.

    The keyed value is ``prev + (next - prev) * fraction``, with the
    fraction clamped to [0, 1].

    Args:
        cache (list): ``(plug, prev_value, next_value)`` tuples from
            :func:`get_tween_cache`.
        fraction (float): 0 for the previous key value, 1 for the next.
        time (float, optional): Frame to key. Defaults to the current time.
    """
    fraction = min(max(fraction, 0.0), 1.0)
    apply_blend(
        [(plug, prev, next_, True) for plug, prev, next_ in cache], fraction, time
    )


def _blend_plug_state(plug):
    """Return whether a plug can be blended, and whether it is animated.

    Keyed and layered plugs are keyed. Plugs without an incoming connection
    are set. Plugs driven by anything else (constraints, expressions,
    driven keys...) are skipped. See ``plug_state``.

    Args:
        plug (str): Plug name.

    Returns:
        tuple: ``(settable, animated)`` booleans.
    """
    state = plug_state(plug)
    return state != PLUG_DRIVEN, state in (PLUG_KEYED, PLUG_LAYERED)


def _add_blend_entry(cache, plug, a, b):
    """Append a blend entry, unless a equals b or the plug can't be set."""
    if abs(b - a) < 1e-9:
        return
    settable, animated = _blend_plug_state(plug)
    if settable:
        cache.append((plug, float(a), float(b), animated))


def blend_attributes(node):
    """Return the attributes a pose blend or a pose capture works on.

    Args:
        node (str): Node name.

    Returns:
        list: The keyable, unlocked, scalar attributes.
    """
    return cmds.listAttr(node, keyable=True, unlocked=True, scalar=True) or []


def get_pose_values(nodes):
    """Return the values of the blend attributes of nodes.

    Pair it with :func:`get_buffer_cache` to blend back to the pose.

    Args:
        nodes (list): Node names.

    Returns:
        dict: ``{node: {attribute: value}}`` in node order, numeric values
            only. Nodes without such values are left out.
    """
    pose = {}
    for node in nodes:
        values = {}
        for attr in blend_attributes(node):
            try:
                value = cmds.getAttr("{}.{}".format(node, attr))
            except (RuntimeError, ValueError):
                continue
            if isinstance(value, (int, float)):
                values[attr] = value
        if values:
            pose[node] = values
    return pose


def get_default_cache(nodes):
    """Return blend entries from the current values to the default values.

    Use with :func:`apply_blend`: weight 1 puts the attributes at their
    default value, negative weights move them away from it.

    Args:
        nodes (list): Node names.

    Returns:
        list: ``(plug, current, default, animated)`` tuples.
    """
    cache = []
    for node in nodes or []:
        if not cmds.objExists(node):
            continue
        for attr in blend_attributes(node):
            plug = "{}.{}".format(node, attr)
            try:
                default = cmds.attributeQuery(attr, node=node, listDefault=True)
                current = cmds.getAttr(plug)
            except (RuntimeError, ValueError):
                continue
            if not default or not isinstance(current, (int, float)):
                continue
            _add_blend_entry(cache, plug, current, default[0])
    return cache


def get_mirror_cache(nodes):
    """Return blend entries from the current values to the mirrored values.

    Each control gets the values of its mirror control, with the same
    channels and inversions as :func:`mirror_controls`. Center controls
    mirror onto themselves. All the values are read before any value is
    set, so left and right controls can be blended together.

    Args:
        nodes (list): Control names.

    Returns:
        list: ``(plug, current, mirrored, animated)`` tuples.
    """
    if not nodes:
        return []
    names = cmds.ls([str(n) for n in nodes], long=True, type="transform") or []
    fn_cache = {}
    channels = {}
    swapped_attrs = {}
    cache = []
    for name in names:
        try:
            source = get_mirror_target_name(name)
            if source is None:
                continue
            for target_attr, target_plug, current, value in _mirror_values(
                source, name, fn_cache, channels, swapped_attrs
            ):
                if target_plug.isKeyable:
                    _add_blend_entry(
                        cache, "{}.{}".format(name, target_attr), current, value
                    )
        except Exception as e:
            mgear.log(
                "Mirror blend: skipped {}: {}".format(name.split("|")[-1], e),
                mgear.sev_warning,
            )
    return cache


def get_buffer_cache(values):
    """Return blend entries from the current values to stored values.

    Args:
        values (dict): ``{node: {attribute: value}}``, e.g. a stored pose
            mapped onto the nodes to blend.

    Returns:
        list: ``(plug, current, stored, animated)`` tuples. Missing nodes
            and attributes, and locked or non keyable ones, are skipped.
    """
    fn_cache = {}
    cache = []
    for node, attrs in (values or {}).items():
        if not cmds.objExists(node):
            continue
        fn = _get_dependency_node(node, fn_cache)
        for attr, value in attrs.items():
            try:
                plug = fn.findPlug(attr, False)
            except RuntimeError:
                continue
            if plug.isLocked or not plug.isKeyable:
                continue
            current = _plug_value(plug)
            if current is not None:
                _add_blend_entry(cache, "{}.{}".format(node, attr), current, value)
    return cache


def get_push_cache(nodes, time=None):
    """Return blend entries from the in-between to the current values.

    The in-between is the linear interpolation in time between the keys
    strictly before and after ``time``. Use with :func:`apply_blend`:
    weight 0 pulls back to the in-between, 1 keeps the current value and
    2 doubles the difference. Attributes without keys on both sides are
    skipped.

    Args:
        nodes (list): Node names.
        time (float, optional): Frame. Defaults to the current time.

    Returns:
        list: ``(plug, in_between, current, True)`` tuples.
    """
    if time is None:
        time = cmds.currentTime(query=True)
    cache = []
    for node in nodes or []:
        for attr in cmds.listAttr(node, keyable=True, unlocked=True) or []:
            plug = "{}.{}".format(node, attr)
            keys = _bracket_keys(plug, time)
            if not keys:
                continue
            t0, v0, t1, v1 = keys
            in_between = v0 + (v1 - v0) * (time - t0) / (t1 - t0)
            current = cmds.getAttr(plug, time=time)
            if abs(current - in_between) >= 1e-9:
                cache.append((plug, float(in_between), float(current), True))
    return cache


def apply_blend(cache, weight, time=None):
    """Write the blend of cached attributes at a weight.

    The written value is ``a + (b - a) * weight``; the weight is not
    clamped, so values below 0 or above 1 exaggerate. Animated plugs are
    keyed, the others are set.

    Args:
        cache (list): ``(plug, a, b, animated)`` tuples, e.g. from
            :func:`get_default_cache`.
        weight (float): 0 for ``a``, 1 for ``b``.
        time (float, optional): Frame to key. Defaults to the current time.
    """
    if time is None:
        time = cmds.currentTime(query=True)
    keyed = []
    for plug, a, b, animated in cache:
        value = a + (b - a) * weight
        if animated:
            cmds.setKeyframe(plug, time=time, value=value)
            keyed.append(plug)
        else:
            try:
                cmds.setAttr(plug, value)
            except RuntimeError:
                continue
    refresh_keyed(keyed)


def get_timeline_range():
    """Return the range highlighted on the time slider.

    Returns:
        tuple: ``(start, end)`` frames, end included, or None when no range
            is highlighted or there is no time slider (batch mode).
    """
    slider = mel.eval("global string $gPlayBackSlider; $_tmp = $gPlayBackSlider")
    if not slider or not cmds.timeControl(slider, exists=True):
        return None
    if not cmds.timeControl(slider, query=True, rangeVisible=True):
        return None
    start, end = cmds.timeControl(slider, query=True, rangeArray=True)
    # the range array end is exclusive
    return start, end - 1


def has_selected_keys():
    """Return True when keys are selected (Graph Editor or Dope Sheet).

    Returns:
        bool: The key selection state.
    """
    return bool(cmds.keyframe(query=True, selected=True, name=True))


def _nudge_moved_times(curve, times, moved, offset, ripple):
    """Return the key times of a curve that a nudge moves.

    Args:
        curve (str): Anim curve name, for the error message.
        times (list): All key times of the curve.
        moved (list): Key times picked to move.
        offset (float): Nudge in frames.
        ripple (bool): Also move the keys after the moved ones.

    Returns:
        list: The sorted key times to move.

    Raises:
        ValueError: When a moved key would land on or pass a key that does
            not move.
    """
    moved = set(moved)
    if ripple:
        last = max(moved)
        moved.update(t for t in times if t > last)
    unmoved = sorted(t for t in times if t not in moved)
    for t in moved:
        # the unmoved key nearest to t in the nudge direction
        if offset > 0:
            index = bisect.bisect_right(unmoved, t)
            blocked = index < len(unmoved) and unmoved[index] <= t + offset
        else:
            index = bisect.bisect_left(unmoved, t) - 1
            blocked = index >= 0 and unmoved[index] >= t + offset
        if blocked:
            raise ValueError(
                "Nudge blocked: keys of {} would overlap other keys".format(curve)
            )
    return sorted(moved)


def nudge_keys(nodes, start, end, offset, ripple=False, attributes=None):
    """Move the keys of nodes inside a frame range in time.

    Nothing moves when a key would land on or pass a key that does not
    move: Maya would clamp it to a sub-frame time or reorder the curve.

    Args:
        nodes (list): Node names.
        start (float): First frame of the keys to move.
        end (float): Last frame of the keys to move, included.
        offset (float): Frames to move by, negative to move back.
        ripple (bool, optional): Also move every later key of the curves.
        attributes (list, optional): Only move the keys of these
            attributes.

    Returns:
        int: Number of moved keys.

    Raises:
        ValueError: When the nudge is blocked by other keys.
    """
    if not offset or not nodes:
        return 0
    if attributes:
        targets = ["{}.{}".format(n, a) for n in nodes for a in attributes]
        targets = [t for t in targets if cmds.objExists(t)]
    else:
        targets = list(nodes)
    curves = cmds.keyframe(targets, query=True, name=True) if targets else None
    plan = []
    for curve in dict.fromkeys(curves or []):
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        picked = [t for t in times if start - 1e-6 <= t <= end + 1e-6]
        if picked:
            moved = _nudge_moved_times(curve, times, picked, offset, ripple)
            plan.append((curve, moved))
    for curve, moved in plan:
        cmds.keyframe(
            curve,
            edit=True,
            relative=True,
            timeChange=offset,
            time=(moved[0], moved[-1]),
            option="over",
        )
    return sum(len(moved) for _curve, moved in plan)


def nudge_selected_keys(offset, ripple=False):
    """Move the selected keys in time, keeping them selected.

    Same rules as :func:`nudge_keys`.

    Args:
        offset (float): Frames to move by, negative to move back.
        ripple (bool, optional): Also move every later key of the curves.

    Returns:
        int: Number of moved keys.

    Raises:
        ValueError: When the nudge is blocked by other keys.
    """
    curves = cmds.keyframe(query=True, selected=True, name=True) or []
    if not offset or not curves:
        return 0
    plan = []
    for curve in dict.fromkeys(curves):
        times = cmds.keyframe(curve, query=True, timeChange=True) or []
        selected = cmds.keyframe(curve, query=True, selected=True, timeChange=True)
        moved = _nudge_moved_times(curve, times, selected, offset, ripple)
        last_selected = max(selected)
        tail = [t for t in moved if t > last_selected]
        plan.append((curve, moved, tail))
    for curve, _moved, tail in plan:
        if tail:
            cmds.selectKey(curve, add=True, time=(tail[0], tail[-1]))
    cmds.keyframe(edit=True, relative=True, timeChange=offset, option="over")
    for curve, _moved, tail in plan:
        if tail:
            cmds.selectKey(
                curve, remove=True, time=(tail[0] + offset, tail[-1] + offset)
            )
    return sum(len(moved) for _curve, moved, _tail in plan)


def get_world_matrices(nodes):
    """Return the world matrix of nodes on the current frame.

    Args:
        nodes (list): Transform names.

    Returns:
        list: One world matrix (16 floats) per node, in order, as used by
            :func:`key_world_matrices`.
    """
    return [list(utils.get_dag_path(node).inclusiveMatrix()) for node in nodes]


def get_play_every_frame():
    """Return True when playback evaluates every frame.

    Returns:
        bool: True for "Play every frame".
    """
    return cmds.playbackOptions(query=True, playbackSpeed=True) == 0


def set_play_every_frame(enabled=True):
    """Set playback to evaluate every frame, or to real time.

    Args:
        enabled (bool, optional): True for "Play every frame", False for
            real time.
    """
    cmds.playbackOptions(playbackSpeed=0 if enabled else 1)


def bake_attributes(
    nodes,
    attrs=None,
    start=None,
    end=None,
    sample=1,
    preroll=0,
    destination_layer=None,
):
    """Bake attributes over a frame range as a simulation.

    Keys outside the range are kept. The viewport is suspended while
    baking. For simulations (springs, dynamics), ``preroll`` frames before
    ``start`` and the start frame are evaluated one by one first, so the
    bake continues a settled simulation instead of restarting it. No keys
    are written before ``start``.

    Args:
        nodes (list): Node names, or full plugs (``node.attr``) when
            ``attrs`` is None.
        attrs (list, optional): Attribute names to bake on every node.
            When None, ``nodes`` must be plugs.
        start (float, optional): First frame. Defaults to the playback
            start.
        end (float, optional): Last frame. Defaults to the playback end.
        sample (float, optional): Bake every ``sample`` frames.
        preroll (int, optional): Frames evaluated before ``start``.
        destination_layer (str, optional): Animation layer receiving the
            keys, created as an override layer when missing. The existing
            curves are kept on the base layer.

    Returns:
        bool: True if something was baked.
    """
    if not nodes:
        return False
    start, end = get_playback_range(start, end)
    nodes = list(nodes)
    plugs = (
        ["{}.{}".format(node, attr) for node in nodes for attr in attrs]
        if attrs
        else nodes
    )
    kwargs = {"attribute": list(attrs)} if attrs else {}
    if destination_layer:
        if not cmds.animLayer(destination_layer, query=True, exists=True):
            cmds.animLayer(destination_layer, override=True)
        # bakeResults adds the plugs to the layer: adding them first would
        # cut their driving connections and bake a constant value
        kwargs["destinationLayer"] = destination_layer
    with utils.viewport_suspended():
        # simulations only compute when read: pull every frame in order
        for frame in range(int(start) - max(0, int(preroll)), int(start) + 1):
            cmds.currentTime(frame, edit=True)
            cmds.dgeval(plugs)
        cmds.bakeResults(
            nodes,
            time=(start, end),
            simulation=True,
            sampleBy=sample,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=False,
            **kwargs,
        )
    return True


def new_time_editor_track():
    """Add a track to the active Time Editor composition.

    A composition is created when the scene has none.

    Returns:
        str: The track, as ``"composition:index"``.
    """
    try:
        composition = cmds.timeEditorComposition(query=True, active=True)
    except RuntimeError:
        composition = None
    if not composition:
        composition = cmds.timeEditorComposition("Composition1")
    index = cmds.timeEditorTracks(composition, edit=True, addTrack=-1)
    return "{}:{}".format(composition, index)


def add_time_editor_clip(name, nodes, start, track=None):
    """Move the animation of nodes into a Time Editor clip.

    The keys leave the scene and play from the clip.

    Args:
        name (str): Clip name; the animation source is named after it.
        nodes (list): Animated nodes.
        start (float): Clip start frame.
        track (str, optional): Track, see :func:`new_time_editor_track`.
            Default: a new track.

    Returns:
        int: The clip id.
    """
    track = track or new_time_editor_track()
    with utils.keep_selection():
        cmds.select(nodes, replace=True)
        source = cmds.timeEditorAnimSource(name, addSelectedObjects=True)
    return cmds.timeEditorClip(
        "{}_clip".format(name), animSource=source, startTime=start, track=track
    )


def getRootNode():
    """Returns the root node from a selected node

    Returns:
        PyNode: The root top node
    """

    root = None

    current = pm.ls(sl=True)
    if not current:
        raise RuntimeError("You need to select at least one rig node")

    if current[0].hasAttr("is_rig"):
        root = current[0]
    else:
        holder = current[0]
        while holder.getParent() and not root:
            if holder.getParent().hasAttr("is_rig"):
                root = holder.getParent()
            else:
                holder = holder.getParent()

    if not root:
        raise RuntimeError("Couldn't find root node from your selection")

    return root


def getControlers(model, gSuffix=CTRL_GRP_SUFFIX):
    """Get thr controlers from the set

    Args:
        model (PyNode or str): Rig root
        gSuffix (str, optional): set suffix

    Returns:
        list: The members of the group, None when the rig has no such set
    """
    try:
        ctl_set = pm.PyNode(pm.PyNode(model).name() + gSuffix)
        members = ctl_set.members()

        return members
    except (TypeError, pm.MayaNodeError):
        # no set with this suffix on the rig
        return None


def get_control_list(control, blend_attr, extension="_ctl"):

    controls = None

    controls_attribute = blend_attr.replace("_blend", extension)
    try:
        controls = cmds.getAttr("{}.{}".format(control, controls_attribute))
    except ValueError:
        if control == "world_ctl":
            _msg = "New type attributes using world as host are not supported"
            raise RuntimeError(_msg)
        attr = "{}_{}_ctl".format(
            blend_attr.split("_")[0], control.split(":")[-1].split("_")[1]
        )
        controls = cmds.getAttr("{}.{}".format(control, attr))

    return controls


def get_ik_fk_controls(control, blend_attr, comp_ctl_list=None):
    """Returns the ik and fk controls related to the given control blend attr

    OBSOLETE:This function is obsolete and just keep for backward compatibility

    Args:
        control (str): uihost control to interact with
        blend_attr (str): attribute containing control list

    Returns:
        dict: fk and ik controls list on a dict
    """

    ik_fk_controls = {"fk_controls": [], "ik_controls": []}

    if comp_ctl_list:
        ctl_list = cmds.getAttr("{}.{}".format(control, comp_ctl_list))
    else:
        ctl_list = get_control_list(control, blend_attr)

    # filters the controls
    for ctl in ctl_list.split(","):
        if len(ctl) == 0:
            continue
        # filters ik controls
        if "_ik" in ctl.lower() or "_upv" in ctl:
            ik_fk_controls["ik_controls"].append(ctl)
        # filters fk controls
        elif "_fk" in ctl.lower():
            ik_fk_controls["fk_controls"].append(ctl)

    return ik_fk_controls


def get_ik_fk_controls_by_role(uiHost, attr_ctl_cnx):
    """Returns the ik fk controls sorted by role.
     Using the new role attr tag

     this makes obsolete get_ik_fk_controls() function.

    Args:
        uiHost (str): uihost control to interact with
        attr_ctl_cnx (str): attribute containing control list

    Returns:
        dict: with the control sorted by role
    """
    ik_controls = {"ik_control": None, "pole_vector": None, "ik_rot": None}
    fk_controls = []
    uiHost = pm.PyNode(uiHost)
    if uiHost.hasAttr(attr_ctl_cnx):
        cnxs = uiHost.attr(attr_ctl_cnx).listConnections()
        if cnxs:
            for c in cnxs:
                role = c.ctl_role.get()
                if "fk" in role:
                    fk_controls.append(c.stripNamespace())
                elif role in ["upv", "leg_pv", "arm_pv"]:
                    ik_controls["pole_vector"] = c.stripNamespace()
                elif role in ["ik", "wrist_ik", "ankle_ik"]:
                    ik_controls["ik_control"] = c.stripNamespace()
                elif role == "ikRot":
                    ik_controls["ik_rot"] = c.stripNamespace()
                elif role == "roll":
                    ik_controls["roll"] = c.stripNamespace()
                # _Swift case
                elif role == "toes_ik":
                    ik_controls["toes_ik"] = c.stripNamespace()
                elif role == "heelIk":
                    ik_controls["heelIk"] = c.stripNamespace()
                elif role == "toeRollIk":
                    ik_controls["toeRollIk"] = c.stripNamespace()
                elif role == "reverse_ankle_ik":
                    ik_controls["reverse_ankle_ik"] = c.stripNamespace()

    # fk_controls = sorted(fk_controls)
    return ik_controls, fk_controls


def get_host_from_node(control):
    """Returns the host control name from the given control
    Args:
        control (str): Rig control

    Returns:
        str: Host UI control name
    """

    # get host control
    namespace = getNamespace(control).split("|")[-1]
    host = cmds.getAttr("{}.uiHost".format(control))
    return "{}:{}".format(namespace, host)


# Rig queries -----------------------------------------------------------------
# Control roles moved by a space switch when the attribute token is not a
# control role itself. i.e: the "elbowref" attribute moves the "mid" control
SPACE_CONTROL_MAP = {
    "elbow": ("mid",),
    "rot": ("orbit", "fk0"),
    "knee": ("mid",),
    "ik": ("headIK",),
    "head": ("headFree",),
}


# Moved to mgear.core.dag, kept for the callers of this module
_find_rig_root_path = dag.find_rig_root_path


def find_rig_root(node):
    """Find the rig top node of the given node.

    Walks up the hierarchy, starting with the node itself, to the first node
    with an ``is_rig`` attribute. Nodes in the controllers_org group and
    control buffers are skipped. Works with rigs parented under other groups.

    Args:
        node (str): Any node of the rig.

    Returns:
        str: Short name of the rig top node (with namespace), None if not
            found.
    """
    path = _find_rig_root_path(node)
    if not path:
        return None
    return path.split("|")[-1]


def _get_ctl_role(control):
    """Get the ctl_role value of a control.

    Args:
        control (str): Control name.

    Returns:
        str: The role, None if the control has no role attribute.
    """
    if not cmds.attributeQuery("ctl_role", node=control, exists=True):
        return None
    return cmds.getAttr("{}.ctl_role".format(control))


def parse_space_attr(attr):
    """Split a space switch attribute name in component name and token.

    The token is the last name part without its "ref" suffix. i.e:
    "arm_ikref" gives ("arm", "ik"), "neck_head_ref" gives ("neck_head", "")

    Args:
        attr (str): Space switch attribute name.

    Returns:
        tuple: Component attribute name and control token.
    """
    parts = attr.split("_")
    token = parts[-1].split("ref")[0].split("Ref")[0]
    return "_".join(parts[:-1]) or parts[0], token


def get_space_switch_targets(ui_host, attr, control_map=None, fallback_role=None):
    """Get the controls moved by a space switch attribute.

    The components sharing the attribute are found with the
    ``<attr_name>_id*_ctl_cnx`` attributes of the ui host. For each component
    the control whose role matches the attribute token (or a role mapped to
    it in control_map) is used. When none matches, all the component
    controls are used, filtered by fallback_role if given. A ``follow``
    attribute without components resolves to the ui host itself.

    Args:
        ui_host (str): Node with the space switch attribute.
        attr (str): Space switch attribute name. i.e: "arm_ikref"
        control_map (dict, optional): Attribute token to control roles.
            Defaults to SPACE_CONTROL_MAP.
        fallback_role (str, optional): Role used to filter the controls of a
            component without a token match.

    Returns:
        list: Control names without namespace.
    """
    if control_map is None:
        control_map = SPACE_CONTROL_MAP
    attr_name, token = parse_space_attr(attr)
    criteria = attr_name + "_id*_ctl_cnx"
    cnx_attrs = cmds.listAttr(ui_host, userDefined=True, string=criteria) or []

    targets = []
    for cnx_attr in cnx_attrs:
        controls = cmds.listConnections("{}.{}".format(ui_host, cnx_attr)) or []
        target = None
        for ctl in controls:
            role = _get_ctl_role(ctl)
            if role == token or role in control_map.get(token, ()):
                target = stripNamespace(ctl)
                break
        if target:
            targets.append(target)
            continue
        for ctl in controls:
            if fallback_role is None or _get_ctl_role(ctl) == fallback_role:
                targets.append(stripNamespace(ctl))

    if token == "follow" and not targets:
        # the control holds its own space switch attribute
        targets.append(stripNamespace(ui_host.split("|")[-1]))
    return targets


def get_ikfk_components(ui_host, blend_attr):
    """Get the IK and FK controls of the components sharing a blend attribute.

    Supports the ``<name>_blend`` attributes and the ``_Switch`` attributes,
    which drive all the components connected to the ui host.

    Args:
        ui_host (str): Node with the IK/FK blend attribute.
        blend_attr (str): Blend attribute name. i.e: "arm_blend"

    Returns:
        tuple: FK control list of all components, merged IK controls dict
            (ik_control, pole_vector, ik_rot and extra roles) and the list of
            (ik_controls, fk_controls) per component.
    """
    if "_Switch" in blend_attr:
        criteria = "*_id*_ctl_cnx"
    else:
        criteria = blend_attr.replace("_blend", "") + "_id*_ctl_cnx"
    cnx_attrs = cmds.listAttr(ui_host, userDefined=True, string=criteria) or []

    fk_list = []
    ik_dict = {}
    components = []
    for cnx_attr in cnx_attrs:
        ik_controls, fk_controls = get_ik_fk_controls_by_role(ui_host, cnx_attr)
        fk_list.extend(fk_controls)
        ik_dict.update({k: v for k, v in ik_controls.items() if v is not None})
        components.append((ik_controls, fk_controls))
    return fk_list, ik_dict, components


def toggle_ctl_xray(node):
    """Toggle the control X-Ray of the rig owning the given control.

    The rig is found through the control's controller tag, else by walking up
    the hierarchy.

    Args:
        node (str): A rig control.

    Returns:
        bool: The new X-Ray state, None if the rig has no ctl_x_ray attribute.
    """
    tags = cmds.listConnections("{}.message".format(node), type="controller") or []
    owners = [
        owner
        for tag in tags
        for owner in cmds.listConnections("{}.message".format(tag)) or []
        if cmds.attributeQuery("is_rig", node=owner, exists=True)
    ]
    root = owners[0] if owners else _find_rig_root_path(node)
    if not root or not cmds.attributeQuery("ctl_x_ray", node=root, exists=True):
        return None
    plug = "{}.ctl_x_ray".format(root)
    state = not cmds.getAttr(plug)
    cmds.setAttr(plug, state)
    return state


def getNamespace(modelName):
    """Get the name space from rig root

    Args:
        modelName (str): Rig top node name

    Returns:
        str: Namespace
    """
    if not modelName:
        return ""

    if len(modelName.split(":")) >= 2:
        nameSpace = ":".join(modelName.split(":")[:-1])
    else:
        nameSpace = ""

    return nameSpace


def stripNamespace(nodeName):
    """Strip all the namespaces from a given name

    Args:
        nodeName (str): Node name to strip the namespaces

    Returns:
        str: Node name without namespace
    """
    return nodeName.split(":")[-1]


def getNode(nodeName):
    """Get a PyNode from the string name


    Args:
        nodeName (str): Node name

    Returns:
        PyNode or None: The node. or None if the object can't be found
    """
    try:
        return pm.PyNode(nodeName)

    except (pm.MayaNodeError, RuntimeError):
        print(f"Not found node:{nodeName} ")
        return None


def listAttrForMirror(node):
    """List attributes to invert the value for mirror posing

    Args:
        node (PyNode): The Node with the attributes to invert

    Returns:
        list: Attributes to invert
    """
    # TODO: should "ro" be here?
    res = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro"]
    res.extend(cmds.listAttr(node, userDefined=True, shortNames=True))
    res = list([x for x in res if not x.startswith("inv")])
    res = list([x for x in res if node.attr(x).type() not in ["message", "string"]])
    return res


def getInvertCheckButtonAttrName(str):
    """Get the invert check butto attribute name

    Args:
        str (str): The attribute name

    Returns:
        str: The checked attribute name
    """
    # type = (str) -> str
    return "inv{0}".format(str.lower().capitalize())


def selAll(model):
    """Select all controlers

    Args:
        model (PyNode): Rig top node
    """
    controlers = getControlers(model)
    pm.select(controlers)


def selGroup(model, groupSuffix):
    """Select the members of a given set

    Args:
        model (PyNode): Rig top node
        groupSuffix (str): Set suffix name
    """
    controlers = getControlers(model, groupSuffix)
    pm.select(controlers)


def select_all_child_controls(control, *args):  # @unusedVariable
    """Selects all child controls from the given control

    This function uses Maya's controller nodes and commands to find relevant
    dependencies between controls

    Args:
        control (str): parent animation control (transform node)
        *args: State of the menu item (if existing) send by mgear's dagmenu
    """

    # gets controller node from the given control. Returns if none is found
    # tag = cmds.ls(cmds.listConnections(control), type="controller")
    # if not tag:
    #     return

    # query child controls
    children = get_all_tag_children(control)
    if not children:
        return

    # adds to current selection the children elements
    cmds.select(children, add=True)


def quickSel(model, channel, mouse_button):
    """Select the object stored on the quick selection attributes

    Args:
        model (PyNode): The rig top node
        channel (str): The quick selection channel name
        mouse_button (QtSignal): Clicked mouse button

    Returns:
        None
    """
    qs_attr = model.attr("quicksel%s" % channel)

    if mouse_button == QtCore.Qt.LeftButton:  # Call Selection
        names = qs_attr.get().split(",")
        if not names:
            return
        pm.select(clear=True)
        for name in names:
            ctl = dag.findChild(model, name)
            if ctl:
                ctl.select(add=True)
    elif mouse_button == QtCore.Qt.MidButton:  # Save Selection
        names = [
            sel.name().split("|")[-1]
            for sel in pm.ls(selection=True)
            if sel.name().endswith("_ctl")
        ]

        qs_attr.set(",".join(names))

    elif mouse_button == QtCore.Qt.RightButton:  # Key Selection
        names = qs_attr.get().split(",")
        if not names:
            return
        else:
            keyObj(model, names)


##################################################
# KEY
##################################################
# ================================================
def keySel():
    """Key selected controls"""

    pm.setKeyframe()


# ================================================


def keyObj(model, object_names):
    """Set the keyframe in the controls pass by a list in obj_names variable

    Args:
        model (Str): Name of the namespace that will define de the model
        object_names (Str): names of the controls, without the name space

    Returns:
        None
    """
    with pm.UndoChunk():
        nodes = []
        nameSpace = getNamespace(model)
        for name in object_names:
            if nameSpace:
                node = getNode(nameSpace + ":" + name)
            else:
                node = getNode(name)

            if not node:
                continue

            if not node and nameSpace:
                mgear.log(
                    "Can't find object : %s:%s" % (nameSpace, name),
                    mgear.sev_error,
                )
            elif not node:
                mgear.log("Can't find object : %s" % (name), mgear.sev_error)
            nodes.append(node)

        if not nodes:
            return

        pm.setKeyframe(*nodes)


def keyAll(model):
    """Keyframe all the controls inside the controls group

    Note: We use the workd "group" to refer to a set in Maya

    Args:
        model (PyNode): Rig top node
    """
    controlers = getControlers(model)
    pm.setKeyframe(controlers)


def keyGroup(model, groupSuffix):
    """Keyframe all the members of a given group

    Args:
        model (PyNode): Rig top node
        groupSuffix (str): The group preffix
    """
    controlers = getControlers(model, groupSuffix)
    pm.setKeyframe(controlers)


# ================================================


def toggleAttr(model, object_name, attr_name):
    """Toggle a boolean attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): The name of the control containing the attribute to
            toggle
        attr_name (str): The attribute to toggle
    """
    nameSpace = getNamespace(model)
    if nameSpace:
        node = dag.findChild(nameSpace + ":" + object_name)
    else:
        node = dag.findChild(model, object_name)

    oAttr = node.attr(attr_name)
    if oAttr.type() in ["float", "bool"]:
        oVal = oAttr.get()
        if oVal == 1:
            oAttr.set(0)
        else:
            oAttr.set(1)


# ================================================


def getComboIndex_with_namespace(namespace, object_name, combo_attr):
    """Get the index from a  combo attribute

    Args:
        namespace (str): namespace
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        int: Current index in the combo attribute
    """
    if namespace:
        node = getNode(namespace + ":" + stripNamespace(object_name))
    else:
        node = getNode(object_name)

    oVal = node.attr(combo_attr).get()
    return oVal


def getComboIndex(model, object_name, combo_attr):
    """Get the index from a  combo attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        int: Current index in the combo attribute
    """
    nameSpace = getNamespace(model)
    return getComboIndex_with_namespace(nameSpace, object_name, combo_attr)


def changeSpace_with_namespace(namespace, uiHost, combo_attr, cnsIndex, ctl_names):
    """Change the space of a control

    i.e: A control with ik reference array

    Args:
        namespace (str): namespace
        uiHost (str): uiHost Name with the switch attr
        combo_attr (str): Combo attribute name
        cnsIndex (int): Combo index to change
        ctl_names ([str]): names of the target controls
    """
    if not isinstance(ctl_names, list):
        ctl_names = [ctl_names]

    if namespace:
        node = getNode(namespace + ":" + stripNamespace(uiHost))
    else:
        node = getNode(uiHost)

    sWM = []
    controls = []
    for e, c_name in enumerate(ctl_names):
        if namespace:
            ctl = getNode(namespace + ":" + stripNamespace(c_name))
        else:
            ctl = getNode(c_name)

        sWM.append(transform.get_world_transform_data(ctl))
        controls.append(ctl)

    oAttr = node.attr(combo_attr)
    oAttr.set(cnsIndex)

    for e, ctl in enumerate(controls):
        transform.set_world_transform_data(ctl, sWM[e])


def changeSpace(model, uiHost, combo_attr, cnsIndex, ctl_names):
    """Change the space of a control

    i.e: A control with ik reference array

    Args:
        model (PyNode): Rig top node
        uiHost (str): uiHost Name with the switch attr
        combo_attr (str): Combo attribute name
        cnsIndex (int): Combo index to change
        ctl_names ([str]]): Name of the target controls
    """
    nameSpace = getNamespace(model)
    return changeSpace_with_namespace(
        nameSpace, uiHost, combo_attr, cnsIndex, ctl_names
    )


def change_rotate_order(control, target_order):
    """Change current control rotate order on all frames

    Args:
        control (str): control to interact on
        target_order (str): target rotate order
    """

    if len(target_order) != 3:
        raise AttributeError(
            "Your target rotate order is not valid. "
            "Please use any of the following: "
            "xyz, yzx, zxy, xzy, yxz, zyx"
        )

    if not cmds.getAttr("{}.rotateOrder".format(control), settable=True):
        raise RuntimeError("RotateOrder is locked on the given control")

    # Maya's rotate order's index
    rotate_orders = {
        "xyz": 0,
        "yzx": 1,
        "zxy": 2,
        "xzy": 3,
        "yxz": 4,
        "zyx": 5,
    }

    # gets current control rotate order
    current_order = cmds.getAttr("{}.rotateOrder".format(control))

    # do nothing if target rotate order is the same as current one
    if current_order == rotate_orders[target_order]:
        return

    # gets anim curves on rotation values
    anim_curves = []
    for axe in ["x", "y", "z"]:
        anim_curves.extend(
            cmds.listConnections("{}.r{}".format(control, axe), type="animCurve") or []
        )

    # gets keyframe on rotateOrder attribute if any
    rotate_order_anim = (
        cmds.listConnections("{}.rotateOrder".format(control), type="animCurve") or []
    )

    # get unique timeline values for all rotate keyframe
    frames = []
    for node in anim_curves:
        [
            frames.append(x)
            for x in cmds.keyframe(node, query=True, controlPoints=True)
            if x not in frames
        ]

    # pauses viewport update
    current_frame = cmds.currentTime(query=True)
    if not cmds.ogs(query=True, pause=True):
        cmds.ogs(pause=True)

    # stores matrix position of your control for each frame
    positions = {}
    holder = cmds.createNode(
        "transform",
        name="{}_rotate_order_switch".format(control.split("|")[-1]),
    )
    cmds.setAttr("{}.rotateOrder".format(holder, rotate_orders[target_order]))
    for frame in frames:
        cmds.currentTime(frame)
        position = cmds.xform(control, query=True, worldSpace=True, matrix=True)
        cmds.xform(holder, worldSpace=True, matrix=position)
        positions[frame] = cmds.xform(holder, query=True, worldSpace=True, matrix=True)

    # change rotate order
    if rotate_order_anim:
        cmds.keyframe(
            rotate_order_anim,
            edit=True,
            valueChange=rotate_orders[target_order],
        )
    else:
        cmds.setAttr("{}.rotateOrder".format(control), rotate_orders[target_order])

    for frame in frames:
        cmds.currentTime(frame)
        cmds.xform(control, worldSpace=True, matrix=positions[frame])

    # filters curves
    cmds.filterCurve(anim_curves)

    # deletes holder and set back the good timeline value
    cmds.delete(holder)
    cmds.currentTime(current_frame)

    # un-pauses viewport
    if cmds.ogs(query=True, pause=True):
        cmds.ogs(pause=True)

    cmds.select(control)


##################################################
# Combo Box
##################################################
# ================================================


def getComboKeys_with_namespace(namespace, object_name, combo_attr):
    """Get the keys from a combo attribute

    Args:
        namespace (str): namespace
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        list: Keys names from the combo attribute.
    """
    if namespace:
        node = getNode(namespace + ":" + stripNamespace(object_name))
    else:
        node = getNode(object_name)

    oAttr = node.attr(combo_attr)
    keys = list(oAttr.getEnums().keys())
    keys.append("++ Range Transfer Options ++")
    return keys


def getComboKeys(model, object_name, combo_attr):
    """Get the keys from a combo attribute

    Args:
        model (PyNode): Rig top node
        object_name (str): Control name
        combo_attr (str): Combo attribute name

    Returns:
        list: Keys names from the combo attribute.
    """
    nameSpace = getNamespace(model)

    return getComboKeys_with_namespace(nameSpace, object_name, combo_attr)


##################################################
# IK FK switch match
##################################################
# ================================================
def ikFkMatch_with_namespace2(
    namespace,
    ikfk_attr,
    ui_host,
    fk_controls,
    ik_controls,
    keyframe=None,
    ik_val=False,
    fk_val=True,
):

    # returns a pymel node on the given name
    def _get_node(name):
        # type = (str) -> pm.nodetypes.Transform
        name = stripNamespace(name)
        if namespace:
            node = getNode(":".join([namespace, name]))
        else:
            node = getNode(name)

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    # returns matching node
    def _get_mth(name):
        # type = (str) -> pm.nodetypes.Transform
        node = _get_node(name)
        if node.hasAttr("match_ref"):
            match_node = node.match_ref.listConnections()
            if match_node:
                return match_node[0]
        else:
            tmp = name.split("_")
            tmp[-1] = "mth"
            return _get_node("_".join(tmp))

    # get elements to match
    fk_ctrls = [_get_node(x) for x in fk_controls]
    fk_targets = [_get_mth(x) for x in fk_controls]

    ik_ctrl = {key: _get_node(value) for key, value in ik_controls.items()}
    ik_targets = {key: _get_mth(value) for key, value in ik_controls.items()}

    # get inital value
    ui_node = _get_node(ui_host)
    o_attr = ui_node.attr(ikfk_attr)

    # get ik values as list
    ik_controls_list = list(ik_controls.values())

    # if already keyframe we always set keyframes
    for c in [o_attr] + fk_ctrls + ik_controls_list:
        if pm.keyframe(c, query=True, keyframeCount=True):
            keyframe = True
            break

    val = o_attr.get()

    # sets keyframes before snapping
    if keyframe:
        _all_controls = []
        _all_controls.extend(fk_controls)
        _all_controls.extend(ik_controls_list)
        _all_controls.extend([o_attr])
        [
            cmds.setKeyframe(
                "{}".format(_get_node(elem)),
                time=(cmds.currentTime(query=True) - 1.0),
            )
            for elem in _all_controls
        ]

    # if is IK then snap FK
    if val == ik_val:
        for target, ctl in zip(fk_targets, fk_ctrls):
            transform.matchWorldTransform(target, ctl)
        pm.setAttr(o_attr, fk_val)

    # if is FK then snap IK
    elif val == fk_val:
        transform.matchWorldTransform(
            ik_targets["ik_control"], ik_ctrl["ik_control"]
        )
        transform.matchWorldTransform(
            ik_targets["pole_vector"], ik_ctrl["pole_vector"]
        )

        try:
            transform.matchWorldTransform(
                ik_targets["toes_ik"], ik_ctrl["toes_ik"]
            )
            transform.matchWorldTransform(
                ik_targets["toeRollIk"], ik_ctrl["toeRollIk"]
            )
            transform.matchWorldTransform(
                ik_targets["heelIk"], ik_ctrl["heelIk"]
            )
            transform.matchWorldTransform(
                ik_targets["reverse_ankle_ik"],
                ik_ctrl["reverse_ankle_ik"],
            )
            match_fk_to_ik_arbitrary_lengths(
                fk_controls, ui_node, ikfk_attr,
                ik_ctrl["pole_vector"],
            )
        except KeyError:
            pass

        # Set the blend attr to IK BEFORE matching roll, because
        # the rig needs to evaluate in IK mode first so the roll
        # control's parent hierarchy is in its final state.
        pm.setAttr(o_attr, ik_val)

        # Match roll control after blend switch
        if "roll" in ik_ctrl and ik_ctrl["roll"] is not None:
            if "roll" in ik_targets and ik_targets["roll"] is not None:
                transform.matchWorldTransform(
                    ik_targets["roll"], ik_ctrl["roll"]
                )

    # sets keyframes
    if keyframe:
        [
            cmds.setKeyframe(
                "{}".format(_get_node(elem)),
                time=(cmds.currentTime(query=True)),
            )
            for elem in _all_controls
        ]
    # cmds.dgdirty(a=True)

    return


def ikFkMatch_with_namespace(
    namespace,
    ikfk_attr,
    ui_host,
    fks,
    ik,
    upv,
    ik_rot=None,
    key=None,
    ik_controls=None,
    ik_val=1.0,
    fk_val=0.0,
):
    """Switch IK/FK with matching functionality

    This function is meant to work with 2 joint limbs.
    i.e: human legs or arms

    Args:
        namespace (str): Rig name space
        ikfk_attr (str): Blend ik fk attribute name
        ui_host (str): Ui host name
        fks ([str]): List of fk controls names
        ik (str): Ik control name
        upv (str): Up vector control name
        ik_rot (None, optional): Ik Rotation control if exist
        key (None, bool): optional. Whether we do an snap with animation
        ik_controls (None, optional): Ik controls
        ik_val (float, optional): Value that will define IK active
        fk_val (float, optional): Value that will define FK active

    Deleted Parameters:
        ikRot (None, str): optional. Name of the Ik Rotation control
    """
    # -----------------------------------------------
    # NOTE: the following section is a workaround to match and reset the gimbal
    # controls for legs and arms
    # this workaround doesn't support custom naming.
    gimbal_exist = False
    try:
        if "arm" in ikfk_attr or "leg" in ikfk_attr:

            fks_gimbal = [pm.PyNode(x.replace("fk", "gimbal")) for x in fks]
            ik_gimbal = pm.PyNode(ik.replace("ik", "gimbalIK"))

            # store world transforms
            fks_wtrans = [x.getMatrix(worldSpace=True) for x in fks_gimbal]
            ik_wtrans = ik_gimbal.getMatrix(worldSpace=True)

            # reset local transform
            for x in fks_gimbal:
                transform.resetTransform(x)
            transform.resetTransform(ik_gimbal)

            # apply transform to main control
            for i, x in enumerate(fks):
                pm.PyNode(x).setMatrix(fks_wtrans[i], worldSpace=True)
            pm.PyNode(ik).setMatrix(ik_wtrans, worldSpace=True)

            # keyframes
            if key:
                for x in fks_gimbal + [ik_gimbal]:
                    pm.setKeyframe(x, time=(cmds.currentTime(query=True) - 1.0))
            gimbal_exist = True
    except:
        pass

    # end of workaround gimbal match
    # -----------------------------------------------
    # returns a pymel node on the given name
    def _get_node(name):
        # type = (str) -> pm.nodetypes.Transform
        name = stripNamespace(name)
        if namespace:
            node = getNode(":".join([namespace, name]))
        else:
            node = getNode(name)

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    # returns matching node
    def _get_mth(name):
        # type = (str) -> pm.nodetypes.Transform
        node = _get_node(name)
        if node.hasAttr("match_ref"):
            match_node = node.match_ref.listConnections()
            if match_node:
                return match_node[0]
        else:
            tmp = name.split("_")
            tmp[-1] = "mth"
            return _get_node("_".join(tmp))

    # get things ready
    fk_ctrls = [_get_node(x) for x in fks]
    fk_targets = [_get_mth(x) for x in fks]
    ik_ctrl = _get_node(ik)
    ik_target = _get_mth(ik)
    upv_ctrl = _get_node(upv)

    if ik_rot:
        ik_rot_node = _get_node(ik_rot)
        ik_rot_target = _get_mth(ik_rot)

    ui_node = _get_node(ui_host)
    o_attr = ui_node.attr(ikfk_attr)
    val = o_attr.get()

    # check for  FOOT cnx
    # get the information to handle the foot if the conexion exist
    foot_cnx = False
    if fk_ctrls[0].hasAttr("compRoot"):
        comp_root = fk_ctrls[0].compRoot.listConnections()[0]
        foot_IK_ctls = []
        foot_FK_matrix = []
        if comp_root.hasAttr("footCnx"):
            foot_cnx = True
            foot_root = comp_root.footCnx.listConnections()[0]
            foot_bk = [x for x in reversed(foot_root.bk_ctl.listConnections())]
            foot_IK_ctls.extend(foot_bk)
            foot_fk = foot_root.fk_ctl.listConnections()
            for c in foot_fk:
                foot_FK_matrix.append(c.getMatrix(worldSpace=True))
            heel_ctl = foot_root.heel_ctl.listConnections()[0]
            foot_IK_ctls.append(heel_ctl)
            tip_ctl = foot_root.tip_ctl.listConnections()[0]
            foot_IK_ctls.append(tip_ctl)
            if foot_root.hasAttr("roll_ctl"):
                roll_ctl = foot_root.roll_ctl.listConnections()[0]
                foot_IK_ctls.append(roll_ctl)
            else:
                roll_ctl = None
            if foot_root.hasAttr("roll_cnx"):
                roll_attr = foot_root.roll_cnx.listConnections()[0]
                bank_attr = foot_root.bank_cnx.listConnections()[0]
            else:
                roll_attr = None
                bank_attr = None

    # sets keyframes before snapping
    _all_controls = []
    _all_controls.extend(fk_ctrls)
    _all_controls.extend([ik_ctrl, upv_ctrl, o_attr])
    if ik_rot:
        _all_controls.extend([ik_rot_node])
    if foot_cnx:
        _all_controls.extend(foot_IK_ctls)
        _all_controls.extend(foot_fk)

    # if already keyframe we always set keyframes
    # Comment out:
    # The behavior wasn't clear for user. So now is removed and the user must
    # keyframe or use + key option
    # if not key:
    #     for c in _all_controls:
    #         if pm.keyframe(c, query=True, keyframeCount=True):
    #             key = True
    #             break

    if key:
        [
            cmds.setKeyframe(
                "{}".format(elem), time=(cmds.currentTime(query=True) - 1.0)
            )
            for elem in _all_controls
        ]

    # if is IK then snap FK
    if val == ik_val:

        for target, ctl in zip(fk_targets, fk_ctrls):
            transform.matchWorldTransform(target, ctl)
        pm.setAttr(o_attr, fk_val)
        # we match the foot FK after switch blend attr
        if foot_cnx:
            for i, c in enumerate(foot_fk):
                c.setMatrix(foot_FK_matrix[i], worldSpace=True)

    # if is FK then sanp IK
    elif val == fk_val:
        transform.matchWorldTransform(ik_target, ik_ctrl)
        if ik_rot:
            transform.matchWorldTransform(ik_rot_target, ik_rot_node)
        # NOTE: Simple match replacing the previous logic.
        # Added TODO to researh in the future
        upv_ctrl_target = _get_mth(upv)
        transform.matchWorldTransform(upv_ctrl_target, upv_ctrl)

        # TODO: The following logic is failing with some components. Apparently
        # the control orientation for normal and binormal axis is affecting
        # transform.matchWorldTransform(fk_targets[1], upv_ctrl)
        # # calculates new pole vector position
        # start_end = fk_targets[-1].getTranslation(space="world") - fk_targets[
        #     0
        # ].getTranslation(space="world")
        # start_mid = fk_targets[1].getTranslation(space="world") - fk_targets[
        #     0
        # ].getTranslation(space="world")

        # dot_p = start_mid * start_end
        # proj = float(dot_p) / float(start_end.length())
        # proj_vector = start_end.normal() * proj
        # arrow_vector = start_mid - proj_vector
        # arrow_vector *= start_end.normal().length()

        # thre = 1e-4
        # # handle the case where three points lie on a line.
        # if (
        #     abs(arrow_vector.x) < thre
        #     and abs(arrow_vector.y) < thre
        #     and abs(arrow_vector.z) < thre
        # ):
        #     # can make roll and move up ctrl
        #     upv_ctrl_target = _get_mth(upv)
        #     transform.matchWorldTransform(upv_ctrl_target, upv_ctrl)
        # else:
        #     # ensure that the pole vector distance is a minimun of 1 unit
        #     # while arrow_vector.length() < 1.0:
        #     while arrow_vector.length() < start_mid.length():
        #         arrow_vector *= 2.0

        #     final_vector = arrow_vector + fk_targets[1].getTranslation(
        #         space="world"
        #     )
        #     upv_ctrl.setTranslation(final_vector, space="world")

        # sets blend attribute new value
        pm.setAttr(o_attr, ik_val)

        # handle the upvector roll
        roll_att_name = ikfk_attr.replace("blend", "roll")
        try:
            roll_att = ui_node.attr(roll_att_name)
        except pm.MayaAttributeError:
            # if is not in the uiHost lets check the IK ctl
            roll_att = ik_ctrl.attr(roll_att_name)
        roll_att.set(0.0)

        # match roll ctl to its reference if it exists,
        # otherwise reset rotateX (arm components have no roll_mth)
        if ik_controls and "roll" in ik_controls.keys():
            roll_ctl_node = _get_node(ik_controls["roll"])
            if roll_ctl_node.hasAttr("match_ref"):
                match_nodes = roll_ctl_node.match_ref.listConnections()
                if match_nodes:
                    transform.matchWorldTransform(
                        match_nodes[0], roll_ctl_node
                    )
                else:
                    roll_ctl_node.rotateX.set(0)
            else:
                roll_ctl_node.rotateX.set(0)

        # reset IK foot ctls
        if foot_cnx:
            attribute.reset_SRT(foot_IK_ctls)
            if roll_attr:
                roll_attr.set(0)
                bank_attr.set(0)

        # we match the foot FK after switch blend attr
        if foot_cnx:
            for i, c in enumerate(foot_fk):
                c.setMatrix(foot_FK_matrix[i], worldSpace=True)

        match_fk_to_ik_arbitrary_lengths(fk_ctrls, ui_node,
                                         ikfk_attr, upv_ctrl)

    # sets keyframes
    if key:
        [
            cmds.setKeyframe("{}".format(elem), time=(cmds.currentTime(query=True)))
            for elem in _all_controls
        ]
        if gimbal_exist:
            for x in fks_gimbal + [ik_gimbal]:
                pm.setKeyframe(x, time=(cmds.currentTime(query=True)))
    # cmds.dgdirty(a=True)


def ikFkMatch(model, ikfk_attr, ui_host, fks, ik, upv, ik_rot=None, key=None):
    """Switch IK/FK with matching functionality

    This function is meant to work with 2 joint limbs.
    i.e: human legs or arms

    Args:
        model (PyNode): Rig top transform node
        ikfk_attr (str): Blend ik fk attribute name
        ui_host (str): Ui host name
        fks ([str]): List of fk controls names
        ik (str): Ik control name
        upv (str): Up vector control name
        ikRot (None, str): optional. Name of the Ik Rotation control
        key (None, bool): optional. Whether we do an snap with animation
    """

    # gets namespace
    current_namespace = getNamespace(model)

    ikFkMatch_with_namespace(
        current_namespace,
        ikfk_attr,
        ui_host,
        fks,
        ik,
        upv,
        ik_rot=ik_rot,
        key=key,
    )


# ==============================================================================
# spine ik/fk matching/switching
# ==============================================================================
def spine_IKToFK(fkControls, ikControls, matchMatrix_dict=None):
    """position the IK controls to match, as best they can, the fk controls.
    Supports component: spine_S_shape_01, spine_ik_02

    Args:
        fkControls (list): list of fk controls, IN THE ORDER OF HIERARCHY,
        ["spine_C0_fk0_ctl", ..., ..., "spine_C0_fk6_ctl"]
        ikControls (list): all ik controls
    """
    if matchMatrix_dict is None:
        currentTime = pm.currentTime(q=True)
        matchMatrix_dict = recordNodesMatrices(fkControls, desiredTime=currentTime)

    attribute.reset_SRT(ikControls)

    for fk in fkControls:
        fk = pm.PyNode(fk)
        fk.setMatrix(matchMatrix_dict[fk.name()], worldSpace=True)


def spine_FKToIK(fkControls, ikControls, matchMatrix_dict=None):
    """Match the IK controls to the FK. Known limitations: Does not compensate
    for stretching. Does not support zig-zag, or complex fk to ik transfers.
    Supports component: spine_S_shape_01, spine_ik_02

    Args:
        fkControls (list): of of nodes, IN THE ORDER OF HIERARCHY
        ikControls (list): of of nodes
    """
    # record the position of controls prior to reseting
    if matchMatrix_dict is None:
        currentTime = pm.currentTime(q=True)
        matchMatrix_dict = recordNodesMatrices(fkControls, desiredTime=currentTime)

    # reset both fk, ik controls
    attribute.reset_SRT(ikControls)
    attribute.reset_SRT(fkControls)

    rootFk = fkControls[0]
    endFk = fkControls[-1]
    # get the ik controls sorted from the list provided
    tan1Ctl = [pm.PyNode(ik) for ik in ikControls if TAN1_TOKEN in ik][0]
    tan0Ctl = [pm.PyNode(ik) for ik in ikControls if TAN0_TOKEN in ik][0]

    # get the ik controls sorted from the list provided
    ik1Ctl = [pm.PyNode(ik) for ik in ikControls if END_IK_TOKEN in ik][0]
    ik0Ctl = [pm.PyNode(ik) for ik in ikControls if START_IK_TOKEN in ik][0]

    # optional controls
    ikPosCtl = [pm.PyNode(ik) for ik in ikControls if POS_IK_TOKEN in ik]
    tanCtl = [pm.PyNode(ik) for ik in ikControls if TAN_TOKEN in ik]

    # while the nodes are reset, get the closest counterparts
    if tanCtl:
        closestFk2Tan = getClosestNode(tanCtl[0], fkControls)

    closestFk2Tan1 = getClosestNode(tan1Ctl, fkControls)
    closestFk2Tan0 = getClosestNode(tan0Ctl, fkControls)

    # optional controls if they exist
    if ikPosCtl:
        ikPosCtl[0].setMatrix(matchMatrix_dict[endFk], worldSpace=True)

    # constrain the top and bottom of the ik controls
    ik0Ctl.setMatrix(matchMatrix_dict[rootFk], worldSpace=True)
    ik1Ctl.setMatrix(matchMatrix_dict[endFk], worldSpace=True)

    if tanCtl:
        tanCtl[0].setMatrix(matchMatrix_dict[closestFk2Tan], worldSpace=True)

    # contrain the tan controls
    tan0Ctl.setMatrix(matchMatrix_dict[closestFk2Tan0], worldSpace=True)
    tan1Ctl.setMatrix(matchMatrix_dict[closestFk2Tan1], worldSpace=True)


##################################################
# POSE
##################################################


def get_mirror_target_name(name):
    """Get the long name of the mirror control of a control.

    Standard side names (i.e. "arm_L0_fk0_ctl") are swapped by name. Controls
    with custom side labels use their side_label attributes. Center controls
    are their own mirror. The control's namespace is kept.

    Args:
        name (str): Control name.

    Returns:
        str: Mirror control long name, None if it doesn't exist.
    """
    short_name = name.split("|")[-1]
    namespace = getNamespace(short_name)
    base_name = stripNamespace(short_name)
    swapped = swapSideLabel(base_name)
    if swapped == base_name:
        side_plug = "{}.side_label".format(name)
        if not cmds.objExists(side_plug) or cmds.getAttr(side_plug) not in "LR":
            # center control mirrors onto itself
            return (cmds.ls(name, long=True) or [None])[0]
        swapped = swapSideLabelNode(name)
    target = "{}:{}".format(namespace, swapped) if namespace else swapped
    return (cmds.ls(target, long=True) or [None])[0]


def getMirrorTarget(nameSpace=None, node=None):
    """Find target control to apply mirroring.

    Args:
        nameSpace (str): Namespace. Defaults to the namespace of the node.
        node (PyNode): Node to mirror

    Returns:
        PyNode: Mirror target, None when the side control has no
            counterpart.
    """
    if not node:
        return
    name = str(node)
    if nameSpace:
        name = "{}:{}".format(nameSpace, stripNamespace(name.split("|")[-1]))
    target = get_mirror_target_name(name)
    return getNode(target) if target else None


def mirrorPose(flip=False, nodes=None, key=None):
    """Mirror or flip the pose of controls.

    Same as mirror_controls, defaulting to the selected controls, and it
    shows what it keyed in the viewport.

    Args:
        flip (bool, options): Set the function behaviour to flip
        nodes (None,  [PyNode]): Controls to mirro/flip the pose
        key (bool, optional): Key the values set, see ``mirror_controls``.
    """
    if nodes is None:
        nodes = pm.selected()
    if not nodes:
        return
    show_mirror_message(mirror_controls(nodes, flip=flip, key=key))


def applyMirror(nameSpace, mirrorEntry):
    """Apply mirror pose

    Args:
        nameSpace (str): Namespace
        mirrorEntry (list): List with the mirror entry template
    """

    node = mirrorEntry["target"]
    attr = mirrorEntry["attr"]
    val = mirrorEntry["val"]

    for skip in NO_MIRROR_ATTRIBUTES:
        if attr.count(skip):
            return

    try:
        if (
            pm.attributeQuery(attr, node=node, shortName=True, exists=True)
            and not node.attr(attr).isLocked()
        ):
            node.attr(attr).set(val)

    except RuntimeError as e:
        mgear.log(
            "applyMirror failed: {0} {1}: {2}".format(node.name(), attr, e),
            mgear.sev_error,
        )


def calculateMirrorData(srcNode, targetNode, flip=False):
    """Calculate the mirror data

    Args:
        srcNode (str): The source Node
        targetNode ([dict[str]]): Target node
        flip (bool, optional): flip option

    Returns:
        [{"target": node, "attr": at, "val": flipVal}]
    """
    results = []

    # mirror attribute of source
    for attrName in listAttrForMirror(srcNode):

        # whether does attribute "invTx" exists when attrName is "tx"
        invCheckName = getInvertCheckButtonAttrName(attrName)
        if not pm.attributeQuery(
            invCheckName, node=srcNode, shortName=True, exists=True
        ):

            # if not exists, straight
            inv = 1

        else:
            # if exists, check its value
            invAttr = srcNode.attr(invCheckName)
            if invAttr.get():
                inv = -1
            else:
                inv = 1

        # if attr name is side specified, record inverted attr name
        if isSideElement(attrName):
            invAttrName = swapSideLabel(attrName)
        else:
            invAttrName = attrName

        # if flip enabled record self also
        if flip:
            flipVal = targetNode.attr(attrName).get()
            results.append(
                {"target": srcNode, "attr": invAttrName, "val": flipVal * inv}
            )

        results.append(
            {
                "target": targetNode,
                "attr": invAttrName,
                "val": srcNode.attr(attrName).get() * inv,
            }
        )
    return results


# Mirror pose -----------------------------------------------------------------


def get_control_side(node):
    """Get the side of a control.

    Uses the side_label attribute of the control when it has one, else the
    Shifter naming (i.e: "arm_L0_fk0_ctl").

    Args:
        node (str or PyNode): Control.

    Returns:
        str: "L" or "R", None for center controls.
    """
    node = str(node)
    if cmds.objExists("{}.side_label".format(node)):
        side = cmds.getAttr("{}.side_label".format(node))
        return side if side in ("L", "R") else None
    name = stripNamespace(node.split("|")[-1])
    for part in name.split("_"):
        if EXPR_LEFT_SIDE.match(part):
            return "L"
        if EXPR_RIGHT_SIDE.match(part):
            return "R"
    if "_L_" in name:
        return "L"
    if "_R_" in name:
        return "R"
    return None


_MIRROR_TRANSFORM_ATTRS = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "ro")
_MIRROR_INT_TYPES = frozenset(
    (
        om2.MFnNumericData.kBoolean,
        om2.MFnNumericData.kByte,
        om2.MFnNumericData.kChar,
        om2.MFnNumericData.kShort,
        om2.MFnNumericData.kInt,
        om2.MFnNumericData.kLong,
        om2.MFnNumericData.kInt64,
    )
)
_MIRROR_FLOAT_TYPES = frozenset((om2.MFnNumericData.kFloat, om2.MFnNumericData.kDouble))


def _get_dependency_node(name, cache):
    """Get a cached MFnDependencyNode of a node.

    Args:
        name (str): Node name.
        cache (dict): Name to MFnDependencyNode cache.

    Returns:
        MFnDependencyNode: The function set.
    """
    if name not in cache:
        cache[name] = utils.get_dependency_node(name)
    return cache[name]


def _plug_value(plug):
    """Get the value of a plug to mirror, in Maya UI units.

    The value is the one cmds.getAttr returns.

    Args:
        plug (MPlug): The plug.

    Returns:
        float or int: The value, None for plugs that can't be mirrored (not
            a single numeric, enum, distance, angle or time value).
    """
    if plug.isCompound or plug.isArray:
        return None
    attr = plug.attribute()
    if attr.hasFn(om2.MFn.kUnitAttribute):
        unit_type = om2.MFnUnitAttribute(attr).unitType()
        if unit_type == om2.MFnUnitAttribute.kAngle:
            return plug.asMAngle().asUnits(om2.MAngle.uiUnit())
        if unit_type == om2.MFnUnitAttribute.kDistance:
            return plug.asMDistance().asUnits(om2.MDistance.uiUnit())
        if unit_type == om2.MFnUnitAttribute.kTime:
            return plug.asMTime().asUnits(om2.MTime.uiUnit())
        return plug.asDouble()
    if attr.hasFn(om2.MFn.kEnumAttribute):
        return plug.asInt()
    if attr.hasFn(om2.MFn.kNumericAttribute):
        numeric_type = om2.MFnNumericAttribute(attr).numericType()
        if numeric_type in _MIRROR_INT_TYPES:
            return plug.asInt()
        if numeric_type in _MIRROR_FLOAT_TYPES:
            return plug.asDouble()
    return None


def _get_mirror_channels(node, fn_cache):
    """Get the channels of a control to mirror, with their inversion.

    Same channels as listAttrForMirror and calculateMirrorData: the
    transform channels and the user attributes, without the inv*
    attributes, the NO_MIRROR_ATTRIBUTES and the non numeric attributes.

    Args:
        node (str): Control long name.
        fn_cache (dict): Name to MFnDependencyNode cache.

    Returns:
        list: (attribute short name, MPlug, 1 or -1) tuples.
    """
    fn = _get_dependency_node(node, fn_cache)
    user_attrs = cmds.listAttr(node, userDefined=True, shortNames=True) or []
    user_set = set(user_attrs)
    channels = []
    for attr in _MIRROR_TRANSFORM_ATTRS + tuple(user_attrs):
        if attr.startswith("inv"):
            continue
        if any(skip in attr for skip in NO_MIRROR_ATTRIBUTES):
            continue
        try:
            plug = fn.findPlug(attr, False)
        except RuntimeError:
            continue
        if _plug_value(plug) is None:
            continue
        inv = 1
        inv_attr = getInvertCheckButtonAttrName(attr)
        if inv_attr in user_set and fn.findPlug(inv_attr, False).asBool():
            inv = -1
        channels.append((attr, plug, inv))
    return channels


def _mirror_values(source, target, fn_cache, channels, swapped_attrs):
    """Yield the values mirrored from a control onto its mirror target.

    Target channels that are missing, locked or not numeric are skipped.

    Args:
        source (str): Control long name to read.
        target (str): Mirror control long name to write.
        fn_cache (dict): Name to MFnDependencyNode cache.
        channels (dict): Control to mirror channels cache.
        swapped_attrs (dict): Attribute to side-swapped attribute cache.

    Yields:
        tuple: ``(target attribute, target MPlug, current, mirrored)``.
    """
    if source not in channels:
        channels[source] = _get_mirror_channels(source, fn_cache)
    target_fn = _get_dependency_node(target, fn_cache)
    for attr, plug, inv in channels[source]:
        if attr not in swapped_attrs:
            swapped_attrs[attr] = swapSideLabel(attr)
        target_attr = swapped_attrs[attr]
        try:
            target_plug = target_fn.findPlug(target_attr, False)
        except RuntimeError:
            continue
        if target_plug.isLocked:
            continue
        current = _plug_value(target_plug)
        if current is None:
            continue
        yield target_attr, target_plug, current, _plug_value(plug) * inv


def _mirror_plan(nodes, flip=False):
    """Compute the mirror values of controls before any value is set.

    Each control finds its mirror target in its own namespace. A center
    control is its own target, so mirroring inverts it. Only the values that
    change are kept. Target channels that are missing, locked or driven
    (constraints, expressions, driven keys) are skipped; keyed channels get
    the value like setting it by hand, and channels on animation layers are
    keyed with it, like ``set_or_key``. See ``plug_state``. A control that
    fails is logged and skipped.

    Args:
        nodes (list): Controls, str or PyNode.
        flip (bool, optional): Also mirror each target back onto its
            control when the target is not in the list.

    Returns:
        tuple: The (target long name, attribute, value) entries to set, the
            entries on animation layers (set by keying them), and the long
            names of the controls and targets whose mirror channels are
            keyed or layered.
    """
    if not nodes:
        return [], [], set()
    names = cmds.ls([str(n) for n in nodes], long=True, type="transform")
    in_list = set(names)
    fn_cache = {}
    channels = {}
    entries = []
    no_target = []
    layered = []
    animated = set()
    swapped_attrs = {}
    animated_states = (PLUG_KEYED, PLUG_LAYERED)

    def add_entries(source, target):
        for target_attr, target_plug, current, value in _mirror_values(
            source, target, fn_cache, channels, swapped_attrs
        ):
            state = plug_state(target_plug)
            if state == PLUG_DRIVEN:
                continue
            if state in animated_states:
                animated.add(target)
            if abs(current - value) > 1e-9:
                entry = (target, target_attr, value)
                (layered if state == PLUG_LAYERED else entries).append(entry)
        if source not in animated and any(
            plug_state(plug) in animated_states
            for _, plug, _ in channels.get(source, ())
        ):
            animated.add(source)

    for name in names:
        try:
            target = get_mirror_target_name(name)
            if target is None:
                no_target.append(name.split("|")[-1])
                continue
            add_entries(name, target)
            if flip and target not in in_list:
                add_entries(target, name)
        except Exception as e:
            mgear.log(
                "Mirror: skipped {}: {}".format(name.split("|")[-1], e),
                mgear.sev_warning,
            )
    if no_target:
        mgear.log(
            "Mirror: skipped {} controls without a mirror control: {}".format(
                len(no_target), ", ".join(no_target)
            ),
            mgear.sev_warning,
        )
    return entries, layered, animated


def _mirror_entries(nodes, flip=False):
    """Compute the mirror values of controls, see ``_mirror_plan``.

    Args:
        nodes (list): Controls, str or PyNode.
        flip (bool, optional): Also mirror each target back onto its
            control when the target is not in the list.

    Returns:
        list: (target long name, attribute, value) tuples, the layered
            channels included.
    """
    entries, layered, _ = _mirror_plan(nodes, flip)
    return entries + layered


def _apply_mirror_entries(entries, key=False, layered=()):
    """Apply mirror entries in one undo step.

    An entry that fails is logged and skipped, the others are still applied.

    Args:
        entries (list): (target, attribute, value) tuples to set.
        key (bool, optional): Also key every value set, at the current
            frame.
        layered (list, optional): Entries on animation layers: keyed with
            their value when ``key`` is on, else skipped.

    Returns:
        list: The long names of the controls keyed, one per channel keyed.
    """
    failed = []
    written = []
    keyed = []
    with utils.undo_chunk("mgearMirrorPose"):
        for target, attr, value in entries:
            plug = "{}.{}".format(target, attr)
            try:
                cmds.setAttr(plug, value)
                written.append((target, plug))
            except Exception as e:
                failed.append("{} ({})".format(plug.split("|")[-1], e))
        if key and written:
            try:
                cmds.setKeyframe([plug for _, plug in written])
                keyed.extend(target for target, _ in written)
            except Exception:
                # one by one, to tell which channel can't be keyed
                for target, plug in written:
                    try:
                        cmds.setKeyframe(plug)
                        keyed.append(target)
                    except Exception as e:
                        failed.append("{} (key: {})".format(plug.split("|")[-1], e))
        layer_keyed = []
        for target, attr, value in layered if key else ():
            plug = "{}.{}".format(target, attr)
            try:
                cmds.setKeyframe(plug, value=value)
                keyed.append(target)
                layer_keyed.append(plug)
            except Exception as e:
                failed.append("{} (layer key: {})".format(plug.split("|")[-1], e))
        refresh_keyed(layer_keyed)
    if failed:
        mgear.log(
            "Mirror: could not set {} attributes: {}".format(
                len(failed), ", ".join(failed[:20])
            ),
            mgear.sev_warning,
        )
    return keyed


def _mirror_and_apply(nodes, flip=False, key=None):
    """Mirror controls, keying the values set when asked or when the pose is
    animated.

    Args:
        nodes (list): Controls, str or PyNode.
        flip (bool, optional): Flip instead of mirror.
        key (bool, optional): Key the values set; None keys them when any
            of the controls or their counterparts is keyed or layered.

    Returns:
        dict: See ``mirror_controls``.
    """
    entries, layered, animated = _mirror_plan(nodes, flip=flip)
    if key is None:
        key = bool(animated)
    keyed = _apply_mirror_entries(entries, key=key, layered=layered)
    controls = set(keyed)
    result = {
        "keyed": len(keyed),
        "controls": len(controls),
        "new": len(controls - animated),
        "layered_skipped": 0 if key else len(layered),
    }
    if result["layered_skipped"]:
        mgear.log(
            "Mirror: skipped {} channel(s) on animation layers: they change "
            "only by keying them".format(result["layered_skipped"]),
            mgear.sev_warning,
        )
    return result


def mirror_message(result):
    """Get the viewport message of a mirror or flip that keyed values.

    Args:
        result (dict): What ``mirror_controls`` returned.

    Returns:
        str: The message with ``<hl>`` highlights, or empty when nothing
            was keyed.
    """
    if not result or not result.get("keyed"):
        return ""
    newly = result.get("new")
    return "Mirror keyed <hl>{}</hl> channel(s) of <hl>{}</hl> control(s){}".format(
        result["keyed"],
        result["controls"],
        ", <hl>{}</hl> of them had no keys yet".format(newly) if newly else "",
    )


def show_mirror_message(result):
    """Show what a mirror or flip keyed in the viewport; nothing when it
    keyed nothing.

    Args:
        result (dict): What ``mirror_controls`` returned.

    Returns:
        dict: The result, so a call can wrap a mirror.
    """
    message = mirror_message(result)
    if message:
        utils.viewport_message(message)
    return result


def mirror_controls(nodes, flip=False, key=None):
    """Mirror or flip the pose of controls, in one undo step.

    All the values are read before any value is set, so a left/right pair
    in the list is computed from the original pose. Mirroring both sides of
    a pair swaps them, the same as a flip. Center controls are inverted.
    Controls of several rigs (namespaces) can be mixed.

    Args:
        nodes (list): Controls, str or PyNode.
        flip (bool, optional): Flip instead of mirror. The controls whose
            counterpart is not in the list are swapped with it.
        key (bool, optional): Key the values set at the current frame.
            None (the default) keys them when any of the controls or their
            counterparts is keyed or on an animation layer on the mirrored
            channels; False never keys.

    Returns:
        dict: ``keyed`` (channels keyed), ``controls`` (controls keyed),
            ``new`` (keyed controls that had no keys yet) and
            ``layered_skipped`` (channels on animation layers left
            unchanged because keying was off). Show it with
            ``show_mirror_message``.
    """
    return _mirror_and_apply(nodes, flip=flip, key=key)


def mirror_side(nodes, source_side, key=None):
    """Mirror the pose of one side of the controls to the other side.

    The controls of the source side are copied to their counterparts and
    the center controls are inverted. The controls of the other side only
    receive values.

    Args:
        nodes (list): Controls, str or PyNode.
        source_side (str): "L" or "R".
        key (bool, optional): Key the values set, see ``mirror_controls``.

    Returns:
        dict: See ``mirror_controls``.
    """
    sources = [n for n in nodes if get_control_side(n) in (source_side, None)]
    return _mirror_and_apply(sources, key=key)


def get_set_members(sets):
    """Get the members of object sets, including the members of sub-sets.

    Args:
        sets (list): Object sets.

    Returns:
        list: Member names without the sets, without duplicates.
    """
    members = []
    seen = set()
    pending = list(sets)
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        for member in cmds.sets(current, query=True) or []:
            if cmds.objectType(member, isAType="objectSet"):
                pending.append(member)
            elif member not in seen:
                seen.add(member)
                members.append(member)
    return members


def get_rig_controls(node):
    """Get the controls of the rig of a node.

    Uses the rig controllers set, else the object sets connected to the
    node. Controls in sub-sets (i.e. Shifter control sub-groups) are
    included.

    Args:
        node (str or PyNode): Any node of the rig.

    Returns:
        list: Control names.
    """
    node = str(node)
    root = _find_rig_root_path(node)
    if root:
        ctl_set = root.split("|")[-1] + CTRL_GRP_SUFFIX
        if cmds.objExists(ctl_set):
            return get_set_members([ctl_set])
    return get_set_members(cmds.ls(cmds.listConnections(node) or [], type="objectSet"))


def _get_rig_sub_sets(root):
    """Get the sets directly inside the controllers set of a rig.

    Args:
        root (str): Rig top node.

    Returns:
        dict: Short label (i.e. "face") to object set name.
    """
    root_name = stripNamespace(root.split("|")[-1])
    ctl_set = root.split("|")[-1] + CTRL_GRP_SUFFIX
    if not cmds.objExists(ctl_set):
        return {}
    sub_sets = {}
    for member in cmds.sets(ctl_set, query=True) or []:
        if not cmds.objectType(member, isAType="objectSet"):
            continue
        label = stripNamespace(member)
        if label.startswith(root_name + "_"):
            label = label[len(root_name) + 1 :]
        if label.endswith("_grp"):
            label = label[: -len("_grp")]
        sub_sets[label] = member
    return sub_sets


def get_rig_control_sets(nodes):
    """Get the control sets of the rigs of the nodes.

    These are the sets directly inside each rig controllers set (Shifter
    control sub-groups), named without the rig prefix and the "_grp"
    suffix. Sets with the same name in several rigs are listed once.

    Args:
        nodes (list): Any nodes of the rigs.

    Returns:
        list: Control set labels. i.e: ["face", "body"]
    """
    # one node per namespace is enough to find the rigs, and much faster
    # with large selections
    samples = {}
    for node in nodes:
        samples.setdefault(getNamespace(str(node).split("|")[-1]), node)
    labels = []
    for root in get_rig_roots(samples.values()):
        for label in _get_rig_sub_sets(root):
            if label not in labels:
                labels.append(label)
    return labels


def get_rig_roots(nodes):
    """Get the unique rig top nodes of the nodes.

    Args:
        nodes (list): Any nodes, str or PyNode.

    Returns:
        list: Full paths of the rig top nodes, in the order found.
    """
    roots = [_find_rig_root_path(str(node)) for node in nodes]
    return list(dict.fromkeys(r for r in roots if r))


def _get_full_pose_controls(nodes, control_set=None):
    """Get the controls of every rig with one of the nodes.

    Args:
        nodes (list): Any nodes of the rigs.
        control_set (str, optional): Only the controls of this control set
            label of each rig. See get_rig_control_sets.

    Returns:
        list: Control names.
    """
    controls = []
    for root in get_rig_roots(nodes):
        if control_set is None:
            controls.extend(get_rig_controls(root))
            continue
        sub_set = _get_rig_sub_sets(root).get(control_set)
        if sub_set:
            controls.extend(get_set_members([sub_set]))
    return controls


def mirror_full_pose(nodes, source_side="L", control_set=None):
    """Mirror the full pose of the rigs from one side to the other.

    Args:
        nodes (list): Any nodes of the rigs to mirror.
        source_side (str, optional): "L" or "R", the side to copy.
        control_set (str, optional): Only mirror the controls of this
            control set (i.e. "face"). See get_rig_control_sets.

    Returns:
        dict: See ``mirror_controls``.
    """
    return mirror_side(_get_full_pose_controls(nodes, control_set), source_side)


def flip_full_pose(nodes, control_set=None):
    """Flip the full pose of the rigs.

    Args:
        nodes (list): Any nodes of the rigs to flip.
        control_set (str, optional): Only flip the controls of this control
            set (i.e. "face"). See get_rig_control_sets.

    Returns:
        dict: See ``mirror_controls``.
    """
    return mirror_controls(_get_full_pose_controls(nodes, control_set), flip=True)


def mirrorPoseOld(flip=False, nodes=False):
    """Deprecated: Mirror pose

    Args:
        flip (bool, optional): if True will flip the pose
        nodes (bool, optional): Nodes to mirror or flip transformation
    """
    axis = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
    aDic = {
        "tx": "invTx",
        "ty": "invTy",
        "tz": "invTz",
        "rx": "invRx",
        "ry": "invRy",
        "rz": "invRz",
        "sx": "invSx",
        "sy": "invSy",
        "sz": "invSz",
    }

    mapDic = {"L": "R", "R": "L"}
    if not nodes:
        nodes = pm.selected()
    pm.undoInfo(ock=1)
    try:
        nameSpace = False
        if nodes:
            if len(nodes[0].split(":")) == 2:
                nameSpace = nodes[0].split(":")[0]
        for oSel in nodes:
            if nameSpace:
                nameParts = oSel.name().split(":")[1].split("|")[-1].split("_")
            else:
                nameParts = oSel.name().split("|")[-1].split("_")

            if nameParts[1][0] == "C":
                if not oSel.attr("tx").isLocked():
                    oSel.attr("tx").set(oSel.attr("tx").get() * -1)
                if not oSel.attr("ry").isLocked():
                    oSel.attr("ry").set(oSel.attr("ry").get() * -1)
                if not oSel.attr("rz").isLocked():
                    oSel.attr("rz").set(oSel.attr("rz").get() * -1)
            else:
                nameParts[1] = mapDic[nameParts[1][0]] + nameParts[1][1:]
                if nameSpace:
                    nameTarget = nameSpace + ":" + "_".join(nameParts)
                else:
                    nameTarget = "_".join(nameParts)
                oTarget = getNode(nameTarget)
                for a in axis:
                    if not oSel.attr(a).isLocked():
                        if oSel.attr(aDic[a]).get():
                            inv = -1
                        else:
                            inv = 1
                        if flip:
                            flipVal = oTarget.attr(a).get()

                        oTarget.attr(a).set(oSel.attr(a).get() * inv)

                        if flip:
                            oSel.attr(a).set(flipVal * inv)
    except Exception:
        pm.displayWarning("Flip/Mirror pose fail")
        pass
    finally:
        pm.undoInfo(cck=1)


def bindPose(model, *args):
    """Restore the reset position of the rig

    Args:
        model (TYPE): Description
    """
    if isinstance(model, pm.node._NodeTypes):
        model = bindPose

    nameSpace = getNamespace(model)
    if nameSpace:
        dagPoseName = nameSpace + ":dagPose1"
    else:
        dagPoseName = "dagPose1"
    pm.dagPose(dagPoseName, restore=True)


def resetSelTrans():
    """Reset the transfom values (SRT) for the selected objects"""
    with pm.UndoChunk():
        for obj in pm.selected():
            transform.resetTransform(obj)


@contextmanager
def default_pose(nodes):
    """Context manager - Put nodes at their default values for the block.

    The keyable, unlocked channels of the nodes are set to their default
    value, and the changed ones are set back on exit, even if the block
    raises. Channels that can't be set (i.e. connected) are left alone.
    Nothing is recorded in the undo queue.

    Args:
        nodes (list): Transforms, i.e. all the controls of a rig.

    Example:
        >>> with default_pose(get_rig_controls("rig")):
        ...     matrix = cmds.getAttr("arm_L0_fk0_ctl.worldMatrix")
    """
    names = cmds.ls([str(n) for n in nodes], long=True, type="transform") or []
    changed = []
    with utils.undo_disabled():
        try:
            for node in dict.fromkeys(names):
                attrs = cmds.listAttr(node, keyable=True, unlocked=True, scalar=True)
                for attr in attrs or []:
                    plug = "{}.{}".format(node, attr)
                    try:
                        value = cmds.getAttr(plug)
                        default = cmds.attributeQuery(
                            attr, node=node, listDefault=True
                        )
                        if not default or value == default[0]:
                            continue
                        cmds.setAttr(plug, default[0])
                    except (RuntimeError, ValueError):
                        continue
                    changed.append((plug, value))
            yield
        finally:
            for plug, value in reversed(changed):
                try:
                    cmds.setAttr(plug, value)
                except RuntimeError:
                    continue


def reset_all_keyable_attributes(dagnodes, *args):  # @unusedVariable
    """Resets to default values all keyable attributes on the given node

    Args:
        dagnodes (list): Maya transform nodes to reset
        *args: State of the menu item (if existing) send by mgear's dagmenu
    """

    for node in dagnodes:
        keyable_attrs = cmds.listAttr(node, keyable=True)
        reset_selected_channels_value([node], keyable_attrs)


##################################################
# Transfer space
##################################################
class AbstractAnimationTransfer(QtWidgets.QDialog):
    """Abstract animation transfer class"""

    try:
        valueChanged = QtCore.Signal(int)
    except Exception:
        valueChanged = pyqt.pyqtSignal()

    def __init__(self):
        # type = () -> None

        self.comboObj = None  # type = widgets.toggleCombo
        self.comboItems = []  # type = list[str]
        self.model = None  # type = pm.nodetypes.Transform
        self.uihost = None  # type = str
        self.switchedAttrShortName = None  # type = str
        self.combo_idx = 0

    def createUI(self, parent=None):
        # type = (QtWidgets.QObject) -> None

        super(AbstractAnimationTransfer, self).__init__(parent)

        self.setWindowTitle("Space Transfer")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):
        # type = () -> None

        self.groupBox = QtWidgets.QGroupBox()

        # must be implemented in each specialized classes
        self.setGroupBoxTitle()

        self.onlyKeyframes_check = QtWidgets.QCheckBox("Only Keyframe Frames")
        self.onlyKeyframes_check.setChecked(True)
        self.startFrame_label = QtWidgets.QLabel("Start")
        self.startFrame_value = QtWidgets.QSpinBox()
        self.startFrame_value = QtWidgets.QSpinBox()
        self.startFrame_value.setMinimum(-999999)
        self.startFrame_value.setMaximum(999999)
        self.endFrame_label = QtWidgets.QLabel("End")
        self.endFrame_value = QtWidgets.QSpinBox()
        self.endFrame_value.setMinimum(-999999)
        self.endFrame_value.setMaximum(999999)
        self.populateRange(True)
        self.allFrames_button = QtWidgets.QPushButton("All Frames")
        self.timeSliderFrames_button = QtWidgets.QPushButton("Time Slider Frames")

        self.comboBoxSpaces = QtWidgets.QComboBox()
        self.comboBoxSpaces.addItems(self.comboItems)
        if self.comboObj is not None:
            # this add suport QlistWidget
            if isinstance(self.comboObj, QtWidgets.QListWidget):
                idx = self.comboObj.currentRow()
            elif isinstance(self.comboObj, (list, tuple)):
                idx = self.combo_idx
            else:
                idx = self.comboObj.currentIndex()
            self.comboBoxSpaces.setCurrentIndex(idx)

        self.spaceTransfer_button = QtWidgets.QPushButton("Space Transfer")

    def create_layout(self):
        # type = () -> None

        frames_layout = QtWidgets.QHBoxLayout()
        frames_layout.setContentsMargins(1, 1, 1, 1)
        frames_layout.addWidget(self.startFrame_label)
        frames_layout.addWidget(self.startFrame_value)
        frames_layout.addWidget(self.endFrame_label)
        frames_layout.addWidget(self.endFrame_value)

        framesSetter_layout = QtWidgets.QHBoxLayout()
        framesSetter_layout.setContentsMargins(1, 1, 1, 1)
        framesSetter_layout.addWidget(self.allFrames_button)
        framesSetter_layout.addWidget(self.timeSliderFrames_button)

        paremeter_layout = QtWidgets.QVBoxLayout(self.groupBox)
        paremeter_layout.setContentsMargins(6, 5, 6, 5)
        paremeter_layout.addWidget(self.onlyKeyframes_check)
        paremeter_layout.addLayout(frames_layout)
        paremeter_layout.addLayout(framesSetter_layout)
        paremeter_layout.addWidget(self.comboBoxSpaces)
        paremeter_layout.addWidget(self.spaceTransfer_button)

        spaceTransfer_layout = QtWidgets.QVBoxLayout()
        spaceTransfer_layout.addWidget(self.groupBox)

        self.setLayout(spaceTransfer_layout)

    def create_connections(self):
        # type = () -> None

        self.spaceTransfer_button.clicked.connect(self.doItByUI)
        self.allFrames_button.clicked.connect(partial(self.populateRange, False))
        self.timeSliderFrames_button.clicked.connect(partial(self.populateRange, True))

    # SLOTS ##########################################################

    def populateRange(self, timeSlider=False):
        # type = (bool) -> None
        if timeSlider:
            start = pm.playbackOptions(q=True, min=True)
            end = pm.playbackOptions(q=True, max=True)
        else:
            start = pm.playbackOptions(q=True, ast=True)
            end = pm.playbackOptions(q=True, aet=True)
        self.startFrame_value.setValue(start)
        self.endFrame_value.setValue(end)

    def setComboBoxItemsFormComboObj(self, combo):
        # type = (widegts.toggleCombo or QtWidgets.QListWidget) -> None

        del self.comboItems[:]
        if isinstance(combo, (list, tuple)):
            for itm in combo:
                self.comboItems.append(str(itm))
            return

        for i in range(combo.count() - 1):
            # this add suport QlistWidget
            if isinstance(combo, QtWidgets.QListWidget):
                self.comboItems.append(combo.item(i).text())
            else:
                self.comboItems.append(combo.itemText(i))

    def setComboBoxItemsFormList(self, comboList):
        # type = (list[str]) -> None

        del self.comboItems[:]
        for i in range(len(comboList)):
            self.comboItems.append(comboList[i])

    # ----------------------------------------------------------------

    def setGroupBoxTitle(self):
        # type = (str) -> None
        # raise NotImplementedError("must implement transfer
        # in each specialized class")
        pass

    def setComboObj(self, combo):
        # type = (widgets.toggleCombo) -> None
        self.comboObj = combo

    def setModel(self, model):
        # type = (pm.nodetypes.Transform) -> None
        self.model = model
        self.nameSpace = getNamespace(self.model)

    def setUiHost(self, uihost):
        # type = (str) -> None
        self.uihost = uihost

    def setSwitchedAttrShortName(self, attr):
        # type = (str) -> None
        self.switchedAttrShortName = attr

    def getHostName(self):
        # type = () -> str
        return ":".join([self.nameSpace, self.uihost])

    def getWorldMatrices(self, start, end, val_src_nodes):
        # type = (int, int, List[pm.nodetypes.Transform]) ->
        # List[List[pm.datatypes.Matrix]]
        """returns matrice List[frame][controller number]."""
        res = []
        for idx, x in enumerate(range(start, end + 1)):
            tmp = []
            for n in val_src_nodes:
                if n:
                    tmp.append(cmds.getAttr(n + ".worldMatrix", time=x))
                else:
                    tmp.append(None)
            res.append(tmp)
        return res

    def transfer(self, startFrame, endFrame, onlyKeyframes, *args, **kwargs):
        # type = (int, int, bool, *str, **str) -> None
        raise NotImplementedError("must be implemented in each " "specialized class")

    def doItByUI(self):
        # type = () -> None

        # gather settings from UI
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # main body
        self.transfer(startFrame, endFrame, onlyKeyframes)

        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            if isinstance(self.comboObj, QtWidgets.QComboBox):
                self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(
        self,
        switch_attr_name,
        val_src_nodes,
        key_src_nodes,
        key_dst_nodes,
        startFrame,
        endFrame,
        onlyKeyframes=True,
        definition="",
    ):

        # type = (str, List[pm.nodetypes.Transform],
        # List[pm.nodetypes.Transform],
        # List[pm.nodetypes.Transform], int, int, bool) -> None

        # Temporaly turn off cycle check to avoid misleading cycle message
        # on Maya 2016.  With Maya 2016.5 and 2017 the cycle warning doesn't
        # show up
        # if versions.current() <= 20180200:
        pm.cycleCheck(e=False)
        # pm.displayWarning(
        #     "Maya version older than: 2016.5: " "CycleCheck temporal turn OFF"
        # )

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        # right here we need to generate the matrix positions by calculating
        # them if we have 3 fk controls.  Once we've grabbed the solved
        # pole vector positions, we'll insert them into the list by passing
        # them into the getWorldMatrix function.
        # Doing it thisway should be safe as we've touched the least amount
        # of code.
        worldMatrixList = self.getWorldMatrices(
            startFrame, endFrame, val_src_nodes)

        src_keys = pm.keyframe(key_src_nodes, at=["t", "r", "s"], q=True)
        if not src_keys:
            src_keys = []
        keyframeList = sorted(set(src_keys))
        # if src_keys:

        #     keyframeList = sorted(set(src_keys))
        # else:
        #     pm.displayWarning("No keys to transfer.")
        #     return

        # delete animation in the space switch channel and destination ctrls
        pm.cutKey(key_dst_nodes, at=channels, time=(startFrame, endFrame))
        pm.cutKey(switch_attr_name, time=(startFrame, endFrame))

        for i, x in enumerate(range(startFrame, endFrame + 1)):

            if onlyKeyframes and x not in keyframeList:
                continue

            pm.currentTime(x)

            # set the new space in the channel
            self.changeAttrToBoundValue()

            # bake the stored transforms to the cotrols
            for j, n in enumerate(key_dst_nodes):
                if worldMatrixList[i][j]:
                    n.setMatrix(worldMatrixList[i][j], worldSpace=True)
            if definition == "IK":
                match_fk_to_ik_arbitrary_lengths(key_src_nodes, switch_attr_name.split(".")[0],
                                                 switch_attr_name.split(".")[1], key_dst_nodes[1])

            pm.setKeyframe(key_dst_nodes, at=channels)
            pm.setKeyframe(switch_attr_name)

        # if versions.current() <= 20180200:
        pm.cycleCheck(e=True)
        # pm.displayWarning("CycleCheck turned back ON")


# ================================================
# Transfer space


class ParentSpaceTransfer(AbstractAnimationTransfer):
    def __init__(self):
        # type = () -> None
        super(ParentSpaceTransfer, self).__init__()

    # ----------------------------------------------------------------

    def setCtrls(self, srcName):
        # type = (str) -> None
        self.ctrlNode = getNode(":".join([self.nameSpace, srcName]))

    def getChangeAttrName(self):
        # type = () -> str
        return "{}.{}".format(self.getHostName(), self.switchedAttrShortName)

    def changeAttrToBoundValue(self):
        # type = () -> None
        pm.setAttr(self.getChangeAttrName(), self.getValue())

    def getValue(self):
        # type = () -> int
        return self.comboBoxSpaces.currentIndex()

    def setGroupBoxTitle(self):
        if hasattr(self, "groupBox"):
            # TODO: extract logic with naming convention
            part = "_".join(self.ctrlNode.name().split(":")[-1].split("_")[:-1])
            self.groupBox.setTitle(part)

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(
        self,
        switch_attr_name,
        val_src_nodes,
        key_src_nodes,
        key_dst_nodes,
        startFrame,
        endFrame,
        onlyKeyframes=True,
        definition="",
    ):

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

        src_keys = pm.keyframe(key_src_nodes, at=["t", "r", "s"], q=True)
        if not src_keys:
            src_keys = []
        keyframeList = sorted(set(src_keys))
        # if src_keys:

        #     keyframeList = sorted(set(src_keys))
        # else:
        #     pm.displayWarning("No keys to transfer.")
        #     return

        # get world transform data for the source nodes
        # and store them in a list for each frame
        world_transform_data = []
        for i, x in enumerate(range(startFrame, endFrame + 1)):
            world_transform_data_frame = []
            if onlyKeyframes and x not in keyframeList:
                world_transform_data.append([])
                continue

            pm.currentTime(x)
            for j, n in enumerate(val_src_nodes):
                world_transform_data_frame.append(transform.get_world_transform_data(n))

            world_transform_data.append(world_transform_data_frame)
        # delete animation in the space switch channel and destination ctrls
        pm.cutKey(key_dst_nodes, at=channels, time=(startFrame, endFrame))
        pm.cutKey(switch_attr_name, time=(startFrame, endFrame))

        # set world transform data to the destination nodes
        # and set keyframes for the switch attribute
        for i, x in enumerate(range(startFrame, endFrame + 1)):

            if onlyKeyframes and x not in keyframeList:
                continue

            pm.currentTime(x)

            # set the new space in the channel
            self.changeAttrToBoundValue()

            # bake the stored transforms to the cotrols
            for j, n in enumerate(key_dst_nodes):
                transform.set_world_transform_data(n, world_transform_data[i][j])

            pm.setKeyframe(key_dst_nodes, at=channels)
            pm.setKeyframe(switch_attr_name)

    def transfer(self, startFrame, endFrame, onlyKeyframes, *args, **kwargs):
        # type = (int, int, bool, *str, **str) -> None

        val_src_nodes = [self.ctrlNode]
        key_src_nodes = val_src_nodes
        key_dst_nodes = val_src_nodes

        self.bakeAnimation(
            self.getChangeAttrName(),
            val_src_nodes,
            key_src_nodes,
            key_dst_nodes,
            startFrame,
            endFrame,
            onlyKeyframes,
        )

    @staticmethod
    def showUI(combo, model, uihost, switchedAttrShortName, ctrl_name, *args):
        # type = (widgets.toggleCombo,
        # pm.nodetypes.Transform, str, str, str, *str) -> None

        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, ParentSpaceTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = ParentSpaceTransfer()
        ui.setComboObj(combo)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(switchedAttrShortName)
        ui.setCtrls(ctrl_name)
        ui.setComboBoxItemsFormComboObj(ui.comboObj)

        if isinstance(combo, (list, tuple)):
            idx = getComboIndex_with_namespace(
                                    getNamespace(model), uihost, switchedAttrShortName
                                    )
            ui.combo_idx = idx

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)


class IkFkTransfer(AbstractAnimationTransfer):
    def __init__(self):
        # type = () -> None
        super(IkFkTransfer, self).__init__()
        self.getValue = self.getValueFromUI

    # ----------------------------------------------------------------

    def getChangeAttrName(self):
        # type = () -> str
        return "{}.{}".format(self.getHostName(), self.switchedAttrShortName)

    def getChangeRollAttrName(self):
        # type = () -> str
        at_name = self.switchedAttrShortName.replace("blend", "roll")
        at = "{}.{}".format(
            self.getHostName(),
            self.switchedAttrShortName.replace("blend", "roll"),
            at_name,
        )
        if pm.objExists(at):
            return at
        else:
            return self.ikCtrl[0].attr(at_name)

    def changeAttrToBoundValue(self):
        # type = () -> None
        pm.setAttr(self.getChangeAttrName(), self.getValue())

    def getValueFromUI(self):
        # type = () -> float
        if self.comboBoxSpaces.currentIndex() == 0:
            # IK
            if self.getChangeAttrName().endswith("_Switch"):
                return 0.0
            else:
                return 1.0
        else:
            # FK
            if self.getChangeAttrName().endswith("_Switch"):
                return 1.0
            else:
                return 0.0

    def _getNode(self, name):
        # type = (str) -> pm.nodetypes.Transform
        node = getNode(":".join([self.nameSpace, name]))

        if not node:
            mgear.log("Can't find object : {0}".format(name), mgear.sev_error)

        return node

    def _getMth(self, name):
        # type = (str) -> pm.nodetypes.Transform
        node = self._getNode(name)
        if node.hasAttr("match_ref"):
            match_node = node.match_ref.listConnections()
            if match_node:
                return match_node[0]
        else:
            tmp = name.split("_")
            tmp[-1] = "mth"
            return self._getNode("_".join(tmp))

    def setCtrls(self, fks, ik, upv, ikRot):
        # type = (list[str], str, str) -> None
        """gather core PyNode represented each controllers"""

        if not isinstance(ik, list):
            ik = [ik]
        if not isinstance(upv, list):
            upv = [upv]

        self.fkCtrls = [self._getNode(x) for x in fks]
        self.fkTargets = [self._getMth(x) for x in fks]

        self.ikCtrl = [self._getNode(x) for x in ik]
        self.ikTarget = [self._getMth(x) for x in ik]

        self.upvCtrl = [self._getNode(x) for x in upv]
        self.upvTarget = [self._getMth(x) for x in upv]

        if ikRot:
            # self.ikRotCtl = self._getNode(ikRot)
            # self.ikRotTarget = self._getMth(ikRot)
            if not isinstance(ikRot, list):
                ikRot = [ikRot]

            self.ikRotCtl = [self._getNode(x) for x in ikRot]
            self.ikRotTarget = [self._getMth(x) for x in ikRot]
            self.hasIkRot = True
        else:
            self.hasIkRot = False

    def setGroupBoxTitle(self):
        if hasattr(self, "groupBox"):
            if len(self.ikCtrl) == 1:
                # TODO: extract logic with naming convention
                part = "_".join(self.ikCtrl[0].name().split(":")[-1].split("_")[:-2])
            else:
                part = "MULTI Transfer"

            self.groupBox.setTitle(part)

    # ----------------------------------------------------------------

    def transfer(
        self,
        startFrame,
        endFrame,
        onlyKeyframes,
        ikRot,
        switchTo=None,
        *args,
        **kargs,
    ):
        # type = (int, int, bool, str, *str, **str) -> None

        def fk_definition():
            src_nodes = self.fkTargets[:]
            key_nodes = self.ikCtrl[:] + self.upvCtrl[:]
            dst_nodes = self.fkCtrls[:]
            if ikRot:
                if isinstance(self.ikRotCtl, list):
                    key_nodes.extend(self.ikRotCtl)
                else:
                    key_nodes.append(self.ikRotCtl)
            return src_nodes, key_nodes, dst_nodes, "FK"

        def ik_definition():
            src_nodes = self.ikTarget + self.upvTarget
            key_nodes = self.fkCtrls
            dst_nodes = self.ikCtrl + self.upvCtrl
            if ikRot:
                if isinstance(self.ikRotTarget, list):
                    src_nodes.extend(self.ikRotTarget)
                else:
                    src_nodes.append(self.ikRotTarget)
                if isinstance(self.ikRotCtl, list):
                    dst_nodes.extend(self.ikRotCtl)
                else:
                    dst_nodes.append(self.ikRotCtl)

            roll_att = self.getChangeRollAttrName()
            pm.cutKey(roll_att, time=(startFrame, endFrame), cl=True)
            pm.setAttr(roll_att, 0)

            return src_nodes, key_nodes, dst_nodes, "IK"

        if switchTo is not None:
            if "fk" in switchTo.lower():
                val_src_n, key_src_n, key_dst_n, definition = fk_definition()
            else:
                val_src_n, key_src_n, key_dst_n, definition = ik_definition()
        else:
            if self.comboBoxSpaces.currentIndex() != 0:  # to FK
                val_src_n, key_src_n, key_dst_n, definition = fk_definition()
            else:  # to IK
                val_src_n, key_src_n, key_dst_n, definition = ik_definition()
        self.bakeAnimation(
            self.getChangeAttrName(),
            val_src_n,
            key_src_n,
            key_dst_n,
            startFrame,
            endFrame,
            onlyKeyframes,
            definition,
        )
        # fore evaluation after execution to refresh the viewport
        # cmds.dgdirty(a=True)
        cmds.currentTime(cmds.currentTime(q=True))

    # ----------------------------------------------------------------
    # re implement doItbyUI to have access to self.hasIKrot option
    def doItByUI(self):
        # type = () -> None

        # gather settings from UI
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # main body
        self.transfer(startFrame, endFrame, onlyKeyframes, self.hasIkRot)

        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    # ----------------------------------------------------------------

    @staticmethod
    def showUI(model, ikfk_attr, uihost, fks, ik, upv, ikRot, *args):
        # type = (pm.nodetypes.Transform, str, str,
        # List[str], str, str, *str) -> None

        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = IkFkTransfer()
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK", "FK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @staticmethod
    def execute(
        model,
        ikfk_attr,
        uihost,
        fks,
        ik,
        upv,
        ikRot=None,
        startFrame=None,
        endFrame=None,
        onlyKeyframes=None,
        switchTo=None,
    ):
        """transfer without displaying UI
        # type = (pm.nodetypes.Transform, str, str,
        # List[str], str, str, int, int, bool, str) -> None
        """

        if startFrame is None:
            startFrame = int(pm.playbackOptions(q=True, ast=True))

        if endFrame is None:
            endFrame = int(pm.playbackOptions(q=True, aet=True))

        if onlyKeyframes is None:
            onlyKeyframes = True

        if switchTo is None:
            switchTo = "fk"

        # Create minimal UI object
        ui = IkFkTransfer()
        ui.setComboObj(None)
        ui.setModel(model)
        ui.setUiHost(uihost)
        ui.setSwitchedAttrShortName(ikfk_attr)
        ui.setCtrls(fks, ik, upv, ikRot)
        ui.setComboBoxItemsFormList(["IK", "FK"])
        ui.getValue = lambda: 0.0 if "fk" in switchTo.lower() else 1.0
        ui.transfer(startFrame, endFrame, onlyKeyframes, ikRot, switchTo=switchTo)

    @staticmethod
    def toIK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type = (pm.nodetypes.Transform, str, str,
        # List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "ik"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs)

    @staticmethod
    def toFK(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs):
        # type = (pm.nodetypes.Transform, str, str,
        # List[str], str, str, **str) -> None

        kwargs.update({"switchTo": "fk"})
        IkFkTransfer.execute(model, ikfk_attr, uihost, fks, ik, upv, ikRot, **kwargs)


# Baker Springs


def _spring_nodes(model):
    """Return the spring nodes of a rig, warning when it has none."""
    springNodes = getControlers(model, gSuffix=PLOT_GRP_SUFFIX)
    if not springNodes:
        pm.displayWarning("No spring nodes found in {}".format(model))
    return springNodes


def _clear_spring_pairblends(springNodes):
    """Delete the baked rotation curves of spring nodes."""
    # spring nodes never baked have no pairBlend
    pairblends = []
    for sn in springNodes:
        pairblends.extend(sn.listConnections(type="pairBlend")[:1])

    for pb in pairblends:
        animCrvs = pb.listConnections(type="animCurveTA")
        for fcrv in animCrvs:
            for conn in fcrv.listConnections(
                connections=True, destination=True, plugs=True
            ):
                pm.disconnectAttr(conn)
        # reset the value to 0
        for attr in ("inRotateX1", "inRotateY1", "inRotateZ1"):
            pb.attr(attr).set(0)

        # delete fcurves
        if animCrvs:
            pm.delete(animCrvs)


@utils.one_undo
def clearSprings(model=None):
    """Delete baked animation from spring

    Args:
        model (dagNode): The rig top node
    """

    # filters the root node from selection
    if not model:
        model = getRootNode()

    springNodes = _spring_nodes(model)
    if springNodes:
        _clear_spring_pairblends(springNodes)


@utils.one_undo
@utils.viewport_off
def bakeSprings(model=None):
    """Bake the automatic spring animation to animation curves

    The current time is restored afterwards.

    Args:
        model (dagNode): The rig top node
    """

    # filters the root node from selection
    if not model:
        model = getRootNode()

    springNodes = _spring_nodes(model)
    if not springNodes:
        return
    mgear.log("Baking springs of {}".format(model))

    # first clear animation
    _clear_spring_pairblends(springNodes)

    # bake again
    start, end = get_playback_range()
    with utils.current_time_kept():
        for frame in range(int(start), int(end) + 1):
            pm.currentTime(frame)
            pm.setKeyframe(springNodes, insertBlend=True, attribute="rotate")


class SpineIkFkTransfer(AbstractAnimationTransfer):
    def __init__(self):
        super(SpineIkFkTransfer, self).__init__()
        self.fkControls = None
        self.ikControls = None

    def doItByUI(self):
        """Gather UI settings to execute transfer"""
        startFrame = self.startFrame_value.value()
        endFrame = self.endFrame_value.value()
        onlyKeyframes = self.onlyKeyframes_check.isChecked()

        # based on user input, decide where to flatten animation
        bakeToIk = self.comboBoxSpaces.currentIndex()

        self.bakeAnimation(
            self.fkControls,
            self.ikControls,
            startFrame,
            endFrame,
            bakeToIk=bakeToIk,
            onlyKeyframes=onlyKeyframes,
        )

        # Refresh the viewport by toggling time, refresh/dgdirty do not work
        pm.currentTime(startFrame)
        pm.currentTime(endFrame)
        # set the new space value in the synoptic combobox
        if self.comboObj is not None:
            self.comboObj.setCurrentIndex(self.comboBoxSpaces.currentIndex())

        for c in pyqt.maya_main_window().children():
            if isinstance(c, AbstractAnimationTransfer):
                c.deleteLater()

    def setCtrls(self, fkControls, ikControls):
        """make provided controls accessible to the class, with namespaces

        Args:
            fkControls (list): of fk  controls
            ikControls (list): of ik controls
        """
        ns = self.nameSpace
        if not ns.endswith(":") and ns != "":
            ns = "{0}:".format(ns)
        self.fkControls = ["{0}{1}".format(ns, x) for x in fkControls]
        self.ikControls = ["{0}{1}".format(ns, x) for x in ikControls]

    @staticmethod
    def showUI(topNode, uihost, fkControls, ikControls, *args):
        """Called from the synaptic qpushbutton, with the spine control names

        Args:
            topNode (string): top node of the rig
            uihost (TYPE): Description
            fkControls (list): of fkControls
            ikControls (list): of ikControls
            *args: additional signal args, n/a
        """
        try:
            for c in pyqt.maya_main_window().children():
                if isinstance(c, IkFkTransfer):
                    c.deleteLater()

        except RuntimeError:
            pass

        # Create minimal UI object
        ui = SpineIkFkTransfer()
        ui.setModel(topNode)
        ui.setUiHost(uihost)
        ui.setCtrls(fkControls, ikControls)
        ui.setComboObj(None)
        ui.setComboBoxItemsFormList(["IK >> FK", "FK >> IK"])

        # Delete the UI if errors occur to avoid causing winEvent
        # and event errors (in Maya 2014)
        try:
            ui.createUI(pyqt.maya_main_window())
            ui.setWindowTitle("Spine IKFK")
            ui.show()

        except Exception as e:
            ui.deleteLater()
            traceback.print_exc()
            mgear.log(e, mgear.sev_error)

    @utils.one_undo
    @utils.viewport_off
    def bakeAnimation(
        self,
        fkControls,
        ikControls,
        startFrame,
        endFrame,
        bakeToIk=True,
        onlyKeyframes=True,
    ):
        """bake animation to desired destination. More adding animtion than
        ik/fk transfer

        Args:
            fkControls (list): of fk controls
            ikControls (list): of ik controls
            startFrame (float): start frame
            endFrame (float): end frame
            bakeToIk (bool, optional): True, bake animation to ik, fk is false
            onlyKeyframes (bool, optional): transfer animation on other
            keyframes, if false, bake every frame
        """
        # Temporaly turn off cycle check to avoid misleading cycle message
        # on Maya 2016.  With Maya 2016.5 and 2017 the cycle warning doesn't
        # show up
        if bakeToIk:
            key_src_nodes = fkControls
            transferFunc = spine_FKToIK
            key_dst_nodes = ikControls
        else:
            key_src_nodes = ikControls
            transferFunc = spine_IKToFK
            key_dst_nodes = fkControls

        # add all nodes, to get all of the keyframes
        allAnimNodes = fkControls + ikControls
        # remove duplicates
        keyframeList = sorted(
            set(pm.keyframe(allAnimNodes, at=["t", "r", "s"], q=True))
        )

        # when getAttr over time, it warns of a cycle
        if versions.current() <= 20180200:
            pm.cycleCheck(e=False)
            print("Maya version older than: 2018.02")

        # create a dict of every frame, and every node involved on that frame
        matchMatrix_dict = {}
        for i, x in enumerate(range(startFrame, endFrame + 1)):
            if onlyKeyframes and x not in keyframeList:
                continue
            matchMatrix_dict[x] = recordNodesMatrices(fkControls, x)

        channels = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]

        # delete animation in the channel and destination ctrls
        pm.cutKey(fkControls, at=channels, time=(startFrame, endFrame))
        pm.cutKey(ikControls, at=channels, time=(startFrame, endFrame))

        if PY2:
            dic_items = matchMatrix_dict.iteritems
        else:
            dic_items = matchMatrix_dict.items

        for frame, matchDict in dic_items():
            pm.currentTime(frame)
            transferFunc(fkControls, ikControls, matchMatrix_dict=matchDict)

            pm.setKeyframe(key_dst_nodes, at=channels)
        # If there are keys on the source node outside of the provided range
        # this wont have an effect
        attribute.reset_SRT(key_src_nodes)

        # re enable cycle check
        if versions.current() <= 20180200:
            pm.cycleCheck(e=True)
            print("CycleCheck turned back ON")


# Functions to support arbitraty limb length for FK to IK

def match_fk_to_ik_scale_slide(fk_controls, ui_host,
                               scale_attr="scale",
                               slide_attr="slide"):
    """Match FK limb to IK using scale and slide on a uiHost node.

    Supports chains with 2 or more segments (3+ FK controls).

    Args:
        fk_controls (list): FK control names in chain order.
        ui_host (str): Node where scale/slide attrs live.
        scale_attr (str): Name of scale attribute.
        slide_attr (str): Name of slide attribute.

    Raises:
        RuntimeError: On missing nodes or zero-length setup.
    """
    s_path = "{}.{}".format(ui_host, scale_attr)
    sl_path = "{}.{}".format(ui_host, slide_attr)
    s_path_info = attribute.get_attr_info(ui_host, scale_attr)
    sl_path_info = attribute.get_attr_info(ui_host, slide_attr)
    s_default_val = s_path_info["default"]
    sl_min_val = sl_path_info["min"]
    sl_max_val = sl_path_info["max"]

    def parent_of(obj):
        p = cmds.listRelatives(obj, parent=True, fullPath=True)
        if not p:
            raise RuntimeError("No parent for {}".format(obj))
        return p[0]

    for ctl in fk_controls:
        if not cmds.objExists(ctl):
            raise RuntimeError("Control not found: {}".format(ctl))

    # Rest lengths from parent hierarchy for each segment
    rest_segments = []
    for ctl in fk_controls[1:]:
        ctl_p = parent_of(ctl)
        ctl_pp = parent_of(ctl_p)
        rest_segments.append(vector.getDistance2(ctl_pp, ctl_p))
    rest_total = sum(rest_segments)

    if rest_total == 0:
        raise RuntimeError("Rest pose total length is zero.")

    # Current lengths between consecutive FK controls
    cur_segments = []
    for i in range(len(fk_controls) - 1):
        cur_segments.append(
            vector.getDistance2(fk_controls[i], fk_controls[i + 1])
        )
    cur_total = sum(cur_segments)

    # Scale
    scale_val = cur_total / rest_total

    # Slide: ratio of upper portion vs total
    mid_idx = len(fk_controls) // 2
    rest_upper = sum(rest_segments[:mid_idx])
    cur_upper = sum(cur_segments[:mid_idx])
    rest_ratio = rest_upper / rest_total
    cur_ratio = cur_upper / cur_total if cur_total > 0 else rest_ratio

    if cur_ratio <= rest_ratio:
        slide_val = (cur_ratio / rest_ratio) * 0.5
    else:
        slide_val = (
            0.5
            + ((cur_ratio - rest_ratio) / (1 - rest_ratio)) * 0.5
        )

    slide_val = max(0.0, min(1.0, slide_val))

    # Map normalized values to attribute ranges
    if s_default_val is not None:
        scale_val = scale_val * s_default_val

    if sl_min_val is not None and sl_max_val is not None:
        slide_val = (sl_max_val - sl_min_val) * slide_val + sl_min_val

    for p in (s_path, sl_path):
        if not cmds.objExists(p):
            raise RuntimeError("Missing attribute: {}".format(p))

    cmds.setAttr(s_path, scale_val)
    cmds.setAttr(sl_path, slide_val)


def place_upv_from_fk(fk_controls, upv_ctl, distance_multiplier=2.0):
    """Place up vector control based on the FK plane.

    Uses the first, middle, and last FK controls to define the limb
    plane and places the pole vector perpendicular to it.
    Supports chains with 3 or more FK controls.

    Args:
        fk_controls (list): FK control names in chain order.
        upv_ctl (str): Up vector control to be moved.
        distance_multiplier (float): Distance scale factor.

    Raises:
        RuntimeError: If any control does not exist.
    """
    for ctl in list(fk_controls) + [upv_ctl]:
        if not cmds.objExists(ctl):
            raise RuntimeError("Control not found: {}".format(ctl))

    first = fk_controls[0]
    mid = fk_controls[len(fk_controls) // 2]
    last = fk_controls[-1]

    v1 = vector.get_mvector(first)
    v2 = vector.get_mvector(mid)
    v3 = vector.get_mvector(last)

    a = v2 - v1
    b = v3 - v1

    b_normalized = b.normal()
    proj = a * b_normalized
    projected = b_normalized * proj
    pole_dir = a - projected
    pole_dir = pole_dir.normal()

    elbow_len = a.length()
    pole_vec = v2 + (pole_dir * elbow_len * distance_multiplier)

    cmds.xform(upv_ctl, ws=True,
               t=[pole_vec.x, pole_vec.y, pole_vec.z])


def match_fk_to_ik_arbitrary_lengths(fk_controls, ui_host,
                                     blend_attr, upv_ctl):
    """Match FK to IK for arbitrary limb lengths.

    Supports chains with 3 or more FK controls (2jnt, 3jnt, etc.).

    Args:
        fk_controls (list): FK controls as strings or PyNodes.
        ui_host (str or PyNode): Node with blend attr.
        blend_attr (str): Name of blend or switch attr.
        upv_ctl (str or PyNode): Up-vector control.

    Returns:
        bool: True if match ran, False if attrs missing.
    """
    names = []
    for c in fk_controls:
        if not isinstance(c, str):
            names.append(c.name())
        else:
            names.append(c)

    if len(names) < 3:
        return False

    if not isinstance(ui_host, str):
        ui_node = ui_host
        ui_str = ui_host.name()
    else:
        ui_node = pm.PyNode(ui_host)
        ui_str = ui_host

    if not isinstance(upv_ctl, str):
        upv_str = upv_ctl.name()
    else:
        upv_str = upv_ctl

    if blend_attr.endswith("_blend"):
        base = blend_attr[:-6]
    elif blend_attr.endswith("_Switch"):
        base = blend_attr[:-7]
    else:
        base = blend_attr
    scale_attr = base + "_ikscale"
    slide_attr = base + "_slide"

    if not ui_node.hasAttr(scale_attr) or not ui_node.hasAttr(
        slide_attr
    ):
        return False

    keyframe = pm.keyframe(
        "{}.{}".format(ui_str, blend_attr),
        query=True,
        keyframeCount=True,
    )

    match_fk_to_ik_scale_slide(
        fk_controls=names,
        ui_host=ui_str,
        scale_attr=scale_attr,
        slide_attr=slide_attr,
    )

    place_upv_from_fk(
        fk_controls=names,
        upv_ctl=upv_str,
        distance_multiplier=1.0,
    )

    if keyframe:
        cur_time = cmds.currentTime(query=True)
        cmds.setKeyframe(
            "{}.{}".format(ui_str, scale_attr), time=cur_time
        )
        cmds.setKeyframe(
            "{}.{}".format(ui_str, slide_attr), time=cur_time
        )

    return True
