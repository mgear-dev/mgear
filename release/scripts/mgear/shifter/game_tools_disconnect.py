import mgear.pymaya as pm
import maya.cmds as cmds
import json
import sys
from functools import partial
import traceback
import os.path
import ast

import mgear.core.utils as mutils
from mgear.core import string
from mgear.core import attribute

import mgear.shifter.game_tools_disconnect_ui as gtUI

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.core import pyqt
from mgear.shifter.utils import get_deformer_joints
from mgear.vendor.Qt import QtCore, QtWidgets

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)

S_CHANNELS = ["scale", "scaleX", "scaleY", "scaleZ", "shear"]

SRT_CHANNELS = [
    "translate",
    "translateX",
    "translateY",
    "translateZ",
    "rotate",
    "rotateX",
    "rotateY",
    "rotateZ",
] + S_CHANNELS

DRIVEN_JOINT_ATTR = "drivenJoint"
DRIVER_ATTRS = "driverAttrs"

#######################################################
# standalone disconnect commands


@mutils.one_undo
def disconnect_joints():
    # get deformer joints from set
    grps = get_deformers_sets()
    for g in grps:
        cnx, mcons_nodes = get_connections(g.members(), embed_info=True)
        # disconnect (input and output connections from mgear_matrixConstraint)
        if cnx:
            disconnect(cnx)
            pm.displayInfo(
                "Joint from group {} has been disconnected".format(g.name())
            )
        else:
            pm.displayWarning(
                "Rig disconnect is not possible, if it is a MetaHuman try to delete the rig and build again."
            )


@mutils.one_undo
def connect_joints_from_matrixConstraint():
    # Note: not using message connection in case the rig and the joint are not
    # keep in the same scene
    connected = False
    cnx_nodes = pm.ls(type="mgear_matrixConstraint")
    if not cnx_nodes:
        cnx_nodes = pm.ls(type="decomposeMatrix")
    for mcon in cnx_nodes:
        if mcon.hasAttr(DRIVEN_JOINT_ATTR) and mcon.getAttr(DRIVEN_JOINT_ATTR):
            jnt_name = mcon.getAttr(DRIVEN_JOINT_ATTR)
            if pm.objExists(jnt_name):
                connected = True
                jnt = pm.PyNode(jnt_name)
                driver_attrs = ast.literal_eval(mcon.getAttr(DRIVER_ATTRS))
                connect_joint(mcon, jnt, driver_attrs)

    if connected:
        pm.displayInfo("Joints has been connected")
    else:
        pm.displayInfo("Nothing to connected")


@mutils.one_undo
def delete_rig_keep_joints(confirmPop=True):
    confirm = False
    if confirmPop:
        # Should pop up confirmation dialog
        button_pressed = QtWidgets.QMessageBox.question(
            pyqt.maya_main_window(), "Warning", "Delete Rigs in the scene?"
        )
        if button_pressed == QtWidgets.QMessageBox.Yes:
            confirm = True

    else:
        pm.displayInfo("Cancelled")
        return
    if confirm:
        disconnect_joints()
        for rig_root in get_rig_root_from_set():
            rig_name = rig_root.name()
            jnt_org = rig_root.jnt_vis.listConnections(type="transform")[0]
            joints = jnt_org.getChildren()
            if joints:
                pm.parent(joints, world=True)
            pm.delete(rig_root.rigGroups.listConnections(type="objectSet"))
            pm.delete(pm.ls(type="mgear_matrixConstraint"))
            pm.delete(rig_root)

            pm.displayInfo("{} deleted.".format(rig_name))


def get_deformers_sets():
    grps = pm.ls("*_deformers_grp", type="objectSet")
    if not grps:
        grps = pm.ls("*:*_deformers_grp", type="objectSet")
    return grps


def get_rig_root_from_set():
    # check message cnx
    roots = []
    for grp in get_deformers_sets():
        rig_root = grp.message.listConnections(type="transform")[0]
        roots.append(rig_root)
    return roots


