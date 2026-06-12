import random

import mgear.pymaya as pm
import maya.mel as mel
import maya.cmds as cmds
import maya.utils as utils
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.renderLayer as renderLayer
import maya.app.renderSetup.model.typeIDs as typeIDs
from maya.api import OpenMaya as om

from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from mgear.core import attribute, pyqt
from mgear.core import string, callbackManager
from mgear.crank import crank_ui

"""
TODO:

    layer lister:
        -Right click menu
            -Toggle ON/OFF
            -Solo
            -----------
            -Delete Selected Layer
            -----------
            -Add selected to layer
            -Remove selected from layer
            -----------
            -Turn Selected ON
            -Turn Selected OFF
            -----------
            -Turn All ON
            -Turn All OFF


"""

####################################
# Crank
####################################

CRANK_TAG = "_isCrankLayer"
CRANK_BS_TAG = "_isCrankLayerBS"
CRANK_RENDER_LAYER_NAME = "crankLayer_randomColor"
CHANNEL_BOX_NAME = "Crank_Box"

####################################
# Layer Node
####################################


def create_layer(oSel, foc=False, useExsitingBS=False):
    """Create new crank layer for shot sculpting

    Args:
        oSel (Mesh list): Objects to be included in the layer
        foc (bool, optional): Set the blendshape node in Front of the chain
        useExsitingBS (bool, optional): If true will try to use existing blendshape

    Returns:
        dagNode: cranklayer node with all the layer data
    """
    oSel = [
        x
        for x in oSel
        if x.getShapes() and x.getShapes()[0].type() in ["mesh", "nurbsCurve"]
    ]

    if oSel:
        result = pm.promptDialog(
            title="Crank Layer Name",
            message="Enter Name:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel",
            text="",
        )

        if result == "OK":
            text = pm.promptDialog(query=True, text=True)
            name = string.normalize(text)

            bs_list = create_blendshape_node(
                name, oSel, foc=foc, useExsitingBS=useExsitingBS
            )
            # avoid creating layer if there are not blendshapes
            if bs_list:
                layer_node = create_layer_node(name, oSel)
                for bs in bs_list:
                    layer_node.crank_layer_envelope >> bs.envelope
                    idx = attribute.get_next_available_index(
                        layer_node.layer_blendshape_node
                    )
                    pm.connectAttr(
                        bs.message, layer_node.layer_blendshape_node[idx]
                    )
                    if not useExsitingBS:
                        bs.isHistoricallyInteresting.set(False)
                pm.select(oSel)

                return layer_node


def create_blendshape_node(bsName, oSel, foc=False, useExsitingBS=False):
    """Create the blendshape node for each object in the layer

    Args:
        bsName (str): The name prefix for the blendshape node
        oSel (Mesh list): The object to apply the blendshape node
        foc (bool, optional): Set the blendshape node in Front of the chain
        useExsitingBS (bool, optional): If true will try to use existing blendshape

    Returns:
        PyNode: The blendshape node list
    """
    bs_list = []
    creation_abort = False
    for obj in oSel:
        if useExsitingBS:
            bs = None
            bs_hist = pm.listHistory(obj.getShape(), type="blendShape")
            for previous_bs in bs_hist:
                if not previous_bs.hasAttr(CRANK_BS_TAG):
                    bs = previous_bs
                    break
            if not bs:
                pm.displayWarning(
                    "Object: {} don't have any previous blendshape node to use or not managed by Crank. Layer creation aborted".format(
                        obj.name()
                    )
                )
                creation_abort = True

        else:
            bs = pm.blendShape(
                obj,
                name="_".join([obj.shortName(), bsName, "blendShape_crank"]),
                foc=foc,
            )[0]
            attribute.addAttribute(
                bs, CRANK_BS_TAG, "bool", False, keyable=False
            )
        if bs:
            # this attr will tag new bs nodes or existing bs nodes
            # as managed by crank
            bs_list.append(bs)

    # if any of the objects is missing a blendshape node we will abort
    # the layer creation
    # I do  the abort return here so we can get the complete print of warnings
    # for all the objects
    if creation_abort:
        return None
    else:
        return bs_list


