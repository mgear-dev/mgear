"""Settings UI for chain_spring_gravity_01 component."""
from mgear.vendor.Qt import QtWidgets


class Ui_Form(object):
    """UI Form class for chain_spring_gravity_01 settings."""

    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(294, 290)

        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")

        self.mirrorBehaviour_checkBox = QtWidgets.QCheckBox(
            "Mirror Behaviour L and R", self.groupBox
        )
        self.mirrorBehaviour_checkBox.setObjectName("mirrorBehaviour_checkBox")

        # Vertical layout for controls
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.addWidget(self.mirrorBehaviour_checkBox)

        # Spacer at bottom
        spacerItem = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(spacerItem)

        # Group box layout
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 0, 1, 1)

        # Main form layout
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
