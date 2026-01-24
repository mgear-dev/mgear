"""Settings UI for lite_chain_01 component.
"""
from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_Form(object):
    """Base UI Form class designed for inheritance.

    Subclasses can override:
        - setup_ui_options(): Define form size and options
        - create_controls(): Create the main controls
        - create_layout(): Arrange controls in layouts

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

    # ------------------------------------------------------------------
    # Now we can override these methods in subclasses
    # ------------------------------------------------------------------

    def setup_ui_options(self, Form):
        """Configure form-level options like size and object name.

        Override in subclass to change form size or add form-level settings.
        """
        Form.setObjectName("Form")
        Form.resize(294, 290)

    def create_controls(self, Form):
        """Create all UI controls/widgets.

        Override in subclass to add new controls. Call super() first
        to create parent controls.
        """
        # Main container
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")

        # Controls
        self.neutralPose_checkBox = QtWidgets.QCheckBox("Neutral pose", self.groupBox)
        self.neutralPose_checkBox.setObjectName("neutralPose_checkBox")

        self.overrideNegate_checkBox = QtWidgets.QCheckBox(
            "Override Negate Axis Direction For \"R\" Side", self.groupBox
        )
        self.overrideNegate_checkBox.setObjectName("overrideNegate_checkBox")

        self.mirrorBehaviour_checkBox = QtWidgets.QCheckBox(
            "Mirror Behaviour L and R", self.groupBox
        )
        self.mirrorBehaviour_checkBox.setObjectName("mirrorBehaviour_checkBox")

        self.addJoints_checkBox = QtWidgets.QCheckBox("Add Joints", self.groupBox)
        self.addJoints_checkBox.setChecked(True)
        self.addJoints_checkBox.setObjectName("addJoints_checkBox")

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

        # Vertical layout for controls
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        # Add controls to vertical layout
        self.verticalLayout.addWidget(self.neutralPose_checkBox)
        self.verticalLayout.addWidget(self.overrideNegate_checkBox)
        self.verticalLayout.addWidget(self.mirrorBehaviour_checkBox)
        self.verticalLayout.addWidget(self.addJoints_checkBox)

        # Spacer at bottom
        self.spacerItem = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(self.spacerItem)

        # Assemble layouts
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