def create_layer_node(name, affectedElements):
    """Create a transform node that contain the layer information.

    Args:
        name (str): layer name
        affectedElements (dagNode list): Elements affected by the layer.
                Only Mesh type is supported

    Returns:
        dagNode: layer node
    """

    fullName = name + "_crankLayer"

    # create node
    if pm.ls(fullName):
        pm.displayWarning("{} already exist".format(fullName))
        return
    layer_node = pm.createNode("transform", n=fullName, p=None, ss=True)
    attribute.lockAttribute(layer_node)
    # add attrs
    attribute.addAttribute(layer_node, CRANK_TAG, "bool", False, keyable=False)
    # this attribute will help to track the edit state to speed up the callback
    attribute.addAttribute(
        layer_node, "edit_state", "bool", False, keyable=False
    )
    # affected objects
    layer_node.addAttr("layer_objects", at="message", m=True)
    layer_node.addAttr("layer_blendshape_node", at="message", m=True)
    # master envelope for on/off
    attribute.addAttribute(
        layer_node,
        "crank_layer_envelope",
        "float",
        value=1,
        minValue=0,
        maxValue=1,
    )
    # create the post-blendshapes nodes for each affected object

    # connections
    for x in affectedElements:
        idx = attribute.get_next_available_index(layer_node.layer_objects)
        pm.connectAttr(x.message, layer_node.layer_objects[idx])

    return layer_node


def list_crank_layer_nodes():
    """Search the scene for crank layer nodes

    Returns:
        dagNode list: List of all the Crank layer nodes
    """
    return [
        sm
        for sm in cmds.ls(type="transform")
        if cmds.attributeQuery(CRANK_TAG, node=sm, exists=True)
    ]


def get_layer_affected_elements(layer_node):
    """From a given Crank layer nodes will return the affeted elements
    of the layers

    Args:
        layer_node (dagNode or list): The Crank Layer nodes

    Returns:
        set: The elements in the layer nodes
    """
    if not isinstance(layer_node, list):
        layer_node = [layer_node]
    members = []
    for lyr in layer_node:
        members = members + lyr.layer_objects.inputs()
    return set(members)


####################################
# random color layer visualization
####################################


def make_random_color_mtl(mtl_type="phong", seedStr="0", seedOffset=1):
    """Make randomColor material

    Args:
        mtl_type (str, optional): Material type i.e: "lambert", "phong"
        seedStr (str, optional): random seed
        seedOffset (int, optional): random seed offset

    Returns:
        pyNode: material node
    """
    randomColor = [0.0, 0.0, 0.0]
    for i in range(0, 3):
        random.seed(seedStr + str(seedOffset + i))
        randomColor[i] = random.random()

    mtl = pm.shadingNode(mtl_type, asShader=True)
    pm.setAttr(mtl.color, randomColor)
    return mtl


def make_random_color_rsl(geo_list, lyr_name, seed=0):
    """Make randomColor renderSetuplayer

    Args:
        geo_list (pyNode list): list of geometries affected by the layer
        lyr_name (str): Layer name
        seed (int, optional): Random Seed
    """
    try:
        pm.undoInfo(openChunk=True)

        rs = renderSetup.instance()
        rs.clearAll()
        mel.eval("MLdeleteUnused;")

        rl = rs.createRenderLayer(CRANK_RENDER_LAYER_NAME)
        for geo in geo_list:
            mtl = make_random_color_mtl(seedStr=str(geo), seedOffset=seed)
            clct = rl.createCollection("clct")
            clct.getSelector().setPattern(geo)
            shOv = clct.createOverride("shOv", typeIDs.shaderOverride)
            shOv.setShader(mtl)

        rs.switchToLayer(rl)
    finally:
        pm.undoInfo(closeChunk=True)


def get_all_rsl():
    """get all the render setup layers names

    Yields:
        str: the names of all the rsl layers
    """
    rs = renderSetup.instance()
    render_layers = rs.getRenderLayers()
    for x in render_layers:
        yield x.name()


