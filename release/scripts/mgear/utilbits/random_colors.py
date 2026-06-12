"""
Maya Random Color Tool - Blender Style
Assigns random muted/pastel colors to selected objects using OpenPBR shaders
"""

import random
import colorsys

import maya.cmds as cmds

from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core.pyqt import maya_main_window


RANDOM_COLOR_PREFIX = "RandomColor_"
DEFAULT_SG = "initialShadingGroup"
COLORABLE_SHAPE_TYPES = ("mesh", "nurbsSurface")

# Module-level state so tracking persists across UI close/reopen.
_original_assignments = {}
_random_assignments = {}
_tracked_objects = []
_active = False


class BlenderColorPalette:
    """
    Generates colors similar to Blender's Random Color feature.
    Uses HSV color space with controlled saturation and value
    to create muted, pastel-like tones.
    """

    # Predefined color palette inspired by Blender's random colors
    # These are the base hues with variations
    BLENDER_HUES = [
        0.95,   # Pink/Rose
        0.02,   # Coral/Salmon
        0.08,   # Orange/Peach
        0.12,   # Yellow/Gold
        0.18,   # Yellow-Green/Olive
        0.28,   # Green/Sage
        0.38,   # Teal/Seafoam
        0.48,   # Cyan/Sky
        0.58,   # Blue/Periwinkle
        0.68,   # Purple/Lavender
        0.78,   # Magenta/Mauve
        0.88,   # Pink/Dusty Rose
    ]

    @classmethod
    def generate_blender_color(cls, saturation_range=(0.25, 0.55),
                                value_range=(0.55, 0.85)):
        """
        Generate a single random color in Blender's style.

        Args:
            saturation_range: Tuple of (min, max) saturation (0-1)
            value_range: Tuple of (min, max) value/brightness (0-1)

        Returns:
            Tuple of (r, g, b) values in 0-1 range
        """
        # Pick a base hue and add some variation
        base_hue = random.choice(cls.BLENDER_HUES)
        hue = (base_hue + random.uniform(-0.05, 0.05)) % 1.0

        # Muted saturation for that pastel look
        saturation = random.uniform(*saturation_range)

        # Medium-high value for visibility
        value = random.uniform(*value_range)

        # Convert HSV to RGB
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)

        return (r, g, b)

    @classmethod
    def generate_fully_random_color(cls, saturation_range=(0.25, 0.55),
                                     value_range=(0.55, 0.85)):
        """
        Generate a fully random color (any hue) with Blender-style muting.
        """
        hue = random.random()
        saturation = random.uniform(*saturation_range)
        value = random.uniform(*value_range)

        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return (r, g, b)

    @classmethod
    def generate_harmony_colors(cls, count, harmony_type="complementary"):
        """
        Generate harmonious colors based on color theory.

        Args:
            count: Number of colors to generate
            harmony_type: One of "complementary", "triadic", "analogous", "split"
        """
        colors = []
        base_hue = random.random()

        if harmony_type == "complementary":
            hue_offsets = [0, 0.5]
        elif harmony_type == "triadic":
            hue_offsets = [0, 0.333, 0.666]
        elif harmony_type == "analogous":
            hue_offsets = [-0.083, 0, 0.083]
        elif harmony_type == "split":
            hue_offsets = [0, 0.416, 0.583]
        else:
            hue_offsets = [0]

        for i in range(count):
            offset = hue_offsets[i % len(hue_offsets)]
            hue = (base_hue + offset + random.uniform(-0.03, 0.03)) % 1.0
            saturation = random.uniform(0.25, 0.55)
            value = random.uniform(0.55, 0.85)

            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            colors.append((r, g, b))

        return colors


# ================================================================
# Colorable object discovery
# ================================================================