def connect_joint(matrixConstraint, joint, driver_attrs):
    leaf_jnt = None
    for e, chn in enumerate(SRT_CHANNELS):
        if driver_attrs[e]:
            if joint.hasAttr("leaf_joint"):
                leaf_jnt = joint.leaf_joint.listConnections()
            if leaf_jnt and chn in S_CHANNELS:
                pm.connectAttr(driver_attrs[e], leaf_jnt[0].attr(chn))
            else:
                pm.connectAttr(driver_attrs[e], joint.attr(chn))
    pm.connectAttr(
        joint.parentInverseMatrix[0],
        driver_attrs[-2],
    )


@mutils.one_undo
def disconnect(cnxDict):
    """Disconnect the joints using the connections dictionary

    Args:
        cnxDict (dict): Description of the deconections to remove
    """
    for i, jnt in enumerate(cnxDict["joints"]):
        # we don't need to disconnect blended joint since the connection is
        # from other joints
        if not jnt.startswith("blend_"):
            oJnt = pm.PyNode(jnt)
            leaf_jnt = None

            if oJnt.hasAttr("leaf_joint"):
                leaf_jnt = oJnt.leaf_joint.listConnections()

            for e, chn in enumerate(SRT_CHANNELS):
                if leaf_jnt and chn in S_CHANNELS:
                    plug = leaf_jnt[0].attr(chn)
                    # pm.disconnectAttr(plug)
                else:
                    plug = oJnt.attr(chn)
                if cnxDict["attrs"][i][e]:
                    try:
                        pm.disconnectAttr(cnxDict["attrs"][i][e], plug)
                    except RuntimeError:
                        pm.displayWarning(
                            "Plug: {} already disconnected".format(plug.name())
                        )

            if cnxDict["attrs"][i][13]:
                pm.disconnectAttr(
                    oJnt.parentInverseMatrix[0], cnxDict["attrs"][i][13]
                )
            if cnxDict["attrs"][i][14]:
                pm.disconnectAttr(
                    oJnt.parentMatrix[0], cnxDict["attrs"][i][14]
                )


def connect(cnxDict, nsRig=None, nsSkin=None):
    """Connect the joints using the connections dictionary.

    Args:
        cnxDict (dict): Description of the deconections to remove
        nsRig (string, optional): rig namespace
        nsSkin (None, optional): model namespace
    """

    def connect_with_ns(attr, plug, nsRig):
        # connect with namespace
        if plug:
            if nsRig:
                pm.connectAttr(
                    attr,
                    nsRig + ":" + plug,
                    f=True,
                )
            else:
                pm.connectAttr(
                    attr,
                    plug,
                    f=True,
                )

    for i, jnt in enumerate(cnxDict["joints"]):
        leaf_jnt = None
        if nsSkin:
            oJnt = pm.PyNode(nsSkin + ":" + jnt)
        else:
            oJnt = pm.PyNode(jnt)

        if oJnt.hasAttr("leaf_joint"):
            leaf_jnt = oJnt.leaf_joint.listConnections()
        for e, chn in enumerate(SRT_CHANNELS):
            if leaf_jnt and chn in S_CHANNELS:
                plug = leaf_jnt[0].attr(chn)
            else:
                plug = oJnt.attr(chn)

            if cnxDict["attrs"][i][e]:
                if nsRig:
                    pm.connectAttr(
                        nsRig + ":" + cnxDict["attrs"][i][e], plug, f=True
                    )
                else:
                    pm.connectAttr(cnxDict["attrs"][i][e], plug, f=True)

        connect_with_ns(
            oJnt.parentInverseMatrix[0], cnxDict["attrs"][i][13], nsRig
        )
        connect_with_ns(oJnt.parentMatrix[0], cnxDict["attrs"][i][14], nsRig)