def clear_all_rsl():
    """Clear all renderSetupLayers"""
    try:
        pm.undoInfo(openChunk=True)
        rs = renderSetup.instance()
        rs.clearAll()
        mel.eval("MLdeleteUnused;")
    finally:
        pm.undoInfo(closeChunk=True)


def clear_rsl_by_name(lyr_name):
    """Clear/Delete layer by name

    Args:
        lyr_name (str): Name of the layer to delete
    """
    try:
        pm.undoInfo(openChunk=True)
        rs = renderSetup.instance()
        layer_list = rs.getRenderLayers()
        for layer in layer_list:
            if not layer.name() == lyr_name:
                continue
            if layer.isVisible():
                rs.switchToLayer(rs.getDefaultRenderLayer())
            rs.detachRenderLayer(layer)
            renderLayer.delete(layer)
        mel.eval("MLdeleteUnused;")
    finally:
        pm.undoInfo(closeChunk=True)


def setEnabled_random_color_rsl(lyr_name, enabled=True):
    """switch randomColorRsl

    Args:
        lyr_name (str): Layer Name
        enabled (bool): If True will enable the layer
    """
    rs = renderSetup.instance()
    if enabled:
        for rl in rs.getRenderLayers():
            if rl.name() == lyr_name:
                rs.switchToLayer(rl)
                break
    else:
        rs.switchToLayer(rs.getDefaultRenderLayer())


####################################
# sculpt frame
####################################


def _add_frame_sculpt(layer_node, anim=False, keyf=[1, 0, 0, 1]):
    """Add a sculpt frame to each selected layer

    Args:
        layer_node (dagNode list):  list of Crank layer node to add the
            sculpt frame
        anim (bool, optional): if True, will keyframe the sculpt frame in the
        specified range.
        keyf (list, optional):  Keyframe range configuration. EaseIn, pre hold,
        post hold and ease out
    """

    objs = layer_node.layer_objects.inputs()
    bs_node = layer_node.layer_blendshape_node.inputs()

    # ensure other targets are set to false the edit flag

    # get current frame
    cframe = int(pm.currentTime(query=True))

    # get valid name. Check if frame is ducplicated in layer
    frame_name = "frame_{}".format(str(cframe))
    i = 1
    while layer_node.hasAttr(frame_name):
        frame_name = "frame_{}_v{}".format(str(cframe), str(i))
        i += 1
    # create frame master channel
    master_chn = attribute.addAttribute(
        layer_node, frame_name, "float", value=1, minValue=0, maxValue=1
    )

    # set edit state
    layer_node.edit_state.set(True)

    # keyframe in range the master channel
    if anim:
        # current frame
        pm.setKeyframe(
            master_chn,
            t=[cframe],
            v=1,
            inTangentType="linear",
            outTangentType="linear",
        )

        # pre and post hold
        pre_hold = keyf[1]
        if pre_hold:
            pm.setKeyframe(
                master_chn,
                t=[cframe - pre_hold],
                v=1,
                inTangentType="linear",
                outTangentType="linear",
            )

        post_hold = keyf[2]
        if post_hold:
            pm.setKeyframe(
                master_chn,
                t=[cframe + post_hold],
                v=1,
                inTangentType="linear",
                outTangentType="linear",
            )

        # ease in and out
        if keyf[0]:
            ei = pre_hold + keyf[0]
            pm.setKeyframe(
                master_chn,
                t=[cframe - ei],
                v=0,
                inTangentType="linear",
                outTangentType="linear",
            )
        if keyf[3]:
            eo = post_hold + keyf[3]
            pm.setKeyframe(
                master_chn,
                t=[cframe + eo],
                v=0,
                inTangentType="linear",
                outTangentType="linear",
            )

    for obj, bsn in zip(objs, bs_node):
        dup = pm.duplicate(obj)[0]
        bst_name = "_".join(
            [
                layer_node.stripNamespace(),
                obj.stripNamespace().split("|")[-1],
                frame_name,
            ]
        )
        pm.rename(dup, bst_name)
        indx = bsn.weight.getNumElements()
        pm.blendShape(
            bsn,
            edit=True,
            t=(obj, indx, dup, 1.0),
            ts=True,
            tc=True,
            w=(indx, 1),
        )
        pm.delete(dup)
        pm.blendShape(bsn, e=True, rtd=(0, indx))
        # is same as: bs.inputTarget[0].sculptTargetIndex.set(3)
        pm.sculptTarget(bsn, e=True, t=indx)

        # connect target to master channel
        pm.connectAttr(master_chn, bsn.attr(bst_name))