def _get_colorable_shapes(transform):
    """Return non-intermediate mesh/NURBS shapes under transform.

    Args:
        transform (str): Transform long name.

    Returns:
        list: Shape long names, empty if none or transform is gone.
    """
    if not cmds.objExists(transform):
        return []
    shapes = cmds.listRelatives(
        transform,
        shapes=True,
        fullPath=True,
        noIntermediate=True,
        type=COLORABLE_SHAPE_TYPES,
    )
    return shapes or []


def get_selected_colorable_transforms():
    """Return selected transforms that have a colorable shape.

    Accepts mesh or NURBS shapes directly (mapped to their parent
    transform) as well as their parent transforms.

    Returns:
        list: Deduplicated transform long names.
    """
    selection = cmds.ls(selection=True, long=True) or []
    transforms = []
    seen = set()
    for node in selection:
        target = node
        node_type = cmds.nodeType(node)
        if node_type in COLORABLE_SHAPE_TYPES:
            parents = cmds.listRelatives(
                node, parent=True, fullPath=True
            )
            if not parents:
                continue
            target = parents[0]
        if not _get_colorable_shapes(target):
            continue
        if target not in seen:
            seen.add(target)
            transforms.append(target)
    return transforms


def get_all_colorable_transforms():
    """Return every transform in the scene with a colorable shape.

    Returns:
        list: Sorted transform long names, intermediate shapes skipped.
    """
    shapes = cmds.ls(
        type=COLORABLE_SHAPE_TYPES,
        noIntermediate=True,
        long=True,
    ) or []
    transforms = set()
    for shape in shapes:
        parents = cmds.listRelatives(
            shape, parent=True, fullPath=True
        )
        if parents:
            transforms.add(parents[0])
    return sorted(transforms)


# ================================================================
# Assignment snapshot / restore
# ================================================================


def store_assignments(transforms, target_dict):
    """Snapshot per-shape shading group membership.

    Mirrors the matcap_viewer pattern: records each SG the shape
    belongs to and normalizes every member name to the shape's
    full DAG path so restore always resolves.  Shapes already
    present in target_dict are skipped so repeated snapshots never
    overwrite an earlier capture (important for Apply-then-Apply
    without Remove All: the true originals survive).

    Args:
        transforms (list): Transform long names.
        target_dict (dict): Mutated in place - shape -> list of
            (sg, members_or_None) tuples.
    """
    for transform in transforms:
        shapes = _get_colorable_shapes(transform)
        if not shapes:
            continue
        short_transform = transform.rsplit("|", 1)[-1]
        for shape in shapes:
            if shape in target_dict:
                continue
            short_shape = shape.rsplit("|", 1)[-1]
            prefixes = (shape, short_shape, transform, short_transform)
            sgs = cmds.listSets(type=1, object=shape) or []
            assignments = []
            for sg in sgs:
                members = cmds.sets(sg, query=True) or []
                shape_members = []
                for member in members:
                    for prefix in prefixes:
                        if member == prefix:
                            shape_members.append(shape)
                            break
                        if member.startswith(prefix + "."):
                            suffix = member[len(prefix):]
                            shape_members.append(shape + suffix)
                            break
                if shape_members:
                    assignments.append((sg, shape_members))
                elif not assignments:
                    assignments.append((sg, None))
            if assignments:
                target_dict[shape] = assignments


def _restore_from(source_dict, sweep_prefix=None):
    """Reapply stored assignments, optionally sweeping residuals.

    Args:
        source_dict (dict): Output of store_assignments - shape ->
            [(sg, members_or_None), ...].
        sweep_prefix (str, optional): If set, any shape still in an
            SG whose name starts with this prefix after the restore
            is forced to initialShadingGroup.  Used to clear stray
            RandomColor_* membership when restoring originals.
    """
    affected_shapes = []
    for shape, assignments in source_dict.items():
        if not cmds.objExists(shape):
            continue
        affected_shapes.append(shape)
        for sg, members in assignments:
            if not cmds.objExists(sg):
                continue
            if members is None:
                cmds.sets(shape, edit=True, forceElement=sg)
            else:
                valid = [m for m in members if cmds.objExists(m)]
                if valid:
                    cmds.sets(valid, edit=True, forceElement=sg)

    if not sweep_prefix:
        return
    for shape in affected_shapes:
        stray = any(
            sg.startswith(sweep_prefix)
            for sg in (cmds.listSets(type=1, object=shape) or [])
        )
        if not stray:
            continue
        try:
            cmds.sets(shape, edit=True, forceElement=DEFAULT_SG)
        except (RuntimeError, ValueError):
            pass


