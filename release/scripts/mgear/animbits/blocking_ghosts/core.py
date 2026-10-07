"""Blocking Ghosts scene logic.

Creates static, semi-transparent copies ("ghosts") of a list of meshes at
the keyframe times of a set of watched controls, and keeps them in sync
with the playhead and the active camera:

- ghosts before the current frame use the "previous" look, ghosts after it
  the "post" look, and the ghost on the current frame is hidden;
- ghosts are spread along the camera's right axis by the spacing value;
- selecting a ghost jumps the timeline to its frame;
- leaving a ghost frame re-captures that ghost from the live pose.

All live state is held by a :class:`GhostSession`. Ghost nodes are never
written to the scene file and tool edits never enter the undo queue.

Example:
    >>> from mgear.animbits.blocking_ghosts import core
    >>> session = core.GhostSession()
    >>> session.objects = ["|char:geo|char:body_geo"]
    >>> session.controls = ["char:arm_L0_fk0_ctl"]
    >>> session.generate()
"""

import contextlib
import time

from maya import cmds
import maya.api.OpenMaya as om2

from mgear.core import anim_utils
from mgear.core import callbackManager
from mgear.core import node
from mgear.core import shading
from mgear.core import string
from mgear.core import utils

ROOT_GROUP = "BlockingGhosts_grp"
PREFIX = "bghost"
PREV_SHADER = "bghost_prev_mat"
POST_SHADER = "bghost_post_mat"
PREV_SG = PREV_SHADER + "SG"
POST_SG = POST_SHADER + "SG"

DEFAULT_PREV_COLOR = (1.0, 0.0, 0.0)
DEFAULT_POST_COLOR = (0.0, 0.0, 1.0)

# Namespace of the session callbacks in mgear.core.callbackManager. Fixed,
# so a new session (or a module reload) replaces the old callbacks instead
# of leaving orphans behind.
CB_NAMESPACE = "blockingGhosts"

STATE_PREV = 0
STATE_POST = 1
STATE_HIDDEN = 2

# Look of ghosts showing their source objects' own shading.
LOOK_ORIGINAL = "original"

# Frame distance treated as "the same frame".
TOLERANCE = 1e-4

# Period of the session tick (camera tracking and scrub settle), seconds.
TICK_PERIOD = 0.1

# Time after the last time change before the parked ghost is re-captured,
# in seconds. Each time change restarts it, so it elapses once the
# playhead settles.
UPDATE_SETTLE = 0.25


#############################################
# PURE HELPERS
#############################################


def _partition(times, current):
    """Split times into those before and after the current time.

    Times within ``TOLERANCE`` of ``current`` are in neither list.

    Args:
        times (list): Times.
        current (float): Time to split around.

    Returns:
        tuple: ``(before, after)``, each sorted ascending.
    """
    before = sorted(t for t in times if t < current - TOLERANCE)
    after = sorted(t for t in times if t > current + TOLERANCE)
    return before, after


def range_times(times, start, end):
    """Return the times inside a frame range, inclusive.

    Args:
        times (list): Keyframe times.
        start (float): First frame of the range.
        end (float): Last frame of the range. Swapped with ``start`` when
            smaller.

    Returns:
        list: Sorted times with ``start <= t <= end`` (within
        ``TOLERANCE``).
    """
    low, high = min(start, end), max(start, end)
    return sorted(t for t in times if low - TOLERANCE <= t <= high + TOLERANCE)


def same_frame(a, b):
    """Return True when two frame numbers are the same frame.

    Args:
        a (float): First frame.
        b (float): Second frame.

    Returns:
        bool: True when they are within ``TOLERANCE``.
    """
    return abs(a - b) <= TOLERANCE


def display_state(frame, current):
    """Return the display state of a ghost frame relative to the playhead.

    Args:
        frame (float): Ghost frame.
        current (float): Current time.

    Returns:
        int: ``STATE_PREV``, ``STATE_POST`` or ``STATE_HIDDEN``.
    """
    if abs(frame - current) <= TOLERANCE:
        return STATE_HIDDEN
    return STATE_PREV if frame < current else STATE_POST