def edit_sculpt_frame():
    """Edit the sculpt frame selected in the channel box.
    Multiple layers can be edited at the same time.
    But Only one frame at the time!
    We only set editable the first selected channel/frame.

    Returns:
        bool: If the edit is set successful
    """
    if pm.channelBox(CHANNEL_BOX_NAME, exists=True) is True:
        attrs = pm.channelBox(CHANNEL_BOX_NAME, query=True, sma=True) or []
    else:
        attrs = attribute.getSelectedChannels()

    if attrs:
        # get the time from the channel name
        pm.currentTime(int(attrs[0].split(".")[-1].split("_")[1]))
        for x in pm.selected():
            # set edit state
            x.edit_state.set(True)
            if x.hasAttr(attrs[0]):
                _set_channel_edit_target(x.attr(attrs[0]), edit=True)
        return True

    else:
        pm.displayWarning("Not channels selected for edit!")
        return False


def edit_layer_off(layer_node):
    """set all targets of specific layer to edit off

    Args:
        layer_node (dagNode): the layer node
    """
    if layer_node.edit_state.get():
        uda = layer_node.listAttr(ud=True, k=True)
        for chn in uda:
            if not chn.name().endswith("envelope"):
                _set_channel_edit_target(chn, False)

        # set edit state
        layer_node.edit_state.set(False)


def _edit_all_off():
    """Set all crank layer edit off"""
    for lyr in list_crank_layer_nodes():
        edit_layer_off(pm.PyNode(lyr))


def _set_channel_edit_target(chn, edit=True):
    """Set the blendshape target of a channel editable or not editable

    Args:
        chn (PyNode): Attribute channel to edit
        edit (bool, optional): Set ON or OFF the channel edit status
    """
    attrs = chn.listConnections(d=True, s=False, p=True)
    for a in attrs:
        if edit:
            pm.sculptTarget(a.node(), e=True, t=a.index())
            pm.inViewMessage(
                amg="{}: Edit mode is ON".format(chn.name()),
                pos="midCenterBot",
                fade=True,
            )
        else:
            # a.node().inputTarget[a.index()].sculptTargetIndex.set(-1)
            pm.sculptTarget(a.node(), e=True, t=-1)
            pm.mel.eval("updateBlendShapeEditHUD;")
            pm.inViewMessage(
                amg="{}: Edit mode is OFF".format(chn.name()),
                pos="midCenterBot",
                fade=True,
            )


####################################
# Crank Box
####################################
def open_graph_editor():
    """
    Opens the Graph Editor if it is not already open.
    """
    # Check if the Graph Editor is open
    graph_editor = "graphEditor1Window"
    if not cmds.window(graph_editor, q=True, exists=True):
        # Use Mel command to open Graph Editor as a workaround
        mel.eval("GraphEditor;")


def get_layer_objects():
    mlc = cmds.channelBox(
        CHANNEL_BOX_NAME, query=True, mainListConnection=True
    )
    layer_objects = cmds.selectionConnection(mlc, object=True, query=True)

    return layer_objects


def get_selected_attrs_fullname():
    layer_objects = get_layer_objects()
    selected_channels = cmds.channelBox(
        CHANNEL_BOX_NAME, q=True, selectedMainAttributes=True
    )

    if layer_objects and selected_channels:
        # Build a list of the selected attributes (channels) on selected objects
        selected_attrs = [
            "{}.{}".format(obj, channel)
            for obj in layer_objects
            for channel in selected_channels
        ]
        return selected_attrs


