"""Main dockable window and launcher for the anim picker.

Extracted from gui.py during the Phase 2 decomposition. Also hosts the
passthrough event filter used by the main window.
"""

from functools import partial

from maya import cmds
import mgear.pymaya as pm

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.core import pyqt
from mgear.core import callbackManager
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtCompat
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker import menu
from mgear.anim_picker import version
from mgear.anim_picker import picker_node
from mgear.anim_picker.constants import ANIM_PICKER_TITLE
from mgear.anim_picker.constants import GROUPBOX_BG_CSS
from mgear.anim_picker.constants import _mgear_version
from mgear.anim_picker.view import GraphicViewWidget
from mgear.anim_picker.tab_widget import ContextMenuTabWidget
from mgear.anim_picker.widgets import basic
from mgear.anim_picker.widgets import edit_panel
from mgear.anim_picker.widgets import tool_bar
from mgear.anim_picker.widgets import widget_binding
from mgear.anim_picker.widgets import alignment
from mgear.anim_picker.widgets import color_palette
from mgear.anim_picker.widgets import tiled_view
from mgear.anim_picker.widgets import overlay_widgets
from mgear.anim_picker.widgets.dialogs.shape_library_dialog import (
    ShapeLibraryDialog,
)
from mgear.anim_picker.handlers import __EDIT_MODE__
from mgear.anim_picker.handlers import __SELECTION__


class APPassthroughEventFilter(QtCore.QObject):
    """AnimPicker eventFilter for MayaMainWindow when enabling
    click passthrough for the GUI.
    """

    # Animpicker gui reference
    APUI = None

    def eventFilter(self, QObject, event):
        """Filter for changing the windowFlags on the animPicker gui"""
        modifiers = None
        if QtCompat.isValid(self.APUI):
            modifiers = QtWidgets.QApplication.queryKeyboardModifiers()
            auto_state = self.APUI.auto_opacity_btn.isChecked()
            flag_state = self.APUI.testAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents
            )
            if auto_state and modifiers == QtCore.Qt.ShiftModifier:
                # if the window is passthrough enabled
                if flag_state:
                    pos = QtGui.QCursor().pos()
                    widgetRect = self.APUI.geometry()
                    if widgetRect.contains(pos):
                        self.APUI.set_mouseEvent_passthrough(False)
                # if the window is passthrough enabled and the feature disabled
            elif flag_state and not menu.get_option_var_passthrough_state():
                self.APUI.set_mouseEvent_passthrough(False)
            else:
                pass
        else:
            try:
                self.deleteLater()
            except RuntimeError:
                pass
        return super().eventFilter(QObject, event)