def spread_steps(frames, current):
    """Rank ghost frames outward from the current time.

    The nearest previous frame is step -1, the nearest post frame step +1,
    and so on. A frame on the current time is step 0.

    Args:
        frames (list): Ghost frames.
        current (float): Current time.

    Returns:
        dict: Frame to signed integer step.
    """
    before, after = _partition(frames, current)
    steps = {f: 0 for f in frames}
    for i, frame in enumerate(reversed(before)):
        steps[frame] = -(i + 1)
    for i, frame in enumerate(after):
        steps[frame] = i + 1
    return steps


def matrix_changed(a, b, eps=1e-5):
    """Return True when two flat matrices differ beyond ``eps``.

    Args:
        a (list): First matrix, flat.
        b (list): Second matrix, flat.
        eps (float, optional): Per-element tolerance.

    Returns:
        bool: True when any element differs by more than ``eps``.
    """
    return any(abs(x - y) > eps for x, y in zip(a, b))


def frame_label(frame):
    """Return a node-name-safe label for a frame number.

    Args:
        frame (float): Frame number.

    Returns:
        str: For example ``"10"``, ``"12_5"`` or ``"neg3"``.
    """
    text = "{:g}".format(frame)
    return text.replace("-", "neg").replace(".", "_")


def ghost_name(frame, source):
    """Return the ghost transform name for a source at a frame.

    Characters Maya does not accept in a new node name (such as a
    namespace separator) are replaced.

    Args:
        frame (float): Ghost frame.
        source (str): Source node name or full path.

    Returns:
        str: Ghost node name.
    """
    short = string.normalize2(source.split("|")[-1])
    return "{}_f{}_{}".format(PREFIX, frame_label(frame), short)


def log(message):
    """Print an info line prefixed with the tool name.

    Args:
        message (str): Message to print.
    """
    om2.MGlobal.displayInfo("Blocking Ghosts: " + message)


def warn(message):
    """Print a warning prefixed with the tool name.

    Args:
        message (str): Message to print.
    """
    cmds.warning("Blocking Ghosts: " + message)


#############################################
# SCENE HELPERS
#############################################


def _set_do_not_write(nodes):
    """Keep nodes out of the saved scene file.

    The flag is per node: children of a flagged node are still written, so
    every created node must be passed.

    Args:
        nodes (list): Node names.
    """
    sel = om2.MSelectionList()
    for name in nodes:
        sel.add(name)
    for i in range(sel.length()):
        om2.MFnDependencyNode(sel.getDependNode(i)).setDoNotWrite(True)


def _mesh_shapes(root):
    """Return the visible mesh shapes under a node, in hierarchy order.

    Args:
        root (str): Transform name or path.

    Returns:
        list: Full paths of non-intermediate mesh shapes.
    """
    return (
        cmds.listRelatives(
            root,
            allDescendents=True,
            type="mesh",
            noIntermediate=True,
            fullPath=True,
        )
        or []
    )[::-1]


def _clean_ghost_hierarchy(ghost):
    """Strip a duplicated hierarchy down to its visible meshes.

    Deletes intermediate shapes, non-mesh shapes and nodes (joints,
    constraints, locators, curves) and child transforms with no mesh
    below them.

    Args:
        ghost (str): Ghost root transform full path.

    Returns:
        list: Full paths of the descendants that were kept.
    """
    descendants = cmds.listRelatives(ghost, allDescendents=True, fullPath=True) or []
    meshes = set(_mesh_shapes(ghost))
    transforms = set(cmds.ls(descendants, exactType="transform", long=True))
    kept = [
        d
        for d in descendants
        if d in meshes
        or (d in transforms and any(m.startswith(d + "|") for m in meshes))
    ]
    doomed = [d for d in descendants if d not in kept]
    # Deleting a node deletes its children, so only delete the top-most.
    top = [d for d in doomed if not any(d.startswith(o + "|") for o in doomed)]
    if top:
        cmds.delete(top)
    return kept