def connectCns(cnxDict, nsRig=None, nsSkin=None):
    """Connect the joints using constraints

    Args:
        cnxDict (dict): Description of the deconections to remove
        nsRig (string, optional): rig namespace
        nsSkin (None, optional): model namespace
    """
    for i, jnt in enumerate(cnxDict["joints"]):
        if nsSkin:
            oJnt = pm.PyNode(nsSkin + ":" + jnt)
        else:
            oJnt = pm.PyNode(jnt)

        if cnxDict["attrs"][i][0]:
            if nsRig:
                oAttr = pm.PyNode(nsRig + ":" + cnxDict["attrs"][i][0])
            else:
                oAttr = pm.PyNode(cnxDict["attrs"][i][0])

            oNode = oAttr.node()
            oTrans = pm.listConnections(
                pm.listConnections(oNode.inputMatrix)[0].matrixIn[0]
            )
            pm.parentConstraint(oTrans, oJnt, mo=True)
            pm.scaleConstraint(oTrans, oJnt, mo=True)


def get_connections(source=None, embed_info=False):
    """Get source joint connections

    Args:
        source (list, optional): List of Joints

    Returns:
        dict: joint connections dictionary
    """

    def embed_driven_joint_data(mcons_node, joint, attrs_list_checked):
        """embed driven joint name

        Args:
            mcons_node (pyNode): mgear_matrixConstraint
            joint (PyNode): Joint
        """
        if not mcons_node.hasAttr(DRIVEN_JOINT_ATTR):
            attribute.addAttribute(
                mcons_node, DRIVEN_JOINT_ATTR, "string", value=joint.name()
            )
            attribute.addAttribute(
                mcons_node,
                DRIVER_ATTRS,
                "string",
                value=str(attrs_list_checked),
            )

    connections = {}
    connections["joints"] = []
    connections["attrs"] = []
    mcons_nodes = []
    if not source:
        source = pm.selected()
    for jnt in source:
        jnt = pm.node.Joint(jnt)
        leaf_jnt = None
        if not jnt.name().startswith(("blend_", "leaf_")):
            connections["joints"].append(jnt.name())
            attrs_list = []
            if jnt.hasAttr("leaf_joint"):
                leaf_jnt = jnt.leaf_joint.listConnections()
            for chn in SRT_CHANNELS:
                if leaf_jnt and chn in S_CHANNELS:
                    at = leaf_jnt[0].attr(chn)
                else:
                    at = jnt.attr(chn)
                at_cnx = pm.listConnections(
                    at, p=True, type="mgear_matrixConstraint"
                )
                if not at_cnx:
                    at_cnx = pm.listConnections(
                        at, p=True, type="decomposeMatrix"
                    )
                attrs_list.append(at_cnx)

            parentInv_attr = pm.listConnections(
                jnt.parentInverseMatrix[0], d=True, p=True
            )
            attrs_list.append(parentInv_attr)

            parentMtx_attr = pm.listConnections(
                jnt.parentMatrix[0], d=True, p=True
            )
            # ensure that only defaul mgear connected rigs are disconnected
            # this will return none if a none supported connection is found
            if parentMtx_attr and parentMtx_attr[0].node().nodeType() not in [
                "mgear_mulMatrix",
                "mgear_matrixConstraint",
            ]:
                return None, None
            attrs_list.append(parentMtx_attr)

            attrs_list_checked = []
            mtx_cons = None
            for at in attrs_list:
                if at:
                    attrs_list_checked.append(at[0].name())
                    mcons_nodes.append(at[0].node())
                    if not mtx_cons:
                        mtx_cons = at[0].node()
                else:
                    attrs_list_checked.append(None)
            if mtx_cons and embed_info:
                embed_driven_joint_data(mtx_cons, jnt, attrs_list_checked)

            connections["attrs"].append(attrs_list_checked)
    return connections, mcons_nodes


