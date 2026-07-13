"""Inline multi-selection edit panel for picker items.

``ItemEditPanel`` is the right-docked, edit-mode-only replacement for the
per-item ``ItemOptionsWindow`` modal. It binds to the current picker selection
and edits every selected item at once through the existing ``PickerItem``
setters -- no re-implementation of the item logic. Fields whose value differs
across the selection are shown in a distinct "mixed" state (numeric spin boxes
via a sentinel + special text, text/color swatches via a placeholder) so a
multi-edit never silently clobbers differing values.

The view calls :meth:`sync_from_view` after any selection change or manipulator
drag; the main window calls :meth:`sync` on tab change / mode toggle. A
``_syncing`` guard breaks the canvas<->panel feedback loop, mirroring the
background options panel.
"""

from functools import partial

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.core import widgets as mwidgets

from mgear.anim_picker.widgets import basic
from mgear.anim_picker.widgets import overlay
from mgear.anim_picker.widgets import graphics
from mgear.anim_picker.widgets import widget_binding
from mgear.anim_picker.widgets import visibility
from mgear.core import svg_import
from mgear.anim_picker.widgets.dialogs.handles_window import (
    HandlesPositionWindow,
)
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomScriptEditDialog,
)
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomMenuEditDialog,
)
from mgear.anim_picker.widgets.dialogs.search_replace_dialog import (
    SearchAndReplaceDialog,
)
from mgear.anim_picker.widgets.dialogs.shape_library_dialog import (
    ShapeLibraryDialog,
)