class MainDockWindow(QtWidgets.QWidget):
    __OBJ_NAME__ = "ctrl_picker_window"
    __TITLE__ = ANIM_PICKER_TITLE.format(
        m_version=_mgear_version, ap_version=version.version
    )

    def __init__(self, parent=None, edit=False, dockable=False):
        super().__init__(parent=parent)
        self.window_parent = parent
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(QtCore.Qt.Window)
        self.ready = False

        # Window size
        # (default size to provide a 450/700 for tab area and proper img size)
        self.default_width = pyqt.dpi_scale(476)
        self.default_height = pyqt.dpi_scale(837)

        # Default vars
        self.status = False
        self.childs = []
        self.script_jobs = []
        # Active canvas tool (Photoshop-style left toolbar); the view reads
        # this to decide whether the transform manipulator is shown/active.
        self.active_tool = tool_bar.TOOL_SELECT

        __EDIT_MODE__.set_init(edit)
        self.is_dockable = dockable
        # mGear dockable convention: toolName is the attribute core.pyqt
        # (showDialog / deleteInstances) reads to name the workspaceControl.
        self.toolName = self.__OBJ_NAME__

        # Setup ui
        self.cb_manager = callbackManager.CallbackManager()
        self.setup()

        # experimental passthrough feature
        self.original_flags = self.windowFlags()
        self.passthrough_eventFilter_installed = False
        self.ap_eventFilter = APPassthroughEventFilter()
        self.ap_eventFilter.APUI = self

    def setup(self):
        """Setup interface"""
        # Only the dockable window gets an object name: Maya derives its
        # workspaceControl name from it. Giving the floating window the same
        # name makes Maya swap/confuse the two when both are open (opacity UI
        # leaking, close-one-closes-both), so leave the floating window unnamed.
        if self.is_dockable:
            self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)

        # Add main widget and vertical layout
        self.main_vertical_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_vertical_layout)

        # Add window fields
        self.add_character_selector()
        self.add_tab_widget()

        # if the window is not dockable we can control the opacity
        # MayaQWidgetDockableMixin overrides setWindowsOpacity
        self.auto_opacity_btn = QtWidgets.QPushButton("")
        if not self.is_dockable:
            opacity_layout = QtWidgets.QHBoxLayout()
            self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.opacity_slider.setRange(10, 100)
            self.opacity_slider.setValue(100)
            self.opacity_slider.valueChanged.connect(self.change_opacity)
            self.auto_opacity_btn = QtWidgets.QPushButton("Auto opacity")
            self.auto_opacity_btn.setCheckable(True)
            self.auto_opacity_btn.toggled.connect(self.change_opacity)
            self.auto_opacity_btn.toggled.connect(
                self.toggle_passthrough_eventFilter
            )
            self.installEventFilter(self)
            opacity_layout.addWidget(self.opacity_slider)
            opacity_layout.addWidget(self.auto_opacity_btn)
            self.main_vertical_layout.addLayout(opacity_layout)

        self.add_overlays()
        self.resize(self.default_width, self.default_height)
        # Creating is done (workaround for signals being fired
        # off before everything is created)
        self.ready = True

    def toggle_passthrough_eventFilter(self):
        """enable the eventFilter for changing the AP gui windowFlags state"""
        # this feature is beta and is off by default
        if (
            menu.get_option_var_passthrough_state() == 0
            or not self.window_parent
        ):
            return
        if self.auto_opacity_btn.isChecked():
            self.window_parent.installEventFilter(self.ap_eventFilter)
            self.passthrough_eventFilter_installed = True
        else:
            self.window_parent.removeEventFilter(self.ap_eventFilter)
            self.passthrough_eventFilter_installed = False

    def set_mouseEvent_passthrough(self, state):
        """set the state of the passthrough feature for anim picker

        Args:
            state (bool): enable or disable
        """
        if state and self.passthrough_eventFilter_installed:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setWindowFlags(
                self.original_flags & QtCore.Qt.WA_TransparentForMouseEvents
            )
            self.show()
        elif state and not self.passthrough_eventFilter_installed:
            self.toggle_passthrough_eventFilter()
        else:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
            self.setWindowFlags(self.original_flags)
            self.show()

    def eventFilter(self, QObject, event):
        """event filter for general override
        current use
        -Auto opacityfilter
        -hide the GraphicsView for compatibility with MacOs

        Args:
            QObject (QObject): the object getting the event
            event (QEvent): event type

        Returns:
            bool: accepting event or not
        """
        modifiers = None
        if self.auto_opacity_btn.isChecked():
            modifiers = QtWidgets.QApplication.queryKeyboardModifiers()

        if event.type() == QtCore.QEvent.Type.Enter:
            shift_state = modifiers == QtCore.Qt.ShiftModifier
            flag_state = self.testAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents
            )
            if self.auto_opacity_btn.isChecked():
                if flag_state and shift_state:
                    self.setWindowOpacity(100)
                    return True
                elif not flag_state:
                    self.setWindowOpacity(100)
                    return True
        else:
            if event.type() == QtCore.QEvent.Type.Leave:
                opacity_state = self.auto_opacity_btn.isChecked()
                flag_state = self.testAttribute(
                    QtCore.Qt.WA_TransparentForMouseEvents
                )
                if opacity_state:
                    pos = QtGui.QCursor().pos()
                    widgetRect = self.geometry()
                    if not widgetRect.contains(pos):
                        self.change_opacity()
                        # check the option var if it is enabled
                        if menu.get_option_var_passthrough_state():
                            self.set_mouseEvent_passthrough(True)
                elif flag_state and not opacity_state:
                    self.set_mouseEvent_passthrough(False)

        # QtCore.QEvent.Type.ScreenChangeInternal
        # hide main tab widget for os compatibility
        if QObject in getattr(self, "overlays", []):
            if event.type() == QtCore.QEvent.Type.Show:
                self.tab_area.hide()
                return True
            elif event.type() == QtCore.QEvent.Type.Hide:
                self.tab_area.show()
                return True

        return False

    def change_opacity(self):
        """Change the  windows opacity"""
        opacity_value = self.opacity_slider.value()
        self.setWindowOpacity(opacity_value / 100.0)

    def reset_default_size(self):
        """Reset window size to default"""
        self.resize(self.default_width, self.default_height)

    def toggle_character_selector(self, *args):
        """Toggle the visibility of the character select widget"""
        if self.character_box.isChecked():
            self.char_select_widget.show()
        else:
            self.char_select_widget.hide()

    def add_character_selector(self):
        """Add Character comboBox selector"""
        # Create group box
        self.character_box = QtWidgets.QGroupBox("Character Selector")
        bg_color = self.palette().color(QtGui.QPalette.Window).getRgb()
        cc_style_sheet = GROUPBOX_BG_CSS.format(color=bg_color)
        self.character_box.setStyleSheet(cc_style_sheet)
        self.character_box.setContentsMargins(0, 0, 0, 0)
        self.character_box.setMinimumHeight(0)
        self.character_box.setMaximumHeight(pyqt.dpi_scale(80))
        self.character_box.setCheckable(True)
        self.character_box.setChecked(True)
        self.character_box.clicked.connect(self.toggle_character_selector)

        self.char_select_widget = QtWidgets.QWidget()
        self.char_select_widget.setContentsMargins(0, 5, 0, 0)
        tmp_layout = QtWidgets.QHBoxLayout(self.character_box)
        tmp_layout.setSpacing(0)
        tmp_layout.addWidget(self.char_select_widget)

        # Create layout
        layout = QtWidgets.QHBoxLayout(self.char_select_widget)

        # Create character picture widget
        self.pic_widget = basic.SnapshotWidget()

        box_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(box_layout)
        layout.addWidget(self.pic_widget, QtCore.Qt.AlignCenter)

        # Add combo box
        self.char_selector_cb = basic.CallbackComboBox(
            callback=self.selector_change_event
        )
        box_layout.addWidget(self.char_selector_cb)

        # Init combo box data
        self.char_selector_cb.nodes = []

        # Add option buttons
        btns_layout = QtWidgets.QHBoxLayout()
        box_layout.addLayout(btns_layout)
        # Kept so add_tab_widget can append the view-mode selector here.
        self.char_btns_layout = btns_layout

        # Add horizont spacer
        spacer = QtWidgets.QSpacerItem(
            10,
            0,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        btns_layout.addItem(spacer)

        # sync checkbox
        self.checkbox = QtWidgets.QCheckBox("Sync Namespace")
        if not __EDIT_MODE__.get():
            btns_layout.addWidget(self.checkbox)

        # About btn
        about_btn = basic.CallbackButton(callback=self.show_about_infos)
        about_btn.setText("?")
        about_btn.setToolTip("Show help/about informations")
        btns_layout.addWidget(about_btn)

        # laod btn
        load_btn = basic.CallbackButton(callback=self.show_load_widget)
        load_btn.setText("Load")
        load_btn.setToolTip("Load from file")
        btns_layout.addWidget(load_btn)

        # Refresh button
        self.char_refresh_btn = basic.CallbackButton(callback=self.refresh)
        self.char_refresh_btn.setText("Refresh")
        btns_layout.addWidget(self.char_refresh_btn)

        # Edit buttons
        self.new_char_btn = None
        self.save_char_btn = None
        if __EDIT_MODE__.get():
            # Add New  button
            self.new_char_btn = basic.CallbackButton(
                callback=self.new_character
            )
            self.new_char_btn.setText("New")
            self.new_char_btn.setFixedWidth(pyqt.dpi_scale(40))

            btns_layout.addWidget(self.new_char_btn)

            # Add Save  button
            self.save_char_btn = basic.CallbackButton(
                callback=self.save_character
            )
            self.save_char_btn.setText("Save")
            self.save_char_btn.setFixedWidth(pyqt.dpi_scale(40))

            btns_layout.addWidget(self.save_char_btn)
        self.main_vertical_layout.addWidget(self.character_box)

    def add_tab_widget(self, name="default"):
        """Add control display field"""
        self.tab_widget = ContextMenuTabWidget(self, main_window=self)

        # Right-docked inline item editor (edit mode only). The tab widget and
        # the panel share a resizable, collapsible splitter, so the classic
        # single-pane view is simply the panel-hidden state.
        self.edit_panel = edit_panel.ItemEditPanel(main_window=self)
        self.edit_panel.setMinimumWidth(pyqt.dpi_scale(220))

        # Wrap the tab widget so it can also be presented as a tiled multi-tab
        # view (grid / vertical / horizontal); the area is the state-sensitive
        # facade (active view, all views, data, fit) used across the window.
        self.tab_area = tiled_view.PickerTabArea(
            self.tab_widget, main_window=self
        )
        self._build_view_mode_selector()

        self.editor_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.editor_splitter.addWidget(self.tab_area)
        self.editor_splitter.addWidget(self.edit_panel)
        self.editor_splitter.setStretchFactor(0, 1)
        self.editor_splitter.setStretchFactor(1, 0)
        self.editor_splitter.setCollapsible(0, False)
        self.editor_splitter.setCollapsible(1, True)

        # Photoshop-style tool strip on the left of the canvas + the splitter.
        self.left_toolbar = tool_bar.PickerToolBar(main_window=self)
        # Quick-access commands below the tools; selection-dependent ones are
        # collected so they can be enabled/disabled with the selection.
        self.left_toolbar.add_command(
            "Add",
            "Add a new item at the origin",
            self._cmd_add_item,
            tool_bar.mgear_icon("mgear_plus-square"),
        )
        self.left_toolbar.add_command(
            "SVG",
            "Import an .svg file as a vector shape "
            "(or drag one onto the canvas)",
            self._cmd_import_svg,
            tool_bar.mgear_icon("mgear_image"),
        )
        self._selection_commands = [
            self.left_toolbar.add_command(
                "Dup",
                "Duplicate selected items",
                self._cmd_duplicate,
                tool_bar.mgear_icon("mgear_copy"),
            ),
            self.left_toolbar.add_command(
                "DupM",
                "Duplicate and mirror the selection (linked as a pair)",
                self._cmd_duplicate_mirror,
                tool_bar.mgear_icon("mgear_duplicate_sym"),
            ),
            self.left_toolbar.add_command(
                "MirS",
                "Mirror the selected shapes",
                self._cmd_mirror_shape,
                tool_bar.mgear_icon("mgear_mirror_controls"),
            ),
            self.left_toolbar.add_command(
                "Shp",
                "Apply a premade / saved shape to the selection",
                self._cmd_shapes,
                tool_bar.mgear_icon("mgear_replace_shape"),
            ),
            self.left_toolbar.add_command(
                "Pin",
                "Pin / unpin the selection to the viewport (HUD overlay)",
                self._cmd_toggle_pin,
                tool_bar.mgear_icon("mgear_map-pin"),
            ),
        ]
        # Trace: one silhouette button per selected Maya control. Not gated on
        # a picker selection (it reads the Maya selection); the drop-down picks
        # the projection plane, a plain click uses Front.
        trace_btn = self.left_toolbar.add_command(
            "Trc",
            "Trace a silhouette button per selected control (Front)",
            partial(self._cmd_trace, "front"),
            tool_bar.mgear_icon("mgear_camera"),
        )
        trace_menu = QtWidgets.QMenu(trace_btn)
        for label, plane in (("Front", "front"), ("Side", "side"),
                             ("Top", "top")):
            trace_menu.addAction(label).triggered.connect(
                partial(self._cmd_trace, plane)
            )
        trace_btn.setMenu(trace_menu)
        trace_btn.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        # Align / distribute the current multi-selection. Two columns: the left
        # column is horizontal ops (left / H-center / right / distribute-H),
        # the right column vertical (top / V-center / bottom / distribute-V).
        self.left_toolbar.add_separator()
        self.left_toolbar.add_section_label("Align")
        align_specs = (
            ("mgear_align_left", "Align left edges",
             partial(self._align_selected, "left")),
            ("mgear_align_top", "Align top edges",
             partial(self._align_selected, "top")),
            ("mgear_align_hcenter", "Align horizontal centers",
             partial(self._align_selected, "hcenter")),
            ("mgear_align_vcenter", "Align vertical centers",
             partial(self._align_selected, "vcenter")),
            ("mgear_align_right", "Align right edges",
             partial(self._align_selected, "right")),
            ("mgear_align_bottom", "Align bottom edges",
             partial(self._align_selected, "bottom")),
            ("mgear_distribute_h", "Distribute horizontally (3+ to redistribute)",
             partial(self._distribute_selected, "h")),
            ("mgear_distribute_v", "Distribute vertically (3+ to redistribute)",
             partial(self._distribute_selected, "v")),
            ("mgear_expand_h", "Expand horizontal spacing (spread apart)",
             partial(self._expand_selected, "h")),
            ("mgear_expand_v", "Expand vertical spacing (spread apart)",
             partial(self._expand_selected, "v")),
            ("mgear_contract_h", "Contract horizontal spacing (bring closer)",
             partial(self._contract_selected, "h")),
            ("mgear_contract_v", "Contract vertical spacing (bring closer)",
             partial(self._contract_selected, "v")),
        )
        self.left_toolbar.add_button_grid(
            [
                (tooltip, callback, tool_bar.mgear_icon(icon))
                for icon, tooltip, callback in align_specs
            ],
            columns=2,
        )

        # Drag-to-canvas creation palette: drag a tile onto the canvas to create
        # that item / widget at the drop position (the primary way to add).
        self.left_toolbar.add_separator()
        self.left_toolbar.add_section_label("Drag to add")
        # Each tile drops to create at the drop point, or double-click to
        # create at the canvas center (a backdrop double-click wraps the
        # current selection).
        palette_specs = (
            ("Btn", "Drag to add a button (double-click = center)",
             widget_binding.WIDGET_BUTTON, "mgear_widget_button"),
            ("Chk", "Drag to add a checkbox (double-click = center)",
             widget_binding.WIDGET_CHECKBOX, "mgear_widget_checkbox"),
            ("Sld", "Drag to add a slider (double-click = center)",
             widget_binding.WIDGET_SLIDER, "mgear_widget_slider"),
            ("2D", "Drag to add a 2D slider (double-click = center)",
             widget_binding.WIDGET_SLIDER2D, "mgear_widget_slider2d"),
            ("Bkd", "Drag to add a backdrop (double-click = wrap selection)",
             tool_bar.BACKDROP_PAYLOAD, "mgear_widget_backdrop"),
        )
        for label, tooltip, payload, icon in palette_specs:
            self.left_toolbar.add_palette_item(
                label,
                tooltip,
                payload,
                tool_bar.mgear_icon(icon),
                double_callback=partial(self._palette_create, payload),
            )
        canvas_row = QtWidgets.QHBoxLayout()
        canvas_row.setContentsMargins(0, 0, 0, 0)
        canvas_row.setSpacing(0)
        canvas_row.addWidget(self.left_toolbar)
        canvas_row.addWidget(self.editor_splitter)
        self.main_vertical_layout.addLayout(canvas_row)

        # Preset L/R/center color palette along the bottom (edit mode only).
        self.color_palette = color_palette.ColorPaletteBar(main_window=self)
        self.main_vertical_layout.addWidget(self.color_palette)

        # Add default first tab
        view = GraphicViewWidget(main_window=self)
        self.tab_widget.addTab(view, name)

        # ensure the picker area retains its size when hidden (overlay filter)
        sp_retain = self.tab_area.sizePolicy()
        sp_retain.setRetainSizeWhenHidden(True)
        self.tab_area.setSizePolicy(sp_retain)

        # Editor panel, tool strip and palette are edit-mode only; refresh the
        # panel when the tab changes.
        self.edit_panel.setVisible(__EDIT_MODE__.get())
        self.left_toolbar.setVisible(__EDIT_MODE__.get())
        self.color_palette.setVisible(__EDIT_MODE__.get())
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # In anim mode the panel is hidden; hand the whole splitter to the
        # picker area so the canvas / tiled view fills the full width.
        if not __EDIT_MODE__.get():
            self.editor_splitter.setSizes([1, 0])

        # Restore the last-used view mode / grid column count.
        self._apply_saved_view_mode()

    # =====================================================================
    # View mode (tabbed / tiled multi-tab) ---
    _VIEW_MODES = (
        tiled_view.MODE_TABBED,
        tiled_view.MODE_GRID,
        tiled_view.MODE_VERTICAL,
        tiled_view.MODE_HORIZONTAL,
    )

    def _build_view_mode_selector(self):
        """Add the Tabbed / Grid / Rows / Columns selector to the char bar."""
        self.char_btns_layout.addWidget(QtWidgets.QLabel("View"))
        self.view_mode_cb = QtWidgets.QComboBox()
        self.view_mode_cb.addItems(["Tabbed", "Grid", "Rows", "Columns"])
        self.view_mode_cb.setToolTip(
            "Show one tab at a time, or all tabs tiled at once"
        )
        self.view_mode_cb.currentIndexChanged.connect(
            self._on_view_mode_changed
        )
        self.char_btns_layout.addWidget(self.view_mode_cb)

        self.grid_cols_sb = QtWidgets.QSpinBox()
        self.grid_cols_sb.setRange(0, 12)
        self.grid_cols_sb.setToolTip("Grid columns (0 = auto)")
        self.grid_cols_sb.setEnabled(False)
        self.grid_cols_sb.valueChanged.connect(self._on_grid_cols_changed)
        self.char_btns_layout.addWidget(self.grid_cols_sb)

    def _view_settings(self):
        """Return the QSettings store for anim picker UI preferences."""
        return QtCore.QSettings("mgear", "anim_picker")

    def _apply_saved_view_mode(self):
        """Restore the persisted view mode + grid columns, without re-saving."""
        settings = self._view_settings()
        mode = settings.value("tab_view_mode", tiled_view.MODE_TABBED)
        try:
            columns = int(settings.value("tab_grid_columns", 0) or 0)
        except (TypeError, ValueError):
            columns = 0
        if mode not in self._VIEW_MODES:
            mode = tiled_view.MODE_TABBED

        self.grid_cols_sb.blockSignals(True)
        self.grid_cols_sb.setValue(columns)
        self.grid_cols_sb.blockSignals(False)
        self.tab_area.set_grid_columns(columns or None)

        index = self._VIEW_MODES.index(mode)
        self.view_mode_cb.blockSignals(True)
        self.view_mode_cb.setCurrentIndex(index)
        self.view_mode_cb.blockSignals(False)
        self._set_view_mode(mode)

    def _on_view_mode_changed(self, index):
        """Apply and persist the selected view mode."""
        mode = self._VIEW_MODES[index]
        self._view_settings().setValue("tab_view_mode", mode)
        self._set_view_mode(mode)

    def _on_grid_cols_changed(self, value):
        """Apply and persist the grid column count (0 = auto)."""
        self._view_settings().setValue("tab_grid_columns", value)
        self.tab_area.set_grid_columns(value or None)

    def _set_view_mode(self, mode):
        """Switch the picker area to ``mode`` and refresh dependent UI."""
        self.tab_area.set_view_mode(mode)
        self.grid_cols_sb.setEnabled(mode == tiled_view.MODE_GRID)
        self.tab_area.fit_contents()
        self._on_tab_changed()

    def _on_tab_changed(self, *args):
        """Rebind the inline editor to the newly active tab's selection."""
        panel = getattr(self, "edit_panel", None)
        if panel is not None:
            panel.sync()
        self.update_tool_commands()

    def set_active_tool(self, name):
        """Set the active canvas tool and repaint so the overlay updates.

        Args:
            name (str): a ``tool_bar`` tool id (TOOL_SELECT / TOOL_TRANSFORM).
        """
        self.active_tool = name
        view = self.tab_area.active_view()
        if view is not None:
            view.viewport().update()

    # =====================================================================
    # Tool-strip quick commands ---
    def _current_view(self):
        """Return the active graphics view, or None."""
        return self.tab_area.active_view()

    def _selected_items(self):
        """Return the current view's selected picker items."""
        view = self._current_view()
        return view.scene().get_selected_items() if view is not None else []

    def update_tool_commands(self):
        """Enable/disable the selection-dependent command buttons."""
        has = bool(self._selected_items())
        for button in getattr(self, "_selection_commands", []):
            button.setEnabled(has)

    def _after_command(self):
        """Refresh the canvas, inline panel and command states after an op."""
        view = self._current_view()
        if view is not None:
            # Record the command's item changes as one editor undo step (a
            # no-op when the command changed nothing).
            view.commit_edit()
            view.viewport().update()
        panel = getattr(self, "edit_panel", None)
        if panel is not None:
            panel.sync()
        self.update_tool_commands()

    def _cmd_add_item(self):
        view = self._current_view()
        if view is not None:
            view.add_picker_item_gui(QtCore.QPointF(0, 0))
        self._after_command()

    def _cmd_import_svg(self):
        """Import one or more .svg files as vector items (file dialog)."""
        view = self._current_view()
        if view is None:
            return
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Import SVG", "", "SVG files (*.svg)"
        )
        for path in paths or []:
            view.add_svg_item(path, view.get_center_pos())
        if paths:
            self._after_command()

    def _cmd_duplicate(self):
        items = self._selected_items()
        if items:
            items[0].duplicate_selected()
        self._after_command()

    def _cmd_shapes(self):
        items = self._selected_items()
        if not items:
            return
        current = [[h.x(), h.y()] for h in items[-1].handles]
        dialog = ShapeLibraryDialog(
            parent=self,
            apply_callback=self._apply_shape_to_selection,
            current_handles=current,
        )
        dialog.show()

    def _apply_shape_to_selection(self, handles):
        for item in self._selected_items():
            item.set_handles([list(point) for point in handles])
        self._after_command()

    def _cmd_mirror(self, method_name):
        """Run a PickerItem mirror op on the selection and propagate it."""
        view = self._current_view()
        items = self._selected_items()
        for item in items:
            getattr(item, method_name)()
        if view is not None:
            view.apply_mirror_for(items)
        self._after_command()

    def _cmd_mirror_shape(self):
        self._cmd_mirror("mirror_shape")

    def _cmd_toggle_pin(self):
        """Pin / unpin the selection to the viewport (anchored to its region).

        Toggles based on the first item's state so a mixed selection resolves
        to a single, predictable result.
        """
        view = self._current_view()
        items = self._selected_items()
        if not (view and items):
            return
        target = not items[0].get_pinned()
        for item in items:
            view.set_item_pinned(item, target)
        view.viewport().update()
        self._after_command()

    def _palette_create(self, payload):
        """Create a palette item at the canvas center (double-click path).

        A backdrop wraps the current selection when one exists (auto-sized),
        otherwise it (and every other tile) is created at the viewport center.

        Args:
            payload (str): the palette payload (widget type / backdrop).
        """
        view = self._current_view()
        if view is None:
            return
        if payload == tool_bar.BACKDROP_PAYLOAD:
            view.add_backdrop_item(
                mouse_pos=view.get_center_pos(),
                fit_items=self._selected_items() or None,
            )
        else:
            view.add_widget_item(payload, view.get_center_pos())
        self._after_command()

    def _item_scene_rect(self, item):
        """Return an item's scene bounding box as ``(x0, y0, x1, y1)``."""
        rect = item.sceneBoundingRect()
        return (rect.left(), rect.top(), rect.right(), rect.bottom())

    def _apply_item_offsets(self, min_count, offsets_fn):
        """Move the current selection by per-item ``(dx, dy)`` offsets.

        Args:
            min_count (int): minimum selection size to act on.
            offsets_fn (callable): ``rects -> [(dx, dy), ...]``.
        """
        items = self._selected_items()
        if len(items) < min_count:
            return
        rects = [self._item_scene_rect(item) for item in items]
        for item, (dx, dy) in zip(items, offsets_fn(rects)):
            item.setPos(item.x() + dx, item.y() + dy)
        self._after_command()

    def _align_selected(self, mode):
        """Align the selected items by ``mode`` (needs 2+)."""
        self._apply_item_offsets(
            2, partial(alignment.align_offsets, mode=mode)
        )

    def _distribute_selected(self, axis):
        """Distribute the selected items along ``axis`` by bounding box (2+).

        Spreads items with even edge gaps when they have room, and fans a
        stack of overlapping items into a row / column.
        """
        self._apply_item_offsets(
            2, partial(alignment.distribute_offsets, axis=axis)
        )

    # Spread step for the expand / contract fine-tune tools. Contract is the
    # inverse of expand, so an expand then a contract returns near the start.
    _SPREAD_STEP = 1.1

    def _expand_selected(self, axis):
        """Spread the selection apart along ``axis`` a step (fine-tune, 2+)."""
        self._apply_item_offsets(
            2,
            partial(
                alignment.scale_spread_offsets,
                axis=axis,
                factor=self._SPREAD_STEP,
            ),
        )

    def _contract_selected(self, axis):
        """Pull the selection closer along ``axis`` a step (fine-tune, 2+)."""
        self._apply_item_offsets(
            2,
            partial(
                alignment.scale_spread_offsets,
                axis=axis,
                factor=1.0 / self._SPREAD_STEP,
            ),
        )

    def _cmd_trace(self, plane):
        """Trace a silhouette button per selected control onto ``plane``.

        Args:
            plane (str): projection plane ("front" / "side" / "top").
        """
        view = self._current_view()
        if view is not None:
            view.add_picker_item_trace(plane=plane)
        self._after_command()

    def apply_palette_color(self, side, level):
        """Apply a preset color to the selection, mirroring by side to partners.

        The selected item(s) get the clicked (side, level) color; each item's
        mirror partner (when not itself selected) gets the same level on the
        opposite side. Presets never repaint items that already used the color.

        Args:
            side (str): "left" / "center" / "right".
            level (str): "primary" / "secondary".
        """
        view = self._current_view()
        if view is None:
            return
        color = self.color_palette.color_for(side, level)
        if color is None:
            return
        mirror_side = color_palette.MIRROR_SIDE.get(side, side)
        partner_color = self.color_palette.color_for(mirror_side, level)
        items = self._selected_items()
        selected = set(items)
        for item in items:
            self._set_item_rgb(item, color)
            partner = view.get_mirror_partner(item)
            if (
                partner is not None
                and partner not in selected
                and partner_color is not None
            ):
                self._set_item_rgb(partner, partner_color)
        view.viewport().update()
        self._after_command()

    def _set_item_rgb(self, item, color):
        """Set an item's RGB from ``color`` while preserving its alpha."""
        result = QtGui.QColor(color)
        result.setAlpha(item.get_color().alpha())
        item.set_color(result)

    def _cmd_duplicate_mirror(self):
        view = self._current_view()
        items = self._selected_items()
        if not (view and items):
            return
        # Reuse the existing duplicate+mirror (handles the search/replace
        # prompt once); link each returned pair as a persistent mirror.
        pairs = items[0].duplicate_and_mirror_selected() or []
        for source, new_item in pairs:
            view.link_mirror_pair(source, new_item)
            self._apply_mirror_color_from_palette(source, new_item)
        self._after_command()

    def _apply_mirror_color_from_palette(self, source, new_item):
        """Color a mirrored copy from the palette (opposite side, same level).

        If the source's color matches a palette swatch, the new item gets the
        opposite-side preset at the same level; otherwise the source color is
        copied (never the old red/blue swap that duplicate_and_mirror applied).
        """
        slot = self.color_palette.match_color(source.get_color())
        if slot is None:
            new_item.set_color(source.get_color())
            return
        side, level = slot
        mirror_side = color_palette.MIRROR_SIDE.get(side, side)
        color = self.color_palette.color_for(mirror_side, level)
        if color is not None:
            self._set_item_rgb(new_item, color)

    def _sync_edit_panel(self):
        """Show/hide the inline editor + tool strip with the mode."""
        edit = __EDIT_MODE__.get()
        toolbar = getattr(self, "left_toolbar", None)
        if toolbar is not None:
            toolbar.setVisible(edit)
        palette = getattr(self, "color_palette", None)
        if palette is not None:
            palette.setVisible(edit)
        panel = getattr(self, "edit_panel", None)
        if panel is None:
            return
        panel.setVisible(edit)
        # Give the whole splitter to the picker area when the panel is hidden
        # (anim mode), so the canvas / tiled view fills the full width.
        splitter = getattr(self, "editor_splitter", None)
        if splitter is not None:
            if edit:
                splitter.setSizes([pyqt.dpi_scale(600), pyqt.dpi_scale(240)])
            else:
                splitter.setSizes([1, 0])
        if edit:
            panel.sync()
        self.update_tool_commands()

    def add_overlays(self):
        """Add transparent overlay widgets"""
        self.about_widget = overlay_widgets.AboutOverlayWidget(self)
        self.load_widget = overlay_widgets.LoadOverlayWidget(self)
        self.save_widget = overlay_widgets.SaveOverlayWidget(self)
        self.overlays = [self.about_widget, self.load_widget, self.save_widget]

        # specificaly hiding and showing the main layer for OS compatibility
        for layer in self.overlays:
            layer.installEventFilter(self)

    def get_picker_items(self):
        """Return picker items for current active tab"""
        return self.tab_area.get_current_picker_items()

    def get_all_picker_items(self):
        """Return all picker items for current picker"""
        return self.tab_area.get_all_picker_items()

    def dockCloseEventTriggered(self):
        self.close()

    def closeEvent(self, evnt):
        self.close()

    def close(self):
        """Overwriting close event to close child windows too"""
        # Delete script jobs
        self.cb_manager.removeAllManagedCB()
        # Close childs
        for child in self.childs:
            try:
                child.close()
            except Exception:
                pass

        # Close ctrls options windows
        for item in self.get_all_picker_items():
            try:
                if not item.edit_window:
                    continue
                item.edit_window.close()
            except Exception:
                pass

        try:
            self.window_parent.removeEventFilter(self.ap_eventFilter)
        except Exception:
            pass

        # Only the dockable window owns a workspaceControl; closing it from the
        # floating window would tear down the (separate) docked picker. Derive
        # the name the same way pyqt.showDialog does (toolName + suffix).
        if self.is_dockable:
            work_name = self.toolName + "WorkspaceControl"
            try:
                cmds.workspaceControl(work_name, e=True, close=True)
            except (ValueError, RuntimeError):
                pass
        self.deleteLater()

    def showEvent(self, *args, **kwargs):
        """Default showEvent overload"""
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        # Default close
        super().showEvent(*args, **kwargs)

        # Force char load
        self.refresh()

        # Add script jobs
        self.add_callback()

    def resizeEvent(self, event):
        """Resize about overlay on resize event"""
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        size = self.size()

        self.about_widget.resize(size)

        self.save_widget.resize(size)

        self.load_widget.resize(size)

        return super().resizeEvent(event)

    def show_about_infos(self):
        """Open animation picker about and help infos"""
        self.about_widget.show()

    def show_load_widget(self):
        """Open animation picker about and help infos"""
        self.load_widget.show()

    # =========================================================================
    # Character selector handlers ---
    def selector_change_event(self, index):
        """Will load data node relative to selector index"""
        self.load_character()

    def populate_char_selector(self):
        """Will populate char selector combo box"""
        # Get char nodes
        nodes = picker_node.get_nodes()
        self.char_selector_cb.nodes = nodes

        # Empty combo box
        self.char_selector_cb.clear()

        # Populate
        for data_node in nodes:
            # text = data_node.get_namespace() or data_node.name
            text = data_node.name
            self.char_selector_cb.addItem(text)

        # Set elements active status
        self.set_field_status()

    def set_field_status(self):
        """Will toggle elements active status"""
        # Define status from node list
        self.status = False
        if self.char_selector_cb.count():
            self.status = True

        # Set status
        self.char_selector_cb.setEnabled(self.status)
        self.tab_area.setEnabled(self.status)
        if self.save_char_btn:
            self.save_char_btn.setEnabled(self.status)

        # Reset tabs
        if not self.status:
            self.load_default_tabs()

    def load_default_tabs(self):
        """Will reset and load default empty tabs"""
        # Return to tabbed so the tab widget owns the (about to be replaced)
        # views before clearing.
        self.tab_area.ensure_tabbed()
        self.tab_widget.clear()
        self.tab_widget.addTab(GraphicViewWidget(main_window=self), "None")

    def refresh(self):
        """Refresh char selector and window"""
        # Get current active node
        current_node = None
        data_node = self.get_current_data_node()
        if data_node and data_node.exists():
            current_node = data_node.name

        # Check/abort on possible data changes
        if __EDIT_MODE__.get() and current_node:
            if not self.check_for_data_change():
                return

        # Re-populate selector
        self.populate_char_selector()

        # Set proper index
        if current_node:
            self.make_node_active(current_node)

        # Refresh selection check
        self.selection_change_event()

        # Force view resize
        self.tab_area.fit_contents()

        # Sync the inline editor's visibility/content with the current mode.
        self._sync_edit_panel()

        # Set focus on view
        active_view = self.tab_area.active_view()
        if active_view is not None:
            active_view.setFocus()

    def load_from_sel_node(self):
        """Will try to load character for selected node"""
        sel = cmds.ls(sl=True)
        if not sel:
            return
        data_node = picker_node.get_node_for_object(sel[0])
        if not data_node:
            return
        self.make_node_active(data_node.name)

    def make_node_active(self, data_node):
        """Will set character selector to specified data_node"""
        index = 0
        for i in range(len(self.char_selector_cb.nodes)):
            node = self.char_selector_cb.nodes[i]
            if not data_node == node.name or data_node == node:
                continue
            index = i
            break
        self.char_selector_cb.setCurrentIndex(index)

    def new_character(self):
        """
        Will create a new data node, and init a new window
        (edit mode only)
        """
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "New character",
            "Node name",
            QtWidgets.QLineEdit.Normal,
            "PICKER_DATA",
        )
        if not (ok and name):
            return

        # Check for possible data changes/loss
        if not self.check_for_data_change():
            return

        # Create new data node
        data_node = picker_node.DataNode(name=str(name))
        data_node.create()
        self.refresh()
        self.make_node_active(data_node)

    # =========================================================================
    # Data ---
    def check_for_data_change(self):
        """
        Check if data changed
        If changes are detected will ask user if he wants to proceed any
        way and loose thoses changes
        Return user answer
        """
        # Get current data node
        data_node = self.get_current_data_node()
        if not (data_node and data_node.exists()):
            return True

        # Return true if no changes were detected
        if data_node == self.get_character_data():
            return True

        # Open question window
        msg = "Any changes will be lost, proceed any way ?"
        answer = QtWidgets.QMessageBox.question(
            self,
            "Changes detected",
            msg,
            buttons=QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def get_current_namespace(self):
        return self.get_current_data_node().get_namespace()

    def get_current_data_node(self):
        """Return current character data node"""
        # Empty list case
        if not self.char_selector_cb.count():
            return None

        # Return node from combo box index
        index = self.char_selector_cb.currentIndex()
        return self.char_selector_cb.nodes[index]

    def load_character(self):
        """Load currently selected data node"""
        # Get DataNode
        data_node = self.get_current_data_node()
        if not data_node:
            return
        picker_data = data_node.get_data()

        # Load snapshot
        path = picker_data.get("snapshot", None)
        self.pic_widget.set_background(path)

        # load tabs (set_data returns the area to the tabbed presentation)
        tabs_data = picker_data.get("tabs", {})
        self.tab_area.set_data(tabs_data)

        # Default tab
        if not self.tab_widget.count():
            self.tab_widget.addTab(
                GraphicViewWidget(main_window=self), "default"
            )
        else:
            # Return to first tab
            self.tab_widget.setCurrentIndex(0)

        # Re-apply the persisted view mode over the freshly loaded tabs.
        self._apply_saved_view_mode()

        # Fit content
        self.tab_area.fit_contents()

        # Update selection states
        self.selection_change_event()

    def save_character(self):
        """Save data to current selected data_node"""
        # Get DataNode
        data_node = self.get_current_data_node()
        assert data_node, "No data_node found/selected"

        # Block save in anim mode
        if not __EDIT_MODE__.get():
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Save is not permited in anim mode"
            )
            return

        # Block save on referenced nodes
        if data_node.is_referenced():
            msg = "Save is not permited on referenced nodes"
            QtWidgets.QMessageBox.warning(self, "Warning", msg)
            return

        self.save_widget.show()

    def get_character_data(self):
        """Return window data"""
        picker_data = {}

        # Add snapshot path data
        snapshot_data = self.pic_widget.get_data()
        if snapshot_data:
            picker_data["snapshot"] = snapshot_data

        # Add tabs data (from the area, so it works in tabbed or tiled view)
        tabs_data = self.tab_area.get_data()
        if tabs_data:
            picker_data["tabs"] = tabs_data

        return picker_data

    # =========================================================================
    # Script jobs handling ---
    def add_callback(self):
        """Will add maya scripts job events"""
        # Clear any existing scrip jobs
        self.cb_manager.removeAllManagedCB()

        # Add selection change event
        self.cb_manager.selectionChangedCB(
            "anim_picker_selection", self.selection_change_event
        )
        # Add scene open event
        self.cb_manager.newSceneCB(
            "anim_picker_newScene", self.selection_change_event
        )
        # No time-change callback: channel-state visibility is not refreshed
        # per playback frame (that would read the rig every frame). A manual /
        # animated channel change is picked up on mouse-over (enterEvent ->
        # refresh_from_rig) instead -- on-demand, never polling.

    def selection_change_event(self, *args):
        """
        Event called with a script job from maya on selection change.
        Will properly parse poly_ctrls associated node, and set border
        visible if content is selected
        """
        # Abort in Edit mode
        if __EDIT_MODE__.get():
            return

        # Update selection data
        __SELECTION__.update()

        # sync with namespce
        if not __EDIT_MODE__.get():
            sel = pm.selected()
            sync = self.checkbox.isChecked()
            if sel and sync:
                ns = sel[0].namespace()
                if ns:
                    for i, n in enumerate(self.char_selector_cb.nodes):
                        if ns in str(n):
                            self.char_selector_cb.setCurrentIndex(i)
                            break
        # Update controls for active tab
        for item in self.get_picker_items():
            item.run_selection_check()

        # Re-evaluate conditional visibility for the new selection / rig state
        # (channel-state conditions may now pass or fail).
        self.refresh_item_visibility()

    def refresh_item_visibility(self, *args):
        """Re-evaluate conditional-visibility items across every live view.

        Each view computes the zoom once and applies its items' show/hide.
        Wired to selection- and time-change callbacks so channel-state
        conditions update as the animator selects or scrubs; iterating every
        view (not just the active one) keeps the multi-tab tiled presentation
        live, and is cheap since each view early-outs when it has none.
        """
        for view in self.tab_area.all_views():
            if view is not None:
                view.refresh_item_visibility()

    def enterEvent(self, event):
        """Refresh rig-driven display when the mouse enters the picker.

        Like the Channel Master tool, a mouse-enter (no focus needed) re-reads
        the bound Maya attributes so interactive widgets and conditional-
        visibility items reflect the current rig even after a change that fired
        no selection / time callback (e.g. a manual channel-box edit). It is
        on-demand only -- it never polls the rig.
        """
        super().enterEvent(event)
        self.refresh_from_rig()

    def refresh_from_rig(self, *args):
        """Re-sync widgets + conditional visibility from the rig (all views).

        One pass per live view reads each interactive widget's attribute and
        re-evaluates the conditional-visibility items. A no-op in edit mode
        (nothing reads the rig while authoring).
        """
        if __EDIT_MODE__.get():
            return
        for view in self.tab_area.all_views():
            if view is None:
                continue
            view.refresh_widget_states()
            view.refresh_item_visibility()