def restore_originals():
    """Restore original materials on every tracked shape.

    Leaves _original_assignments / _random_assignments / tracking
    intact so Toggle can flip back to random colors.
    """
    global _active
    if not _original_assignments:
        _active = False
        return
    cmds.undoInfo(openChunk=True)
    try:
        _restore_from(
            _original_assignments,
            sweep_prefix=RANDOM_COLOR_PREFIX,
        )
        _active = False
    finally:
        cmds.undoInfo(closeChunk=True)


def reapply_random_colors():
    """Re-assign the last-captured random-color SGs to tracked shapes."""
    global _active
    if not _random_assignments:
        return
    cmds.undoInfo(openChunk=True)
    try:
        _restore_from(_random_assignments)
        _active = True
    finally:
        cmds.undoInfo(closeChunk=True)


def toggle_random_colors():
    """Flip between originals and last-applied random colors.

    Returns:
        str: "off", "on", or "empty" (nothing tracked yet).
    """
    if _active:
        restore_originals()
        return "off"
    if _random_assignments:
        reapply_random_colors()
        return "on"
    return "empty"


def remove_colors(transforms=None):
    """Restore originals and drop tracking for the given transforms.

    Args:
        transforms (list, optional): Transform long names to remove
            from tracking.  None means "all tracked" - equivalent to
            the old remove-all behavior.  Anything not currently
            tracked is silently skipped.

    Returns:
        int: Number of transforms that were actually removed.
    """
    global _active

    if not _original_assignments and not _random_assignments:
        return 0

    if transforms is None:
        targets = list(_tracked_objects)
    else:
        tracked_set = set(_tracked_objects)
        targets = [t for t in transforms if t in tracked_set]

    if not targets:
        return 0

    target_shapes = set()
    for transform in targets:
        for shape in _get_colorable_shapes(transform):
            target_shapes.add(shape)

    partial_originals = {
        shape: _original_assignments[shape]
        for shape in target_shapes
        if shape in _original_assignments
    }

    cmds.undoInfo(openChunk=True)
    try:
        _restore_from(
            partial_originals,
            sweep_prefix=RANDOM_COLOR_PREFIX,
        )

        sgs_to_delete = set()
        for shape in target_shapes:
            for sg, _members in _random_assignments.get(shape, []):
                if sg and sg.startswith(RANDOM_COLOR_PREFIX):
                    sgs_to_delete.add(sg)
        for sg in sgs_to_delete:
            if not cmds.objExists(sg):
                continue
            # Skip SGs still referenced by a shape we are not
            # removing in this call.
            remaining = cmds.sets(sg, query=True) or []
            if remaining:
                continue
            shader = cmds.listConnections(
                sg + ".surfaceShader", source=True, destination=False
            ) or []
            try:
                cmds.delete(sg)
            except RuntimeError:
                pass
            for node in shader:
                if cmds.objExists(node):
                    try:
                        cmds.delete(node)
                    except RuntimeError:
                        pass
    finally:
        cmds.undoInfo(closeChunk=True)

    for shape in target_shapes:
        _original_assignments.pop(shape, None)
        _random_assignments.pop(shape, None)
    for transform in targets:
        if transform in _tracked_objects:
            _tracked_objects.remove(transform)
    if not _tracked_objects:
        _active = False
    return len(targets)


