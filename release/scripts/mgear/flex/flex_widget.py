"""flex.ui

Contains the Flex user interface

:module: flex.ui
"""

# imports
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets
from mgear.flex import logger
from mgear.flex.colors import RED, GREEN, BLUE, YELLOW

# flex ui name
FLEX_UI_NAME = "flex_qdialog"


class FlexDialog(QtWidgets.QDialog):
    """The Flex UI widgets

    Flex UI contains several options you can tweak to customise your rig update
    """

    def __init__(self, parent=None):
        """Creates all the user interface widgets

        :param parent: the parent widget for the Flex dialog widget
        :type parent: PySide2.QtWidgets
        """
        super(FlexDialog, self).__init__(parent=parent)

        logger.debug("Flex widget initialised")

        # sets window rules
        self.setObjectName(FLEX_UI_NAME)
        self.setWindowTitle("mGear: Flex (rig updater)")
        self.setStyleSheet(self.__style_sheet())
        self.setMinimumWidth(350)
        self.setMinimumHeight(100)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # creates widgets
        self.layout_widgets()
        self.models_groups_widgets()
        self.options_widgets()
        self.run_widgets()

    def __style_sheet(self):
        """Hard coded style sheet

        :return: the hard coded style sheet
        :rtype: str
        """

        style = (
            "QFrame{"
            "border:1px solid gray;"
            "border-radius:2px;"
            "margin: 0px;"
            "padding: 8px;}"
            "QGroupBox{"
            "border:1px solid gray;"
            "border-radius:2px;"
            "margin-top: 2ex;}"
            "QGroupBox::title{"
            "subcontrol-origin: margin;"
            "subcontrol-position: top center;"
            "padding:0px 10px;}"
            "QHeaderView{"
            "border:0px;"
            "padding: 0px;"
            "margin: 0px;}"
            "QTableView{"
            "margin:10px;"
            "padding:0px;}"
        )

        return style

    def deformed_widgets(self):
        """Creates the deformed options widgets"""

        # deformed main group box
        self.deformed_check = QtWidgets.QGroupBox("Deformed")
        self.deformed_check.setCheckable(True)
        self.deformed_check.setChecked(True)

        # creates the layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.deformed_check.setLayout(layout)

        # ignore topology changes
        self.mismatched_topologies = QtWidgets.QCheckBox("Mismatched topologies")
        self.mismatched_topologies.setChecked(True)

        layout.addWidget(self.mismatched_topologies)

    def layout_widgets(self):
        """Creates the general UI layouts"""

        # layout widgets
        main_vertical_layout = QtWidgets.QVBoxLayout()
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_vertical_layout)

        # frame
        model_frame = QtWidgets.QFrame()
        self.widgets_layout = QtWidgets.QVBoxLayout()
        self.widgets_layout.setContentsMargins(0, 0, 0, 0)
        self.widgets_layout.setSpacing(10)
        model_frame.setLayout(self.widgets_layout)

        # adds widgets layout
        main_vertical_layout.addWidget(model_frame)

    def models_groups_widgets(self):
        """Creates the source and target widgets area"""

        # create layout
        grid_layout = QtWidgets.QGridLayout()

        # creates group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("MODEL GROUPS")
        group_box.setLayout(grid_layout)
        group_box.setFixedHeight(80)
        group_box.setMinimumHeight(0)

        # source widgets
        self.source_text = QtWidgets.QLineEdit()
        self.source_text.setObjectName("source_qlineedit")
        self.source_text.setPlaceholderText(
            "New Geometry group to replace Original Geo"
        )
        self.source_text.setStatusTip(
            "Type the name of your source group here. Source geometries should have same naming as Target"
        )
        self.add_source_button = QtWidgets.QPushButton("<--  source (New Geo)")
        self.add_source_button.setObjectName("source_qpushbutton")
        self.add_source_button.setPalette(YELLOW)
        self.add_source_button.setStatusTip("Add selected source group")

        # target widgets
        self.target_text = QtWidgets.QLineEdit()
        self.target_text.setObjectName("target_qlineedit")
        self.target_text.setPlaceholderText("Original Geometry with History")
        self.target_text.setStatusTip(
            "Type the name of your target group here. Target geometries should have same naming as Source"
        )
        self.add_target_button = QtWidgets.QPushButton("<--  target (Original Geo)")
        self.add_target_button.setObjectName("target_qpushbutton")
        self.add_target_button.setPalette(BLUE)
        self.add_target_button.setStatusTip("Add selected target group")

        # adds widgets to layout
        grid_layout.addWidget(self.source_text, 0, 0, 1, 2)
        grid_layout.addWidget(self.add_source_button, 0, 2, 1, 1)
        grid_layout.addWidget(self.target_text, 1, 0, 1, 2)
        grid_layout.addWidget(self.add_target_button, 1, 2, 1, 1)

        # adds the group box widget to the widgets_layout
        self.widgets_layout.addWidget(group_box)

    def options_widgets(self):
        """Create the options widget area"""
        # create layout
        grid_layout = QtWidgets.QGridLayout()

        # creates group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("OPTIONS")
        group_box.setLayout(grid_layout)
        group_box.setMinimumHeight(0)

        # user defined attributes
        self.user_attributes_check = QtWidgets.QCheckBox("User Attributes")
        self.user_attributes_check.setChecked(True)

        # plug-in attributes
        self.plugin_attributes_check = QtWidgets.QCheckBox("Plug-in " "Attributes")
        self.plugin_attributes_check.setChecked(False)

        # render attributes
        self.render_attributes_check = QtWidgets.QCheckBox("Render Attributes")
        self.render_attributes_check.setChecked(True)

        # =====================================================================
        # # vertex colours
        # self.vertex_colours_check = QtWidgets.QCheckBox("Vertex Colours")
        # self.vertex_colours_check.setChecked(True)
        # self.vertex_colours_check.setEnabled(False)
        # =====================================================================

        # Transformed & Deformed layout
        t_n_d_widget = QtWidgets.QWidget()
        t_n_d_layout = QtWidgets.QHBoxLayout()
        t_n_d_layout.setContentsMargins(0, 0, 0, 0)
        t_n_d_widget.setContentsMargins(0, 0, 0, 0)
        t_n_d_widget.setLayout(t_n_d_layout)

        # creates transformed and deformed widgets
        self.transformed_widgets()
        self.deformed_widgets()

        # add to layout
        t_n_d_layout.addWidget(self.transformed_check)
        t_n_d_layout.addWidget(self.deformed_check)

        # object display
        self.display_attributes_check = QtWidgets.QCheckBox("Object Display Attrs.")
        self.display_attributes_check.setChecked(False)

        # component display
        self.component_attributes_check = QtWidgets.QCheckBox(
            "Component Display Attrs."
        )
        self.component_attributes_check.setChecked(False)

        # adds widgets to layout
        grid_layout.addWidget(self.user_attributes_check, 0, 0, 1, 1)
        grid_layout.addWidget(self.plugin_attributes_check, 0, 1, 1, 1)
        grid_layout.addWidget(self.render_attributes_check, 0, 2, 1, 1)
        #         grid_layout.addWidget(self.vertex_colours_check, 1, 2, 1, 1)
        grid_layout.addWidget(self.display_attributes_check, 1, 0, 1, 1)
        grid_layout.addWidget(self.component_attributes_check, 1, 1, 1, 1)
        grid_layout.addWidget(t_n_d_widget, 2, 0, 1, 3)

        # adds the group box widget to the widgets_layout
        self.widgets_layout.addWidget(group_box)

    def run_widgets(self):
        """Creates the run widgets area"""

        # create layout
        vertical_layout = QtWidgets.QVBoxLayout()

        # creates group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("RUN")
        group_box.setLayout(vertical_layout)
        group_box.setFixedHeight(80)

        # analyse widget
        self.analyse_button = QtWidgets.QPushButton("Analyze")
        self.analyse_button.setPalette(GREEN)
        self.analyse_button.setStatusTip("Hit to analyze the source and target shapes")

        # run widget
        self.run_button = QtWidgets.QPushButton("--> Update shapes <--")
        self.run_button.setPalette(RED)
        self.run_button.setStatusTip("Hit to execute updating your rig shapes")

        # adds widget to layout
        vertical_layout.addWidget(self.analyse_button)
        vertical_layout.addWidget(self.run_button)

        # adds the group box widget to the widgets_layout
        self.widgets_layout.addWidget(group_box)

    def transformed_widgets(self):
        """Creates the transformed options widgets"""

        # transformed main group box
        self.transformed_check = QtWidgets.QGroupBox("Transformed")
        self.transformed_check.setCheckable(True)
        self.transformed_check.setChecked(True)

        # creates the layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.transformed_check.setLayout(layout)

        # hold position values
        self.transformed_hold_check = QtWidgets.QRadioButton("Hold position values")
        self.transformed_hold_check.setChecked(True)
        # new position values
        self.transformed_new_check = QtWidgets.QRadioButton("New position values")

        # add widgets to transformed group box
        layout.addWidget(self.transformed_hold_check)
        layout.addWidget(self.transformed_new_check)
        layout.addWidget(self.transformed_new_check)