def _unlock(ghost):
    """Unlock every locked attribute of a transform.

    Args:
        ghost (str): Transform full path.
    """
    for attr in cmds.listAttr(ghost, locked=True) or []:
        cmds.setAttr("{}.{}".format(ghost, attr), lock=False)


def duplicate_ghost(source, name, parent):
    """Create a static ghost copy of a mesh in its current world pose.

    The copy has no construction history, keeps only its visible mesh
    shapes, inherits its parent's transform and is not saved with the
    scene. It is placed under ``parent`` with its local matrix set to the
    source's world matrix, so offsetting ``parent`` offsets the ghost.

    Args:
        source (str): Source mesh transform full path.
        name (str): Ghost transform name.
        parent (str): Group to place the ghost under.

    Returns:
        str: Ghost transform full path.
    """
    world = cmds.xform(source, query=True, matrix=True, worldSpace=True)
    handle = _handle(cmds.duplicate(source, returnRootsOnly=True, name=name)[0])
    ghost = _path(handle)
    cmds.delete(ghost, constructionHistory=True)
    kept = _clean_ghost_hierarchy(ghost)
    _set_do_not_write([ghost] + kept)
    _unlock(ghost)
    cmds.parent(ghost, parent, relative=True)
    ghost = _path(handle)
    cmds.setAttr(ghost + ".inheritsTransform", True)
    cmds.xform(ghost, matrix=world, objectSpace=True)
    node.set_hide_on_playback([ghost])
    return ghost


def copy_pose(source, ghost):
    """Update an existing ghost in place from the source's current pose.

    Only handles a source whose meshes sit directly under the source
    transform (the common case); anything else returns False so the
    caller can rebuild the ghost.

    Args:
        source (str): Source mesh transform full path.
        ghost (str): Ghost transform full path.

    Returns:
        bool: True when the ghost was updated, False when it must be
        rebuilt (different hierarchy or vertex count).
    """
    if cmds.listRelatives(source, children=True, type="transform"):
        return False
    src_shapes = _mesh_shapes(source)
    ghost_shapes = _mesh_shapes(ghost)
    if not src_shapes or len(src_shapes) != len(ghost_shapes):
        return False

    sel = om2.MSelectionList()
    for shape in src_shapes + ghost_shapes:
        sel.add(shape)
    count = len(src_shapes)
    pairs = []
    for i in range(count):
        src_fn = om2.MFnMesh(sel.getDagPath(i))
        ghost_fn = om2.MFnMesh(sel.getDagPath(count + i))
        if src_fn.numVertices != ghost_fn.numVertices:
            return False
        pairs.append((src_fn, ghost_fn))

    for src_fn, ghost_fn in pairs:
        # Read the evaluated outMesh: MFnMesh on a deformed shape can
        # return stale points until something pulls on the DG.
        out_mesh = src_fn.findPlug("outMesh", False).asMObject()
        points = om2.MFnMesh(out_mesh).getPoints(om2.MSpace.kObject)
        ghost_fn.setPoints(points, om2.MSpace.kObject)
        # Flag the bounding box and the viewport for redraw.
        ghost_fn.updateSurface()
    world = cmds.xform(source, query=True, matrix=True, worldSpace=True)
    cmds.xform(ghost, matrix=world, objectSpace=True)
    return True


def remove_stale_ghosts():
    """Remove ghost nodes and callbacks left by a previous session.

    Used when the tool opens, so a crashed or reloaded session can not
    leave ghosts or callbacks behind.
    """
    callbackManager.removeNamespaceCB(CB_NAMESPACE)
    _delete_ghost_nodes()


def _delete_ghost_nodes():
    """Delete the ghost root group and ghost shaders, if they exist."""
    existing = cmds.ls(ROOT_GROUP, PREV_SG, POST_SG, PREV_SHADER, POST_SHADER)
    if existing:
        with utils.undo_disabled():
            cmds.delete(existing)


