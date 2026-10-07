"""Blocking Ghosts window."""

import json
import os

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.core import pyqt
from mgear.core import widgets

from . import __version__
from . import core

SETTINGS_PREFIX = "blockingGhosts_"
CONFIG_EXT = ".bgh"
CONFIG_FILTER = "Blocking Ghosts (*.bgh);;JSON (*.json)"
MAX_SPACING = 500
MAX_FRAME = 1000000

# Above this many poses, Generate asks for confirmation first.
MAX_POSES_WITHOUT_CONFIRM = 30

# Default value of every saved setting, keyed by its configuration name.
DEFAULTS = {
    "objects": [],
    "controls": [],
    "start_frame": 1,
    "end_frame": 120,
    "prev_color": list(core.DEFAULT_PREV_COLOR),
    "post_color": list(core.DEFAULT_POST_COLOR),
    "transparency": 50,
    "spacing": 0,
    "ghost_color": True,
}

_GHOST_COLOR_TEXT = "Pre / Post Color"
_ORIGINAL_TEXT = "Original Shader"


class BlockingGhostsUI(MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin):
    """Dockable Blocking Ghosts window."""

    toolName = "blockingGhostsWindow"
    TOOL_TITLE = "Blocking Ghosts"

    def __init__(self, parent=None):
        """Initialize the window.

        Args:
            parent (QtWidgets.QWidget, optional): Parent widget.
        """
        super(BlockingGhostsUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)
        self.session = core.GhostSession()
        self.closed = False

        self.export_action = None
        self.import_action = None
        self.recent_menu = None
        self.objects_list = None
        self.controls_list = None
        self.start_spin = None
        self.end_spin = None
        self.timeline_btn = None
        self.prev_color_btn = None
        self.post_color_btn = None
        self.trans_slider = None
        self.trans_label = None
        self.spacing_slider = None
        self.spacing_label = None
        self.shader_toggle = None
        self.generate_btn = None
        self.clear_btn = None
        self.config_widgets = {}

        self.setObjectName(self.toolName)
        self.setWindowTitle("{} {}".format(self.TOOL_TITLE, __version__))
        self.setMinimumWidth(340)

        # Ghosts or callbacks left by a crashed or reloaded session.
        core.remove_stale_ghosts()

        self.setup_ui()
        self.config_widgets = {
            "objects": self.objects_list,
            "controls": self.controls_list,
            "start_frame": self.start_spin,
            "end_frame": self.end_spin,
            "prev_color": self.prev_color_btn,
            "post_color": self.post_color_btn,
            "transparency": self.trans_slider,
            "spacing": self.spacing_slider,
            "ghost_color": self.shader_toggle,
        }
        self.user_settings = {
            SETTINGS_PREFIX + key: (widget, DEFAULTS[key])
            for key, widget in self.config_widgets.items()
        }
        self.load_settings()
        self._update_labels()
        # Connected after loading, so restoring settings does not push
        # values into the session.
        self.create_connections()

    # -----------------------------------------------------------------
    # UI setup
    # -----------------------------------------------------------------
    def setup_ui(self):
        """Build the window."""
        self.create_actions()
        self.create_widgets()
        self.create_layouts()

    def create_actions(self):
        """Create the File menu actions."""
        self.export_action = QtWidgets.QAction("Export Configuration...", self)
        self.import_action = QtWidgets.QAction("Import Configuration...", self)
        self.recent_menu = widgets.RecentFilesMenu(
            SETTINGS_PREFIX + "recent",
            title="Recent Configurations",
            settings=self.settings,
            parent=self,
        )

    def create_widgets(self):
        """Create the widgets."""
        self.objects_list = widgets.NodeListWidget()
        self.controls_list = widgets.NodeListWidget()

        self.start_spin = QtWidgets.QSpinBox()
        self.start_spin.setRange(-MAX_FRAME, MAX_FRAME)
        self.start_spin.setValue(DEFAULTS["start_frame"])
        self.end_spin = QtWidgets.QSpinBox()
        self.end_spin.setRange(-MAX_FRAME, MAX_FRAME)
        self.end_spin.setValue(DEFAULTS["end_frame"])
        self.timeline_btn = QtWidgets.QPushButton("Timeline")
        self.timeline_btn.setToolTip("Use the timeline's playback range.")

        self.prev_color_btn = widgets.ColorSwatchButton(DEFAULTS["prev_color"])
        self.post_color_btn = widgets.ColorSwatchButton(DEFAULTS["post_color"])

        self.trans_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.trans_slider.setRange(0, 100)
        self.trans_slider.setValue(DEFAULTS["transparency"])
        self.trans_slider.setToolTip(
            "Ghost transparency. Applies to Pre / Post Color shading only."
        )
        self.trans_label = QtWidgets.QLabel()
        self.trans_label.setFixedWidth(34)

        self.spacing_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.spacing_slider.setRange(-MAX_SPACING, MAX_SPACING)
        self.spacing_slider.setValue(DEFAULTS["spacing"])
        self.spacing_slider.setToolTip(
            "Distance between poses along the camera's right axis, in world "
            "units. Positive values place previous poses on the right, negative "
            "values on the left."
        )
        self.spacing_label = QtWidgets.QLabel()
        self.spacing_label.setFixedWidth(34)

        self.shader_toggle = QtWidgets.QPushButton()
        self.shader_toggle.setCheckable(True)
        self.shader_toggle.setChecked(DEFAULTS["ghost_color"])

        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.clear_btn = QtWidgets.QPushButton("Clear")

    def create_layouts(self):
        """Arrange the widgets."""
        menu_bar = QtWidgets.QMenuBar()
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.export_action)
        file_menu.addAction(self.import_action)
        file_menu.addSeparator()
        file_menu.addMenu(self.recent_menu)

        frame_range = QtWidgets.QHBoxLayout()
        frame_range.addWidget(QtWidgets.QLabel("Frame range:"))
        frame_range.addWidget(self.start_spin)
        frame_range.addWidget(QtWidgets.QLabel("to"))
        frame_range.addWidget(self.end_spin)
        frame_range.addWidget(self.timeline_btn)
        frame_range.addStretch()

        colors = QtWidgets.QHBoxLayout()
        colors.addWidget(QtWidgets.QLabel("Previous color:"))
        colors.addWidget(self.prev_color_btn)
        colors.addSpacing(12)
        colors.addWidget(QtWidgets.QLabel("Post color:"))
        colors.addWidget(self.post_color_btn)
        colors.addStretch()

        transparency = QtWidgets.QHBoxLayout()
        transparency.addWidget(QtWidgets.QLabel("Transparency:"))
        transparency.addWidget(self.trans_slider)
        transparency.addWidget(self.trans_label)

        spacing = QtWidgets.QHBoxLayout()
        spacing.addWidget(QtWidgets.QLabel("Spacing:"))
        spacing.addWidget(self.spacing_slider)
        spacing.addWidget(self.spacing_label)

        shading = QtWidgets.QHBoxLayout()
        shading.addWidget(QtWidgets.QLabel("Shading:"))
        shading.addWidget(self.shader_toggle)
        shading.addStretch()

        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.generate_btn)
        actions.addWidget(self.clear_btn)

        main = QtWidgets.QVBoxLayout(self)
        main.setMenuBar(menu_bar)
        main.addWidget(QtWidgets.QLabel("Objects to ghost:"))
        main.addWidget(self.objects_list, 1)
        main.addWidget(QtWidgets.QLabel("Watch controls (keyframes):"))
        main.addWidget(self.controls_list, 1)
        main.addLayout(frame_range)
        main.addLayout(colors)
        main.addLayout(transparency)
        main.addLayout(spacing)
        main.addLayout(shading)
        main.addLayout(actions)

    def create_connections(self):
        """Connect signals to slots."""
        self.export_action.triggered.connect(self.export_config)
        self.import_action.triggered.connect(self.import_config)
        self.recent_menu.fileTriggered.connect(self.load_config_file)
        self.timeline_btn.clicked.connect(self.use_timeline_range)

        self.prev_color_btn.colorChanged.connect(self._on_colors)
        self.post_color_btn.colorChanged.connect(self._on_colors)
        self.trans_slider.valueChanged.connect(self._on_transparency)
        self.spacing_slider.valueChanged.connect(self._on_spacing)
        self.shader_toggle.toggled.connect(self._on_shader_toggle)
        self.generate_btn.clicked.connect(self._on_generate)
        self.clear_btn.clicked.connect(self.session.clear)

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------
    def _transparency(self):
        """Return the transparency slider as a 0-1 value.

        Returns:
            float: Transparency.
        """
        return self.trans_slider.value() / 100.0

    def _update_labels(self):
        """Show the current slider and toggle values."""
        self.trans_label.setText("{:.2f}".format(self._transparency()))
        self.spacing_label.setText(str(self.spacing_slider.value()))
        ghost_color = self.shader_toggle.isChecked()
        self.shader_toggle.setText(_GHOST_COLOR_TEXT if ghost_color else _ORIGINAL_TEXT)
        # Transparency only applies to the ghost colors.
        self.trans_slider.setEnabled(ghost_color)
        self.trans_label.setEnabled(ghost_color)

    def _sync_session(self):
        """Copy the current UI values into the session."""
        session = self.session
        session.objects = self.objects_list.nodes()
        session.controls = self.controls_list.nodes()
        session.start_frame = float(self.start_spin.value())
        session.end_frame = float(self.end_spin.value())
        session.prev_color = self.prev_color_btn.color()
        session.post_color = self.post_color_btn.color()
        session.transparency = self._transparency()
        session.spacing = float(self.spacing_slider.value())
        session.use_ghost_color = self.shader_toggle.isChecked()

    def use_timeline_range(self):
        """Set the frame range to the timeline's playback range."""
        self.start_spin.setValue(int(cmds.playbackOptions(query=True, minTime=True)))
        self.end_spin.setValue(int(cmds.playbackOptions(query=True, maxTime=True)))

    def _on_generate(self):
        """Generate ghosts from the current settings.

        Asks for confirmation first when the range holds many poses.
        """
        self._sync_session()
        count = len(self.session.sample_times())
        if count > MAX_POSES_WITHOUT_CONFIRM:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Blocking Ghosts",
                "The frame range has {} keyed poses. Every pose copies every "
                "object, which can be slow on heavy rigs.\n\n"
                "Generate all of them?".format(count),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.session.generate()

    def _on_colors(self, *args):
        """Apply the ghost colors live."""
        self.session.set_colors(
            self.prev_color_btn.color(), self.post_color_btn.color()
        )

    def _on_transparency(self, *args):
        """Apply the transparency live."""
        self._update_labels()
        self.session.set_transparency(self._transparency())

    def _on_spacing(self, value):
        """Apply the spacing live.

        Args:
            value (int): Slider value in world units.
        """
        self._update_labels()
        self.session.set_spacing(float(value))

    def _on_shader_toggle(self, checked):
        """Switch between ghost colors and original shading.

        Args:
            checked (bool): True for ghost colors.
        """
        self._update_labels()
        self.session.set_ghost_color(checked)

    # -----------------------------------------------------------------
    # Configuration files
    # -----------------------------------------------------------------
    def gather_config(self):
        """Return the current settings as a JSON-serializable dict.

        Returns:
            dict: Configuration.
        """
        return {
            key: self.get_widget_value(widget)
            for key, widget in self.config_widgets.items()
        }

    def apply_config(self, data):
        """Fill the UI from a configuration dict. Does not generate.

        Missing keys reset to their defaults.

        Args:
            data (dict): Configuration as returned by :meth:`gather_config`.
        """
        for key, widget in self.config_widgets.items():
            self.set_widget_value(widget, data.get(key, DEFAULTS[key]), DEFAULTS[key])

    def export_config(self):
        """Save the current settings to a configuration file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Blocking Ghosts Configuration", "", CONFIG_FILTER
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += CONFIG_EXT
        try:
            with open(path, "w") as handle:
                json.dump(self.gather_config(), handle, indent=2)
        except (IOError, OSError) as exc:
            core.warn("could not export config: {}".format(exc))
            return
        self.recent_menu.add_file(path)

    def import_config(self):
        """Load settings from a configuration file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Blocking Ghosts Configuration", "", CONFIG_FILTER
        )
        if path:
            self.load_config_file(path)

    def load_config_file(self, path):
        """Apply a configuration file and add it to the recent list.

        Args:
            path (str): Configuration file path (.bgh or .json).
        """
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (IOError, OSError, ValueError) as exc:
            core.warn("could not read config: {}".format(exc))
            return
        if not isinstance(data, dict):
            core.warn("not a configuration file.")
            return
        self.apply_config(data)
        self.recent_menu.add_file(path)

    # -----------------------------------------------------------------
    # Window lifecycle
    # -----------------------------------------------------------------
    def shutdown(self):
        """Save settings and remove all ghosts and callbacks (once)."""
        if self.closed:
            return
        self.closed = True
        self.save_settings()
        self.session.clear()

    def closeEvent(self, event):
        """Handle the floating-window close.

        Args:
            event (QtGui.QCloseEvent): The close event.
        """
        self.shutdown()
        super(BlockingGhostsUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Handle the docked workspace-control close."""
        self.shutdown()


def show(*args):
    """Show the dockable Blocking Ghosts window, replacing an open one.

    Returns:
        BlockingGhostsUI: The window instance.
    """
    return pyqt.showDialog(BlockingGhostsUI, dockable=True)