# version of the anim picker ui that uses MayaQWidgetDockableMixin for docking
class MainDockableWindow(MayaQWidgetDockableMixin, MainDockWindow):
    def __init__(self, parent=None, edit=False, dockable=True):
        # Pass edit/dockable through: MayaQWidgetDockableMixin forwards extra
        # kwargs down the MRO to MainDockWindow, so is_dockable/edit are set
        # (dropping them left is_dockable False and showed the opacity UI).
        super().__init__(parent=parent, edit=edit, dockable=dockable)


# =============================================================================
# Load user interface function
# =============================================================================
def load(edit=False, dockable=False):
    """Launch the anim picker UI (a fresh instance each call).

    Args:
        edit (bool, optional): open in edit mode.
        dockable (bool, optional): open as a dockable workspaceControl.

    Returns:
        MainDockWindow: the created window instance.
    """
    if dockable:
        # Launch through the shared mGear docking helper, the same path the
        # other dockable tools (crank, channel master, spring manager) use.
        # A partial supplies the edit/dockable args because showDialog builds
        # the window with no arguments; showDialog also closes any stale
        # <toolName>WorkspaceControl before showing.
        return pyqt.showDialog(
            partial(MainDockableWindow, edit=edit, dockable=True),
            dockable=True,
        )

    ANIM_PKR_UI = MainDockWindow(parent=pyqt.get_main_window(), edit=edit)
    ANIM_PKR_UI.show()
    return ANIM_PKR_UI