def _restore_selection(selection):
    """Reselect nodes that still exist, or clear the selection.

    Args:
        selection (list): Node names.
    """
    nodes = cmds.ls(selection, long=True) if selection else []
    if nodes:
        cmds.select(nodes, replace=True)
    else:
        cmds.select(clear=True)


def _path(handle):
    """Return the full DAG path of a node handle, or None if it is gone.

    Args:
        handle (om2.MObjectHandle): Handle to a DAG node.

    Returns:
        str: Full path, or None when the node no longer exists.
    """
    if not handle.isValid() or not handle.isAlive():
        return None
    return om2.MDagPath.getAPathTo(handle.object()).fullPathName()


def _handle(name):
    """Return an MObjectHandle for a node name.

    Args:
        name (str): Node name or path.

    Returns:
        om2.MObjectHandle: The handle.
    """
    return om2.MObjectHandle(callbackManager.getMObject(name))


#############################################
# SESSION
#############################################


class Ghost(object):
    """One ghost copy of a source object."""

    def __init__(self, path, source):
        """Initialize the ghost record.

        Args:
            path (str): Ghost transform full path.
            source (str): Source transform full path.
        """
        self.handle = _handle(path)
        self.source = source
        self.shapes = [_handle(s) for s in _mesh_shapes(path)]

    def path(self):
        """Return the ghost transform path, or None if it was deleted.

        Returns:
            str: Full path or None.
        """
        return _path(self.handle)

    def shape_paths(self):
        """Return the paths of the ghost's mesh shapes that still exist.

        Returns:
            list: Full paths, in hierarchy order.
        """
        paths = (_path(h) for h in self.shapes)
        return [p for p in paths if p]


class GhostFrame(object):
    """The ghosts of all source objects at one frame."""

    def __init__(self, frame, group):
        """Initialize the frame record.

        Args:
            frame (float): Source frame.
            group (str): Per-frame group full path.
        """
        self.frame = frame
        self.group = _handle(group)
        # Stored: a handle's hashCode() changes once its node is deleted.
        self.key = self.group.hashCode()
        self.ghosts = []
        self.visible = True
        self.look = LOOK_ORIGINAL
        self.offset = (0.0, 0.0, 0.0)

    def group_path(self):
        """Return the per-frame group path, or None if it was deleted.

        Returns:
            str: Full path or None.
        """
        return _path(self.group)


