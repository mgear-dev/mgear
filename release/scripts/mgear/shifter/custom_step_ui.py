from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_Form(object):

    def setupUi(self, Form):
        Form.resize(312, 655)

        self.gridLayout = QtWidgets.QGridLayout(Form)

        # Main group box
        self.groupBox = QtWidgets.QGroupBox("Custom Steps", Form)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.gridLayout_2.addLayout(self.verticalLayout_3, 0, 0, 1, 1)

        # Pre Custom Step section
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.addLayout(self.verticalLayout)

        self.preCustomStep_checkBox = QtWidgets.QCheckBox("Pre Custom Step", self.groupBox)
        self.verticalLayout.addWidget(self.preCustomStep_checkBox)

        self.preSearch_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.preSearch_lineEdit.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.verticalLayout.addWidget(self.preSearch_lineEdit)

        self.preCustomStep_horizontalLayout = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(self.preCustomStep_horizontalLayout)

        # Pre list widget
        self.preCustomStep_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.preCustomStep_horizontalLayout.addLayout(self.preCustomStep_verticalLayout_1)

        self.preCustomStep_listWidget = QtWidgets.QListWidget(self.groupBox)
        self.preCustomStep_listWidget.setDragDropOverwriteMode(True)
        self.preCustomStep_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.preCustomStep_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.preCustomStep_listWidget.setAlternatingRowColors(True)
        self.preCustomStep_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.preCustomStep_verticalLayout_1.addWidget(self.preCustomStep_listWidget)

        # Pre buttons
        self.preCustomStep_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.preCustomStep_horizontalLayout.addLayout(self.preCustomStep_verticalLayout_2)

        self.preCustomStepAdd_pushButton = QtWidgets.QPushButton("Add", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepAdd_pushButton)

        self.preCustomStepNew_pushButton = QtWidgets.QPushButton("New", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepNew_pushButton)

        self.preCustomStepDuplicate_pushButton = QtWidgets.QPushButton("Duplicate", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepDuplicate_pushButton)

        self.preCustomStepRemove_pushButton = QtWidgets.QPushButton("Remove", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepRemove_pushButton)

        self.preCustomStepRun_pushButton = QtWidgets.QPushButton("Run Sel.", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepRun_pushButton)

        self.preCustomStepEdit_pushButton = QtWidgets.QPushButton("Edit", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepEdit_pushButton)

        self.preCustomStepExport_pushButton = QtWidgets.QPushButton("Export", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepExport_pushButton)

        self.preCustomStepImport_pushButton = QtWidgets.QPushButton("Import", self.groupBox)
        self.preCustomStep_verticalLayout_2.addWidget(self.preCustomStepImport_pushButton)

        self.preCustomStep_verticalLayout_2.addStretch()

        # Separator line
        self.line = QtWidgets.QFrame(self.groupBox)
        self.line.setLineWidth(3)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.verticalLayout_3.addWidget(self.line)

        # Post Custom Step section
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.addLayout(self.verticalLayout_2)

        self.postCustomStep_checkBox = QtWidgets.QCheckBox("Post Custom Step", self.groupBox)
        self.verticalLayout_2.addWidget(self.postCustomStep_checkBox)

        self.postSearch_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.postSearch_lineEdit.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.verticalLayout_2.addWidget(self.postSearch_lineEdit)

        self.preCustomStep_horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.verticalLayout_2.addLayout(self.preCustomStep_horizontalLayout_2)

        # Post list widget
        self.preCustomStep_verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.preCustomStep_horizontalLayout_2.addLayout(self.preCustomStep_verticalLayout_3)

        self.postCustomStep_listWidget = QtWidgets.QListWidget(self.groupBox)
        self.postCustomStep_listWidget.setDragDropOverwriteMode(True)
        self.postCustomStep_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.postCustomStep_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.postCustomStep_listWidget.setAlternatingRowColors(True)
        self.postCustomStep_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.preCustomStep_verticalLayout_3.addWidget(self.postCustomStep_listWidget)

        # Post buttons
        self.preCustomStep_verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.preCustomStep_horizontalLayout_2.addLayout(self.preCustomStep_verticalLayout_4)

        self.postCustomStepAdd_pushButton = QtWidgets.QPushButton("Add", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepAdd_pushButton)

        self.postCustomStepNew_pushButton = QtWidgets.QPushButton("New", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepNew_pushButton)

        self.postCustomStepDuplicate_pushButton = QtWidgets.QPushButton("Duplicate", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepDuplicate_pushButton)

        self.postCustomStepRemove_pushButton = QtWidgets.QPushButton("Remove", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepRemove_pushButton)

        self.postCustomStepRun_pushButton = QtWidgets.QPushButton("Run Sel.", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepRun_pushButton)

        self.postCustomStepEdit_pushButton = QtWidgets.QPushButton("Edit", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepEdit_pushButton)

        self.postCustomStepExport_pushButton = QtWidgets.QPushButton("Export", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepExport_pushButton)

        self.postCustomStepImport_pushButton = QtWidgets.QPushButton("Import", self.groupBox)
        self.preCustomStep_verticalLayout_4.addWidget(self.postCustomStepImport_pushButton)

        self.preCustomStep_verticalLayout_4.addStretch()