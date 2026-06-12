"""Rigbits eye rigger tool"""

import json
from functools import partial

from maya import cmds
import mgear.core.pyqt as gqt
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.vendor.Qt import QtCore, QtWidgets

from . import lib
from . import eye_rigger


##########################################################
# Eye Rig UI
##########################################################


class ui(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ui, self).__init__(parent)

        # File type filter for settings.
        self.filter = "Eyes Rigger Configuration .eyes (*.eyes)"

        self.create()

    def create(self):

        self.setWindowTitle("Eye Rigger 2.1")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):

        # Geometry input controls
        self.geometryInput_group = QtWidgets.QGroupBox("Geometry Input")
        self.eyeball_label = QtWidgets.QLabel("Eyeball:")
        self.eyeMesh = QtWidgets.QLineEdit()
        self.eyeball_button = QtWidgets.QPushButton("<< Set")
        self.edgeloop_label = QtWidgets.QLabel("Edge Loop:")
        self.edgeLoop = QtWidgets.QLineEdit()
        self.edgeloop_button = QtWidgets.QPushButton("<< Set")
        self.sel_edgeloop_button = QtWidgets.QPushButton("select")
        # Manual corners
        self.manualCorners_group = QtWidgets.QGroupBox("Custom Eye Corners")
        self.customCorner = QtWidgets.QCheckBox("Set Manual Vertex Corners")
        self.customCorner.setChecked(False)
        self.intCorner_label = QtWidgets.QLabel("Internal Corner")
        self.intCorner = QtWidgets.QLineEdit()
        self.intCorner_button = QtWidgets.QPushButton("<< Set")
        self.sel_intCorner_button = QtWidgets.QPushButton("Select")
        self.extCorner_label = QtWidgets.QLabel("External Corner")
        self.extCorner = QtWidgets.QLineEdit()
        self.extCorner_button = QtWidgets.QPushButton("<< Set")
        self.sel_extCorner_button = QtWidgets.QPushButton("Select")

        # # Blink heigh slider
        # self.blinkHeight_group = QtWidgets.QGroupBox("Blink Height")
        # self.blinkH = QtWidgets.QSpinBox()
        # self.blinkH.setRange(0, 100)
        # self.blinkH.setSingleStep(10)
        # self.blinkH.setValue(20)
        # self.blinkHeight_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        # self.blinkHeight_slider.setRange(0, 100)
        # self.blinkHeight_slider.setSingleStep(
        #     self.blinkHeight_slider.maximum() / 10.0
        # )
        # self.blinkHeight_slider.setValue(20)

        # vTrack and hTrack
        self.tracking_group = QtWidgets.QGroupBox("Tracking")
        self.upperVTrack = QtWidgets.QDoubleSpinBox()
        self.upperVTrack.setValue(0.02)
        self.upperHTrack = QtWidgets.QDoubleSpinBox()
        self.upperHTrack.setValue(0.01)
        self.lowerVTrack = QtWidgets.QDoubleSpinBox()
        self.lowerVTrack.setValue(0.02)
        self.lowerHTrack = QtWidgets.QDoubleSpinBox()
        self.lowerHTrack.setValue(0.01)

        # Name prefix
        self.prefix_group = QtWidgets.QGroupBox("Name Prefix")
        self.namePrefix = QtWidgets.QLineEdit()
        self.namePrefix.setText("eye")
        self.control_group = QtWidgets.QGroupBox("Control Name Extension")
        self.ctlName = QtWidgets.QLineEdit()
        self.ctlName.setText("ctl")

        # joints
        self.joints_group = QtWidgets.QGroupBox("Joints")
        self.headJnt_label = QtWidgets.QLabel("Head or Eye area Joint:")
        self.headJnt = QtWidgets.QLineEdit()
        self.headJnt_button = QtWidgets.QPushButton("<< Set")
        self.everyNVertex_label = QtWidgets.QLabel(
            "Create Joint evey N number of Vertex:"
        )
        self.everyNVertex = QtWidgets.QSpinBox()
        self.everyNVertex.setRange(0, 100)
        self.everyNVertex.setSingleStep(1)
        self.everyNVertex.setValue(1)

        self.fixedJoints = QtWidgets.QCheckBox("Set Fixed Number of Joints")
        self.fixedJoints.setChecked(False)

        # self.fixedJointsNumber_label = QtWidgets.QLabel(
        #     "Number of Joints:"
        # )
        self.fixedJointsNumber = QtWidgets.QSpinBox()
        self.fixedJointsNumber.setRange(1, 100)
        self.fixedJointsNumber.setSingleStep(1)
        self.fixedJointsNumber.setValue(3)

        self.orderFromCenter = QtWidgets.QCheckBox(
            "Right side Joints order starts from center"
        )
        self.orderFromCenter.setChecked(False)

        # Topological Autoskin
        self.topoSkin_group = QtWidgets.QGroupBox("Skin")
        self.rigidLoops_label = QtWidgets.QLabel("Rigid Loops:")
        self.rigidLoops = QtWidgets.QSpinBox()
        self.rigidLoops.setRange(0, 30)
        self.rigidLoops.setSingleStep(1)
        self.rigidLoops.setValue(2)
        self.falloffLoops_label = QtWidgets.QLabel("Falloff Loops:")
        self.falloffLoops = QtWidgets.QSpinBox()
        self.falloffLoops.setRange(0, 30)
        self.falloffLoops.setSingleStep(1)
        self.falloffLoops.setValue(4)

        self.doSkin = QtWidgets.QCheckBox("Compute Topological Autoskin")
        self.doSkin.setChecked(True)

        # Options
        self.options_group = QtWidgets.QGroupBox("Options")
        self.parent_label = QtWidgets.QLabel("Rig Parent:")
        self.parent_node = QtWidgets.QLineEdit()
        self.parent_button = QtWidgets.QPushButton("<< Set")
        self.aim_controller_label = QtWidgets.QLabel("Aim Controller:")
        self.aim_controller = QtWidgets.QLineEdit()
        self.aim_controller_button = QtWidgets.QPushButton("<< Set")
        self.ctlShapeOffset_label = QtWidgets.QLabel("Controls Offset:")
        self.offset = QtWidgets.QDoubleSpinBox()
        self.offset.setRange(0, 10)
        self.offset.setSingleStep(0.05)
        self.offset.setValue(0.05)
        self.ctl_size_label = QtWidgets.QLabel("Controls Size:")
        self.ctl_size = QtWidgets.QDoubleSpinBox()
        self.ctl_size.setRange(0.1, 10)
        self.ctl_size.setSingleStep(0.05)
        self.ctl_size.setValue(1.0)
        self.sideRange = QtWidgets.QCheckBox(
            "Use Z axis for wide calculation (i.e: Horse and fish side eyes)"
        )
        self.sideRange.setChecked(False)

        self.simplified = QtWidgets.QCheckBox(
            "Simplified controls. If Checked reduce the eyelid controls number"
        )
        self.simplified.setChecked(False)

        self.ctlSet_label = QtWidgets.QLabel("Controls Set:")
        self.ctlSet = QtWidgets.QLineEdit()
        self.ctlSet_button = QtWidgets.QPushButton("<< Set")

        self.deformersSet_label = QtWidgets.QLabel("Deformers Set:")
        self.defSet = QtWidgets.QLineEdit()
        self.deformersSet_button = QtWidgets.QPushButton("<< Set")

        self.deformers_group_label = QtWidgets.QLabel("Static Rig Parent:")
        self.deformers_group = QtWidgets.QLineEdit()
        self.deformers_group_button = QtWidgets.QPushButton("<< Set")

        # Main buttons
        self.build_button = QtWidgets.QPushButton("Build Eye Rig")
        self.import_button = QtWidgets.QPushButton("Import Config from json")
        self.export_button = QtWidgets.QPushButton("Export Config to json")

    def create_layout(self):

        # Eyeball Layout
        eyeball_layout = QtWidgets.QHBoxLayout()
        eyeball_layout.setContentsMargins(1, 1, 1, 1)
        eyeball_layout.addWidget(self.eyeball_label)
        eyeball_layout.addWidget(self.eyeMesh)
        eyeball_layout.addWidget(self.eyeball_button)

        # Edge Loop Layout
        edgeloop_layout = QtWidgets.QHBoxLayout()
        edgeloop_layout.setContentsMargins(1, 1, 1, 1)
        edgeloop_layout.addWidget(self.edgeloop_label)
        edgeloop_layout.addWidget(self.edgeLoop)
        edgeloop_layout.addWidget(self.edgeloop_button)
        edgeloop_layout.addWidget(self.sel_edgeloop_button)

        # Geometry Input Layout
        geometryInput_layout = QtWidgets.QVBoxLayout()
        geometryInput_layout.setContentsMargins(6, 1, 6, 2)
        geometryInput_layout.addLayout(eyeball_layout)
        geometryInput_layout.addLayout(edgeloop_layout)
        self.geometryInput_group.setLayout(geometryInput_layout)

        # # Blink Height Layout
        # blinkHeight_layout = QtWidgets.QHBoxLayout()
        # blinkHeight_layout.setContentsMargins(1, 1, 1, 1)
        # blinkHeight_layout.addWidget(self.blinkH)
        # blinkHeight_layout.addWidget(self.blinkHeight_slider)
        # self.blinkHeight_group.setLayout(blinkHeight_layout)

        # Tracking Layout
        tracking_layout = QtWidgets.QVBoxLayout()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Upper Vertical"))
        layout.addWidget(self.upperVTrack)
        layout.addWidget(QtWidgets.QLabel("Upper Horizontal"))
        layout.addWidget(self.upperHTrack)
        tracking_layout.addLayout(layout)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Lower Vertical"))
        layout.addWidget(self.lowerVTrack)
        layout.addWidget(QtWidgets.QLabel("Lower Horizontal"))
        layout.addWidget(self.lowerHTrack)
        tracking_layout.addLayout(layout)
        self.tracking_group.setLayout(tracking_layout)

        # joints Layout
        headJnt_layout = QtWidgets.QHBoxLayout()
        headJnt_layout.addWidget(self.headJnt_label)
        headJnt_layout.addWidget(self.headJnt)
        headJnt_layout.addWidget(self.headJnt_button)

        everyNVertex_layout = QtWidgets.QHBoxLayout()
        everyNVertex_layout.addWidget(self.everyNVertex_label)
        everyNVertex_layout.addWidget(self.everyNVertex)

        fixedJoints_layout = QtWidgets.QHBoxLayout()
        fixedJoints_layout.addWidget(self.fixedJoints)
        fixedJoints_layout.addWidget(self.fixedJointsNumber)

        joints_layout = QtWidgets.QVBoxLayout()
        joints_layout.setContentsMargins(6, 4, 6, 4)
        joints_layout.addLayout(headJnt_layout)
        joints_layout.addLayout(everyNVertex_layout)
        joints_layout.addLayout(fixedJoints_layout)
        joints_layout.addWidget(self.orderFromCenter)
        self.joints_group.setLayout(joints_layout)

        # topological autoskin Layout
        skinLoops_layout = QtWidgets.QGridLayout()
        skinLoops_layout.addWidget(self.rigidLoops_label, 0, 0)
        skinLoops_layout.addWidget(self.falloffLoops_label, 0, 1)
        skinLoops_layout.addWidget(self.rigidLoops, 1, 0)
        skinLoops_layout.addWidget(self.falloffLoops, 1, 1)

        topoSkin_layout = QtWidgets.QVBoxLayout()
        topoSkin_layout.setContentsMargins(6, 4, 6, 4)
        topoSkin_layout.addWidget(self.doSkin, alignment=QtCore.Qt.Alignment())
        topoSkin_layout.addLayout(skinLoops_layout)
        self.topoSkin_group.setLayout(topoSkin_layout)

        # Manual Corners Layout
        intCorner_layout = QtWidgets.QHBoxLayout()
        intCorner_layout.addWidget(self.intCorner_label)
        intCorner_layout.addWidget(self.intCorner)
        intCorner_layout.addWidget(self.intCorner_button)
        intCorner_layout.addWidget(self.sel_intCorner_button)

        extCorner_layout = QtWidgets.QHBoxLayout()
        extCorner_layout.addWidget(self.extCorner_label)
        extCorner_layout.addWidget(self.extCorner)
        extCorner_layout.addWidget(self.extCorner_button)
        extCorner_layout.addWidget(self.sel_extCorner_button)

        manualCorners_layout = QtWidgets.QVBoxLayout()
        manualCorners_layout.setContentsMargins(6, 4, 6, 4)
        manualCorners_layout.addWidget(
            self.customCorner, alignment=QtCore.Qt.Alignment()
        )
        manualCorners_layout.addLayout(intCorner_layout)
        manualCorners_layout.addLayout(extCorner_layout)
        self.manualCorners_group.setLayout(manualCorners_layout)

        # Options Layout
        parent_layout = QtWidgets.QHBoxLayout()
        parent_layout.addWidget(self.parent_label)
        parent_layout.addWidget(self.parent_node)
        parent_layout.addWidget(self.parent_button)
        parent_layout.addWidget(self.aim_controller_label)
        parent_layout.addWidget(self.aim_controller)
        parent_layout.addWidget(self.aim_controller_button)
        offset_layout = QtWidgets.QHBoxLayout()
        offset_layout.addWidget(self.ctlShapeOffset_label)
        offset_layout.addWidget(self.offset)
        ctl_size_layout = QtWidgets.QHBoxLayout()
        ctl_size_layout.addWidget(self.ctl_size_label)
        ctl_size_layout.addWidget(self.ctl_size)
        ctlSet_layout = QtWidgets.QHBoxLayout()
        ctlSet_layout.addWidget(self.ctlSet_label)
        ctlSet_layout.addWidget(self.ctlSet)
        ctlSet_layout.addWidget(self.ctlSet_button)
        deformersGrp_layout = QtWidgets.QHBoxLayout()
        deformersGrp_layout.addWidget(self.deformersSet_label)
        deformersGrp_layout.addWidget(self.defSet)
        deformersGrp_layout.addWidget(self.deformersSet_button)
        deformersGrp_layout.addWidget(self.deformers_group_label)
        deformersGrp_layout.addWidget(self.deformers_group)
        deformersGrp_layout.addWidget(self.deformers_group_button)

        options_layout = QtWidgets.QVBoxLayout()
        options_layout.setContentsMargins(6, 1, 6, 2)
        options_layout.addLayout(parent_layout)
        options_layout.addLayout(offset_layout)
        options_layout.addLayout(ctl_size_layout)
        # options_layout.addWidget(self.blinkHeight_group)
        options_layout.addWidget(self.tracking_group)
        options_layout.addWidget(self.sideRange)
        options_layout.addWidget(self.simplified)
        options_layout.addLayout(ctlSet_layout)
        options_layout.addLayout(deformersGrp_layout)
        self.options_group.setLayout(options_layout)

        # Name prefix
        namePrefix_layout = QtWidgets.QVBoxLayout()
        namePrefix_layout.setContentsMargins(1, 1, 1, 1)
        namePrefix_layout.addWidget(self.namePrefix)
        self.prefix_group.setLayout(namePrefix_layout)

        # Name prefix
        controlExtension_layout = QtWidgets.QVBoxLayout()
        controlExtension_layout.setContentsMargins(1, 1, 1, 1)
        controlExtension_layout.addWidget(self.ctlName)
        self.control_group.setLayout(controlExtension_layout)

        # Main Layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(self.prefix_group)
        main_layout.addWidget(self.control_group)
        main_layout.addWidget(self.geometryInput_group)
        main_layout.addWidget(self.manualCorners_group)
        main_layout.addWidget(self.options_group)
        main_layout.addWidget(self.joints_group)
        main_layout.addWidget(self.topoSkin_group)
        main_layout.addWidget(self.build_button)
        main_layout.addWidget(self.import_button)
        main_layout.addWidget(self.export_button)

        self.setLayout(main_layout)

    def create_connections(self):
        # self.blinkH.valueChanged[int].connect(self.blinkHeight_slider.setValue)
        # self.blinkHeight_slider.valueChanged[int].connect(self.blinkH.setValue)

        self.eyeball_button.clicked.connect(
            partial(self.populate_object, self.eyeMesh)
        )
        self.parent_button.clicked.connect(
            partial(self.populate_object, self.parent_node)
        )
        self.aim_controller_button.clicked.connect(
            partial(self.populate_object, self.aim_controller)
        )
        self.headJnt_button.clicked.connect(
            partial(self.populate_object, self.headJnt, 1)
        )

        self.edgeloop_button.clicked.connect(self.populate_edgeloop)
        self.sel_edgeloop_button.clicked.connect(
            partial(self.select_components_from_lineEdit, self.edgeLoop)
        )

        self.build_button.clicked.connect(self.build_rig)
        self.import_button.clicked.connect(self.import_settings)
        self.export_button.clicked.connect(self.export_settings)

        self.intCorner_button.clicked.connect(
            partial(self.populate_element, self.intCorner, "vertex")
        )
        self.sel_intCorner_button.clicked.connect(
            partial(self.select_components_from_lineEdit, self.intCorner)
        )
        self.extCorner_button.clicked.connect(
            partial(self.populate_element, self.extCorner, "vertex")
        )
        self.sel_extCorner_button.clicked.connect(
            partial(self.select_components_from_lineEdit, self.extCorner)
        )

        self.ctlSet_button.clicked.connect(
            partial(self.populate_element, self.ctlSet, "objectSet")
        )
        self.deformersSet_button.clicked.connect(
            partial(self.populate_element, self.defSet, "objectSet")
        )
        self.deformers_group_button.clicked.connect(
            partial(self.populate_element, self.deformers_group)
        )

    # SLOTS ##########################################################
    def populate_element(self, lEdit, oType="transform"):
        if oType == "joint":
            oTypeInst = pm.nodetypes.Joint
        elif oType == "vertex":
            oTypeInst = pm.MeshVertex
        elif oType == "objectSet":
            oTypeInst = pm.nodetypes.ObjectSet
        else:
            oTypeInst = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oTypeInst):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning(
                    "The selected element is not a valid %s" % oType
                )
        else:
            pm.displayWarning("Please select first one %s." % oType)

    def populate_object(self, lEdit, oType=None):
        if oType == 1:
            oType = pm.nodetypes.Joint
        else:
            oType = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oType):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning("The selected element is not a valid object")
        else:
            pm.displayWarning("Please select first the  object.")

    def populate_edgeloop(self):
        self.edgeLoop.setText(lib.get_edge_loop_from_selection())

    def build_rig(self):
        eye_rigger.rig(**lib.get_settings_from_widget(self))

    def export_settings(self):
        data_string = json.dumps(
            lib.get_settings_from_widget(self), indent=4, sort_keys=True
        )

        file_path = lib.get_file_path(self.filter, "save")
        if not file_path:
            return

        with open(file_path, "w") as f:
            f.write(data_string)

    def import_settings(self):
        file_path = lib.get_file_path(self.filter, "open")
        if not file_path:
            return

        lib.import_settings_from_file(file_path, self)

    def select_components_from_lineEdit(self, lEdit):
        """Select components (edges, vertices, etc.) from a lineEdit.

        """
        comp_str = lEdit.text()
        if not comp_str:
            print("No component string provided. Maybe lineEdit is empty.")
            return

        # Split and clean
        comp_list = [x.strip() for x in comp_str.split(",") if x.strip()]

        if not comp_list:
            print("No valid components found.")
            return

        # Select components
        try:
            cmds.select(comp_list, r=True)
            print("Selected {} components.".format(len(comp_list)))
        except Exception as e:
            print("Error selecting components: {}".format(e))



# Build from json file.
# def rig_from_file(path):
#     rig(**json.load(open(path)))


def show(*args):
    gqt.showDialog(ui)


if __name__ == "__main__":
    show()