class GhostSession(object):
    """Owns the ghosts, their settings and the callbacks keeping them live.

    Set the public attributes, then call :meth:`generate`. Call
    :meth:`clear` to remove everything; ghost data is also dropped on new
    scene and scene open.
    """

    def __init__(self):
        self.objects = []
        self.controls = []
        self.start_frame = 1.0
        self.end_frame = 120.0
        self.prev_color = DEFAULT_PREV_COLOR
        self.post_color = DEFAULT_POST_COLOR
        self.transparency = 0.5
        self.spacing = 0.0
        self.use_ghost_color = True

        # Per-frame records keyed by their group's MObjectHandle hash, in
        # ascending frame order.
        self._frames = {}
        self._shading_cache = {}
        self._camera_matrix = None
        self._camera_right = (1.0, 0.0, 0.0)
        self._parked_frame = None
        self._last_time_change = None
        self._prev_selection = []
        self._busy = False

        self._callbacks = callbackManager.CallbackManager()
        self._callbacks.setNamespace(CB_NAMESPACE)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def frames(self):
        """Return the ghost frames.

        Returns:
            list: Ghost frame numbers, ascending.
        """
        return [gf.frame for gf in self._frames.values()]

    def sample_times(self):
        """Return the keyframe times of the watched controls in the range.

        Returns:
            list: Sorted frames that would get a ghost.
        """
        times = anim_utils.get_keyframe_times(self.controls)
        return range_times(times, self.start_frame, self.end_frame)

    def generate(self):
        """Create ghosts for every watched key in the range.

        Existing ghosts are replaced. A key on the current frame gets a
        ghost too; it stays hidden while the playhead is on it.

        Returns:
            bool: True when ghosts were created, False when skipped (with a
            warning explaining why).
        """
        objects = self._source_objects()
        if not objects:
            warn("no objects to ghost.")
            return False
        if not self.controls:
            warn("no watch controls set.")
            return False
        sample_times = self.sample_times()
        if not sample_times:
            warn(
                "the watch controls have no keyframes between frame {:g} and "
                "{:g}.".format(self.start_frame, self.end_frame)
            )
            return False

        start = time.perf_counter()
        self.clear()
        current = cmds.currentTime(query=True)
        with self._scene_edit(current), utils.viewport_suspended():
            root = cmds.group(empty=True, world=True, name=ROOT_GROUP)
            _set_do_not_write([root])
            if self.use_ghost_color:
                self._ensure_ghost_shaders()
            self._add_frames(sample_times, objects)

        self._update_camera(force=True)
        self.refresh()
        self._start_callbacks()
        log(
            "generated {} pose(s) for {} object(s) in {:.3f}s".format(
                len(sample_times), len(objects), time.perf_counter() - start
            )
        )
        return True

    def clear(self):
        """Delete all ghosts and ghost shaders and stop all callbacks."""
        self.teardown()
        _delete_ghost_nodes()

    def teardown(self):
        """Stop all callbacks and forget the ghost data.

        Scene nodes are left untouched; use :meth:`clear` to delete them.
        """
        self._callbacks.removeAllManagedCB()
        self._frames = {}
        self._shading_cache = {}
        self._camera_matrix = None
        self._parked_frame = None
        self._last_time_change = None
        self._prev_selection = []
        self._busy = False

    def refresh(self):
        """Update ghost looks, visibility and spacing for the current time.

        Skipped while the timeline plays; a playback-stop callback calls
        it once playback ends. The scene is only touched for frames whose
        visibility, look or offset actually changed.
        """
        if not self._frames or self._busy:
            return
        if om2.MConditionMessage.getConditionState("playingBack"):
            return
        current = cmds.currentTime(query=True)
        steps = spread_steps(self.frames(), current)
        changes = []
        for gf in self._frames.values():
            state = display_state(gf.frame, current)
            visible = state != STATE_HIDDEN
            look = self._look_for(state) if visible else gf.look
            # Positive spacing places previous poses on the camera's
            # right and post poses on its left; negative swaps them.
            distance = -steps[gf.frame] * self.spacing
            offset = tuple(axis * distance for axis in self._camera_right)
            if (
                visible != gf.visible
                or look != gf.look
                or matrix_changed(offset, gf.offset, 1e-6)
            ):
                changes.append((gf, visible, look, offset))
        if not changes:
            return
        with utils.undo_disabled():
            for gf, visible, look, offset in changes:
                group = gf.group_path()
                if not group:
                    continue
                if visible != gf.visible:
                    cmds.setAttr(group + ".visibility", visible)
                    gf.visible = visible
                if look != gf.look:
                    self._apply_look(gf, look)
                if matrix_changed(offset, gf.offset, 1e-6):
                    cmds.setAttr(group + ".translate", *offset, type="double3")
                    gf.offset = offset

    def set_transparency(self, transparency):
        """Set the ghost transparency, live.

        Args:
            transparency (float): 0 opaque to 1 fully transparent.
        """
        self.transparency = transparency
        with utils.undo_disabled():
            for shader in cmds.ls(PREV_SHADER, POST_SHADER):
                shading.set_shader_transparency(shader, transparency)

    def set_colors(self, prev_color, post_color):
        """Set the previous and post ghost colors, live.

        Args:
            prev_color (tuple): Previous RGB, 0-1 range.
            post_color (tuple): Post RGB, 0-1 range.
        """
        self.prev_color = tuple(prev_color)
        self.post_color = tuple(post_color)
        if cmds.objExists(PREV_SHADER):
            self._ensure_ghost_shaders()

    def set_spacing(self, spacing):
        """Set the spread distance between poses, live.

        Args:
            spacing (float): World units between adjacent poses along the
                camera's right axis.
        """
        self.spacing = spacing
        self.refresh()

    def set_ghost_color(self, enabled):
        """Switch between ghost colors and the original shading, live.

        Args:
            enabled (bool): True for ghost colors, False for the source
                objects' own shading.
        """
        self.use_ghost_color = bool(enabled)
        if self.use_ghost_color and self._frames:
            self._ensure_ghost_shaders()
        self.refresh()

    def recapture(self, frame, restore_to):
        """Update the ghosts of one frame from the live pose at that frame.

        Args:
            frame (float): Ghost frame to update.
            restore_to (float): Time to restore afterwards.
        """
        gf = self._frame_at(frame)
        group = gf.group_path() if gf else None
        if not group:
            return
        start = time.perf_counter()
        with self._scene_edit(restore_to):
            cmds.currentTime(frame, edit=True)
            self._recapture_ghosts(gf, group)
        self.refresh()
        log("updated frame {:g} in {:.3f}s".format(frame, time.perf_counter() - start))

    # -----------------------------------------------------------------
    # Scene edit guards
    # -----------------------------------------------------------------
    @contextlib.contextmanager
    def _suppressed(self):
        """Ignore the session's own callbacks while the block runs.

        Nests safely: the previous state is restored on exit.
        """
        previous = self._busy
        self._busy = True
        try:
            yield
        finally:
            self._busy = previous

    @contextlib.contextmanager
    def _scene_edit(self, restore_time):
        """Run a tool scene edit that may change time and selection.

        Callbacks are suppressed and undo is not recorded. The current time
        and the user's selection are restored afterwards.

        Args:
            restore_time (float): Time to restore on exit.
        """
        selection = cmds.ls(selection=True, long=True)
        with self._suppressed(), utils.undo_disabled():
            try:
                yield
            finally:
                cmds.currentTime(restore_time, edit=True)
                _restore_selection(selection)

    # -----------------------------------------------------------------
    # Ghost building
    # -----------------------------------------------------------------
    def _source_objects(self):
        """Return the existing source objects as full paths.

        Returns:
            list: Full paths, in list order.
        """
        return cmds.ls(self.objects, long=True) if self.objects else []

    def _add_frames(self, frames, objects):
        """Create the ghosts of every object at each frame.

        Moves the current time; call inside :meth:`_scene_edit`. The frame
        records are kept in ascending frame order.

        Args:
            frames (list): Frames to ghost.
            objects (list): Source mesh transform full paths.
        """
        for frame in frames:
            cmds.currentTime(frame, edit=True)
            group = cmds.group(
                empty=True,
                parent=ROOT_GROUP,
                name="{}_f{}".format(PREFIX, frame_label(frame)),
            )
            gf = GhostFrame(frame, group)
            group = gf.group_path()
            _set_do_not_write([group])
            for source in objects:
                ghost = duplicate_ghost(source, ghost_name(frame, source), group)
                gf.ghosts.append(Ghost(ghost, source))
            self._frames[gf.key] = gf
        self._frames = dict(sorted(self._frames.items(), key=lambda i: i[1].frame))

    def sync_keys(self):
        """Match the ghosts to the watched keys inside the range.

        Adds ghosts for new keys and deletes ghosts whose key is gone (a
        moved key is both). Called when scrubbing settles, so nothing is
        built while the playhead moves.

        Returns:
            bool: True when ghosts were added or removed.
        """
        if not self._frames or not cmds.objExists(ROOT_GROUP):
            return False
        keys = self.sample_times()
        frames = self.frames()
        added = [k for k in keys if not any(same_frame(k, f) for f in frames)]
        removed = [
            gf
            for gf in self._frames.values()
            if not any(same_frame(gf.frame, k) for k in keys)
        ]
        objects = self._source_objects()
        if not objects or not (added or removed):
            return False

        start = time.perf_counter()
        with self._scene_edit(cmds.currentTime(query=True)):
            groups = [gf.group_path() for gf in removed]
            groups = [g for g in groups if g]
            if groups:
                cmds.delete(groups)
            for gf in removed:
                del self._frames[gf.key]
            if added:
                if self.use_ghost_color:
                    self._ensure_ghost_shaders()
                self._add_frames(added, objects)
        self.refresh()
        log(
            "keys changed: added {} and removed {} pose(s) in {:.3f}s".format(
                len(added), len(removed), time.perf_counter() - start
            )
        )
        return True

    def _recapture_ghosts(self, gf, group):
        """Update a frame's ghosts from the current pose.

        Ghosts are updated in place when possible, and rebuilt (with the
        frame's current look) otherwise.

        Args:
            gf (GhostFrame): The frame record.
            group (str): Its group full path.
        """
        for i, ghost in enumerate(gf.ghosts):
            if not cmds.objExists(ghost.source):
                continue
            path = ghost.path()
            if path and copy_pose(ghost.source, path):
                continue
            if path:
                cmds.delete(path)
            path = duplicate_ghost(
                ghost.source, ghost_name(gf.frame, ghost.source), group
            )
            gf.ghosts[i] = Ghost(path, ghost.source)
            self._apply_look_to(gf.ghosts[i], gf.look)

    def _ensure_ghost_shaders(self):
        """Create or update the previous and post ghost shaders."""
        with utils.undo_disabled():
            for name, color in (
                (PREV_SHADER, self.prev_color),
                (POST_SHADER, self.post_color),
            ):
                nodes = shading.create_flat_shader(name, color, self.transparency)
                _set_do_not_write(nodes)

    def _look_for(self, state):
        """Return the look a visible ghost frame should have.

        Args:
            state (int): ``STATE_PREV`` or ``STATE_POST``.

        Returns:
            str: A ghost shading group, or ``LOOK_ORIGINAL``.
        """
        if not self.use_ghost_color:
            return LOOK_ORIGINAL
        return PREV_SG if state == STATE_PREV else POST_SG

    def _apply_look(self, gf, look):
        """Give every ghost of a frame a look.

        Args:
            gf (GhostFrame): The frame record.
            look (str): A ghost shading group, or ``LOOK_ORIGINAL``.
        """
        if look == LOOK_ORIGINAL:
            for ghost in gf.ghosts:
                self._apply_look_to(ghost, look)
        else:
            shapes = [s for g in gf.ghosts for s in g.shape_paths()]
            if shapes:
                cmds.sets(shapes, edit=True, forceElement=look)
        gf.look = look

    def _apply_look_to(self, ghost, look):
        """Give one ghost a look.

        Args:
            ghost (Ghost): The ghost record.
            look (str): A ghost shading group, or ``LOOK_ORIGINAL`` for the
                source's per-face shading.
        """
        shapes = ghost.shape_paths()
        if not shapes:
            return
        if look != LOOK_ORIGINAL:
            cmds.sets(shapes, edit=True, forceElement=look)
            return
        if ghost.source not in self._shading_cache:
            if not cmds.objExists(ghost.source):
                return
            self._shading_cache[ghost.source] = [
                shading.get_face_shader_mapping(s) for s in _mesh_shapes(ghost.source)
            ]
        for shape, mapping in zip(shapes, self._shading_cache[ghost.source]):
            shading.apply_face_shader_mapping(shape, mapping)

    def _frame_at(self, frame):
        """Return the frame record for a frame number.

        Args:
            frame (float): Frame number.

        Returns:
            GhostFrame: The record, or None when there is no ghost there.
        """
        for gf in self._frames.values():
            if abs(gf.frame - frame) <= TOLERANCE:
                return gf
        return None

    def _frame_of_selected(self, dag_path):
        """Return the frame record a selected DAG node belongs to.

        Args:
            dag_path (om2.MDagPath): A selected node.

        Returns:
            GhostFrame: The record, or None for non-ghost nodes.
        """
        path = om2.MDagPath(dag_path)
        while path.length() > 0:
            gf = self._frames.get(om2.MObjectHandle(path.node()).hashCode())
            if gf is not None:
                return gf
            path.pop()
        return None

    # -----------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------
    def _start_callbacks(self):
        """Register the time, playback, tick, selection and scene
        callbacks."""
        cbm = self._callbacks
        cbm.eventCB("timeChanged", self._on_time_changed, "timeChanged")
        cbm.conditionCB("playingBack", self._on_playing_back, "playingBack")
        cbm.timerCB("tick", self._on_tick, TICK_PERIOD)
        cbm.selectionChangedCB("selection", self._on_selection_changed)
        cbm.sceneMessageCB(
            "beforeNew", self._on_scene_change, om2.MSceneMessage.kBeforeNew
        )
        cbm.sceneMessageCB(
            "beforeOpen", self._on_scene_change, om2.MSceneMessage.kBeforeOpen
        )

    def _on_time_changed(self, *args):
        """Refresh on time change and restart the settle countdown."""
        if self._busy:
            return
        self.refresh()
        self._last_time_change = time.perf_counter()

    def _on_playing_back(self, state, *args):
        """Refresh once when playback stops.

        Args:
            state (bool): True when playback starts, False when it stops.
        """
        if not state:
            self.refresh()

    def _on_tick(self, *args):
        """Re-capture once scrubbing settles, and follow the camera."""
        if self._busy or not self._frames:
            return
        if (
            self._last_time_change is not None
            and time.perf_counter() - self._last_time_change >= UPDATE_SETTLE
        ):
            self._last_time_change = None
            self._on_scrub_settled()
        if self._update_camera():
            self.refresh()

    def _update_camera(self, force=False):
        """Cache the active camera's right axis when the camera moved.

        Args:
            force (bool, optional): Update even when the matrix is unchanged.

        Returns:
            bool: True when the cached axis was updated.
        """
        camera = utils.get_active_camera()
        if not camera:
            return False
        matrix = cmds.xform(camera, query=True, matrix=True, worldSpace=True)
        if (
            not force
            and self._camera_matrix is not None
            and not matrix_changed(matrix, self._camera_matrix)
        ):
            return False
        self._camera_matrix = matrix
        self._camera_right = utils.get_camera_axis(camera, "x", matrix=matrix)
        return True

    def _on_scrub_settled(self):
        """Sync ghosts with the keys and re-capture the parked ghost.

        Runs once the playhead has settled after a time change.
        """
        self.sync_keys()
        current = cmds.currentTime(query=True)
        if (
            self._parked_frame is not None
            and not same_frame(current, self._parked_frame)
            and self._frame_at(self._parked_frame) is not None
        ):
            self.recapture(self._parked_frame, current)
        gf = self._frame_at(current)
        self._parked_frame = gf.frame if gf else None

    def _on_selection_changed(self, *args):
        """Jump to the frame of a selected ghost, keeping the rig selection."""
        if self._busy or not self._frames:
            return
        selection = om2.MGlobal.getActiveSelectionList()
        target = None
        for i in range(selection.length()):
            try:
                dag_path = selection.getDagPath(i)
            except (TypeError, RuntimeError):
                continue
            gf = self._frame_of_selected(dag_path)
            if gf is not None:
                target = gf.frame
                break
        if target is None:
            self._prev_selection = selection.getSelectionStrings()
            return

        current = cmds.currentTime(query=True)
        if abs(target - current) > TOLERANCE:
            # Re-capture the frame being left while still on it, then move
            # once, so the settle countdown does not flip the time back.
            leaving = self._frame_at(current)
            if leaving is not None:
                self.recapture(leaving.frame, current)
            cmds.currentTime(target, edit=True)
            self._parked_frame = target
        with self._suppressed():
            _restore_selection(self._prev_selection)

    def _on_scene_change(self, *args):
        """Drop callbacks and ghost data before a new or opened scene."""
        self.teardown()
