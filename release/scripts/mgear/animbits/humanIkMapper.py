import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.cmds as cmds

# from shiboken2 import wrapInstance
from maya import mel

import mgear
from mgear.core import callbackManager
from mgear.core import widgets as mwgt
from mgear.core.utils import one_undo, viewport_off
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from mgear.core import pyqt

from mgear.rigbits.mirror_controls import MirrorController

import json
from functools import partial
import ast

########################################
#   Load Plugins
########################################
if not pm.pluginInfo("fbxmaya", query=True, loaded=True):
    pm.loadPlugin("fbxmaya")
if not pm.pluginInfo("mayaHIK", query=True, loaded=True):
    pm.loadPlugin("mayaHIK")


class HumanIKMapper:
    # Hard coded values for bone names in Human Ik

    HEAD_NAMES = [
        "Head",
        "Neck",
        "Neck1",
        "Neck2",
        "Neck3",
        "Neck4",
        "Neck5",
        "Neck6",
        "Neck7",
        "Neck8",
        "Neck9",
    ]
    SPINE_NAMES = [
        "Hips",
        "Spine",
        "Spine1",
        "Spine2",
        "Spine3",
        "Spine4",
        "Spine5",
        "Spine6",
        "Spine7",
        "Spine8",
        "Spine9",
    ]

    LEFT_ARM_NAMES = ["LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"]

    LEFT_UPPER_ARM_ROLLS = [
        "LeafLeftArmRoll1",
        "LeafLeftArmRoll2",
        "LeafLeftArmRoll3",
        "LeafLeftArmRoll4",
        "LeafLeftArmRoll5",
    ]

    LEFT_LOWER_ARM_ROLLS = [
        "LeafLeftForeArmRoll1",
        "LeafLeftForeArmRoll2",
        "LeafLeftForeArmRoll3",
        "LeafLeftForeArmRoll4",
        "LeafLeftForeArmRoll5",
    ]

    LEFT_HAND = [
        "LeftHandThumb1",
        "LeftHandThumb2",
        "LeftHandThumb3",
        "LeftHandIndex1",
        "LeftHandIndex2",
        "LeftHandIndex3",
        "LeftHandMiddle1",
        "LeftHandMiddle2",
        "LeftHandMiddle3",
        "LeftHandRing1",
        "LeftHandRing2",
        "LeftHandRing3",
        "LeftHandPinky1",
        "LeftHandPinky2",
        "LeftHandPinky3",
    ]

    LEFT_LEG_NAMES = ["LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"]

    LEFT_UPPER_LEG_ROLLS = [
        "LeafLeftUpLegRoll1",
        "LeafLeftUpLegRoll2",
        "LeafLeftUpLegRoll3",
        "LeafLeftUpLegRoll4",
        "LeafLeftUpLegRoll5",
    ]
    LEFT_LOWER_LEG_ROLLS = [
        "LeafLeftLegRoll1",
        "LeafLeftLegRoll2",
        "LeafLeftLegRoll3",
        "LeafLeftLegRoll4",
        "LeafLeftLegRoll5",
    ]

    CHAR_NAME = "MGearIKHuman"

    # Dictionary containing all relevant info; [bone] = {target:'', sub_ik:''}

    char_config = {}

    @classmethod
    def initialize_character(cls):
        selection = cmds.ls(sl=1)
        if not selection:
            cmds.error("Must have reference bone selected")
            return
        reference_bone = selection[-1]

        cmds.HIKCharacterControlsTool()

        # creates a set with current HIKCharNodes, creates a new node and subtracts sets members to get new node

        tmp = set(pm.ls(type="HIKCharacterNode"))
        mel.eval("hikCreateDefinition;")
        hikChar = list(set(pm.ls(type="HIKCharacterNode")) - tmp)[0]
        hikChar.rename(cls.CHAR_NAME)
        mel.eval('hikSetCurrentCharacter("{}");'.format(hikChar))

        if reference_bone:
            node_id = cmds.hikGetNodeIdFromName("Reference")
            mel.eval(
                'setCharacterObject("{}", "{}", "{}", {});'.format(
                    reference_bone, hikChar, node_id, 0
                )
            )

        mel.eval("hikUpdateDefinitionUI();")

    @classmethod
    def is_initialized(cls):
        return mel.eval("hikGetCurrentCharacter;")

    @classmethod
    @one_undo
    def set_list_of_bones_from_selection(
        cls, bones_list, ctrls, do_mirror=False
    ):
        # mirror logic
        if do_mirror:
            if "Left" in bones_list[0]:
                bones_list.extend(
                    [bone.replace("Left", "Right") for bone in bones_list]
                )
                ctrls.extend(
                    [
                        MirrorController.get_opposite_control(ctrl)
                        for ctrl in ctrls
                    ]
                )
            elif "Right" in bones_list[0]:
                bones_list.extend(
                    [bone.replace("Right", "Left") for bone in bones_list]
                )
                ctrls.extend(
                    [
                        MirrorController.get_opposite_control(ctrl)
                        for ctrl in ctrls
                    ]
                )

        hikChar = mel.eval("hikGetCurrentCharacter;")
        locked_ctrls = cls.get_locked_ctrls(ctrls)
        if locked_ctrls:
            if LockedCtrlsDialog(ctrls_list=locked_ctrls).exec_():
                cls.unlock_ctrls_srt(locked_ctrls)
            else:
                return

        for bone, ctrl in zip(bones_list, ctrls):
            node_id = cmds.hikGetNodeIdFromName(bone)
            mel.eval(
                'setCharacterObject("{}", "{}", "{}", {});'.format(
                    ctrl, hikChar, node_id, 0
                )
            )

        pm.evalDeferred(
            'from maya import mel; mel.eval("hikUpdateDefinitionUI();")'
        )
        return

    @classmethod
    def get_locked_ctrls(cls, ctrl_list):
        """
        Receives a list of controllers and returns the controllers that have a locked attribute
        """
        locked_ctrls = []
        for ctrl in ctrl_list:
            attrs = []
            attrs.extend(ctrl.scale.children())
            attrs.extend(ctrl.rotate.children())
            attrs.extend(ctrl.translate.children())
            for attr in attrs:
                if not attr.get(settable=1):
                    locked_ctrls.append(ctrl)
                    break

        return locked_ctrls

    @classmethod
    @one_undo
    def unlock_ctrls_srt(cls, ctrl_list):
        for ctrl in ctrl_list:
            attrs = []
            attrs.extend(ctrl.scale.children())
            attrs.extend(ctrl.rotate.children())
            attrs.extend(ctrl.translate.children())
            for attr in attrs:
                attr.unlock()
                attr.set(keyable=True)

    @classmethod
    def refresh_char_configuration(cls):
        # TODO: Check if character exists on scene
        # clears current char config
        cls.char_config = {}

        hik_count = cmds.hikGetNodeCount()
        hikChar = mel.eval("hikGetCurrentCharacter;")

        if not hikChar:
            return cls.char_config
        for i in range(hik_count):
            bone_name = cmds.GetHIKNodeName(i)
            # bone_target = cmds.hikGetSkNode(hikChar, i)
            bone_target = mel.eval('hikGetSkNode("{}", {})'.format(hikChar, i))

            if bone_target:
                cls.char_config[bone_name] = {"target": bone_target}
                cls.char_config[bone_name]["sub_ik"] = []

                if pm.attributeQuery("sub_ik", node=bone_target, exists=True):
                    connections = cmds.listConnections(
                        "{}.sub_ik".format(bone_target),
                        source=0,
                        destination=1,
                    )
                    if connections:
                        sub_ik_ctls = connections
                        cls.char_config[bone_name]["sub_ik"] = sub_ik_ctls

        return cls.char_config

    @classmethod
    def export_char_configuration(cls):
        cls.refresh_char_configuration()
        file_path = pm.fileDialog2(fileMode=0, fileFilter="*.hikm")[0]
        data_string = json.dumps(cls.char_config, indent=4)
        with open(file_path, "w") as fp:
            fp.write(data_string)
        print(file_path)

    @classmethod
    def import_char_configuration(cls):
        file_path = pm.fileDialog2(fileMode=1, fileFilter="*.hikm")[0]
        with open(file_path, "r") as fp:
            cls.char_config = json.load(fp)

        hikChar = mel.eval("hikGetCurrentCharacter;")

        if not hikChar:
            cmds.HIKCharacterControlsTool()

            tmp = set(pm.ls(type="HIKCharacterNode"))
            cmds.hikCreateDefinition()
            hikChar = list(set(pm.ls(type="HIKCharacterNode")) - tmp)[0]
            hikChar.rename(cls.CHAR_NAME)
            cmds.hikSetCurrentCharacter(hikChar)

        ctls = [
            pm.PyNode(cls.char_config[bone]["target"])
            for bone in cls.char_config
        ]

        for bone in cls.char_config:
            if cls.char_config[bone]["sub_ik"]:
                bone_sub_iks = cls.char_config[bone]["sub_ik"]
                ctls.extend([pm.PyNode(sub_ik) for sub_ik in bone_sub_iks])

        locked_ctrls = cls.get_locked_ctrls(ctls)
        if locked_ctrls:
            if LockedCtrlsDialog(ctrls_list=locked_ctrls).exec_():
                cls.unlock_ctrls_srt(locked_ctrls)
            else:
                # the process was canceled, empty char config and halt
                cls.char_config = {}
                return

        for bone in cls.char_config:
            bone_id = cmds.hikGetNodeIdFromName(bone)
            mel.eval(
                'setCharacterObject("{}", "{}", "{}", {});'.format(
                    cls.char_config[bone]["target"], hikChar, bone_id, 0
                )
            )
            if cls.char_config[bone]["sub_ik"]:
                cls.set_sub_ik(
                    cls.char_config[bone]["target"],
                    cls.char_config[bone]["sub_ik"],
                )

    @classmethod
    def set_sub_ik(cls, bone_target, sub_ik_ctls, do_mirror=False):
        def sub_ik_setup(bone_target, sub_ik_ctls):
            if not pm.attributeQuery("sub_ik", node=bone_target, exists=True):
                pm.addAttr(
                    bone_target, longName="sub_ik", attributeType="message"
                )

            for sub_ik_ctl in sub_ik_ctls:
                if not pm.attributeQuery(
                    "sub_ik", node=sub_ik_ctl, exists=True
                ):
                    pm.addAttr(
                        sub_ik_ctl, longName="sub_ik", attributeType="message"
                    )

                bone_target.sub_ik >> sub_ik_ctl.sub_ik

        # get ctrls

        bone_target = pm.PyNode(bone_target)
        sub_ik_ctls = [pm.PyNode(ctl) for ctl in sub_ik_ctls]
        all_sub_ik_ctls = list(sub_ik_ctls)

        if do_mirror:
            opposite_bone_target = MirrorController.get_opposite_control(
                bone_target
            )
            opposite_sub_ik_ctls = [
                MirrorController.get_opposite_control(ctl)
                for ctl in sub_ik_ctls
            ]
            all_sub_ik_ctls.extend(opposite_sub_ik_ctls)

        locked_ctrls = cls.get_locked_ctrls(all_sub_ik_ctls)
        if locked_ctrls:
            if LockedCtrlsDialog(ctrls_list=locked_ctrls).exec_():
                cls.unlock_ctrls_srt(locked_ctrls)
            else:
                return

        sub_ik_setup(bone_target, sub_ik_ctls)
        if do_mirror:
            sub_ik_setup(opposite_bone_target, opposite_sub_ik_ctls)

    @classmethod
    def clear_sub_ik(cls, bone_target):
        sub_ik_ctls = pm.listConnections(
            "{}.sub_ik".format(bone_target), source=0, destination=1
        )

        if sub_ik_ctls:
            for sub_ik_ctl in sub_ik_ctls:
                if pm.attributeQuery("sub_ik", node=sub_ik_ctl, exists=True):
                    pm.disconnectAttr(
                        "{}.sub_ik".format(bone_target),
                        "{}.sub_ik".format(sub_ik_ctl),
                    )
                    parent_constraint = pm.parentConstraint(sub_ik_ctl, q=1)
                    if parent_constraint:
                        pm.delete(parent_constraint)
        else:
            print("Bone target did not have sub ik nodes.")

    @classmethod
    def sub_iks_binding(cls, activate=True):
        if activate:
            for bone in cls.char_config:
                src_ctl = cls.char_config[bone]["target"]
                for sub_ik in cls.char_config[bone]["sub_ik"]:
                    pm.parentConstraint(src_ctl, sub_ik, maintainOffset=True)
        else:
            for bone in cls.char_config:
                for sub_ik in cls.char_config[bone]["sub_ik"]:
                    constraint = pm.parentConstraint(sub_ik, query=True)
                    if constraint:
                        pm.delete(constraint)

    @classmethod
    @viewport_off
    def bake(cls):
        current_ik_char = mel.eval("hikGetCurrentCharacter;")
        attrs_string = " ".join(cls.get_sub_ik_bake_attrs())
        sub_ik_ctls = [
            cls.char_config[bone]["sub_ik"]
            for bone in cls.char_config
            if cls.char_config[bone]["sub_ik"]
        ]
        if sub_ik_ctls:
            sub_ik_constraints = [
                cmds.parentConstraint(ctl, query=True) for ctl in sub_ik_ctls
            ]
            sub_ik_constraints_string = " ".join(sub_ik_constraints)

            mel_cmd = """
                string $currCharacter = hikGetCurrentCharacter();

                if( $currCharacter != "" )
                {{
                    string $preBakeCmd =  "hikBakeCharacterPre( \\"{0}\\" ); ";
                    $preBakeCmd += "select -add {1};";
                    string $postBakeCmd = "hikBakeCharacterPost( \\"{0}\\" ); ";
                    $postBakeCmd += "delete {2};";

                    performBakeSimulationArgList 2 {{ "1", "animationList", $preBakeCmd, $postBakeCmd }};
                }}

            """.format(
                current_ik_char, attrs_string, sub_ik_constraints_string
            )

            mel.eval(mel_cmd)
            # cls.sub_iks_binding(False)

    @classmethod
    def get_sub_ik_bake_attrs(cls):
        attrs = []
        for bone in cls.char_config:
            for sub_ik in cls.char_config[bone]["sub_ik"]:
                sub_ik = pm.PyNode(sub_ik)
                t_locked = [
                    attr.get(settable=1)
                    for attr in sub_ik.translate.children()
                ]
                r_locked = [
                    attr.get(settable=1) for attr in sub_ik.rotate.children()
                ]
                if False not in t_locked:
                    attrs.append(sub_ik.translate.name())
                if False not in r_locked:
                    attrs.append(sub_ik.rotate.name())
        return attrs

    @classmethod
    @one_undo
    def batch_bake(cls, file_list):
        # curr_character = mel.eval("hikGetCurrentCharacter;") # Not used ?
        # cmds.hikSetCurrentCharacter(hikChar)
        existing_ik_humans = set(pm.ls(type="HIKCharacterNode"))

        HumanIKMapper.refresh_char_configuration()

        # TODO: determine first and last frame, change anim layer name to fbx name,
        sub_ik_ctls = [
            cls.char_config[bone]["sub_ik"]
            for bone in cls.char_config
            if cls.char_config[bone]["sub_ik"]
        ]
        sub_ik_constraints = [
            cmds.parentConstraint(ctl, query=True) for ctl in sub_ik_ctls
        ]

        for file in file_list:
            # TODO test with references
            ref_node = cmds.file(file, r=True, namespace=":", type="FBX")
            file_ik_human = list(
                set(pm.ls(type="HIKCharacterNode")) - existing_ik_humans
            )
            if file_ik_human:
                file_ik_human = file_ik_human[0]
            existing_ik_humans = set(pm.ls(type="HIKCharacterNode"))

            frame_range = (
                cmds.playbackOptions(q=True, min=True),
                cmds.playbackOptions(q=True, max=True)
            )
            # pm.evalDeferred(deferred_cmd)
            cmds.evalDeferred(
                "from mgear.animbits.humanIkMapper import HumanIKMapper \n"
                'HumanIKMapper.deferred_bake("{0}", "{1}")'.format(
                    file_ik_human, frame_range
                )
            )

    @classmethod
    def deferred_bake(cls, ikhuman, frame_range):
        # updates src
        HumanIKMapper.sub_iks_binding(True)
        cmds.optionMenuGrp(
            "hikSourceList", edit=True, value=" {0}".format(ikhuman)
        )
        mel.eval("hikUpdateCurrentSourceFromUI;")

        sub_ik_ctls = [
            cls.char_config[bone]["sub_ik"]
            for bone in HumanIKMapper.char_config
            if HumanIKMapper.char_config[bone]["sub_ik"]
        ]
        sub_ik_constraints = [
            cmds.parentConstraint(ctl, query=True) for ctl in sub_ik_ctls
        ]
        # print("sub ik ctls = {1}, \n subik constraints = {1}".format(sub_ik_ctls, sub_ik_constraints))

        mel.eval(
            'hikBakeCharacterPre("{}");'.format(
                mel.eval("hikGetCurrentCharacter;")
            )
        )
        cmds.select(HumanIKMapper.get_sub_ik_bake_attrs(), add=1)
        cmds.bakeResults(
            cmds.ls(sl=1),
            bakeOnOverrideLayer=True,
            simulation=True,
            t=ast.literal_eval(frame_range),
            sampleBy=1,
        )
        mel.eval(
            'hikBakeCharacterPost("{}");'.format(
                mel.eval("hikGetCurrentCharacter;")
            )
        )
        if sub_ik_constraints:
            cmds.delete(sub_ik_constraints)
        cmds.rename("BakeResults", ikhuman)


class HumanIKMapperUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(HumanIKMapperUI, self).__init__(parent)

        # self.func = MirrorController()

        self.setWindowTitle("HumanIK Mapper")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)
        self.setMinimumSize(QtCore.QSize(0, 0))
        default_w = 300
        default_h = 300
        self.resize(default_w, default_h)

        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.update_mapping()

    @QtCore.Slot()
    def adjustSize(self, *args, **kwargs):
        # Needed to mark the adjustSize method as slot
        self.setup_tab.resize(self.setup_tab.minimumSizeHint())
        self.setup_tab.adjustSize()
        self.resize(self.minimumSizeHint())
        super(HumanIKMapperUI, self).adjustSize()

    def create_actions(self):
        self.import_action = QtWidgets.QAction("Import")
        self.export_action = QtWidgets.QAction("Export")
        self.bake_action = QtWidgets.QAction("Bake")
        self.export_batch_bake_action = QtWidgets.QAction(
            "Export Batch Bake Config"
        )
        self.import_batch_bake_action = QtWidgets.QAction(
            "Import Batch Bake Config"
        )

    def create_widgets(self):
        self.menu_bar = QtWidgets.QMenuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addAction(self.export_action)
        self.bake_menu = self.menu_bar.addMenu("Bake")
        self.bake_menu.addAction(self.bake_action)
        self.bake_menu.addSeparator()
        self.bake_menu.addAction(self.export_batch_bake_action)
        self.bake_menu.addAction(self.import_batch_bake_action)

        self.initialize_btn = QtWidgets.QPushButton("Initialize")

        self.head_btn = QtWidgets.QPushButton("Head")
        self.spine_btn = QtWidgets.QPushButton("Spine")

        self.left_arm_btn = QtWidgets.QPushButton("Left Arm")
        self.left_upper_arm_rolls_btn = QtWidgets.QPushButton(
            "Left Upper Arm Rolls"
        )
        self.left_lower_arm_rolls_btn = QtWidgets.QPushButton(
            "Left Lower Arm Rolls"
        )
        self.left_hand_btn = QtWidgets.QPushButton("Left Hand")

        self.right_arm_btn = QtWidgets.QPushButton("Right Arm")
        self.right_upper_arm_rolls_btn = QtWidgets.QPushButton(
            "Right Upper Arm Rolls"
        )
        self.right_lower_arm_rolls_btn = QtWidgets.QPushButton(
            "Right Lower Arm Rolls"
        )
        self.right_hand_btn = QtWidgets.QPushButton("Right Hand")

        self.left_leg_btn = QtWidgets.QPushButton("Left Leg")
        self.left_upper_leg_rolls_btn = QtWidgets.QPushButton(
            "Left Upper Leg Rolls"
        )
        self.left_lower_leg_rolls_btn = QtWidgets.QPushButton(
            "Left Lower Leg Rolls"
        )

        self.right_leg_btn = QtWidgets.QPushButton("Right Leg")
        self.right_upper_leg_rolls_btn = QtWidgets.QPushButton(
            "Right Upper Leg Rolls"
        )
        self.right_lower_leg_rolls_btn = QtWidgets.QPushButton(
            "Right Lower Leg Rolls"
        )

        self.mirror_checkbox = QtWidgets.QCheckBox("Apply mirror")
        self.mirror_checkbox.setChecked(True)

        self.instructions_tb = QtWidgets.QTextEdit()
        self.instructions_tb.setText(
            "1. Select the Reference Bone Ctrl and click initialize \n"
            "2. Click the element you want to configure \n"
            "3. Select the elements in the indicated order and click confirm. \n"
            "Note: Bones that have a number in their name are not mandatory. "
        )
        self.instructions_tb.setReadOnly(True)
        self.instructions_tb.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents
        )
        self.instructions_tb.setFixedHeight(120)

        self.refresh_mapping_btn = QtWidgets.QPushButton("Refresh")
        self.sub_ik_active_cb = QtWidgets.QCheckBox("Sub Ik Active")
        self.mapping_table = QtWidgets.QTableWidget(1, 3)
        self.mapping_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.mapping_table.setHorizontalHeaderLabels(
            ["Bone", "Target", "Sub IK"]
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )

        # bake tab
        self.bake_paths_lw = QtWidgets.QListWidget()
        self.bake_paths_lw.setSelectionMode(
            QtWidgets.QListWidget.ExtendedSelection
        )
        add_remove_font = QtGui.QFont()
        add_remove_font.setPointSize(25)
        self.add_bake_path_btn = QtWidgets.QPushButton("+")
        self.add_bake_path_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum
        )
        self.add_bake_path_btn.setFont(add_remove_font)
        self.remove_bake_path_btn = QtWidgets.QPushButton("-")
        self.remove_bake_path_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum
        )
        self.remove_bake_path_btn.setFont(add_remove_font)
        self.batch_bake_btn = QtWidgets.QPushButton("Batch Bake")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setMenuBar(self.menu_bar)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.minimumSizeHint()
        main_layout.addWidget(self.tabs)
        self.setup_tab = QtWidgets.QWidget()
        self.setup_tab.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.setup_layout = QtWidgets.QVBoxLayout(self.setup_tab)
        self.tabs.addTab(self.setup_tab, "Setup")

        self.configure_collapsible = mwgt.CollapsibleWidget(
            "Configuration", expanded=True
        )
        # self.configure_collapsible.header_wgt.setFixedHeight(18)
        self.configure_collapsible.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum
        )

        self.setup_layout.addWidget(self.configure_collapsible)

        configure_gb = QtWidgets.QGroupBox("Configure")
        self.configure_collapsible.addWidget(configure_gb)
        configure_layout = QtWidgets.QVBoxLayout()
        configure_gb.setLayout(configure_layout)

        configure_layout.addWidget(self.initialize_btn)
        configure_layout.addWidget(self.head_btn)
        configure_layout.addLayout(
            self._group_in_hlayout(self.right_arm_btn, self.left_arm_btn)
        )
        configure_layout.addLayout(
            self._group_in_hlayout(
                self.right_lower_arm_rolls_btn,
                self.right_upper_arm_rolls_btn,
                self.left_upper_arm_rolls_btn,
                self.left_lower_arm_rolls_btn,
            )
        )
        configure_layout.addLayout(
            self._group_in_hlayout(self.right_hand_btn, self.left_hand_btn)
        )
        configure_layout.addWidget(self.spine_btn)
        configure_layout.addLayout(
            self._group_in_hlayout(self.right_leg_btn, self.left_leg_btn)
        )
        configure_layout.addLayout(
            self._group_in_hlayout(
                self.right_lower_leg_rolls_btn,
                self.right_upper_leg_rolls_btn,
                self.left_upper_leg_rolls_btn,
                self.left_lower_leg_rolls_btn,
            )
        )

        mirror_layout = QtWidgets.QHBoxLayout()
        mirror_layout.addStretch()
        mirror_layout.addWidget(self.mirror_checkbox)
        configure_layout.addLayout(mirror_layout)

        self.instructions_collapsible = mwgt.CollapsibleWidget(
            "Instructions", expanded=False
        )
        self.setup_layout.addWidget(self.instructions_collapsible)
        self.instructions_collapsible.header_wgt.setFixedHeight(18)
        self.instructions_collapsible.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        )
        self.instructions_collapsible.addWidget(self.instructions_tb)

        self.mapping_collapsible = mwgt.CollapsibleWidget(
            "Mapping", expanded=False
        )
        self.setup_layout.addWidget(self.mapping_collapsible)
        self.mapping_collapsible.header_wgt.setFixedHeight(18)
        self.mapping_collapsible.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        mapping_buttons = QtWidgets.QHBoxLayout()
        mapping_buttons.addWidget(self.refresh_mapping_btn)
        mapping_buttons.addStretch()
        mapping_buttons.addWidget(self.sub_ik_active_cb)
        self.mapping_collapsible.addLayout(mapping_buttons)
        self.mapping_collapsible.addWidget(self.mapping_table)

        # batch bake

        self.batch_bake_tab = QtWidgets.QWidget()
        self.batch_bake_tab.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored
        )
        batch_bake_vlayout = QtWidgets.QVBoxLayout(self.batch_bake_tab)
        paths_hlayout = QtWidgets.QHBoxLayout()
        path_buttons_vlayout = QtWidgets.QVBoxLayout()

        path_buttons_vlayout.addWidget(self.add_bake_path_btn)
        path_buttons_vlayout.addWidget(self.remove_bake_path_btn)

        paths_hlayout.addWidget(self.bake_paths_lw)
        paths_hlayout.addLayout(path_buttons_vlayout)

        batch_bake_vlayout.addLayout(paths_hlayout)
        batch_bake_vlayout.addWidget(self.batch_bake_btn)

        self.tabs.addTab(self.batch_bake_tab, "Batch Bake")

    def create_connections(self):
        self.export_action.triggered.connect(
            HumanIKMapper.export_char_configuration
        )
        self.import_action.triggered.connect(self.import_config)
        self.bake_action.triggered.connect(HumanIKMapper.bake)
        self.export_batch_bake_action.triggered.connect(
            self.export_batch_bake_config
        )
        self.import_batch_bake_action.triggered.connect(
            self.import_batch_bake_config
        )

        self.initialize_btn.clicked.connect(HumanIKMapper.initialize_character)

        self.head_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.HEAD_NAMES)
        )

        self.left_arm_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_ARM_NAMES)
        )
        self.left_upper_arm_rolls_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_UPPER_ARM_ROLLS)
        )
        self.left_lower_arm_rolls_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_LOWER_ARM_ROLLS)
        )
        self.left_hand_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_HAND)
        )

        self.right_arm_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_ARM_NAMES)
            )
        )
        self.right_upper_arm_rolls_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_UPPER_ARM_ROLLS)
            )
        )
        self.right_lower_arm_rolls_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_LOWER_ARM_ROLLS)
            )
        )
        self.right_hand_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_HAND)
            )
        )

        self.spine_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.SPINE_NAMES)
        )

        self.left_leg_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_LEG_NAMES)
        )
        self.left_upper_leg_rolls_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_UPPER_LEG_ROLLS)
        )
        self.left_lower_leg_rolls_btn.clicked.connect(
            self.display_list_mb_cb(HumanIKMapper.LEFT_LOWER_LEG_ROLLS)
        )

        self.right_leg_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_LEG_NAMES)
            )
        )
        self.right_upper_leg_rolls_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_UPPER_LEG_ROLLS)
            )
        )
        self.right_lower_leg_rolls_btn.clicked.connect(
            self.display_list_mb_cb(
                self._change_bones_2_right(HumanIKMapper.LEFT_LOWER_LEG_ROLLS)
            )
        )

        self.instructions_collapsible.header_wgt.clicked.connect(
            self.deferred_resize
        )

        self.mapping_collapsible.header_wgt.clicked.connect(
            self.deferred_resize
        )

        self.refresh_mapping_btn.clicked.connect(self.update_mapping)
        self.sub_ik_active_cb.stateChanged.connect(
            HumanIKMapper.sub_iks_binding
        )
        self.mapping_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.mapping_table.customContextMenuRequested.connect(
            self._mapping_menu
        )

        # batch bake path

        self.add_bake_path_btn.clicked.connect(self.add_batch_bake_paths)
        self.remove_bake_path_btn.clicked.connect(self.remove_batch_bake_paths)
        self.batch_bake_btn.clicked.connect(self.batch_bake)

    def deferred_resize(self):
        # print("calling deferred resize")
        QtCore.QMetaObject.invokeMethod(
            self, "adjustSize", QtCore.Qt.QueuedConnection
        )

    def display_list_mb_cb(self, bone_list):
        def display():
            if not HumanIKMapper.is_initialized():
                pm.error("HumanIK character is not initialized, aborting.")
                return
            dialog = BoneListDialog(
                self, bone_list, self.mirror_checkbox.isChecked()
            )
            dialog.show()

        return display

    def update_mapping(self):
        bone_dict = HumanIKMapper.refresh_char_configuration()
        self.mapping_table.setRowCount(len(bone_dict))
        for i, bone in enumerate(bone_dict):
            bone_item = QtWidgets.QTableWidgetItem(bone)
            target_item = QtWidgets.QTableWidgetItem(bone_dict[bone]["target"])
            sub_ik_text = ",".join(bone_dict[bone]["sub_ik"])
            sub_ik_item = QtWidgets.QTableWidgetItem(sub_ik_text)
            self.mapping_table.setItem(i, 0, bone_item)
            self.mapping_table.setItem(i, 1, target_item)
            self.mapping_table.setItem(i, 2, sub_ik_item)

    def import_config(self):
        HumanIKMapper.import_char_configuration()
        self.update_mapping()

    def set_selection_as_sub_ik(self, bone_target):
        do_mirror = self.mirror_checkbox.isChecked()
        HumanIKMapper.set_sub_ik(bone_target, pm.ls(sl=1), do_mirror)
        self.update_mapping()

    def clear_sub_ik(self, bone_target):
        HumanIKMapper.clear_sub_ik(bone_target)
        self.update_mapping()

    def add_batch_bake_paths(self):
        fbx_filter = "*.fbx"
        paths = cmds.fileDialog2(fileFilter=fbx_filter, fileMode=4)

        self.bake_paths_lw.addItems(paths)

    def remove_batch_bake_paths(self):
        selected_items = self.bake_paths_lw.selectedItems()

        for item in selected_items:
            self.bake_paths_lw.takeItem(self.bake_paths_lw.row(item))

    def batch_bake(self):
        files = []
        for i in range(self.bake_paths_lw.count()):
            files.append(self.bake_paths_lw.item(i).text())
        print(files)
        HumanIKMapper.batch_bake(files)

    def export_batch_bake_config(self):
        files = []
        for i in range(self.bake_paths_lw.count()):
            files.append(self.bake_paths_lw.item(i).text())

        file_path = pm.fileDialog2(fileMode=0, fileFilter="*.bkcn")
        if not file_path:
            return
        file_path = file_path[0]
        data_string = json.dumps(files, indent=4)
        with open(file_path, "w") as fp:
            fp.write(data_string)
        print(file_path)

    def import_batch_bake_config(self):
        file_path = pm.fileDialog2(fileMode=1, fileFilter="*.bkcn")
        if not file_path:
            return
        file_path = file_path[0]
        with open(file_path, "r") as fp:
            data_string = json.load(fp)
            self.bake_paths_lw.clear()
            self.bake_paths_lw.addItems(data_string)

    def _group_in_hlayout(self, *args):
        h_layout = QtWidgets.QHBoxLayout()
        for i in args:
            h_layout.addWidget(i)

        return h_layout

    def _change_bones_2_right(self, bones):
        new_bones_list = list(bones)
        for i in range(len(new_bones_list)):
            new_bones_list[i] = bones[i].replace("Left", "Right")

        return new_bones_list

    def _mapping_menu(self, QPos):
        comp_widget = self.mapping_table

        self.item_menu = QtWidgets.QMenu()
        parent_position = comp_widget.mapToGlobal(QtCore.QPoint(0, 0))
        item = self.mapping_table.itemAt(QPos)
        corresponding_bone = self.mapping_table.item(item.row(), 1).text()
        set_selection_as_sub_ik = self.item_menu.addAction(
            "Set selection as Sub Ik"
        )
        clear_sub_ik = self.item_menu.addAction("Clear Sub Ik")

        set_selection_as_sub_ik.triggered.connect(
            partial(self.set_selection_as_sub_ik, corresponding_bone)
        )
        clear_sub_ik.triggered.connect(
            partial(self.clear_sub_ik, corresponding_bone)
        )

        self.item_menu.move(parent_position + QPos)
        self.item_menu.show()


class BoneListDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, bone_list=[], do_mirror=False):
        super(BoneListDialog, self).__init__(parent)

        # self.func = MirrorController()

        self.setWindowTitle("Limb Selection Order")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)
        self.setMinimumSize(QtCore.QSize(350, 250))

        self.bone_list = list(bone_list)
        self.do_mirror = do_mirror

        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.cb_manager = callbackManager.CallbackManager()
        self.add_callback()

    def close(self):
        self.cb_manager.removeAllManagedCB()
        self.deleteLater()

    def closeEvent(self, evnt):
        self.close()

    def dockCloseEventTriggered(self):
        self.close()

    def create_widgets(self):
        self.bone_te = QtWidgets.QTextEdit()
        self.bone_te.setText("\n".join(self.bone_list))
        self.bone_te.setReadOnly(True)

        self.selection_lw = QtWidgets.QListWidget()
        self.selection_changed()

        self.confirm_btn = QtWidgets.QPushButton("Confirm")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        text_layout = QtWidgets.QHBoxLayout()
        text_layout.addWidget(self.bone_te)
        text_layout.addWidget(self.selection_lw)

        main_layout.addLayout(text_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.confirm_btn)

        main_layout.addLayout(buttons_layout)

    def create_connections(self):
        self.cancel_btn.clicked.connect(self.close)
        self.confirm_btn.clicked.connect(self.confirm_cb)

    def add_callback(self):
        self.cb_manager.selectionChangedCB(
            "BoneListDialog_selection_CB", self.selection_changed
        )

    def selection_changed(self, *args):
        self.selection_lw.clear()
        selection = cmds.ls(sl=1)
        for i in selection:
            self.selection_lw.addItem(i)

    def confirm_cb(self):
        selection = pm.ls(sl=1)
        HumanIKMapper.set_list_of_bones_from_selection(
            self.bone_list, selection, self.do_mirror
        )
        self.close()