def exportConnections(source=None, filePath=None, disc=False):
    """Export connection to a json file wiht .jnn extension

    Args:
        source (list, optional): List of Joints
        filePath (None, optional): Directory path to save the file
        disc (bool, optional): If True, will disconnect the joints.

    Returns:
        set: Decompose matrix nodes. We need to return the decompose
            matrix nodes to track it at export time.
    """
    connections, mcons_nodes = get_connections(source)

    data_string = json.dumps(connections, indent=4, sort_keys=True)
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=0,
            fileFilter=" Shifter joint cnx matrix" "  .jmm (*%s)" % ".jmm",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

    if connections["joints"]:
        with open(filePath, "w") as f:
            f.write(data_string)

        if disc:
            disconnect(connections)
    # we need to return the decompose matrix nodes to track it at export time.
    return set(mcons_nodes)


def importConnections(filePath=None, nsRig=None, nsSkin=None, useMtx=True):
    """import connections  from file

    Args:
        filePath (str, optional): Connection json file pth
        nsRig (str, optional): Rig namespace
        nsSkin (str, optional): mMdel namespace
        useMtx (bool, optional): If True will use matrix multiplication, if
            False, will use constraint connections

    Returns:
        None: None
    """
    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            fileMode=1,
            startingDirectory=startDir,
            fileFilter=" Shifter joint cnx matrix " " .jmm (*%s)" % ".jmm",
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    with open(filePath) as fp:
        configDict = json.load(fp)

    if useMtx:
        connect(configDict, nsRig=nsRig, nsSkin=nsSkin)
    else:
        connectCns(configDict, nsRig=nsRig, nsSkin=nsSkin)


def getRigTopNode(node=None):
    """Checker to ensure the top rig node is valid

    Args:
        node (dagNode, optional):Rig top node

    Returns:
        str: Rig top node name
    """
    if not node and pm.selected():
        node = pm.selected()[0]
        if not node.hasAttr("is_rig"):
            pm.displayWarning(
                "Please select a valid rig top node!. '{}' "
                "is not a rig top node".format(node.name())
            )
            return False
        return node.name()
    else:
        pm.displayWarning("Please select a rig top node!")
        return False


def runScript(path=None):
    """Run a custom script file

    Args:
        path (str, optional): Path to the python file
    """
    if path:
        exec(compile(open(path, "rb").read(), path, "exec"))


@mutils.one_undo
def exportAssetAssembly(name, rigTopNode, meshTopNode, path, postScript=None):
    """Export the asset assembly. Model, rig and connections dict.

    Args:
        name (str): Name of the asset
        rigTopNode (str): Name of the rig top node
        meshTopNode (str): Name of the model top node
        path (str): Pestination directory
        postScript (path, optional): Script to run before export

    Returns:
        None: None
    """
    if pm.ls(rigTopNode):
        rigTopNode = pm.PyNode(rigTopNode)
    else:
        pm.displayError(
            "{} doesn't exist or duplicated. Please check your "
            "scene".format(rigTopNode)
        )
        return

    if pm.ls(meshTopNode):
        meshTopNode = pm.PyNode(meshTopNode)
    else:
        pm.displayError(
            "{} doesn't exist or duplicated. Please check "
            "your scene".format(meshTopNode)
        )
        return
    # check the folder and script
    # if the target name exist abort and request another name

    deformer_jnts = get_deformer_joints(rigTopNode)

    # export connections and cut joint connections
    file_path = os.path.join(path, name + ".jmm")
    dm_nodes = exportConnections(
        source=deformer_jnts, filePath=file_path, disc=True
    )

    # cut al possible remaining connection and adjust hierarchy
    # joint or visibility
    jnt_org = pm.PyNode("jnt_org")
    pm.disconnectAttr(rigTopNode.jnt_vis, jnt_org.visibility)

    # restructure model
    model = pm.createNode("transform", n="model", p=None, ss=True)
    pm.addAttr(model, ln="rigGroups", at="message", m=1)
    pm.parent(meshTopNode, jnt_org, model)

    # disconnect jnt set
    sets = rigTopNode.listConnections(type="objectSet")

    deformersGrp = None
    for oSet in sets:
        if "deformers_grp" in oSet.name():
            deformersGrp = oSet

    if deformersGrp:
        for cnx in deformersGrp.message.listConnections(p=True):
            pm.disconnectAttr(deformersGrp.message, cnx)
        pm.connectAttr(deformersGrp.message, model.attr("rigGroups[0]"))

    # disconnect bindPoses
    dg_poses = rigTopNode.message.listConnections(type="dagPose", p=True)
    for dgp in dg_poses:
        if dgp.node().name().startswith("bindPose"):
            pm.disconnectAttr(rigTopNode.message, dgp)

    # post script
    if postScript:
        try:
            exec(compile(open(postScript, "rb").read(), postScript, "exec"))
        except Exception as ex:
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            pm.displayError(message)
            cont = pm.confirmBox(
                "FAIL: Script Fail",
                "Do you want to export anyway?"
                + "\n\n"
                + message
                + "\n\n"
                + traceback.format_exc(),
                "Continue",
                "Cancel",
            )
            if not cont:
                pm.undo()
                return

    # export rig model
    pm.select(dm_nodes, r=True)
    pm.select(rigTopNode, add=True)
    file_path = os.path.join(path, name + "_rig.ma")
    exp = pm.exportSelected(file_path, f=True, type="mayaAscii")
    pm.displayInfo(exp)

    # export mesh and joints
    pm.select(model, r=True)
    file_path = os.path.join(path, name + "_model.ma")
    exp = pm.exportSelected(file_path, f=True, type="mayaAscii")
    pm.displayInfo(exp)