class ItemEditPanel(QtWidgets.QWidget):
    """Right-docked inline editor for the current picker item selection."""

    # Sentinel spin value shown as ``MIXED_TEXT`` when a field is mixed. It is
    # the spin box minimum, so the display reads "-" until the user commits a
    # real value; the apply handlers skip it so a mixed field is never written.
    MIXED = -1.0e7
    MIXED_INT = -1000000
    MIXED_TEXT = "-"

    # Widget type combo order (index -> widget_binding type).
    _WIDGET_TYPE_ORDER = (
        widget_binding.WIDGET_BUTTON,
        widget_binding.WIDGET_CHECKBOX,
        widget_binding.WIDGET_SLIDER,
        widget_binding.WIDGET_SLIDER2D,
    )

    # Visibility mode combo order (index -> visibility mode).
    _VIS_MODE_ORDER = (
        visibility.VIS_NONE,
        visibility.VIS_CHANNEL,
        visibility.VIS_ZOOM,
    )

    # Vector render mode combo order (index -> svg_import mode).
    _SVG_MODE_ORDER = (svg_import.MODE_FILL, svg_import.MODE_STROKE)

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent=parent)
        self.main_window = main_window
        # Currently bound selection and the view it came from.
        self.items = []
        self._view = None
        # Guard against panel<->canvas write-back while populating fields.
        self._syncing = False
        # Child windows opened from the panel (handles table).
        self.handles_window = None
        # Interactive widgets toggled with the selection presence.
        self._fields = []

        # Widgets created in the section builders.
        self.pos_x_sb = None
        self.pos_y_sb = None
        self.rotate_sb = None
        self.scale_factor_sb = None
        self.worldspace_cb = None
        self.color_button = None
        self.alpha_sb = None
        self.text_field = None
        self.text_size_sb = None
        self.text_color_button = None
        self.text_alpha_sb = None
        self.text_align_combo = None
        self.text_offset_sb = None
        self.count_sb = None
        self.handles_cb = None
        self._shape_polygon_box = None
        self._shape_vector_box = None
        self._shape_vector_label = None
        self.svg_mode_combo = None
        self.svg_width_sb = None
        self.control_list = None
        self.menus_list = None
        self.custom_action_cb = None
        self.mirror_axis_sb = None
        self.mirror_status = None
        self.pinned_cb = None
        self.anchor_group = None
        self.anchor_buttons = {}
        self.pin_off_x_sb = None
        self.pin_off_y_sb = None
        self.widget_type_combo = None
        self.widget_attr_field = None
        self.widget_min_sb = None
        self.widget_max_sb = None
        self.widget_orient_combo = None
        self.widget_attr_x_field = None
        self.widget_min_x_sb = None
        self.widget_max_x_sb = None
        self.widget_attr_y_field = None
        self.widget_min_y_sb = None
        self.widget_max_y_sb = None
        self.widget_recenter_cb = None
        self._wx_attr_row = None
        self._wx_checkbox_box = None
        self._wx_slider_box = None
        self._wx_2d_box = None
        self.backdrop_title_field = None
        self.backdrop_radius_sb = None
        self.vis_mode_combo = None
        self.vis_attr_field = None
        self.vis_operator_combo = None
        self.vis_threshold_sb = None
        self.vis_min_zoom_sb = None
        self.vis_max_zoom_sb = None
        self._vx_channel_box = None
        self._vx_zoom_box = None

        self._build_ui()
        self.refresh_fields()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.title = QtWidgets.QLabel("Item Editor")
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        outer.addWidget(self.title)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        content = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(content)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(2)
        scroll.setWidget(content)

        self._build_transform_section()
        self._build_appearance_section()
        self._build_shape_section()
        self._build_pin_section()
        self._build_mirror_section()
        self._build_controls_section()
        self._build_action_section()
        self._build_widget_section()
        self._build_backdrop_section()
        self._build_visibility_section()
        self.content_layout.addStretch()

    def _add_section(self, title):
        """Add a collapsible section and return its widget."""
        section = mwidgets.CollapsibleWidget(title, expanded=True)
        self.content_layout.addWidget(section)
        return section

    def _double_spin(self, callback, maximum=1.0e6, step=1.0, decimals=2):
        """Return a mixed-aware double spin box (sentinel minimum).

        Built on ``basic.CallBackDoubleSpinBox`` (the framework's value->callback
        wrapper); the mixed state is layered on via the sentinel minimum +
        ``setSpecialValueText``.
        """
        spin = basic.CallBackDoubleSpinBox(
            callback=callback, value=0.0, min=self.MIXED, max=maximum
        )
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setSpecialValueText(self.MIXED_TEXT)
        self._fields.append(spin)
        return spin

    def _int_spin(self, callback, minimum, maximum):
        """Return a mixed-aware int spin box (sentinel minimum)."""
        spin = basic.CallBackSpinBox(
            callback=callback, value=0, min=self.MIXED_INT, max=maximum
        )
        spin.setSpecialValueText(self.MIXED_TEXT)
        # ``minimum`` is the real usable floor; the sentinel sits below it.
        spin.setProperty("usable_minimum", minimum)
        self._fields.append(spin)
        return spin

    def _build_transform_section(self):
        section = self._add_section("Transform")

        form = QtWidgets.QFormLayout()
        self.pos_x_sb = self._double_spin(self._apply_position)
        self.pos_y_sb = self._double_spin(self._apply_position)
        self.rotate_sb = self._double_spin(
            self._apply_rotation, maximum=3600.0, step=5.0
        )
        form.addRow("X", self.pos_x_sb)
        form.addRow("Y", self.pos_y_sb)
        form.addRow("Rotation", self.rotate_sb)
        section.addLayout(form)

        reset_rot = basic.CallbackButton(callback=self._reset_rotation)
        reset_rot.setText("Reset Rotation")
        self._fields.append(reset_rot)
        section.addWidget(reset_rot)

        # Scale (shape) factor + axis buttons, mirroring the modal.
        scale_row = QtWidgets.QHBoxLayout()
        scale_row.addWidget(QtWidgets.QLabel("Factor"))
        self.scale_factor_sb = QtWidgets.QDoubleSpinBox()
        self.scale_factor_sb.setRange(0.01, 100.0)
        self.scale_factor_sb.setValue(1.1)
        self.scale_factor_sb.setSingleStep(0.05)
        scale_row.addWidget(self.scale_factor_sb)
        section.addLayout(scale_row)

        self.worldspace_cb = QtWidgets.QCheckBox("World space")
        section.addWidget(self.worldspace_cb)

        btn_row = QtWidgets.QHBoxLayout()
        for label, kwargs in (
            ("X", {"x": True}),
            ("Y", {"y": True}),
            ("XY", {"x": True, "y": True}),
        ):
            btn = basic.CallbackButton(callback=self._apply_scale, **kwargs)
            btn.setText(label)
            self._fields.append(btn)
            btn_row.addWidget(btn)
        section.addLayout(btn_row)

    def _build_appearance_section(self):
        section = self._add_section("Appearance")

        color_row = QtWidgets.QHBoxLayout()
        self.color_button = basic.CallbackButton(callback=self._pick_color)
        self.color_button.setToolTip("Shape color")
        color_row.addWidget(self.color_button)
        color_row.addWidget(QtWidgets.QLabel("Alpha"))
        self.alpha_sb = self._int_spin(self._apply_alpha, 0, 255)
        color_row.addWidget(self.alpha_sb)
        section.addLayout(color_row)

        # ``CallbackLineEdit`` commits on Enter (returnPressed), so a focus-out
        # never clobbers a field left blank for the mixed state.
        self.text_field = basic.CallbackLineEdit(callback=self._apply_text)
        self.text_field.setPlaceholderText("Text")
        self._fields.append(self.text_field)
        section.addWidget(self.text_field)

        text_form = QtWidgets.QFormLayout()
        self.text_size_sb = self._double_spin(
            self._apply_text_size, maximum=100.0, step=0.1
        )
        text_form.addRow("Text size", self.text_size_sb)

        self.text_align_combo = QtWidgets.QComboBox()
        self.text_align_combo.addItems(
            ["Center", "Top", "Bottom", "Left", "Right"]
        )
        self.text_align_combo.setToolTip(
            "Text placement relative to the item (edge alignments sit just "
            "outside so the text does not overlap the button)"
        )
        self.text_align_combo.currentIndexChanged.connect(
            self._apply_text_align
        )
        self._fields.append(self.text_align_combo)
        text_form.addRow("Text align", self.text_align_combo)

        self.text_offset_sb = self._double_spin(
            self._apply_text_offset, maximum=500.0, step=1.0
        )
        self.text_offset_sb.setToolTip("Gap in pixels from the aligned edge")
        text_form.addRow("Text offset", self.text_offset_sb)
        section.addLayout(text_form)

        tcolor_row = QtWidgets.QHBoxLayout()
        self.text_color_button = basic.CallbackButton(
            callback=self._pick_text_color
        )
        self.text_color_button.setToolTip("Text color")
        tcolor_row.addWidget(self.text_color_button)
        tcolor_row.addWidget(QtWidgets.QLabel("Alpha"))
        self.text_alpha_sb = self._int_spin(self._apply_text_alpha, 0, 255)
        tcolor_row.addWidget(self.text_alpha_sb)
        section.addLayout(tcolor_row)

    def _build_shape_section(self):
        section = self._add_section("Shape")

        # Polygon point editing -- hidden for a vector (SVG) item, which has no
        # per-point handles (including the "Show handles" toggle).
        self._shape_polygon_box = QtWidgets.QWidget()
        poly_layout = QtWidgets.QVBoxLayout(self._shape_polygon_box)
        poly_layout.setContentsMargins(0, 0, 0, 0)
        self.handles_cb = QtWidgets.QCheckBox("Show handles")
        self.handles_cb.setTristate(True)
        self.handles_cb.clicked.connect(self._apply_show_handles)
        self._fields.append(self.handles_cb)
        poly_layout.addWidget(self.handles_cb)
        count_row = QtWidgets.QHBoxLayout()
        count_row.addWidget(QtWidgets.QLabel("Vtx count"))
        self.count_sb = self._int_spin(self._apply_point_count, 2, 200)
        count_row.addWidget(self.count_sb)
        poly_layout.addLayout(count_row)
        handles_btn = basic.CallbackButton(callback=self._edit_handles)
        handles_btn.setText("Handles Positions...")
        self._fields.append(handles_btn)
        poly_layout.addWidget(handles_btn)
        section.addWidget(self._shape_polygon_box)

        shapes_btn = basic.CallbackButton(callback=self._open_shape_library)
        shapes_btn.setText("Shapes...")
        shapes_btn.setToolTip("Apply a premade / saved shape to the selection")
        self._fields.append(shapes_btn)
        section.addWidget(shapes_btn)

        # Vector (SVG) import: create a curved item from an .svg file (or drag
        # a file onto the canvas).
        import_btn = basic.CallbackButton(callback=self._import_svg)
        import_btn.setText("Import SVG...")
        import_btn.setToolTip(
            "Import an .svg file as a vector shape "
            "(or drag one onto the canvas)"
        )
        self._fields.append(import_btn)
        section.addWidget(import_btn)

        # Vector-only controls (render fill vs stroke + a summary), shown only
        # when the active item is a vector shape.
        self._shape_vector_box = QtWidgets.QWidget()
        vec_layout = QtWidgets.QVBoxLayout(self._shape_vector_box)
        vec_layout.setContentsMargins(0, 0, 0, 0)
        self._shape_vector_label = QtWidgets.QLabel("")
        self._shape_vector_label.setWordWrap(True)
        vec_layout.addWidget(self._shape_vector_label)
        render_row = QtWidgets.QHBoxLayout()
        render_row.addWidget(QtWidgets.QLabel("Render"))
        self.svg_mode_combo = QtWidgets.QComboBox()
        self.svg_mode_combo.addItems(["Fill", "Stroke (lines)"])
        self.svg_mode_combo.setToolTip(
            "Fill the shape, or draw it as lines of a given thickness "
            "(better for line-art icons)"
        )
        self.svg_mode_combo.currentIndexChanged.connect(self._apply_svg_mode)
        self._fields.append(self.svg_mode_combo)
        render_row.addWidget(self.svg_mode_combo)
        self.svg_width_sb = basic.CallBackDoubleSpinBox(
            callback=self._apply_svg_stroke_width,
            value=2.0,
            min=0.1,
            max=100.0,
        )
        self.svg_width_sb.setDecimals(1)
        self.svg_width_sb.setToolTip("Line thickness (stroke mode)")
        render_row.addWidget(self.svg_width_sb)
        vec_layout.addLayout(render_row)
        section.addWidget(self._shape_vector_box)

    def _build_pin_section(self):
        section = self._add_section("Pin")

        self.pinned_cb = QtWidgets.QCheckBox("Pinned to viewport")
        self.pinned_cb.setTristate(True)
        self.pinned_cb.setToolTip(
            "Lock the item to a viewport corner / edge (HUD overlay); it "
            "ignores canvas pan and zoom"
        )
        self.pinned_cb.clicked.connect(self._apply_pinned)
        self._fields.append(self.pinned_cb)
        section.addWidget(self.pinned_cb)

        # 3x3 anchor picker: nine exclusive toggle cells laid out like the
        # viewport regions (top-left ... bottom-right). Explicit cell borders
        # are set so the empty (unchecked) cells stay visible against Maya's
        # dark stylesheet -- a bare QToolButton renders frameless there.
        section.addWidget(QtWidgets.QLabel("Anchor"))
        anchor_grid = QtWidgets.QGridLayout()
        anchor_grid.setSpacing(2)
        anchor_style = (
            "QToolButton{border:1px solid #5a5a5a;border-radius:2px;"
            "background:#3c3c3c;}"
            "QToolButton:hover{border:1px solid #8a8a8a;}"
            "QToolButton:checked{background:#5285a6;"
            "border:1px solid #79b0d0;}"
        )
        self.anchor_group = QtWidgets.QButtonGroup(self)
        self.anchor_group.setExclusive(True)
        labels = {
            "tl": "Top-left",
            "tc": "Top-center",
            "tr": "Top-right",
            "ml": "Middle-left",
            "mc": "Center",
            "mr": "Middle-right",
            "bl": "Bottom-left",
            "bc": "Bottom-center",
            "br": "Bottom-right",
        }
        for index, code in enumerate(overlay.ANCHOR_CODES):
            button = QtWidgets.QToolButton()
            button.setCheckable(True)
            button.setFixedSize(QtCore.QSize(22, 22))
            button.setStyleSheet(anchor_style)
            button.setToolTip(labels[code])
            button.clicked.connect(partial(self._apply_anchor, code))
            self.anchor_group.addButton(button)
            self.anchor_buttons[code] = button
            self._fields.append(button)
            anchor_grid.addWidget(button, index // 3, index % 3)
        anchor_row = QtWidgets.QHBoxLayout()
        anchor_row.addLayout(anchor_grid)
        anchor_row.addStretch()
        section.addLayout(anchor_row)

        offset_form = QtWidgets.QFormLayout()
        self.pin_off_x_sb = self._int_spin(self._apply_offset, -10000, 10000)
        self.pin_off_y_sb = self._int_spin(self._apply_offset, -10000, 10000)
        offset_form.addRow("Offset X", self.pin_off_x_sb)
        offset_form.addRow("Offset Y", self.pin_off_y_sb)
        section.addLayout(offset_form)

        hint = QtWidgets.QLabel(
            "Drag the item on the canvas to set its offset; the anchor snaps "
            "to the nearest region."
        )
        hint.setWordWrap(True)
        section.addWidget(hint)

    def _build_mirror_section(self):
        section = self._add_section("Mirror")

        form = QtWidgets.QFormLayout()
        # Global axis setting (not a per-item field), so it uses the framework
        # callback spin directly rather than the mixed-value _double_spin.
        self.mirror_axis_sb = basic.CallBackDoubleSpinBox(
            callback=self._apply_mirror_axis, value=0.0, min=-1.0e6, max=1.0e6
        )
        form.addRow("Axis X", self.mirror_axis_sb)
        section.addLayout(form)

        link_btn = basic.CallbackButton(callback=self._link_mirror)
        link_btn.setText("Link selected pair")
        link_btn.setToolTip("Link exactly two selected items as a mirror pair")
        self._fields.append(link_btn)
        section.addWidget(link_btn)

        row = QtWidgets.QHBoxLayout()
        unlink_btn = basic.CallbackButton(callback=self._unlink_mirror)
        unlink_btn.setText("Unlink")
        self._fields.append(unlink_btn)
        row.addWidget(unlink_btn)
        symm_btn = basic.CallbackButton(callback=self._make_symmetric)
        symm_btn.setText("Make Symmetric")
        self._fields.append(symm_btn)
        row.addWidget(symm_btn)
        section.addLayout(row)

        self.mirror_status = QtWidgets.QLabel("")
        section.addWidget(self.mirror_status)

    def _build_controls_section(self):
        section = self._add_section("Controls")

        self.control_list = QtWidgets.QListWidget()
        self.control_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.control_list.setToolTip(
            "Controls of the active (last selected) item"
        )
        self.control_list.setMaximumHeight(120)
        section.addWidget(self.control_list)

        row1 = QtWidgets.QHBoxLayout()
        add_btn = basic.CallbackButton(callback=self._add_selected_controls)
        add_btn.setText("Add Selection")
        add_btn.setToolTip("Add the Maya selection to every selected item")
        self._fields.append(add_btn)
        row1.addWidget(add_btn)
        remove_btn = basic.CallbackButton(callback=self._remove_controls)
        remove_btn.setText("Remove")
        remove_btn.setToolTip("Remove the highlighted controls (active item)")
        self._fields.append(remove_btn)
        row1.addWidget(remove_btn)
        section.addLayout(row1)

        replace_btn = basic.CallbackButton(callback=self._search_replace)
        replace_btn.setText("Search && Replace")
        replace_btn.setToolTip("Search/replace control names on all selected")
        self._fields.append(replace_btn)
        section.addWidget(replace_btn)

    def _build_action_section(self):
        section = self._add_section("Action")

        self.custom_action_cb = QtWidgets.QCheckBox("Custom action (script)")
        self.custom_action_cb.setTristate(True)
        self.custom_action_cb.setToolTip(
            "Off = select controls, On = run the custom action script"
        )
        self.custom_action_cb.clicked.connect(self._apply_action_mode)
        self._fields.append(self.custom_action_cb)
        section.addWidget(self.custom_action_cb)

        script_btn = basic.CallbackButton(callback=self._edit_action_script)
        script_btn.setText("Edit Action Script...")
        self._fields.append(script_btn)
        section.addWidget(script_btn)

        section.addWidget(QtWidgets.QLabel("Custom Menus (active item)"))
        self.menus_list = QtWidgets.QListWidget()
        self.menus_list.setMaximumHeight(90)
        self.menus_list.itemDoubleClicked.connect(self._edit_menu)
        section.addWidget(self.menus_list)

        menu_row = QtWidgets.QHBoxLayout()
        new_menu = basic.CallbackButton(callback=self._new_menu)
        new_menu.setText("New")
        self._fields.append(new_menu)
        menu_row.addWidget(new_menu)
        del_menu = basic.CallbackButton(callback=self._remove_menu)
        del_menu.setText("Remove")
        self._fields.append(del_menu)
        menu_row.addWidget(del_menu)
        section.addLayout(menu_row)

    def _binding_spin(self):
        """Return a framework callback double spin that applies on change.

        Uses ``basic.CallBackDoubleSpinBox`` (like ``_double_spin``) rather than
        a raw ``QDoubleSpinBox``; binding fields follow the active item, so the
        mixed-value sentinel of ``_double_spin`` is intentionally not used here.
        """
        spin = basic.CallBackDoubleSpinBox(
            callback=self._apply_binding, value=0.0, min=-1.0e6, max=1.0e6
        )
        spin.setDecimals(3)
        self._fields.append(spin)
        return spin

    def _binding_attr_field(self, placeholder, callback=None):
        """Return a namespaced-attribute line edit that applies on edit-finish.

        Args:
            placeholder (str): the field's placeholder text.
            callback (callable, optional): the ``editingFinished`` handler;
                defaults to ``_apply_binding`` (the widget binding fields).
        """
        field = QtWidgets.QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setToolTip(
            "Enter node.attribute without a namespace; the picker's active "
            "namespace is applied automatically (like control names). A "
            "namespace you type explicitly is kept as-is."
        )
        field.editingFinished.connect(callback or self._apply_binding)
        self._fields.append(field)
        return field

    def _widget_script_button(self, label, key):
        """Return a button that opens the script editor for a widget state."""
        button = basic.CallbackButton(
            callback=partial(self._edit_widget_script, key)
        )
        button.setText(label)
        self._fields.append(button)
        return button

    def _build_widget_section(self):
        section = self._add_section("Widget")

        type_form = QtWidgets.QFormLayout()
        self.widget_type_combo = QtWidgets.QComboBox()
        self.widget_type_combo.addItems(
            ["Button", "Checkbox", "Slider (1D)", "2D Slider"]
        )
        self.widget_type_combo.setToolTip(
            "Button selects controls / runs the action; the others drive a "
            "bound attribute and/or a script"
        )
        self.widget_type_combo.currentIndexChanged.connect(
            self._apply_widget_type
        )
        self._fields.append(self.widget_type_combo)
        type_form.addRow("Type", self.widget_type_combo)
        section.addLayout(type_form)

        # Shared attribute row (checkbox + 1D slider).
        self._wx_attr_row = QtWidgets.QWidget()
        attr_form = QtWidgets.QFormLayout(self._wx_attr_row)
        attr_form.setContentsMargins(0, 0, 0, 0)
        self.widget_attr_field = self._binding_attr_field("node.attribute")
        attr_form.addRow("Attribute", self.widget_attr_field)
        section.addWidget(self._wx_attr_row)

        # Checkbox on / off scripts.
        self._wx_checkbox_box = QtWidgets.QWidget()
        cb_row = QtWidgets.QHBoxLayout(self._wx_checkbox_box)
        cb_row.setContentsMargins(0, 0, 0, 0)
        cb_row.addWidget(self._widget_script_button("On Script...", "on"))
        cb_row.addWidget(self._widget_script_button("Off Script...", "off"))
        section.addWidget(self._wx_checkbox_box)

        # 1D slider range + orientation + value script.
        self._wx_slider_box = QtWidgets.QWidget()
        slider_layout = QtWidgets.QVBoxLayout(self._wx_slider_box)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        range_row = QtWidgets.QHBoxLayout()
        range_row.addWidget(QtWidgets.QLabel("Min"))
        self.widget_min_sb = self._binding_spin()
        range_row.addWidget(self.widget_min_sb)
        range_row.addWidget(QtWidgets.QLabel("Max"))
        self.widget_max_sb = self._binding_spin()
        range_row.addWidget(self.widget_max_sb)
        slider_layout.addLayout(range_row)
        orient_form = QtWidgets.QFormLayout()
        self.widget_orient_combo = QtWidgets.QComboBox()
        self.widget_orient_combo.addItems(["Horizontal", "Vertical"])
        self.widget_orient_combo.currentIndexChanged.connect(
            self._apply_binding
        )
        self._fields.append(self.widget_orient_combo)
        orient_form.addRow("Orientation", self.widget_orient_combo)
        slider_layout.addLayout(orient_form)
        slider_layout.addWidget(
            self._widget_script_button("Value Script...", "value")
        )
        section.addWidget(self._wx_slider_box)

        # 2D slider: two attributes + ranges + recenter + script.
        self._wx_2d_box = QtWidgets.QWidget()
        twod_layout = QtWidgets.QVBoxLayout(self._wx_2d_box)
        twod_layout.setContentsMargins(0, 0, 0, 0)
        x_row = QtWidgets.QHBoxLayout()
        x_row.addWidget(QtWidgets.QLabel("X"))
        self.widget_attr_x_field = self._binding_attr_field("node.attrX")
        x_row.addWidget(self.widget_attr_x_field)
        self.widget_min_x_sb = self._binding_spin()
        self.widget_max_x_sb = self._binding_spin()
        x_row.addWidget(self.widget_min_x_sb)
        x_row.addWidget(self.widget_max_x_sb)
        twod_layout.addLayout(x_row)
        y_row = QtWidgets.QHBoxLayout()
        y_row.addWidget(QtWidgets.QLabel("Y"))
        self.widget_attr_y_field = self._binding_attr_field("node.attrY")
        y_row.addWidget(self.widget_attr_y_field)
        self.widget_min_y_sb = self._binding_spin()
        self.widget_max_y_sb = self._binding_spin()
        y_row.addWidget(self.widget_min_y_sb)
        y_row.addWidget(self.widget_max_y_sb)
        twod_layout.addLayout(y_row)
        self.widget_recenter_cb = QtWidgets.QCheckBox("Recenter on release")
        self.widget_recenter_cb.clicked.connect(self._apply_binding)
        self._fields.append(self.widget_recenter_cb)
        twod_layout.addWidget(self.widget_recenter_cb)
        twod_layout.addWidget(
            self._widget_script_button("XY Script...", "xy")
        )
        section.addWidget(self._wx_2d_box)

    def _build_backdrop_section(self):
        section = self._add_section("Backdrop")

        form = QtWidgets.QFormLayout()
        self.backdrop_title_field = QtWidgets.QLineEdit()
        self.backdrop_title_field.setPlaceholderText("Backdrop title")
        self.backdrop_title_field.editingFinished.connect(
            self._apply_backdrop_title
        )
        self._fields.append(self.backdrop_title_field)
        form.addRow("Title", self.backdrop_title_field)

        self.backdrop_radius_sb = self._double_spin(
            self._apply_backdrop_radius, maximum=80.0, step=1.0
        )
        self.backdrop_radius_sb.setToolTip(
            "Corner radius; 0 = straight corners"
        )
        form.addRow("Corners", self.backdrop_radius_sb)
        section.addLayout(form)

        hint = QtWidgets.QLabel(
            "Color + transparency are set in Appearance. Drag the backdrop to "
            "move everything inside it together."
        )
        hint.setWordWrap(True)
        section.addWidget(hint)

    def _capture_zoom_button(self, which):
        """Return a button that captures the current view zoom into a bound."""
        button = basic.CallbackButton(
            callback=partial(self._capture_zoom, which)
        )
        button.setText("Capture current")
        button.setToolTip("Set this bound from the view's current zoom level")
        self._fields.append(button)
        return button

    def _build_visibility_section(self):
        section = self._add_section("Visibility")

        mode_form = QtWidgets.QFormLayout()
        self.vis_mode_combo = QtWidgets.QComboBox()
        self.vis_mode_combo.addItems(["None", "Channel state", "Zoom level"])
        self.vis_mode_combo.setToolTip(
            "Show the item only when a Maya attribute passes a test "
            "(channel state) or the view zoom is within a range (zoom level). "
            "Edit mode always shows every item."
        )
        self.vis_mode_combo.currentIndexChanged.connect(self._apply_visibility)
        self._fields.append(self.vis_mode_combo)
        mode_form.addRow("Condition", self.vis_mode_combo)
        section.addLayout(mode_form)

        # Channel-state fields: attribute + operator + threshold.
        self._vx_channel_box = QtWidgets.QWidget()
        channel_layout = QtWidgets.QVBoxLayout(self._vx_channel_box)
        channel_layout.setContentsMargins(0, 0, 0, 0)
        attr_form = QtWidgets.QFormLayout()
        self.vis_attr_field = self._binding_attr_field(
            "node.attribute", callback=self._apply_visibility
        )
        attr_form.addRow("Attribute", self.vis_attr_field)
        channel_layout.addLayout(attr_form)
        test_row = QtWidgets.QHBoxLayout()
        test_row.addWidget(QtWidgets.QLabel("Show when"))
        self.vis_operator_combo = QtWidgets.QComboBox()
        self.vis_operator_combo.addItems(list(visibility.OPERATORS))
        self.vis_operator_combo.setCurrentIndex(
            visibility.OPERATORS.index(">=")
        )
        self.vis_operator_combo.currentIndexChanged.connect(
            self._apply_visibility
        )
        self._fields.append(self.vis_operator_combo)
        test_row.addWidget(self.vis_operator_combo)
        self.vis_threshold_sb = basic.CallBackDoubleSpinBox(
            callback=self._apply_visibility, value=0.5, min=-1.0e6, max=1.0e6
        )
        self.vis_threshold_sb.setDecimals(3)
        self._fields.append(self.vis_threshold_sb)
        test_row.addWidget(self.vis_threshold_sb)
        channel_layout.addLayout(test_row)
        section.addWidget(self._vx_channel_box)

        # Zoom-level fields: min / max scale, each with a capture button. A
        # bound of 0 means open-ended (a real zoom scale is always > 0).
        self._vx_zoom_box = QtWidgets.QWidget()
        zoom_form = QtWidgets.QFormLayout(self._vx_zoom_box)
        zoom_form.setContentsMargins(0, 0, 0, 0)
        min_row = QtWidgets.QHBoxLayout()
        self.vis_min_zoom_sb = basic.CallBackDoubleSpinBox(
            callback=self._apply_visibility, value=0.0, min=0.0, max=1.0e6
        )
        self.vis_min_zoom_sb.setDecimals(3)
        self.vis_min_zoom_sb.setToolTip("Lower zoom bound; 0 = no lower bound")
        min_row.addWidget(self.vis_min_zoom_sb)
        min_row.addWidget(self._capture_zoom_button("min"))
        zoom_form.addRow("Min zoom", min_row)
        max_row = QtWidgets.QHBoxLayout()
        self.vis_max_zoom_sb = basic.CallBackDoubleSpinBox(
            callback=self._apply_visibility, value=0.0, min=0.0, max=1.0e6
        )
        self.vis_max_zoom_sb.setDecimals(3)
        self.vis_max_zoom_sb.setToolTip("Upper zoom bound; 0 = no upper bound")
        max_row.addWidget(self.vis_max_zoom_sb)
        max_row.addWidget(self._capture_zoom_button("max"))
        zoom_form.addRow("Max zoom", max_row)
        section.addWidget(self._vx_zoom_box)

    # ------------------------------------------------------------------
    # Selection binding
    # ------------------------------------------------------------------
    def _current_view(self):
        """Return the main window's active graphics view, or None."""
        getter = getattr(self.main_window, "_current_view", None)
        if getter is None:
            return None
        return getter()

    def _commit_edit(self, label=None):
        """Record the just-applied panel change as one editor undo step.

        The view owns the undo stack and diffs against its own baseline, so
        this only needs to signal that an edit committed; a call with no change
        is a harmless no-op.
        """
        view = self._view
        if view is not None and hasattr(view, "commit_edit"):
            view.commit_edit(label)

    def sync(self):
        """Rebind to the current active view's selection."""
        self.sync_from_view(self._current_view())

    def sync_from_view(self, view):
        """Rebind to ``view``'s current picker selection.

        Args:
            view (GraphicViewWidget): the view whose selection to edit.
        """
        self._view = view
        items = []
        if view is not None:
            items = view.scene().get_selected_items()
        self.items = list(items)
        self.refresh_fields()

    def refresh_transform(self):
        """Refresh only the transform fields (live during a manipulator drag).

        The selection set is stable during a drag, so this avoids rebuilding the
        control / menu lists (and their per-control ``objExists`` checks) every
        mouse-move frame. Skipped entirely when the panel is hidden.
        """
        if not self.items or not self.isVisible():
            return
        self._guarded(self._populate_transform)

    def _active_item(self):
        """Return the reference item for per-item fields (controls/menus)."""
        return self.items[-1] if self.items else None

    def _shared(self, func):
        """Return ``(value, mixed)`` for ``func`` across the selection.

        ``value`` is the first item's value; ``mixed`` is True when the items
        do not all agree.
        """
        if not self.items:
            return (None, False)
        values = [func(item) for item in self.items]
        first = values[0]
        mixed = any(value != first for value in values[1:])
        return (first, mixed)

    # ------------------------------------------------------------------
    # Field population
    # ------------------------------------------------------------------
    def _guarded(self, populate):
        """Run a populate function with the canvas<->panel sync guard set."""
        self._syncing = True
        try:
            populate()
        finally:
            self._syncing = False

    def _populate_all(self):
        self._populate_transform()
        self._populate_appearance()
        self._populate_shape()
        self._populate_pin()
        self._populate_mirror()
        self._populate_controls()
        self._populate_action()
        self._populate_widget()
        self._populate_backdrop()
        self._populate_visibility()

    def _populate_backdrop(self):
        item = self._active_item()
        is_backdrop = item is not None and item.get_backdrop()
        self.backdrop_title_field.blockSignals(True)
        self.backdrop_title_field.setText(
            item.get_backdrop_title() if is_backdrop else ""
        )
        self.backdrop_title_field.blockSignals(False)
        radius = item.get_corner_radius() if is_backdrop else 0.0
        self._set_spin(self.backdrop_radius_sb, round(radius, 4), False)

    def _update_visibility_mode(self, mode):
        """Show only the sub-box relevant to ``mode`` (VIS_NONE hides both)."""
        self._vx_channel_box.setVisible(mode == visibility.VIS_CHANNEL)
        self._vx_zoom_box.setVisible(mode == visibility.VIS_ZOOM)

    def _populate_visibility(self):
        mode, mode_mixed = self._shared(
            lambda item: item.get_visibility().get("mode", visibility.VIS_NONE)
        )
        self._set_enum_combo(
            self.vis_mode_combo, self._VIS_MODE_ORDER, mode, mode_mixed
        )

        # Condition fields follow the active item (like the widget binding); an
        # edit applies to the whole selection via _apply_visibility.
        item = self._active_item()
        condition = (item.get_visibility() if item else None) or {}
        self.vis_attr_field.setText(condition.get("attr", ""))
        self._set_enum_combo(
            self.vis_operator_combo,
            visibility.OPERATORS,
            condition.get("operator", ">="),
        )
        self.vis_threshold_sb.setValue(condition.get("threshold", 0.5))
        self.vis_min_zoom_sb.setValue(condition.get("min_zoom") or 0.0)
        self.vis_max_zoom_sb.setValue(condition.get("max_zoom") or 0.0)

        self._update_visibility_mode(
            visibility.VIS_NONE if mode_mixed else mode
        )

    def _update_widget_visibility(self, widget_type):
        """Show only the sub-rows relevant to ``widget_type`` (None hides all)."""
        self._wx_attr_row.setVisible(
            widget_type
            in (widget_binding.WIDGET_CHECKBOX, widget_binding.WIDGET_SLIDER)
        )
        self._wx_checkbox_box.setVisible(
            widget_type == widget_binding.WIDGET_CHECKBOX
        )
        self._wx_slider_box.setVisible(
            widget_type == widget_binding.WIDGET_SLIDER
        )
        self._wx_2d_box.setVisible(
            widget_type == widget_binding.WIDGET_SLIDER2D
        )

    def _populate_widget(self):
        wtype, wtype_mixed = self._shared(lambda item: item.get_widget_type())
        self._set_enum_combo(
            self.widget_type_combo,
            self._WIDGET_TYPE_ORDER,
            wtype,
            wtype_mixed,
        )

        # Binding fields follow the active item (like controls / menus); an
        # edit applies to the whole selection via _apply_binding.
        item = self._active_item()
        binding = (item.get_binding() if item else None) or {}
        self.widget_attr_field.setText(binding.get("attr", ""))
        self.widget_min_sb.setValue(binding.get("min", 0.0))
        self.widget_max_sb.setValue(binding.get("max", 1.0))
        horizontal = (
            binding.get("orientation", widget_binding.ORIENT_HORIZONTAL)
            == widget_binding.ORIENT_HORIZONTAL
        )
        self.widget_orient_combo.setCurrentIndex(0 if horizontal else 1)
        self.widget_attr_x_field.setText(binding.get("attr_x", ""))
        self.widget_min_x_sb.setValue(binding.get("min_x", -1.0))
        self.widget_max_x_sb.setValue(binding.get("max_x", 1.0))
        self.widget_attr_y_field.setText(binding.get("attr_y", ""))
        self.widget_min_y_sb.setValue(binding.get("min_y", -1.0))
        self.widget_max_y_sb.setValue(binding.get("max_y", 1.0))
        self.widget_recenter_cb.setChecked(bool(binding.get("recenter")))

        self._update_widget_visibility(None if wtype_mixed else wtype)

    def _populate_pin(self):
        pinned, pinned_mixed = self._shared(lambda item: item.get_pinned())
        self._set_tristate(self.pinned_cb, pinned, pinned_mixed)

        anchor, anchor_mixed = self._shared(lambda item: item.get_anchor())
        self.anchor_group.setExclusive(False)
        for code, button in self.anchor_buttons.items():
            button.blockSignals(True)
            button.setChecked(not anchor_mixed and code == anchor)
            button.blockSignals(False)
        self.anchor_group.setExclusive(True)

        ox, ox_mixed = self._shared(lambda item: int(round(item.get_offset()[0])))
        oy, oy_mixed = self._shared(lambda item: int(round(item.get_offset()[1])))
        self._set_spin(self.pin_off_x_sb, ox, ox_mixed)
        self._set_spin(self.pin_off_y_sb, oy, oy_mixed)

    def _populate_mirror(self):
        if self._view is not None:
            self.mirror_axis_sb.setValue(self._view.mirror_axis_x)
        linked = sum(1 for item in self.items if item.mirror_id)
        if linked:
            self.mirror_status.setText(
                "{} of {} selected linked".format(linked, len(self.items))
            )
        else:
            self.mirror_status.setText("no mirror link")

    def refresh_fields(self):
        """Populate every field from the current selection (mixed-aware)."""
        has = bool(self.items)
        for widget in self._fields:
            widget.setEnabled(has)
        self.title.setText(
            "Item Editor - {} selected".format(len(self.items))
            if has
            else "Item Editor - no selection"
        )
        if not has:
            return
        self._guarded(self._populate_all)

    def _set_spin(self, spin, value, mixed):
        """Set a spin box to ``value`` or the mixed sentinel."""
        if mixed or value is None:
            spin.setValue(spin.minimum())
        else:
            spin.setValue(value)

    def _set_tristate(self, checkbox, value, mixed):
        """Set a tristate checkbox from a shared value (partial when mixed)."""
        checkbox.blockSignals(True)
        checkbox.setTristate(True)
        if mixed:
            checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            state = QtCore.Qt.Checked if value else QtCore.Qt.Unchecked
            checkbox.setCheckState(state)
        checkbox.blockSignals(False)

    def _set_enum_combo(self, combo, order, value, mixed=False):
        """Select ``value``'s index in ``combo`` (signals blocked).

        Mixed selections clear the combo (index -1); an unknown value falls
        back to the first entry. ``order`` is the index -> value sequence.
        """
        combo.blockSignals(True)
        if mixed or value not in order:
            combo.setCurrentIndex(-1 if mixed else 0)
        else:
            combo.setCurrentIndex(order.index(value))
        combo.blockSignals(False)

    def _populate_transform(self):
        x, x_mixed = self._shared(lambda item: round(item.x(), 4))
        y, y_mixed = self._shared(lambda item: round(item.y(), 4))
        rot, rot_mixed = self._shared(lambda item: round(item.rotation(), 4))
        self._set_spin(self.pos_x_sb, x, x_mixed)
        self._set_spin(self.pos_y_sb, y, y_mixed)
        self._set_spin(self.rotate_sb, rot, rot_mixed)

    def _populate_appearance(self):
        color, color_mixed = self._shared(
            lambda item: item.get_color().getRgb()
        )
        self._set_swatch(
            self.color_button, None if color_mixed else QtGui.QColor(*color)
        )
        alpha, alpha_mixed = self._shared(
            lambda item: item.get_color().alpha()
        )
        self._set_spin(self.alpha_sb, alpha, alpha_mixed)

        text, text_mixed = self._shared(lambda item: item.get_text())
        self.text_field.blockSignals(True)
        if text_mixed:
            self.text_field.clear()
            self.text_field.setPlaceholderText("- multiple -")
        else:
            self.text_field.setText(text or "")
            self.text_field.setPlaceholderText("Text")
        self.text_field.blockSignals(False)

        size, size_mixed = self._shared(
            lambda item: round(item.get_text_size(), 4)
        )
        self._set_spin(self.text_size_sb, size, size_mixed)

        tcolor, tcolor_mixed = self._shared(
            lambda item: item.get_text_color().getRgb()
        )
        self._set_swatch(
            self.text_color_button,
            None if tcolor_mixed else QtGui.QColor(*tcolor),
        )
        talpha, talpha_mixed = self._shared(
            lambda item: item.get_text_color().alpha()
        )
        self._set_spin(self.text_alpha_sb, talpha, talpha_mixed)

        align, align_mixed = self._shared(lambda item: item.get_text_align())
        self._set_enum_combo(
            self.text_align_combo, graphics.TEXT_ALIGNS, align, align_mixed
        )

        offset, offset_mixed = self._shared(
            lambda item: round(item.get_text_offset(), 4)
        )
        self._set_spin(self.text_offset_sb, offset, offset_mixed)

    def _populate_shape(self):
        count, count_mixed = self._shared(lambda item: item.point_count)
        self._set_spin(self.count_sb, count, count_mixed)

        status, status_mixed = self._shared(
            lambda item: item.get_edit_status()
        )
        self._set_tristate(self.handles_cb, status, status_mixed)

        # Show polygon point editing only for a polygon item; the vector render
        # controls (fill / stroke + width) only for a vector item.
        item = self._active_item()
        is_vector = item is not None and item.is_vector_shape()
        self._shape_polygon_box.setVisible(not is_vector)
        self._shape_vector_box.setVisible(is_vector)
        if not is_vector:
            return
        svg = item.get_svg_shape()
        self._shape_vector_label.setText(
            "Vector: {} ({} subpaths)".format(
                svg.get("name", "(svg)"), len(svg.get("subpaths", []))
            )
        )
        self._set_enum_combo(
            self.svg_mode_combo, self._SVG_MODE_ORDER, item.get_svg_mode()
        )
        self.svg_width_sb.setValue(item.get_svg_stroke_width())

    def _apply_svg_mode(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        index = self.svg_mode_combo.currentIndex()
        if index < 0:
            return
        mode = self._SVG_MODE_ORDER[index]
        for item in self.items:
            if item.is_vector_shape():
                item.set_svg_mode(mode)
        self._repaint_view()

    def _apply_svg_stroke_width(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        width = self.svg_width_sb.value()
        for item in self.items:
            if item.is_vector_shape():
                item.set_svg_stroke_width(width)
        self._repaint_view()

    def _import_svg(self):
        """Open the main window's SVG import (file dialog)."""
        if self.main_window is not None:
            self.main_window._cmd_import_svg()

    def _populate_controls(self):
        self.control_list.clear()
        item = self._active_item()
        if item is None:
            return
        for name in item.get_controls(with_namespace=False):
            list_item = basic.CtrlListWidgetItem()
            list_item.setText(name)
            self.control_list.addItem(list_item)

    def _populate_action(self):
        mode, mode_mixed = self._shared(
            lambda item: item.get_custom_action_mode()
        )
        self._set_tristate(self.custom_action_cb, mode, mode_mixed)

        self.menus_list.clear()
        item = self._active_item()
        if item is None:
            return
        for name, _cmd in item.get_custom_menus():
            self.menus_list.addItem(name)

    def _set_swatch(self, button, color):
        """Show ``color`` on ``button`` or a 'multiple' placeholder if None."""
        if color is None:
            button.setText("multiple")
            button.setPalette(QtWidgets.QApplication.palette())
            button.setAutoFillBackground(False)
        else:
            button.setText("")
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Button, color)
            button.setPalette(palette)
            button.setAutoFillBackground(True)

    # ------------------------------------------------------------------
    # Apply helpers (write to every selected item)
    # ------------------------------------------------------------------
    def _repaint_view(self):
        """Propagate edits to mirror partners, then repaint the canvas.

        Also records the just-applied field edit as one editor undo step: every
        transform / appearance / text / shape / widget / backdrop / visibility
        edit ends here, so this is the single seam that makes them undoable.
        """
        if self._view is None:
            return
        # Live-mirror the edit to any linked partners (guarded against loops),
        # then repaint so both sides refresh.
        self._view.apply_mirror_for(self.items)
        self._view.viewport().update()
        self._commit_edit()

    def _committed(self, spin):
        """Return a committed spin value, or None while the field is mixed.

        A mixed field sits at ``spin.minimum()`` (the sentinel shown as
        ``MIXED_TEXT``); any other value is a real, user-committed edit.
        """
        value = spin.value()
        return None if value == spin.minimum() else value

    def _resolve_tristate(self, checkbox):
        """Resolve a user-clicked tristate to a bool (partial counts as on).

        Clears the tristate so a subsequent click toggles cleanly on/off.
        """
        resolved = checkbox.checkState() != QtCore.Qt.Unchecked
        checkbox.setTristate(False)
        return resolved

    # -- transform ------------------------------------------------------
    def _apply_position(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        x = self._committed(self.pos_x_sb)
        y = self._committed(self.pos_y_sb)
        for item in self.items:
            new_x = item.x() if x is None else x
            new_y = item.y() if y is None else y
            item.setPos(new_x, new_y)
        self._repaint_view()

    def _apply_rotation(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        angle = self._committed(self.rotate_sb)
        if angle is None:
            return
        for item in self.items:
            item.setRotation(angle)
            item.update()
        self._repaint_view()

    def _reset_rotation(self):
        if not self.items:
            return
        for item in self.items:
            item.reset_rotation()
        self._repaint_view()
        self.refresh_fields()

    def _apply_scale(self, x=False, y=False):
        if not self.items:
            return
        factor = self.scale_factor_sb.value()
        world = self.worldspace_cb.isChecked()
        sx = factor if x else 1.0
        sy = factor if y else 1.0
        for item in self.items:
            item.scale_shape(x=sx, y=sy, world=world)
        self._repaint_view()
        # Position may change in world-space scale mode.
        self._guarded(self._populate_transform)

    # -- appearance -----------------------------------------------------
    def _pick_color(self):
        if not self.items:
            return
        initial = self._active_item().get_color()
        color = QtWidgets.QColorDialog.getColor(initial=initial, parent=self)
        if not color.isValid():
            return
        for item in self.items:
            new_color = QtGui.QColor(color)
            new_color.setAlpha(item.get_color().alpha())
            item.set_color(new_color)
        self._repaint_view()
        self._guarded(self._populate_appearance)

    def _apply_alpha(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        alpha = self._committed(self.alpha_sb)
        if alpha is None:
            return
        for item in self.items:
            color = item.get_color()
            color.setAlpha(alpha)
            item.set_color(color)
        self._repaint_view()

    def _apply_text(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        text = str(self.text_field.text())
        for item in self.items:
            item.set_text(text)
        self._repaint_view()

    def _apply_text_size(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        size = self._committed(self.text_size_sb)
        if size is None:
            return
        for item in self.items:
            item.set_text_size(size)
        self._repaint_view()

    def _pick_text_color(self):
        if not self.items:
            return
        initial = self._active_item().get_text_color()
        color = QtWidgets.QColorDialog.getColor(initial=initial, parent=self)
        if not color.isValid():
            return
        for item in self.items:
            new_color = QtGui.QColor(color)
            new_color.setAlpha(item.get_text_color().alpha())
            item.set_text_color(new_color)
        self._repaint_view()
        self._guarded(self._populate_appearance)

    def _apply_text_alpha(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        alpha = self._committed(self.text_alpha_sb)
        if alpha is None:
            return
        for item in self.items:
            color = item.get_text_color()
            color.setAlpha(alpha)
            item.set_text_color(color)
        self._repaint_view()

    def _apply_text_align(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        index = self.text_align_combo.currentIndex()
        if index < 0:
            return
        align = graphics.TEXT_ALIGNS[index]
        for item in self.items:
            item.set_text_align(align)
        self._repaint_view()

    def _apply_text_offset(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        offset = self._committed(self.text_offset_sb)
        if offset is None:
            return
        for item in self.items:
            item.set_text_offset(offset)
        self._repaint_view()

    # -- shape ----------------------------------------------------------
    def _apply_show_handles(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        # A user click resolves the tristate; treat partial as "show".
        show = self._resolve_tristate(self.handles_cb)
        for item in self.items:
            item.set_edit_status(show)
        self._repaint_view()

    def _apply_point_count(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        count = self._committed(self.count_sb)
        if count is None:
            return
        floor = self.count_sb.property("usable_minimum") or 2
        count = max(count, floor)
        for item in self.items:
            item.edit_point_count(count)
        self._repaint_view()

    def _edit_handles(self):
        item = self._active_item()
        if item is None:
            return
        if self.handles_window:
            try:
                self.handles_window.close()
                self.handles_window.deleteLater()
            except Exception:
                pass
        self.handles_window = HandlesPositionWindow(
            parent=self, picker_item=item
        )
        self.handles_window.show()
        self.handles_window.raise_()

    def _open_shape_library(self):
        if not self.items:
            return
        active = self._active_item()
        current = None
        if active is not None:
            current = [[h.x(), h.y()] for h in active.handles]
        dialog = ShapeLibraryDialog(
            parent=self,
            apply_callback=self._apply_shape,
            current_handles=current,
        )
        dialog.show()

    def _apply_shape(self, handles):
        if not self.items:
            return
        for item in self.items:
            item.set_handles([list(point) for point in handles])
        self._repaint_view()

    # -- mirror ---------------------------------------------------------
    def _apply_mirror_axis(self, *args, **kwargs):
        if self._syncing or self._view is None:
            return
        self._view.mirror_axis_x = self.mirror_axis_sb.value()
        self._view.viewport().update()

    def _link_mirror(self):
        if self._view is None:
            return
        if len(self.items) != 2:
            QtWidgets.QMessageBox.information(
                self, "Mirror", "Select exactly two items to link."
            )
            return
        # Establish the relationship without moving anything; the user snaps
        # the sides explicitly with Make Symmetric.
        self._view.link_mirror_pair(self.items[0], self.items[1])
        self._view.viewport().update()
        self._guarded(self._populate_mirror)
        self._commit_edit("Link mirror")

    def _unlink_mirror(self):
        if self._view is None:
            return
        for item in self.items:
            self._view.unlink_mirror(item)
        self._view.viewport().update()
        self._guarded(self._populate_mirror)
        self._commit_edit("Unlink mirror")

    def _make_symmetric(self):
        if self._view is None:
            return
        # Reflect each selected item onto its partner (per-item, so a selected
        # item forces its own side onto the other).
        for item in self.items:
            self._view.apply_mirror_for([item])
        self._view.viewport().update()
        self._commit_edit("Make symmetric")

    # -- pin ------------------------------------------------------------
    def _apply_pinned(self, *args, **kwargs):
        if self._syncing or not self.items or self._view is None:
            return
        state = self._resolve_tristate(self.pinned_cb)
        for item in self.items:
            self._view.set_item_pinned(item, state)
        self._view.viewport().update()
        self._guarded(self._populate_pin)
        self._commit_edit("Pin item")

    def _apply_anchor(self, code, *args, **kwargs):
        if self._syncing or not self.items or self._view is None:
            return
        for item in self.items:
            item.set_anchor(code)
        self._view._update_pinned_items()
        self._view.viewport().update()
        self._commit_edit("Set anchor")

    def _apply_offset(self, *args, **kwargs):
        if self._syncing or not self.items or self._view is None:
            return
        x = self._committed(self.pin_off_x_sb)
        y = self._committed(self.pin_off_y_sb)
        for item in self.items:
            off = item.get_offset()
            item.set_offset(
                [off[0] if x is None else x, off[1] if y is None else y]
            )
        self._view._update_pinned_items()
        self._view.viewport().update()
        self._commit_edit("Set pin offset")

    # -- widget ---------------------------------------------------------
    def _apply_widget_type(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        index = self.widget_type_combo.currentIndex()
        if index < 0:
            return
        widget_type = self._WIDGET_TYPE_ORDER[index]
        for item in self.items:
            item.set_widget_type(widget_type)
        self._update_widget_visibility(widget_type)
        self._repaint_view()
        # A fresh non-button widget gets a default binding; reflect it back.
        self._guarded(self._populate_widget)

    def _collect_binding(self):
        """Build a binding dict from the current field values."""
        orientation = (
            widget_binding.ORIENT_HORIZONTAL
            if self.widget_orient_combo.currentIndex() == 0
            else widget_binding.ORIENT_VERTICAL
        )
        return {
            "attr": str(self.widget_attr_field.text()).strip(),
            "min": self.widget_min_sb.value(),
            "max": self.widget_max_sb.value(),
            "orientation": orientation,
            "attr_x": str(self.widget_attr_x_field.text()).strip(),
            "min_x": self.widget_min_x_sb.value(),
            "max_x": self.widget_max_x_sb.value(),
            "attr_y": str(self.widget_attr_y_field.text()).strip(),
            "min_y": self.widget_min_y_sb.value(),
            "max_y": self.widget_max_y_sb.value(),
            "recenter": self.widget_recenter_cb.isChecked(),
        }

    def _apply_binding(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        binding = self._collect_binding()
        for item in self.items:
            item.set_binding(binding)
        self._repaint_view()

    def _edit_widget_script(self, key):
        """Edit the widget script for ``key`` and apply it to the selection."""
        item = self._active_item()
        if item is None:
            return
        # Seed an empty script with the per-state sample snippet so the editor
        # opens with a documented, runnable example.
        current = (item.get_widget_scripts() or {}).get(
            key
        ) or widget_binding.script_template(key)
        cmd, ok = CustomScriptEditDialog.get(cmd=current, item=item)
        if not (ok and cmd):
            return
        for target in self.items:
            scripts = dict(target.get_widget_scripts() or {})
            scripts[key] = cmd
            target.set_widget_scripts(scripts)
        self._commit_edit("Edit widget script")

    # -- backdrop -------------------------------------------------------
    def _apply_backdrop_title(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        title = str(self.backdrop_title_field.text())
        for item in self.items:
            if item.get_backdrop():
                item.set_backdrop_title(title)
        self._repaint_view()

    def _apply_backdrop_radius(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        radius = self._committed(self.backdrop_radius_sb)
        if radius is None:
            return
        for item in self.items:
            if item.get_backdrop():
                item.set_corner_radius(radius)
        self._repaint_view()

    # -- visibility -----------------------------------------------------
    def _collect_visibility(self):
        """Build a visibility condition dict from the current field values."""
        index = self.vis_mode_combo.currentIndex()
        mode = (
            self._VIS_MODE_ORDER[index]
            if index >= 0
            else visibility.VIS_NONE
        )
        if mode == visibility.VIS_CHANNEL:
            return {
                "mode": visibility.VIS_CHANNEL,
                "attr": str(self.vis_attr_field.text()).strip(),
                "operator": visibility.OPERATORS[
                    self.vis_operator_combo.currentIndex()
                ],
                "threshold": self.vis_threshold_sb.value(),
            }
        if mode == visibility.VIS_ZOOM:
            low = self.vis_min_zoom_sb.value()
            high = self.vis_max_zoom_sb.value()
            # A bound of 0 means open-ended (a real zoom scale is always > 0).
            return {
                "mode": visibility.VIS_ZOOM,
                "min_zoom": low if low > 0 else None,
                "max_zoom": high if high > 0 else None,
            }
        return {}

    def _apply_visibility(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        condition = self._collect_visibility()
        for item in self.items:
            item.set_visibility(condition)
        self._update_visibility_mode(
            condition.get("mode", visibility.VIS_NONE)
        )
        # Refresh the view's "any conditioned item?" gate and re-apply the
        # show/hide. The display is unchanged while editing (edit mode forces
        # everything visible), but this keeps the runtime state correct.
        if self._view is not None:
            self._view._recompute_conditional_flag()
            self._view.refresh_item_visibility()
        self._repaint_view()

    def _capture_zoom(self, which):
        """Set a zoom bound from the active view's current zoom scale."""
        view = self._current_view()
        if view is None:
            return
        zoom = round(abs(view.viewportTransform().m11()), 3)
        spin = (
            self.vis_min_zoom_sb if which == "min" else self.vis_max_zoom_sb
        )
        spin.setValue(zoom)
        self._apply_visibility()

    # -- controls -------------------------------------------------------
    def _add_selected_controls(self):
        if not self.items:
            return
        for item in self.items:
            item.add_selected_controls()
        self._populate_controls()
        self._commit_edit("Add controls")

    def _remove_controls(self):
        item = self._active_item()
        if item is None:
            return
        for row in self.control_list.selectedItems():
            item.remove_control(row.node())
        self._populate_controls()
        self._commit_edit("Remove controls")

    def _search_replace(self):
        if not self.items:
            return
        search, replace, ok = SearchAndReplaceDialog.get()
        if not ok:
            return
        for item in self.items:
            item.search_and_replace_controls(search=search, replace=replace)
        self._populate_controls()
        self._commit_edit("Search & replace controls")

    # -- action ---------------------------------------------------------
    def _apply_action_mode(self, *args, **kwargs):
        if self._syncing or not self.items:
            return
        custom = self._resolve_tristate(self.custom_action_cb)
        for item in self.items:
            item.set_custom_action_mode(custom)
        self._commit_edit("Set action mode")

    def _edit_action_script(self):
        item = self._active_item()
        if item is None:
            return
        cmd, ok = CustomScriptEditDialog.get(
            cmd=item.get_custom_action_script(), item=item
        )
        if not (ok and cmd):
            return
        for target in self.items:
            target.set_custom_action_script(cmd)
        self._commit_edit("Edit action script")

    def _edit_menu(self, list_item):
        item = self._active_item()
        if item is None:
            return
        index = self.menus_list.row(list_item)
        menus = item.get_custom_menus()
        if not (0 <= index < len(menus)):
            return
        name, cmd = menus[index]
        name, cmd, ok = CustomMenuEditDialog.get(name=name, cmd=cmd, item=item)
        if not (ok and name and cmd):
            return
        menus[index] = [name, cmd]
        item.set_custom_menus(menus)
        self._populate_action()
        self._commit_edit("Edit custom menu")

    def _new_menu(self):
        item = self._active_item()
        if item is None:
            return
        name, cmd, ok = CustomMenuEditDialog.get(item=item)
        if not (ok and name and cmd):
            return
        menus = item.get_custom_menus()
        menus.append([name, cmd])
        item.set_custom_menus(menus)
        self._populate_action()
        self._commit_edit("Add custom menu")

    def _remove_menu(self):
        item = self._active_item()
        if item is None:
            return
        index = self.menus_list.currentRow()
        menus = item.get_custom_menus()
        if not (0 <= index < len(menus)):
            return
        menus.pop(index)
        item.set_custom_menus(menus)
        self._populate_action()
        self._commit_edit("Remove custom menu")

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.handles_window:
            try:
                self.handles_window.close()
            except Exception:
                pass
        super().closeEvent(event)