class LockedCtrlsDialog(QtWidgets.QDialog):
    def __init__(self, parent=pyqt.maya_main_window(), ctrls_list=[]):
        super(LockedCtrlsDialog, self).__init__(parent)

        self.setWindowTitle("Locked attributes detected")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)
        self.setMinimumSize(QtCore.QSize(350, 250))

        self.ctrl_list = ctrls_list

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        warning_font = QtGui.QFont()
        warning_font.setBold(True)
        warning_font.setPointSize(13)

        self.locked_lb = QtWidgets.QLabel(
            "The following objects have locked attributes \n"
        )
        self.locked_lb.setAlignment(QtCore.Qt.AlignCenter)
        self.locked_lb.setFont(warning_font)
        self.unlock_lb = QtWidgets.QLabel("\n Do you wish to unlock them? \n")
        self.unlock_lb.setAlignment(QtCore.Qt.AlignCenter)

        self.list_wl = QtWidgets.QListWidget()
        self.list_wl.setSelectionMode(QtWidgets.QListWidget.NoSelection)
        for ctrl in self.ctrl_list:
            self.list_wl.addItem(ctrl.name())
        self.list_wl.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents
        )

        self.confirm_btn = QtWidgets.QPushButton("Confirm")
        self.confirm_btn.setDefault(True)
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # main_layout.addWidget(self.warning_lb)
        main_layout.addWidget(self.locked_lb)
        main_layout.addWidget(self.list_wl)
        main_layout.addWidget(self.unlock_lb)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.confirm_btn)

        main_layout.addLayout(buttons_layout)

    def create_connections(self):
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)


def show(*args):
    return mgear.core.pyqt.showDialog(HumanIKMapperUI, dockable=True)


if __name__ == "__main__":
    show()
