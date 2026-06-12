# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Jeremie Passerin
# Author:     Miquel Campos           www.mcsgear.com
# Date:       2016 / 10 / 10

"""Settings UI for chain_01 component."""
from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_Form(object):
    """Base UI Form class designed for inheritance.

    Subclasses can override:
        - setup_ui_options(): Define form size and options
        - create_controls(): Create the main controls
        - create_layout(): Arrange controls in layouts
        - create_connections(): Set up signal/slot connections

    The setupUi() method calls these in order, so subclasses can
    override specific parts while reusing others via super().
    """

    def setupUi(self, Form):
        """Main setup method that orchestrates UI creation.

        Args:
            Form: The QDialog/QWidget to set up
        """
        self.form = Form
        self.setup_ui_options(Form)
        self.create_controls(Form)
        self.create_layout(Form)
        self.create_connections()

    # ------------------------------------------------------------------
    # Override these methods in subclasses
    # ------------------------------------------------------------------

    def setup_ui_options(self, Form):
        """Configure form-level options like size and object name.

        Override in subclass to change form size or add form-level settings.
        """
        Form.setObjectName("Form")
        Form.resize(255, 290)

    def create_controls(self, Form):
        """Create all UI controls/widgets.

        Override in subclass to add new controls. Call super() first
        to create parent controls.
        """
        # Main container
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")

        # Mode combobox
        self.mode_label = QtWidgets.QLabel("Mode:", self.groupBox)
        self.mode_label.setObjectName("mode_label")

        self.mode_comboBox = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.mode_comboBox.sizePolicy().hasHeightForWidth()
        )
        self.mode_comboBox.setSizePolicy(sizePolicy)
        self.mode_comboBox.setObjectName("mode_comboBox")
        self.mode_comboBox.addItem("FK")
        self.mode_comboBox.addItem("IK")
        self.mode_comboBox.addItem("FK/IK")

        # IK/FK Blend slider and spinbox
        self.ikfk_label = QtWidgets.QLabel("IK/FK Blend:", self.groupBox)
        self.ikfk_label.setObjectName("ikfk_label")

        self.ikfk_slider = QtWidgets.QSlider(self.groupBox)
        self.ikfk_slider.setMinimumSize(QtCore.QSize(0, 15))
        self.ikfk_slider.setMaximum(100)
        self.ikfk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.ikfk_slider.setObjectName("ikfk_slider")

        self.ikfk_spinBox = QtWidgets.QSpinBox(self.groupBox)
        self.ikfk_spinBox.setMaximum(100)
        self.ikfk_spinBox.setObjectName("ikfk_spinBox")

        # Neutral pose checkbox
        self.neutralPose_checkBox = QtWidgets.QCheckBox(
            "Neutral pose", self.groupBox
        )
        self.neutralPose_checkBox.setObjectName("neutralPose_checkBox")

        # IK Reference Array group
        self.ikRefArray_groupBox = QtWidgets.QGroupBox("IK Reference Array", Form)
        self.ikRefArray_groupBox.setObjectName("ikRefArray_groupBox")

        self.ikRefArray_listWidget = QtWidgets.QListWidget(self.ikRefArray_groupBox)
        self.ikRefArray_listWidget.setDragDropOverwriteMode(True)
        self.ikRefArray_listWidget.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.ikRefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.ikRefArray_listWidget.setAlternatingRowColors(True)
        self.ikRefArray_listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.ikRefArray_listWidget.setSelectionRectVisible(False)
        self.ikRefArray_listWidget.setObjectName("ikRefArray_listWidget")

        self.ikRefArrayAdd_pushButton = QtWidgets.QPushButton(
            "<<", self.ikRefArray_groupBox
        )
        self.ikRefArrayAdd_pushButton.setObjectName("ikRefArrayAdd_pushButton")

        self.ikRefArrayRemove_pushButton = QtWidgets.QPushButton(
            ">>", self.ikRefArray_groupBox
        )
        self.ikRefArrayRemove_pushButton.setObjectName("ikRefArrayRemove_pushButton")

    def create_layout(self, Form):
        """Arrange controls in layouts.

        Override in subclass to modify layout. For adding controls to
        an existing layout, override create_controls() instead and
        use self.verticalLayout.addWidget() after calling super().
        """
        # Main form layout
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")

        # Group box layout
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")

        # Vertical layout for main controls
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        # Form layout for mode and IK/FK blend
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")

        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.LabelRole, self.mode_label
        )
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.FieldRole, self.mode_comboBox
        )
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.LabelRole, self.ikfk_label
        )

        # Horizontal layout for slider and spinbox
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.horizontalLayout_3.addWidget(self.ikfk_slider)
        self.horizontalLayout_3.addWidget(self.ikfk_spinBox)
        self.formLayout.setLayout(
            1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3
        )

        self.verticalLayout.addLayout(self.formLayout)
        self.verticalLayout.addWidget(self.neutralPose_checkBox)

        self.gridLayout_2.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        # IK Reference Array layout
        self.gridLayout_3 = QtWidgets.QGridLayout(self.ikRefArray_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")

        self.ikRefArray_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ikRefArray_horizontalLayout.setObjectName("ikRefArray_horizontalLayout")

        self.ikRefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.ikRefArray_verticalLayout_1.setObjectName("ikRefArray_verticalLayout_1")
        self.ikRefArray_verticalLayout_1.addWidget(self.ikRefArray_listWidget)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_1)

        self.ikRefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.ikRefArray_verticalLayout_2.setObjectName("ikRefArray_verticalLayout_2")
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayAdd_pushButton)
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayRemove_pushButton)

        spacerItem = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.ikRefArray_verticalLayout_2.addItem(spacerItem)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_2)

        self.gridLayout_3.addLayout(self.ikRefArray_horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.ikRefArray_groupBox, 1, 0, 1, 1)

    def create_connections(self):
        """Set up signal/slot connections.

        Override in subclass to add additional connections.
        """
        self.ikfk_slider.valueChanged.connect(self.ikfk_spinBox.setValue)
        self.ikfk_spinBox.valueChanged.connect(self.ikfk_slider.setValue)