def show_selected_channels_in_graph_editor():
    """
    Shows the selected channels from a specified channelBox in the Graph Editor.
    If the Graph Editor is not open, it opens it.
    """
    # Ensure the Graph Editor is open
    open_graph_editor()

    # Get and select objects to ensure their channels can be displayed
    layer_objects = get_layer_objects()
    cmds.select(layer_objects)

    # Get selected channels from the channel box
    selected_channels = cmds.channelBox(
        CHANNEL_BOX_NAME, q=True, selectedMainAttributes=True
    )

    if layer_objects and selected_channels:
        # Build a list of the selected attributes (channels) on selected objects
        selected_attrs = get_selected_attrs_fullname()

        # Use select command with replace flag to show only selected channels in the Graph Editor
        if selected_attrs:
            cmds.select(selected_attrs, r=True)
    else:
        print("No objects or channels selected.")


def set_key():
    """Keyframes the attribute at current frame"""
    cmds.setKeyframe(get_selected_attrs_fullname())


def set_key_val(val=1):
    for at in get_selected_attrs_fullname():
        cmds.setAttr(at, val)
    set_key()


def set_key_to_0():
    set_key_val(0)


def remove_key():
    """Remove the keyframe of an attribute at current frame"""
    pm.cutKey(get_selected_attrs_fullname(), clear=True, time=pm.currentTime())


def remove_animation():
    """Remove the animation of an attribute"""
    pm.cutKey(get_selected_attrs_fullname(), clear=True)


def crank_box_ui():
    # Create the window and layout
    form = pm.formLayout("form")
    crank_box = pm.channelBox(CHANNEL_BOX_NAME)
    pm.formLayout(
        form,
        e=True,
        af=[
            (crank_box, "top", 0),
            (crank_box, "left", 0),
            (crank_box, "right", 0),
            (crank_box, "bottom", 0),
        ],
    )

    # Attach a popup menu to the channel box
    cmds.popupMenu(parent=crank_box)
    call_set_key = "import mgear.crank.crank_tool as ct; ct.set_key()"
    cmds.menuItem(
        label="Keyframe",
        command=call_set_key,
        image=pyqt.get_icon_path("mgear_key.svg"),
    )
    call_set_key_val = "import mgear.crank.crank_tool as ct; ct.set_key_val()"
    cmds.menuItem(
        label="Keyframe to 1",
        command=call_set_key_val,
        image=pyqt.get_icon_path("mgear_key.svg"),
    )
    call_set_key_to_0 = (
        "import mgear.crank.crank_tool as ct; ct.set_key_to_0()"
    )
    cmds.menuItem(
        label="Keyframe to 0",
        command=call_set_key_to_0,
        image=pyqt.get_icon_path("mgear_key.svg"),
    )
    cmds.menuItem(divider=True)
    call_remove_key = "import mgear.crank.crank_tool as ct; ct.remove_key()"
    cmds.menuItem(
        label="Delete Keyframe",
        command=call_remove_key,
        image=pyqt.get_icon_path("mgear_minus-square.svg"),
    )
    cmds.menuItem(divider=True)
    call_show_selected_channels_in_graph_editor = "import mgear.crank.crank_tool as ct; ct.show_selected_channels_in_graph_editor()"
    cmds.menuItem(
        label="Open GraphEditor",
        command=call_show_selected_channels_in_graph_editor,
        image=pyqt.get_icon_path("mgear_activity.svg"),
    )
    cmds.menuItem(divider=True)
    call_remove_animation = (
        "import mgear.crank.crank_tool as ct; ct.remove_animation()"
    )
    cmds.menuItem(
        label="Delete Animation",
        command=call_remove_animation,
        image=pyqt.get_icon_path("mgear_trash-2.svg"),
    )

    # Connect the layer to the channel box
    pm.selectionConnection("crank_holder", object=pm.selected()[0])
    pm.channelBox(
        crank_box,
        edit=True,
        mainListConnection="crank_holder",
        st=True,
    )