def createAssetAssembly(filePath=None, reference=False):
    """Create the asset assembly.

    The assets for asset assembly can be imported o referenced.
    The namespace will be the name of the asset.

    Args:
        filePath (str, optional): Path to the connection dictionary
        reference (bool, optional): If True will create references

    Returns:
        None: None
    """
    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(
            fileMode=1,
            startingDirectory=startDir,
            fileFilter=" Shifter joint cnx matrix " " .jmm (*%s)" % ".jmm",
        )

    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]

    asset_name = os.path.basename(filePath).split(".")[0]
    dir_path = os.path.dirname(filePath)

    for part in ["model.ma", "rig.ma"]:
        asset_path = os.path.join(dir_path, "_".join([asset_name, part]))
        if reference:
            ref = True
            imp = False
            message = "Reference"
        else:
            ref = False
            imp = True
            message = "Import"
        pm.displayInfo("{} asset: {} ".format(message, asset_path))
        cmds.file(
            asset_path,
            i=imp,
            reference=ref,
            type="mayaAscii",
            ignoreVersion=True,
            mergeNamespacesOnClash=True,
            namespace=asset_name,
        )

    # import cnx
    pm.displayInfo("Import connections dictionary ".format(filePath))
    importConnections(filePath, nsRig=asset_name, nsSkin=asset_name)

    # reconnect jont_vis
    root = [x for x in pm.ls(type="transform") if x.hasAttr("is_rig")]
    if root:
        jnt_org = pm.PyNode(asset_name + ":jnt_org")
        pm.connectAttr(root[0].jnt_vis, jnt_org.visibility)


####################################
# Disconnect dialog
####################################