class RandomColorTool(QtWidgets.QWidget):
    """Main UI widget for the Random Color Tool"""

    WINDOW_TITLE = "Random Color Tool"
    WINDOW_NAME = "randomColorToolWindow"

    def __init__(self, parent=None):
        # Delete existing window if it exists
        self.delete_existing_window()

        super(RandomColorTool, self).__init__(parent or maya_main_window())

        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setMinimumWidth(320)

        self.setup_ui()
        self.connect_signals()

    def delete_existing_window(self):
        """Delete any existing instance of this window"""
        existing = maya_main_window().findChild(
            QtWidgets.QWidget, self.WINDOW_NAME
        )
        if existing:
            existing.deleteLater()

    def setup_ui(self):
        """Create the UI layout"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # === Color Mode Group ===
        mode_group = QtWidgets.QGroupBox("Color Mode")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([
            "Blender Palette (Recommended)",
            "Fully Random",
            "Complementary Harmony",
            "Triadic Harmony",
            "Analogous Harmony"
        ])
        mode_layout.addWidget(self.mode_combo)

        main_layout.addWidget(mode_group)

        # === Saturation Controls ===
        sat_group = QtWidgets.QGroupBox("Saturation Range")
        sat_layout = QtWidgets.QVBoxLayout(sat_group)

        # Min saturation
        sat_min_layout = QtWidgets.QHBoxLayout()
        sat_min_layout.addWidget(QtWidgets.QLabel("Min:"))
        self.sat_min_spin = QtWidgets.QDoubleSpinBox()
        self.sat_min_spin.setRange(0.0, 1.0)
        self.sat_min_spin.setSingleStep(0.05)
        self.sat_min_spin.setValue(0.25)
        sat_min_layout.addWidget(self.sat_min_spin)
        sat_layout.addLayout(sat_min_layout)

        # Max saturation
        sat_max_layout = QtWidgets.QHBoxLayout()
        sat_max_layout.addWidget(QtWidgets.QLabel("Max:"))
        self.sat_max_spin = QtWidgets.QDoubleSpinBox()
        self.sat_max_spin.setRange(0.0, 1.0)
        self.sat_max_spin.setSingleStep(0.05)
        self.sat_max_spin.setValue(0.55)
        sat_max_layout.addWidget(self.sat_max_spin)
        sat_layout.addLayout(sat_max_layout)

        main_layout.addWidget(sat_group)

        # === Value/Brightness Controls ===
        val_group = QtWidgets.QGroupBox("Brightness Range")
        val_layout = QtWidgets.QVBoxLayout(val_group)

        # Min value
        val_min_layout = QtWidgets.QHBoxLayout()
        val_min_layout.addWidget(QtWidgets.QLabel("Min:"))
        self.val_min_spin = QtWidgets.QDoubleSpinBox()
        self.val_min_spin.setRange(0.0, 1.0)
        self.val_min_spin.setSingleStep(0.05)
        self.val_min_spin.setValue(0.55)
        val_min_layout.addWidget(self.val_min_spin)
        val_layout.addLayout(val_min_layout)

        # Max value
        val_max_layout = QtWidgets.QHBoxLayout()
        val_max_layout.addWidget(QtWidgets.QLabel("Max:"))
        self.val_max_spin = QtWidgets.QDoubleSpinBox()
        self.val_max_spin.setRange(0.0, 1.0)
        self.val_max_spin.setSingleStep(0.05)
        self.val_max_spin.setValue(0.85)
        val_max_layout.addWidget(self.val_max_spin)
        val_layout.addLayout(val_max_layout)

        main_layout.addWidget(val_group)

        # === Options ===
        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QVBoxLayout(options_group)

        self.unique_colors_cb = QtWidgets.QCheckBox("Unique color per object")
        self.unique_colors_cb.setChecked(True)
        options_layout.addWidget(self.unique_colors_cb)

        self.reuse_materials_cb = QtWidgets.QCheckBox(
            "Reuse existing RandomColor materials"
        )
        self.reuse_materials_cb.setChecked(False)
        self.reuse_materials_cb.setToolTip(
            "If checked, will try to find and reuse existing RandomColor_* materials"
        )
        options_layout.addWidget(self.reuse_materials_cb)

        self.apply_to_all_cb = QtWidgets.QCheckBox(
            "Apply to all (scene mesh + NURBS)"
        )
        self.apply_to_all_cb.setChecked(False)
        self.apply_to_all_cb.setToolTip(
            "When checked, ignore selection and apply to every "
            "mesh and NURBS surface in the scene."
        )
        options_layout.addWidget(self.apply_to_all_cb)

        main_layout.addWidget(options_group)

        # === Preset Buttons ===
        preset_group = QtWidgets.QGroupBox("Quick Presets")
        preset_layout = QtWidgets.QHBoxLayout(preset_group)

        self.preset_pastel_btn = QtWidgets.QPushButton("Pastel")
        self.preset_pastel_btn.setToolTip("Soft, light colors")
        preset_layout.addWidget(self.preset_pastel_btn)

        self.preset_muted_btn = QtWidgets.QPushButton("Muted")
        self.preset_muted_btn.setToolTip("Desaturated, earthy tones")
        preset_layout.addWidget(self.preset_muted_btn)

        self.preset_vibrant_btn = QtWidgets.QPushButton("Vibrant")
        self.preset_vibrant_btn.setToolTip("More saturated colors")
        preset_layout.addWidget(self.preset_vibrant_btn)

        main_layout.addWidget(preset_group)

        # === Action Buttons ===
        action_layout = QtWidgets.QHBoxLayout()

        self.apply_btn = QtWidgets.QPushButton("Apply Random Colors")
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #5285a6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6395b6;
            }
            QPushButton:pressed {
                background-color: #4275a6;
            }
        """)
        action_layout.addWidget(self.apply_btn, 2)

        self.toggle_btn = QtWidgets.QPushButton("Toggle")
        self.toggle_btn.setMinimumHeight(40)
        self.toggle_btn.setToolTip(
            "Toggle between random colors and the original "
            "materials on all tracked objects."
        )
        action_layout.addWidget(self.toggle_btn, 1)

        main_layout.addLayout(action_layout)

        # === Utility Buttons ===
        util_layout = QtWidgets.QHBoxLayout()

        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.remove_btn.setToolTip(
            "Restore original materials.  With 'Apply to all' "
            "checked, restores every tracked object; otherwise "
            "restores only the selected tracked objects."
        )
        util_layout.addWidget(self.remove_btn)

        self.cleanup_btn = QtWidgets.QPushButton("Cleanup Unused")
        self.cleanup_btn.setToolTip("Delete unused RandomColor materials")
        util_layout.addWidget(self.cleanup_btn)

        main_layout.addLayout(util_layout)

        # === Status Label ===
        self.status_label = QtWidgets.QLabel(
            "Select objects and click 'Apply Random Colors'"
        )
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        main_layout.addWidget(self.status_label)

        main_layout.addStretch()

    def connect_signals(self):
        """Connect UI signals to slots"""
        self.apply_btn.clicked.connect(self.apply_random_colors)
        self.toggle_btn.clicked.connect(self.on_toggle)
        self.remove_btn.clicked.connect(self.on_remove)
        self.cleanup_btn.clicked.connect(self.cleanup_unused_materials)

        self.preset_pastel_btn.clicked.connect(self.apply_pastel_preset)
        self.preset_muted_btn.clicked.connect(self.apply_muted_preset)
        self.preset_vibrant_btn.clicked.connect(self.apply_vibrant_preset)

    def apply_pastel_preset(self):
        """Apply pastel color preset"""
        self.sat_min_spin.setValue(0.20)
        self.sat_max_spin.setValue(0.40)
        self.val_min_spin.setValue(0.75)
        self.val_max_spin.setValue(0.95)
        self.status_label.setText("Preset: Pastel")

    def apply_muted_preset(self):
        """Apply muted/earthy color preset"""
        self.sat_min_spin.setValue(0.15)
        self.sat_max_spin.setValue(0.35)
        self.val_min_spin.setValue(0.45)
        self.val_max_spin.setValue(0.65)
        self.status_label.setText("Preset: Muted")

    def apply_vibrant_preset(self):
        """Apply vibrant color preset"""
        self.sat_min_spin.setValue(0.50)
        self.sat_max_spin.setValue(0.75)
        self.val_min_spin.setValue(0.65)
        self.val_max_spin.setValue(0.85)
        self.status_label.setText("Preset: Vibrant")

    def create_openpbr_shader(self, name, color):
        """
        Create an OpenPBR shader with the given color.

        Args:
            name: Name for the shader
            color: Tuple of (r, g, b) values in 0-1 range

        Returns:
            Tuple of (shader_node, shading_group)
        """
        # Create the OpenPBR surface shader
        shader = cmds.shadingNode('standardSurface', asShader=True, name=name)

        # Create shading group
        sg = cmds.sets(renderable=True, noSurfaceShader=True,
                       empty=True, name=f"{name}SG")

        # Connect shader to shading group
        cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)

        # Set the base color
        cmds.setAttr(f"{shader}.baseColor", color[0], color[1], color[2], type='double3')

        # Set some nice default values for a clean look
        cmds.setAttr(f"{shader}.base", 1.0)
        cmds.setAttr(f"{shader}.specular", 0.3)
        cmds.setAttr(f"{shader}.specularRoughness", 0.4)

        return shader, sg

    def assign_material(self, transform, shading_group):
        """Assign a shading group to every colorable shape."""
        for shape in _get_colorable_shapes(transform):
            cmds.sets(shape, edit=True, forceElement=shading_group)

    def apply_random_colors(self):
        """Apply random colors to selected or all colorable objects."""
        global _random_assignments
        global _tracked_objects
        global _active

        if self.apply_to_all_cb.isChecked():
            transforms = get_all_colorable_transforms()
            empty_msg = "No mesh or NURBS objects in the scene."
        else:
            transforms = get_selected_colorable_transforms()
            empty_msg = "No mesh or NURBS objects selected!"

        if not transforms:
            self.status_label.setText(empty_msg)
            cmds.warning(empty_msg)
            return

        sat_range = (self.sat_min_spin.value(), self.sat_max_spin.value())
        val_range = (self.val_min_spin.value(), self.val_max_spin.value())
        mode = self.mode_combo.currentIndex()
        unique_colors = self.unique_colors_cb.isChecked()

        if mode == 0:
            if unique_colors:
                colors = [
                    BlenderColorPalette.generate_blender_color(
                        sat_range, val_range
                    )
                    for _ in transforms
                ]
            else:
                single = BlenderColorPalette.generate_blender_color(
                    sat_range, val_range
                )
                colors = [single] * len(transforms)
        elif mode == 1:
            if unique_colors:
                colors = [
                    BlenderColorPalette.generate_fully_random_color(
                        sat_range, val_range
                    )
                    for _ in transforms
                ]
            else:
                single = BlenderColorPalette.generate_fully_random_color(
                    sat_range, val_range
                )
                colors = [single] * len(transforms)
        else:
            harmony_types = {
                2: "complementary",
                3: "triadic",
                4: "analogous",
            }
            harmony = harmony_types.get(mode, "complementary")
            colors = BlenderColorPalette.generate_harmony_colors(
                len(transforms), harmony
            )

        cmds.undoInfo(openChunk=True)
        try:
            # Snapshot originals for any transforms we have not
            # seen yet.  Repeated Apply without Remove All keeps
            # the true pre-apply state.
            store_assignments(transforms, _original_assignments)

            # Re-snapshot random-color SGs from scratch for the
            # set being (re)applied now.  We drop only the
            # affected shapes so previously tracked objects left
            # untouched by this apply still round-trip on Toggle.
            affected_shapes = []
            for transform in transforms:
                affected_shapes.extend(_get_colorable_shapes(transform))
            for shape in affected_shapes:
                _random_assignments.pop(shape, None)

            created_count = 0
            for transform, color in zip(transforms, colors):
                short_name = (
                    transform.split("|")[-1].replace(":", "_")
                )
                material_name = "{prefix}{name}_{rand}".format(
                    prefix=RANDOM_COLOR_PREFIX,
                    name=short_name,
                    rand=random.randint(1000, 9999),
                )
                shader, sg = self.create_openpbr_shader(
                    material_name, color
                )
                self.assign_material(transform, sg)
                created_count += 1

            store_assignments(transforms, _random_assignments)

            for transform in transforms:
                if transform not in _tracked_objects:
                    _tracked_objects.append(transform)
            _active = True

            self.status_label.setText(
                f"Applied colors to {created_count} object(s)"
            )
        except Exception as e:
            cmds.warning(f"Error applying colors: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
        finally:
            cmds.undoInfo(closeChunk=True)

    def on_toggle(self):
        """Toggle between random colors and originals on tracked set."""
        result = toggle_random_colors()
        if result == "off":
            self.status_label.setText(
                f"Originals restored on {len(_tracked_objects)} object(s)"
            )
        elif result == "on":
            self.status_label.setText(
                f"Random colors reapplied to {len(_tracked_objects)} object(s)"
            )
        else:
            self.status_label.setText(
                "Nothing tracked yet - click Apply first."
            )

    def on_remove(self):
        """Remove random colors from all tracked or just the selection.

        When "Apply to all" is checked, restores originals on every
        tracked object.  Otherwise, restores only the tracked objects
        currently selected - lets the user undo parts of a prior apply.
        """
        if self.apply_to_all_cb.isChecked():
            count = remove_colors(None)
            empty_msg = "Nothing to remove."
        else:
            selected = get_selected_colorable_transforms()
            if not selected:
                self.status_label.setText(
                    "No mesh or NURBS objects selected!"
                )
                return
            count = remove_colors(selected)
            empty_msg = "Selected objects are not tracked."
        if count:
            self.status_label.setText(
                f"Removed random colors from {count} object(s)"
            )
        else:
            self.status_label.setText(empty_msg)

    def cleanup_unused_materials(self):
        """Delete unused RandomColor materials"""
        # Find all RandomColor materials
        all_materials = cmds.ls(materials=True)
        random_materials = [m for m in all_materials if m.startswith("RandomColor_")]

        deleted_count = 0

        for mat in random_materials:
            # Get the shading group
            sgs = cmds.listConnections(mat, type='shadingEngine') or []

            for sg in sgs:
                # Check if anything is connected to this shading group
                members = cmds.sets(sg, query=True) or []

                if not members:
                    # Delete the shading group and material
                    try:
                        cmds.delete(sg)
                        deleted_count += 1
                    except:
                        pass

            # Try to delete the material if it has no connections
            if not cmds.listConnections(mat, type='shadingEngine'):
                try:
                    cmds.delete(mat)
                except:
                    pass

        self.status_label.setText(f"Cleaned up {deleted_count} unused material(s)")


def show():
    """Show the Random Color Tool window"""
    global random_color_tool_window

    try:
        random_color_tool_window.close()
        random_color_tool_window.deleteLater()
    except:
        pass

    random_color_tool_window = RandomColorTool()
    random_color_tool_window.show()

    return random_color_tool_window


# Run if executed directly in Maya
if __name__ == "__main__":
    show()
