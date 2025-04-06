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

import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(284, 207)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.mirrorBehaviour_groupBox = QtWidgets.QGroupBox(Form)
        self.mirrorBehaviour_groupBox.setTitle("")
        self.mirrorBehaviour_groupBox.setObjectName("mirrorBehaviour_groupBox")
        self.mirrorBehaviour_gridLayout = QtWidgets.QGridLayout(self.mirrorBehaviour_groupBox)
        self.mirrorBehaviour_gridLayout.setObjectName("mirrorBehaviour_gridLayout")
        self.mirrorBehaviour_checkBox = QtWidgets.QCheckBox(Form)
        self.mirrorBehaviour_checkBox.setObjectName("mirrorBehaviour_checkBox")
        self.mirrorBehaviour_gridLayout.addWidget(self.mirrorBehaviour_checkBox)
        self.gridLayout.addWidget(self.mirrorBehaviour_groupBox, 0, 0, 1, 1)
        self.upvRefArray_groupBox = QtWidgets.QGroupBox(Form)
        self.upvRefArray_groupBox.setObjectName("upvRefArray_groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.upvRefArray_groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.upvRefArray_horizontalLayout = QtWidgets.QHBoxLayout()
        self.upvRefArray_horizontalLayout.setObjectName("upvRefArray_horizontalLayout")
        self.upvRefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.upvRefArray_verticalLayout_1.setObjectName("upvRefArray_verticalLayout_1")
        self.refArray_listWidget = QtWidgets.QListWidget(self.upvRefArray_groupBox)
        self.refArray_listWidget.setDragDropOverwriteMode(True)
        self.refArray_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.refArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.refArray_listWidget.setAlternatingRowColors(True)
        self.refArray_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.refArray_listWidget.setSelectionRectVisible(False)
        self.refArray_listWidget.setObjectName("refArray_listWidget")
        self.upvRefArray_verticalLayout_1.addWidget(self.refArray_listWidget)
        self.upvRefArray_horizontalLayout.addLayout(self.upvRefArray_verticalLayout_1)
        self.upvRefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.upvRefArray_verticalLayout_2.setObjectName("upvRefArray_verticalLayout_2")
        self.refArrayAdd_pushButton = QtWidgets.QPushButton(self.upvRefArray_groupBox)
        self.refArrayAdd_pushButton.setObjectName("refArrayAdd_pushButton")
        self.upvRefArray_verticalLayout_2.addWidget(self.refArrayAdd_pushButton)
        self.refArrayRemove_pushButton = QtWidgets.QPushButton(self.upvRefArray_groupBox)
        self.refArrayRemove_pushButton.setObjectName("refArrayRemove_pushButton")
        self.upvRefArray_verticalLayout_2.addWidget(self.refArrayRemove_pushButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.upvRefArray_verticalLayout_2.addItem(spacerItem)
        self.upvRefArray_horizontalLayout.addLayout(self.upvRefArray_verticalLayout_2)
        self.gridLayout_2.addLayout(self.upvRefArray_horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.upvRefArray_groupBox, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.mirrorBehaviour_checkBox.setText(gqt.fakeTranslate("Form", "Mirror Behaviour L and R", None, -1))
        self.upvRefArray_groupBox.setTitle(gqt.fakeTranslate("Form", "Reference Array", None, -1))
        self.refArrayAdd_pushButton.setText(gqt.fakeTranslate("Form", "<<", None, -1))
        self.refArrayRemove_pushButton.setText(gqt.fakeTranslate("Form", ">>", None, -1))

