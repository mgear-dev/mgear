"""
Maya Random Color Tool - Blender Style
Assigns random muted/pastel colors to selected objects using OpenPBR shaders
"""

import random
import colorsys

import maya.cmds as cmds

from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core.pyqt import maya_main_window


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
        action_layout.addWidget(self.apply_btn)

        main_layout.addLayout(action_layout)

        # === Utility Buttons ===
        util_layout = QtWidgets.QHBoxLayout()

        self.remove_btn = QtWidgets.QPushButton("Remove Colors")
        self.remove_btn.setToolTip("Remove RandomColor materials from selected objects")
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
        self.remove_btn.clicked.connect(self.remove_random_colors)
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

    def get_selected_meshes(self):
        """Get selected mesh transform nodes"""
        selection = cmds.ls(selection=True, long=True)
        meshes = []

        for obj in selection:
            # Check if it's a mesh or has a mesh shape
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh', fullPath=True) or []
            if shapes:
                meshes.append(obj)
            elif cmds.nodeType(obj) == 'mesh':
                parent = cmds.listRelatives(obj, parent=True, fullPath=True)
                if parent:
                    meshes.append(parent[0])

        return meshes

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

    def assign_material(self, mesh, shading_group):
        """Assign a shading group to a mesh"""
        shapes = cmds.listRelatives(mesh, shapes=True, type='mesh', fullPath=True) or []
        for shape in shapes:
            cmds.sets(shape, edit=True, forceElement=shading_group)

    def apply_random_colors(self):
        """Main function to apply random colors to selected objects"""
        meshes = self.get_selected_meshes()

        if not meshes:
            self.status_label.setText("No mesh objects selected!")
            cmds.warning("No mesh objects selected!")
            return

        # Get settings
        sat_range = (self.sat_min_spin.value(), self.sat_max_spin.value())
        val_range = (self.val_min_spin.value(), self.val_max_spin.value())
        mode = self.mode_combo.currentIndex()
        unique_colors = self.unique_colors_cb.isChecked()

        # Generate colors based on mode
        if mode == 0:  # Blender Palette
            if unique_colors:
                colors = [BlenderColorPalette.generate_blender_color(sat_range, val_range)
                          for _ in meshes]
            else:
                single_color = BlenderColorPalette.generate_blender_color(sat_range, val_range)
                colors = [single_color] * len(meshes)

        elif mode == 1:  # Fully Random
            if unique_colors:
                colors = [BlenderColorPalette.generate_fully_random_color(sat_range, val_range)
                          for _ in meshes]
            else:
                single_color = BlenderColorPalette.generate_fully_random_color(sat_range, val_range)
                colors = [single_color] * len(meshes)

        else:  # Harmony modes
            harmony_types = {2: "complementary", 3: "triadic", 4: "analogous"}
            harmony = harmony_types.get(mode, "complementary")
            colors = BlenderColorPalette.generate_harmony_colors(len(meshes), harmony)

        # Start undo chunk
        cmds.undoInfo(openChunk=True)

        try:
            created_count = 0

            for mesh, color in zip(meshes, colors):
                # Create unique material name
                short_name = mesh.split('|')[-1].replace(':', '_')
                material_name = f"RandomColor_{short_name}_{random.randint(1000, 9999)}"

                # Create shader and assign
                shader, sg = self.create_openpbr_shader(material_name, color)
                self.assign_material(mesh, sg)
                created_count += 1

            self.status_label.setText(f"Applied colors to {created_count} object(s)")

        except Exception as e:
            cmds.warning(f"Error applying colors: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")

        finally:
            cmds.undoInfo(closeChunk=True)

    def remove_random_colors(self):
        """Remove RandomColor materials from selected objects and assign default"""
        meshes = self.get_selected_meshes()

        if not meshes:
            self.status_label.setText("No mesh objects selected!")
            return

        cmds.undoInfo(openChunk=True)

        try:
            # Get default lambert
            default_sg = "initialShadingGroup"

            for mesh in meshes:
                shapes = cmds.listRelatives(mesh, shapes=True, type='mesh', fullPath=True) or []
                for shape in shapes:
                    cmds.sets(shape, edit=True, forceElement=default_sg)

            self.status_label.setText(f"Reset {len(meshes)} object(s) to default material")

        except Exception as e:
            cmds.warning(f"Error removing colors: {str(e)}")

        finally:
            cmds.undoInfo(closeChunk=True)

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