class GameToolsDisconnectUI(QtWidgets.QDialog, gtUI.Ui_gameTools):

    """Game tools UI layout"""

    def __init__(self, parent=None):
        super(GameToolsDisconnectUI, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(GameToolsDisconnectUI, self).keyPressEvent(event)


class GameToolsDisconnect(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    """Game Tools UI

    Attributes:
        gt_layout (object): Ui Layout

    """

    def __init__(self, parent=None):
        self.toolName = "shifterGameTools"
        super(self.__class__, self).__init__(parent=parent)
        self.gtUIInst = GameToolsDisconnectUI()

        self.startDir = pm.workspace(q=True, rootDirectory=True)

        self.gameTools_window()
        self.gameTools_layout()
        self.createConnections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(GameToolsDisconnect, self).keyPressEvent(event)

    def gameTools_window(self):
        """Game tools window"""
        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Shifter Game Tools")
        self.resize(300, 330)

    def gameTools_layout(self):
        self.gt_layout = QtWidgets.QVBoxLayout()
        self.gt_layout.addWidget(self.gtUIInst)

        self.setLayout(self.gt_layout)

    # Slots
    @staticmethod
    def _validCharacters(lEdit):
        """Validate name charactes

        Args:
            lEdit (object): Qt line edit with name information
        """
        name = string.removeInvalidCharacter(lEdit.text())
        lEdit.setText(name)

    def populateRigTopNode(self):
        """Populate the rig top node information"""
        topNode = getRigTopNode()
        if topNode:
            self.gtUIInst.rigNode_lineEdit.setText(topNode)

    def populateMeshTopNode(self):
        """Populate the geometry top node information

        Returns:
            bool
        """
        if pm.selected():
            node = pm.selected()[0]
            self.gtUIInst.meshNode_lineEdit.setText(node.name())
        else:
            pm.displayWarning("Please select a Mesh top node!")
            return False

    def populateOutputFolder(self):
        """Populate output path folder

        Returns:
            None: None
        """
        filePath = pm.fileDialog2(
            fileMode=2,
            startingDirectory=self.startDir,
            fileFilter=" Shifter Game Assembly folder",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]
        self.gtUIInst.path_lineEdit.setText(filePath)

    def populateScript(self):
        """Populate custom script path

        Returns:
            None: None
        """
        filePath = pm.fileDialog2(
            fileMode=1,
            startingDirectory=self.startDir,
            fileFilter=" Post Script  .py (*%s)" % ".py",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]
        self.gtUIInst.script_lineEdit.setText(filePath)

    def disconnectExport(self):
        """Collect all the information and export the asset assembly"""
        name = self.gtUIInst.assetName_lineEdit.text()
        rigTopNode = self.gtUIInst.rigNode_lineEdit.text()
        meshTopNode = self.gtUIInst.meshNode_lineEdit.text()
        path = self.gtUIInst.path_lineEdit.text()
        postScript = self.gtUIInst.script_lineEdit.text()

        if name and rigTopNode and meshTopNode and path:
            exportAssetAssembly(
                name, rigTopNode, meshTopNode, path, postScript
            )
        else:
            pm.displayWarning(
                "Name, Rig Top Node, Mesh Top Node and path "
                "are mandatory fields. Please check it."
            )

    def importAssembly(self):
        """Import asset assembly"""
        createAssetAssembly(filePath=None, reference=False)

    def referenceAssembly(self):
        """References the asset assembly"""
        createAssetAssembly(filePath=None, reference=True)

    # Connect slots
    def createConnections(self):
        """Create slots connections"""
        self.gtUIInst.assetName_lineEdit.editingFinished.connect(
            partial(
                GameToolsDisconnect._validCharacters,
                self.gtUIInst.assetName_lineEdit,
            )
        )
        self.gtUIInst.rigNode_pushButton.clicked.connect(
            self.populateRigTopNode
        )
        self.gtUIInst.meshNode_pushButton.clicked.connect(
            self.populateMeshTopNode
        )
        self.gtUIInst.path_pushButton.clicked.connect(
            self.populateOutputFolder
        )
        self.gtUIInst.script_pushButton.clicked.connect(self.populateScript)
        self.gtUIInst.disconnectExport_pushButton.clicked.connect(
            self.disconnectExport
        )
        self.gtUIInst.importConnect_pushButton.clicked.connect(
            self.importAssembly
        )
        self.gtUIInst.referenceConnect_pushButton.clicked.connect(
            self.referenceAssembly
        )


def openGameToolsDisconnect(*args):
    """Open game tools window

    Args:
        *args: Dummy for Maya
    """
    pyqt.showDialog(GameToolsDisconnect)


if __name__ == "__main__":
    pyqt.showDialog(GameToolsDisconnect)