def crank_box(crank_layer):
    if crank_layer:
        # Position of the cursor
        # point = QtGui.QCursor.pos().toTuple()
        # update_pos = True
        try:
            pm.deleteUI("crank_holder")
            pm.deleteUI(CHANNEL_BOX_NAME)
            # update_pos = False
        except:
            pass

    dock_control_name = CHANNEL_BOX_NAME + "_Dock"

    # Check if the dockControl exists already, delete if it does
    if cmds.workspaceControl(dock_control_name, exists=True):
        cmds.deleteUI(dock_control_name, control=True)

    # Create a new workspaceControl (dockable UI)
    call_crank_box = "import mgear.crank.crank_tool as ct; ct.crank_box_ui()"
    cmds.workspaceControl(
        dock_control_name,
        label="Crank Box",
        uiScript=call_crank_box,
        retain=False,
        floating=True,
    )


####################################
# Crank Tool UI
####################################


class crankUIW(QtWidgets.QDialog, crank_ui.Ui_Form):

    """UI Widget"""

    def __init__(self, parent=None):
        super(crankUIW, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(crankUIW, self).keyPressEvent(event)


class crankTool(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    """Crank shot sculpt main window"""

    valueChanged = QtCore.Signal(int)
    wi_to_destroy = []

    def __init__(self, parent=None):
        self.toolName = "Crank"
        super(crankTool, self).__init__(parent)

        self.cbm = None

        self.crankUIWInst = crankUIW()

        self.__proxyModel = QtCore.QSortFilterProxyModel(self)
        self.crankUIWInst.layers_listView.setModel(self.__proxyModel)

        self.setup_crankWindow()
        self.create_layout()
        self.create_connections()
        self._refreshList()

        self.eval_mode = self.get_evaluation_mode()

        # check if the eval model is DG , if is not the callback will be deactivated
        if self.check_evaluation_mode():
            self.time_change_cb()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def close(self):
        pm.displayInfo("Closing Crank")
        self.clear_random_color()
        self.edit_all_off()
        # callback cleaning
        if self.cbm:
            self.cbm.removeAllManagedCB()
        # set the previous state in the evaluation manager if it was parallel
        if self.eval_mode == "parallel":
            self.set_eval_to_parallel()
        self.deleteLater()

    def closeEvent(self, evnt):
        self.close()

    def dockCloseEventTriggered(self):
        self.close()

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(crankTool, self).keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Custom event filter."""
        if event.type() == QtCore.QEvent.Close:
            # Optionally do something before close
            # Return False to continue the event propagation
            return False
        # For other events, return super's eventFilter result
        return super(crankTool, self).eventFilter(obj, event)

    def setup_crankWindow(self):
        """Setup the window"""
        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Crank: Shot Sculpting")
        self.resize(266, 445)

    def create_layout(self):
        """Create the layout"""
        self.crank_layout = QtWidgets.QVBoxLayout()
        self.crank_layout.addWidget(self.crankUIWInst)
        self.crank_layout.setContentsMargins(3, 3, 3, 3)

        self.setLayout(self.crank_layout)

    def setSourceModel(self, model):
        """Set the source model for the listview

        Args:
            model (Qt model): QtCore.QSortFilterProxyModel
        """
        self.__proxyModel.setSourceModel(model)

    ###########################
    # Helper functions
    ###########################

    def _refreshList(self):
        """Refresh listview content"""
        model = QtGui.QStandardItemModel(self)
        for c_node in list_crank_layer_nodes():
            model.appendRow(QtGui.QStandardItem(c_node))
        self.setSourceModel(model)

    def _getSelectedListIndexes(self):
        """Get the selected layer index from the list view

        Returns:
            dagNode list: The selected layers list
        """
        layers = []
        for x in self.crankUIWInst.layers_listView.selectedIndexes():
            try:
                layers.append(pm.PyNode(x.data()))

            except pm.MayaNodeError:
                pm.displayWarning("{}  can't be find.".format(x.data()))
                return False
        return layers

    def select_layer_node(self):
        """Select the layer node from the list index"""
        layers = self._getSelectedListIndexes()
        pm.select(layers)

    def create_layer(self):
        """Create a new layer and update the window list"""
        foc = self.crankUIWInst.foc_checkBox.isChecked()
        useExistingBS = self.crankUIWInst.useExistingBS_checkBox.isChecked()
        create_layer(pm.selected(), foc=foc, useExsitingBS=useExistingBS)
        self._refreshList()

    def add_frame_sculpt(self):
        """Add a new fram sculpt"""
        anim = self.crankUIWInst.keyframe_checkBox.isChecked()
        ei = self.crankUIWInst.easeIn_spinBox.value()
        eo = self.crankUIWInst.easeOut_spinBox.value()
        pre = self.crankUIWInst.preHold_spinBox.value()
        pos = self.crankUIWInst.postHold_spinBox.value()
        for layer_node in self._getSelectedListIndexes():
            _add_frame_sculpt(layer_node, anim=anim, keyf=[ei, pre, pos, eo])

        self.select_members()

    def edit_frame_sculpt(self):
        """Edit fram sculpt"""
        self.select_layer_node()
        if edit_sculpt_frame():
            self.select_members()

    def edit_layer_off(self):
        """Turn off the layer edit status"""
        for layer_node in self._getSelectedListIndexes():
            edit_layer_off(layer_node)

    def edit_all_off(self, *args):
        """Turn off all the layers edit status"""

        # if om.MConditionMessage.getConditionState("playingBack"):
        #     return
        # else:
        print("Turn off Edit triggered")
        _edit_all_off()

    def get_evaluation_mode(self):
        """
        Checks the current evaluation mode in Autodesk Maya.

        Returns:
            str: The current evaluation mode, either 'off' or 'parallel'.
        """
        # Query the current evaluation mode
        mode = cmds.evaluationManager(query=True, mode=True)

        # The evaluationManager command returns a list of modes. The first
        # mode in the list is the current evaluation mode.
        current_mode = mode[0]

        return current_mode

    def set_eval_to_parallel(self, parallel=True):
        # Function to set evaluation mode to parallel or DG
        if parallel:
            eval_mode = "parallel"
        else:
            eval_mode = "off"

        def set_eval():
            cmds.evaluationManager(mode=eval_mode)

        # Use Maya's main thread to change evaluation mode
        pm.displayInfo("Parallel evaluation: {}".format(eval_mode))
        utils.executeInMainThreadWithResult(set_eval)
        # cmds.evaluationManager(mode="parallel")

    def check_evaluation_mode(self):
        """
        Checks the current evaluation mode. If it is in Parallel, prompts the
        user with a dialog to ask if they want to change to DG mode. If Yes,
        changes the evaluation mode to DG.
        """
        # Check current evaluation mode
        current_mode = self.get_evaluation_mode()

        # If in Parallel mode, prompt the user
        if current_mode == "parallel":
            # Define the dialog message
            message = (
                "The current evaluation mode is Parallel. \n"
                "For shot sculpting is recommended to use DG. \n"
                "Do you want to change it to DG?"
            )

            # Show confirmation dialog
            result = cmds.confirmDialog(
                title="Change Evaluation Mode",
                message=message,
                button=["Yes", "No"],
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )

            # If user chooses 'Yes', change to DG mode
            if result == "Yes":
                self.set_eval_to_parallel(False)
                pm.displayInfo("Evaluation mode changed to DG.")
                return True
            else:
                pm.displayInfo("Evaluation mode remains as Parallel.")
                return False

        return True

    ###########################
    # Callback
    ###########################
    def time_change_cb(self):
        self.cbm = callbackManager.CallbackManager()
        self.cbm.debug = False
        self.cbm.timeChangedCB("crankTimeChange_editOFF", self.edit_all_off)

    ###########################
    # "right click context menu for layers"
    ###########################

    def _layer_menu(self, QPos):
        """Create the layers rightclick menu

        Args:
            QPos (QPos): Position

        Returns:
            None: None
        """
        lyr_widget = self.crankUIWInst.layers_listView
        currentSelection = lyr_widget.selectedIndexes()
        if currentSelection is None:
            return
        self.lyr_menu = QtWidgets.QMenu()
        parentPosition = lyr_widget.mapToGlobal(QtCore.QPoint(0, 0))
        menu_item_00 = self.lyr_menu.addAction("Open Crank Box")
        self.lyr_menu.addSeparator()
        menu_item_01 = self.lyr_menu.addAction("Select Members")
        self.lyr_menu.addSeparator()
        menu_item_02 = self.lyr_menu.addAction("Selected Layer Edit OFF")
        menu_item_03 = self.lyr_menu.addAction("All Layers Edit OFF")
        self.lyr_menu.addSeparator()
        menu_item_04 = self.lyr_menu.addAction("Random Color + Isolate")
        menu_item_05 = self.lyr_menu.addAction("Clear Random Color")
        self.lyr_menu.addSeparator()

        menu_item_00.triggered.connect(self.open_crank_box)
        menu_item_01.triggered.connect(self.select_members)
        menu_item_02.triggered.connect(self.edit_layer_off)
        menu_item_03.triggered.connect(self.edit_all_off)
        menu_item_04.triggered.connect(self.random_color)
        menu_item_05.triggered.connect(self.clear_random_color)

        self.lyr_menu.move(parentPosition + QPos)
        self.lyr_menu.show()

    def open_crank_box(self):
        layers = self._getSelectedListIndexes()
        if layers:
            crank_box(layers[0])

    def select_members(self):
        """Select the members of a given layer"""
        layers = self._getSelectedListIndexes()
        pm.select(get_layer_affected_elements(layers))

    def random_color(self):
        """Create a random color render layer for each layer"""
        layers = self._getSelectedListIndexes()
        geo_list = get_layer_affected_elements(layers)
        make_random_color_rsl(geo_list, CRANK_RENDER_LAYER_NAME)

    def clear_random_color(self):
        """Clear random color layers of all layers"""
        clear_rsl_by_name(CRANK_RENDER_LAYER_NAME)

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):
        """Create connections"""
        self.crankUIWInst.search_lineEdit.textChanged.connect(
            self.filterChanged
        )
        self.crankUIWInst.refresh_pushButton.clicked.connect(self._refreshList)
        self.crankUIWInst.createLayer_pushButton.clicked.connect(
            self.create_layer
        )
        self.crankUIWInst.addFrame_pushButton.clicked.connect(
            self.add_frame_sculpt
        )
        self.crankUIWInst.editFrame_pushButton.clicked.connect(
            self.edit_frame_sculpt
        )

        self.crankUIWInst.editOFF_pushButton.clicked.connect(self.edit_all_off)

        # handle first time the item is selected
        selModel = self.crankUIWInst.layers_listView.selectionModel()
        selModel.selectionChanged.connect(self.select_layer_node)

        # handle if the item is already selected
        self.crankUIWInst.layers_listView.clicked.connect(self.onItemClicked)

        # connect menu
        self.crankUIWInst.layers_listView.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self.crankUIWInst.layers_listView.customContextMenuRequested.connect(
            self._layer_menu
        )

    #############
    # SLOTS
    #############
    def filterChanged(self, filter):
        """Filter out the elements in the list view"""
        regExp = QtCore.QRegExp(
            filter, QtCore.Qt.CaseSensitive, QtCore.QRegExp.Wildcard
        )
        self.__proxyModel.setFilterRegExp(regExp)

    def onItemClicked(self, index):
        """Handle clicks on items in the view.

        Args:
            index (QModelIndex): The index of the clicked item.
        """
        selModel = self.crankUIWInst.layers_listView.selectionModel()
        if selModel.isSelected(index):
            # The clicked item is already selected
            self.select_layer_node()


def openUI(*args):
    """Open the UI window

    Args:
        *args: Dummy
    """
    pyqt.showDialog(crankTool, dockable=True)


####################################


if __name__ == "__main__":

    openUI()
