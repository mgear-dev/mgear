"""
SoftTweak is a dynamic position tweak using softmod deformer
The credit of the idea goes to Vasil Shotarov, thanks!
http://bindpose.com/help-animators-fix-intersections-softmod-deformer/
"""

# TODO:
# add options for L  and R. By position and by name detection
# if the parent have name space, the tweak should have the same namespace
# maybe? controls grp inside another set and automatic if  shifter rig.
# Maybe check the parent of the root. if already member of a controllers group
# or subgroup

import json
import sys

import mgear.animbits.softTweakWindowUI as stUI
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.core import pyqt, attribute, icon, node, primitive, applyop, skin
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from mgear.pymaya import datatypes
from mgear.pymaya import versions
from maya import cmds

from mgear.core import string

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)

#########################################
# Soft Tweak
#########################################


ASSET_TAG = "_isAssetSoftTweak"
SHOT_TAG = "_isSoftTweak"

# CREATORS -------------------------------
# Create the controls for the softTweak


def _createSoftTweakControls(
    name, parent=None, t=datatypes.Matrix(), grps=None, size=0.5
):
    root_name = "{}_{}".format(name, "softTweak_root")
    namespace = None
    try:
        # simple check if exist a tweak with the same name
        exist = pm.PyNode(root_name)
        if exist:
            pm.displayError(
                "the tweak: {} already exist. Please use a "
                "unique name.".format(name)
            )
            return False, False
    except RuntimeError:
        if parent:
            try:
                p = pm.PyNode(parent)
                namespace = p.namespace()

            except RuntimeError:
                pm.displayWarning(
                    "{} is not a valid parent or doesn't "
                    "exist".format(parent)
                )
                p = None
        else:
            p = None
        root = primitive.addTransform(p, root_name, t)
        attribute.addAttribute(root, "iconSize", "float", size, keyable=False)

        baseCtl = icon.create(
            parent=root,
            name="{}_{}".format(name, "baseSoftTweak_ctl"),
            m=t,
            color=[1, 0.622, 0],
            icon="square",
            d=size,
            w=size,
        )
        tweakCtl = icon.create(
            parent=baseCtl,
            name="{}_{}".format(name, "softTweak_ctl"),
            m=t,
            color=[0.89, 0.0, 0.143],
            icon="diamond",
            w=size * 0.8,
        )
        attribute.addAttribute(tweakCtl, "falloff", "float", size)
        attribute.addAttribute(tweakCtl, "surfaceMode", "bool", False)

        if grps:
            if not isinstance(grps, list):
                grps = [grps]
            for grp in grps:
                try:
                    # try if exist
                    oGrp = pm.PyNode(grp)
                except RuntimeError:
                    # create a new grp if does't exist
                    if len(grp.split("_")) >= 3:  # check  name convention
                        name = grp
                    else:
                        name = "rig_{}_grp".format(grp)

                        # namespace basic handling
                        # NOTE: Doesn't support more than one namespace stacked
                        if namespace and len(name.split(":")) < 2:
                            name = namespace + name

                    oGrp = pm.sets(n=name, em=True)

                pm.sets(oGrp, add=[baseCtl, tweakCtl])
        if t:
            root.setMatrix(t, worldSpace=True)

        return baseCtl, tweakCtl


# Create a tweak using softMod deformer
# We have separated the softmode creationg so we can use any pre-existing ctl.


def _createSoftModTweak(
    baseCtl, tweakCtl, name, targets, nameExt="softMod", is_asset=False
):

    sm = pm.softMod(targets, wn=[tweakCtl, tweakCtl])
    pm.rename(sm[0], "{}_{}".format(name, nameExt))

    # disconnect default connection
    plugs = sm[0].softModXforms.listConnections(p=True)
    for p in plugs:
        pm.disconnectAttr(p, sm[0].softModXforms)
        pm.delete(p.node())

    dm_node = node.createDecomposeMatrixNode(baseCtl.worldMatrix[0])
    pm.connectAttr(dm_node.outputTranslate, sm[0].falloffCenter)
    mul_node = node.createMulNode(
        dm_node.outputScaleX, tweakCtl.attr("falloff")
    )
    pm.connectAttr(mul_node.outputX, sm[0].falloffRadius)
    pm.connectAttr(tweakCtl.attr("surfaceMode"), sm[0].falloffMode)
    mulMatrix_node = applyop.gear_mulmatrix_op(
        tweakCtl.worldMatrix[0], tweakCtl.parentInverseMatrix[0]
    )
    pm.connectAttr(mulMatrix_node.output, sm[0].weightedMatrix)
    pm.connectAttr(baseCtl.worldInverseMatrix[0], sm[0].postMatrix)
    pm.connectAttr(baseCtl.worldMatrix[0], sm[0].preMatrix)
    if is_asset:
        tag_name = ASSET_TAG
    else:
        tag_name = SHOT_TAG

    attribute.addAttribute(sm[0], tag_name, "bool", False, keyable=False)

    sm[0].addAttr("ctlRoot", at="message", m=False)
    sm[0].addAttr("ctlBase", at="message", m=False)
    sm[0].addAttr("ctlTweak", at="message", m=False)

    # fix issue with Maya 2022 and later for falloffAroundSelection
    if versions.current() >= 20220000:
        sm[0].falloffAroundSelection.set(0)

    pm.connectAttr(baseCtl.getParent().attr("message"), sm[0].attr("ctlRoot"))
    pm.connectAttr(baseCtl.attr("message"), sm[0].attr("ctlBase"))
    pm.connectAttr(tweakCtl.attr("message"), sm[0].attr("ctlTweak"))

    # This connection allow the softTweak to work if we apply the  skin
    # precision fix.
    # TODO: By default only apply to a non asset tweaks.
    if skin.getSkinCluster(targets[0]) and not is_asset:

        skin_cls = skin.getSkinCluster(targets[0])
        cnxs = skin_cls.matrix[0].listConnections()
        if (
            cnxs
            and cnxs[0].type() == "mgear_mulMatrix"
            and not sm[0].hasAttr("_fixedSkinFix")
        ):

            # tag the softmod as fixed
            attribute.addAttribute(sm[0], "_fixedSkinFix", "bool")

            # original connections
            matrix_cnx = sm[0].matrix.listConnections(p=True)[0]
            preMatrix_cnx = sm[0].preMatrix.listConnections(p=True)[0]
            wgtMatrix_cnx = sm[0].weightedMatrix.listConnections(p=True)[0]
            postMatrix_cnx = sm[0].postMatrix.listConnections(p=True)[0]

            # pre existing node operators
            mulMtx_node = wgtMatrix_cnx.node()
            dcMtx_node = sm[0].falloffCenter.listConnections(p=True)[0].node()

            # geo offset connnections
            geo_root = targets[0].getParent()
            gr_W = geo_root.worldMatrix[0]
            gr_WI = geo_root.worldInverseMatrix[0]

            # new offset operators
            mmm1 = applyop.gear_mulmatrix_op(preMatrix_cnx, gr_WI)
            mmm2 = applyop.gear_mulmatrix_op(matrix_cnx, gr_WI)
            mmm3 = applyop.gear_mulmatrix_op(gr_W, postMatrix_cnx)

            # re-wire connections
            pm.connectAttr(mmm1.output, dcMtx_node.inputMatrix, f=True)
            pm.connectAttr(mmm1.output, sm[0].preMatrix, f=True)

            pm.connectAttr(mmm2.output, sm[0].matrix, f=True)
            pm.connectAttr(mmm2.output, mulMtx_node.matrixA, f=True)

            pm.connectAttr(mmm3.output, mulMtx_node.matrixB, f=True)
            pm.connectAttr(mmm3.output, sm[0].postMatrix, f=True)

            _neutra_geomMatrix(sm[0])

    return sm[0]


#  Create softTweak and controls convenience function.
def createSoftTweak(
    name,
    targets=[],
    parent=None,
    t=None,
    grp=None,
    size=0.5,
    nameExt="softMod",
    is_asset=False,
):

    with pm.UndoChunk():
        if isinstance(targets, string_types):
            targets = pm.PyNode(targets)
        if not isinstance(targets, list):
            targets = [targets]
        if not targets:
            pm.displayWarning(
                "Can't find the targets to apply to "
                "softModTweak or Targets not selectedIndexes"
            )
            return False, False, False
        # namespace basic handling
        # NOTE: Doesn't support more than one namespace stacked
        if pm.ls(parent) and len(name.split(":")) < 2:
            name = pm.PyNode(parent).namespace() + name

        baseCtl, tweakCtl = _createSoftTweakControls(
            name, parent, t, grp, size
        )

        if baseCtl:
            softModNode = _createSoftModTweak(
                baseCtl, tweakCtl, name, targets, nameExt, is_asset
            )

            return softModNode, baseCtl, tweakCtl
        else:
            return False, False, False


# Create Auto SoftTweak
def createAutoSoftTweak(size=1.0, nameExt="softMod", is_asset=False):

    # get the object to apply
    if pm.selected() and len(pm.selected()) >= 2:
        oSel = [
            x
            for x in pm.selected()[:-1]
            if x.getShape().type() in ["mesh", "nurbsSurface"]
        ]
    else:
        pm.displayWarning(
            "Selection should be at less 2 object. The "
            " deformed object and the parent control"
        )
        return
    ctl_parent = pm.selected()[-1]
    grps = [s.name() for s in ctl_parent.listConnections(type="objectSet")]
    if ctl_parent.name().endswith("_ctl"):
        baseName = "_".join(ctl_parent.name().split("_")[:-1])
    else:
        baseName = ctl_parent.name()
    idName = 0
    while pm.ls("_".join([baseName, str(idName), "softTweak_ctl"])):
        idName += 1

    createSoftTweak(
        baseName + "_" + str(idName),
        targets=oSel,
        parent=ctl_parent,
        t=ctl_parent.getMatrix(worldSpace=True),
        grp=grps,
        size=size,
        nameExt=nameExt,
        is_asset=is_asset,
    )
    pm.select(oSel, r=True)


# EDIT -------------------------------
# get softMod affected objects
def _getAffectedObjects(softMods):
    affectedList = []
    if not isinstance(softMods, list):
        softMods = [softMods]
    for softMod in softMods:
        if isinstance(softMod, string_types):
            softMod = pm.PyNode(softMod)
        objs = [pm.PyNode(x).getParent().name() for x in softMod.getGeometry()]
        affectedList = affectedList + objs

    return affectedList


# get plugget object
def _getPluggetObj(softMods, plug):
    ctlRoots = []
    if not isinstance(softMods, list):
        softMods = [softMods]
    for softMod in softMods:
        if isinstance(softMod, string_types):
            softMod = pm.PyNode(softMod)
        ctlRoots.append(softMod.attr(plug).listConnections(p=True)[0].node())
    return ctlRoots


def _neutra_geomMatrix(softmod):
    # ensure the geomMatrix is neutral
    # this will fix the softTweak if it is apply in other position
    # that is not bindpose
    at = softmod.geomMatrix
    m = datatypes.Matrix()
    targets = _getAffectedObjects(softmod)
    for i in range(len(targets)):
        at.attr("geomMatrix[{}]".format(str(i))).set(m)


# add or remove obj from softmod
def _addRemoveSoftMode(softMods, targets=[], rm=True):
    if isinstance(softMods, string_types):
        softMods = pm.PyNode(softMods)
    if not isinstance(softMods, list):
        softMods = [softMods]

    if isinstance(targets, string_types):
        targets = pm.PyNode(targets)
    if not isinstance(targets, list):
        targets = [targets]

    for softMod in softMods:
        for t in targets:
            cmds.deformer(softMod.name(), rm=rm, e=True, g=t.name())
            # print("Added softtweak for: {}".format(t.name()))

        _neutra_geomMatrix(softMod)


# add to softmod
def addToSoftMod(softMods, targets=[]):
    _addRemoveSoftMode(softMods, targets)


# remove from soft mode


def removeSoftMod(softMods, targets=[]):
    _addRemoveSoftMode(softMods, targets, True)


# list soft modeTweaks in the scene


def _listSoftModTweaks(is_asset=False):
    if is_asset:
        tag_name = ASSET_TAG
    else:
        tag_name = SHOT_TAG
    return [sm for sm in pm.ls(type="softMod") if sm.hasAttr(tag_name)]


def order_softmods(target_objects, softmod_nodes):
    """
    Return a list of softmod deformers based on the order they are applied to the target_objects.

    Parameters:
    - target_objects (list of str): List of Maya object names.
    - softmod_nodes (list of str): List of softmod node names to be ordered.

    Returns:
    - list of str: Ordered list of softmod nodes based on their connection order.
    """
    final_ordered_list = []

    for target_object in target_objects:
        # Get the history of the current target object
        history_nodes = pm.listHistory(target_object)

        # Filter out only the softMod nodes from the history
        ordered_softmods = [
            node
            for node in history_nodes
            if pm.nodeType(node) == "softMod" and node.name() in softmod_nodes
        ]

        # Since the listHistory command returns nodes in reverse order of application,
        # reverse the list to get the correct order.
        ordered_softmods.reverse()

        # final_ordered_list shold only extend if the mod.name() is not in the list
        # also the entry that is repeted will be moved to the last position
        # TODO: this logic will fail if we add object to the softmod after creation
        for mod in ordered_softmods:
            mod_name = mod.name()
            if mod_name in final_ordered_list:
                final_ordered_list.remove(mod_name)
            final_ordered_list.append(mod_name)

        # final_ordered_list.extend([mod.name() for mod in ordered_softmods])

    return final_ordered_list


def _buildConfigDict(softMods=[]):
    """build the config dictionary softMod list

    Returns:
        dic: SoftMod tweaks configuration
    """
    configDict = {}

    # Softmods list
    alphabetic_softMods = [sm.name() for sm in softMods]
    affected_objects = []
    # loop over alphabetic_softMods and use _getAffectedObjects(sm) to get the affected objects. add the returned list items to affected_objects if are not already in the list
    for sm in alphabetic_softMods:
        objs = _getAffectedObjects(sm)
        for obj in objs:
            if obj not in affected_objects:
                affected_objects.append(obj)
    configDict["affected_objects"] = affected_objects

    deformation_order_softMods = order_softmods(
        affected_objects, alphabetic_softMods
    )

    configDict["softMods"] = deformation_order_softMods
    print(alphabetic_softMods)
    print(deformation_order_softMods)

    for sm in softMods:
        softModConfig = {}
        root = sm.ctlRoot.listConnections(p=True)[0].node()
        baseCtl = sm.ctlBase.listConnections(p=True)[0].node()
        ctl = sm.ctlTweak.listConnections(p=True)[0].node()

        # base name without the extension_softMod
        # softModConfig["name"] = sm.name().replace("_softMod", "")
        softModConfig["name"] = "_".join(sm.name().split("_")[:-1])
        # name extension
        softModConfig["nameExt"] = sm.name().split("_")[-1]
        # is asset
        softModConfig["isAsset"] = sm.hasAttr(ASSET_TAG)
        # fallof value
        softModConfig["falloff"] = ctl.falloff.get()
        # affected objects
        # print _getAffectedObjects(sm)
        softModConfig["affected"] = _getAffectedObjects(sm)
        # root parent
        if root.getParent():
            parentName = root.getParent().name()
        else:
            parentName = None
        softModConfig["rootParent"] = parentName
        # icons size
        softModConfig["iconSize"] = root.iconSize.get()
        # root matrix
        m = root.getMatrix(objectSpace=True)
        softModConfig["rootMatrix"] = m.get()
        # ctl base matrix
        m = baseCtl.getMatrix(objectSpace=True)
        softModConfig["baseCtlMatrix"] = m.get()
        # ctl matrix
        m = ctl.getMatrix(objectSpace=True)
        softModConfig["ctlMatrix"] = m.get()
        # grp name
        # oSet = root.grp.listConnections(p=True)
        oSet = ctl.instObjGroups.listConnections()
        if oSet:
            # grp = oSet[0].node().name()
            grp = [g.name() for g in oSet]
        else:
            grp = None
        softModConfig["grpName"] = grp

        configDict[sm.name()] = softModConfig

    return configDict


# EXPORTERS -------------------------------
# export configuration from a softMod tweaks list


def exportConfiguration(softMods, filePath=None):
    configDict = _buildConfigDict(softMods)
    data_string = json.dumps(configDict, indent=4, sort_keys=True)
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=0,
            fileFilter="SoftMod Tweaks configuration .smt (*%s)" % ".smt",
        )
    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    f = open(filePath, "w")
    f.write(data_string)
    f.close()


# IMPORTERS -------------------------------
# import softTweaker configuration


def _importConfiguration(configDict):
    with pm.UndoChunk():
        for sm in configDict["softMods"]:
            smConfig = configDict[sm]
            targets = []
            for t in smConfig["affected"]:
                try:
                    targets.append(pm.PyNode(t))
                except RuntimeError:
                    pm.displayWarning(
                        "{}: has not been found in the scene "
                        "and will be skipped".format(t)
                    )

            name = smConfig["name"]
            parent = smConfig["rootParent"]
            size = smConfig["iconSize"]
            grp = smConfig["grpName"]
            is_asset = smConfig["isAsset"]
            nameExt = smConfig["nameExt"]
            rootMatrix = datatypes.Matrix(smConfig["rootMatrix"])
            softModNode, baseCtl, tweakCtl = createSoftTweak(
                name,
                targets=targets,
                parent=parent,
                t=rootMatrix,
                grp=grp,
                size=size,
                nameExt=nameExt,
                is_asset=is_asset,
            )
            if softModNode:
                ctlBaseMatrix = datatypes.Matrix(smConfig["baseCtlMatrix"])
                ctlMatrix = datatypes.Matrix(smConfig["ctlMatrix"])
                baseCtl.setMatrix(ctlBaseMatrix, objectSpace=True)
                tweakCtl.setMatrix(ctlMatrix, objectSpace=True)
                tweakCtl.falloff.set(smConfig["falloff"])
                # we have to set the matrix again on the root because is stored
                # in local space
                baseCtl.getParent().setMatrix(rootMatrix, objectSpace=True)


# import softTweaker configuration from file


def importConfigurationFromFile(filePath=None):
    if not filePath:
        filePath = pm.fileDialog2(
            fileMode=1,
            fileFilter="SoftMod Tweaks configuration .smt (*%s)" % ".smt",
        )

    if not filePath:
        return
    if not isinstance(filePath, string_types):
        filePath = filePath[0]
    configDict = json.load(open(filePath))
    _importConfiguration(configDict)


####################################
# Soft tweaks Manager dialog
####################################


class softTweakManagerUI(QtWidgets.QMainWindow, stUI.Ui_MainWindow):
    def __init__(self, parent=None):
        super(softTweakManagerUI, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(softTweakManagerUI, self).keyPressEvent(event)


class softTweakManager(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        self.toolName = "softTweakManager"
        super(softTweakManager, self).__init__(parent)
        self.stUIInst = softTweakManagerUI()

        self.__proxyModel = QtCore.QSortFilterProxyModel(self)
        self.stUIInst.softTweak_listView.setModel(self.__proxyModel)

        self.setup_softTweakManagerrWindow()
        self.create_layout()
        self.create_connections()
        self._refreshList()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(softTweakManager, self).keyPressEvent(event)

    def setup_softTweakManagerrWindow(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Animbits: SoftTweak Manager")
        self.resize(400, 600)

    def create_layout(self):

        self.stm_layout = QtWidgets.QVBoxLayout()
        self.stm_layout.addWidget(self.stUIInst)

        self.setLayout(self.stm_layout)

    def setSourceModel(self, model):
        self.__proxyModel.setSourceModel(model)

    ####################
    # Helper functions
    ####################

    # export selected softTweaker configuration from selected on the list
    def _exportSelectedConfigurationFromList(self):
        softMods = None
        exportConfiguration(softMods)
        return

    # export all the softTweaks in the list
    def _exportAllFromList(self):
        softMods = None
        exportConfiguration(softMods)
        return

    def _refreshList(self):
        model = QtGui.QStandardItemModel(self)
        is_asset = self.stUIInst.isAsset_checkBox.isChecked()
        for t_node in _listSoftModTweaks(is_asset):
            model.appendRow(QtGui.QStandardItem(t_node.name()))
        self.setSourceModel(model)

    def _getSelectedListIndexes(self):
        softMods = []
        for x in self.stUIInst.softTweak_listView.selectedIndexes():
            try:
                softMods.append(pm.PyNode(x.data()))

            except RuntimeError:
                pm.displayWarning("{}  can't be find.".format(x.data()))
                return False
        return softMods

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):
        self.stUIInst.search_lineEdit.textChanged.connect(self.filterChanged)
        self.stUIInst.refresh_pushButton.clicked.connect(self.refreshList)
        self.stUIInst.addObjectToTweak_pushButton.clicked.connect(self.addObj)
        self.stUIInst.removeObjFromTweak_pushButton.clicked.connect(
            self.removeObj
        )
        self.stUIInst.auto_pushButton.clicked.connect(self.autoTweak)
        self.stUIInst.setParent_pushButton.clicked.connect(self.setTweakParent)
        self.stUIInst.setCtrlGrp_pushButton.clicked.connect(self.setCtlGrp)
        self.stUIInst.newTweak_pushButton.clicked.connect(self.newTweak)
        self.stUIInst.delete_pushButton.clicked.connect(self.deleteTweak)
        self.stUIInst.selectObjectsFromTweak_pushButton.clicked.connect(
            self.selectectAffected
        )
        self.stUIInst.selectCtlBase_pushButton.clicked.connect(
            self.selectBaseCtl
        )
        self.stUIInst.selectCtl_pushButton.clicked.connect(self.selectCtl)

        self.stUIInst.isAsset_checkBox.clicked.connect(self._refreshList)

        # actions
        self.stUIInst.exportSelected_action.triggered.connect(
            self.exportSelection
        )
        self.stUIInst.exportAll_action.triggered.connect(self.exportAll)
        self.stUIInst.import_action.triggered.connect(self.importConfiguration)

        # Misc
        self.stUIInst.name_lineEdit.textChanged.connect(self.name_text_changed)
        self.stUIInst.customExt_lineEdit.textChanged.connect(
            self.nameExt_text_changed
        )
        self.stUIInst.customExt_checkBox.toggled.connect(
            self.stUIInst.customExt_lineEdit.setEnabled
        )

    #############
    # SLOTS
    #############
    @staticmethod
    def _validate_name(name):
        # check and correct bad formating
        return string.removeInvalidCharacter(name)

    def name_text_changed(self):
        name = self._validate_name(self.stUIInst.name_lineEdit.text())
        self.stUIInst.name_lineEdit.setText(name)

    def nameExt_text_changed(self):
        name = self._validate_name(self.stUIInst.customExt_lineEdit.text())
        self.stUIInst.customExt_lineEdit.setText(name)

    def filterChanged(self, filter):
        regExp = QtCore.QRegExp(
            filter, QtCore.Qt.CaseSensitive, QtCore.QRegExp.Wildcard
        )
        self.__proxyModel.setFilterRegExp(regExp)

    # FILE MENU COMMANDS
    # export from list ui
    def exportSelection(self):
        softMods = self._getSelectedListIndexes()
        exportConfiguration(softMods)

    def exportAll(self):
        is_asset = self.stUIInst.isAsset_checkBox.isChecked()
        softMods = _listSoftModTweaks(is_asset)
        exportConfiguration(softMods)

    # import configuration
    def importConfiguration(self):
        # import the configuration
        importConfigurationFromFile()
        # refresh UI list
        self.refreshList()

    # UI BUTTONS
    # refresh the softTweakers list
    def refreshList(self):
        self._refreshList()

    def _addRemoveObj(self, rm=False):
        softMods = self._getSelectedListIndexes()
        _addRemoveSoftMode(softMods, pm.selected(), rm)

    def addObj(self):
        self._addRemoveObj()

    def removeObj(self):
        self._addRemoveObj(True)

    def _populate_object(self, lEdit, oType=True):
        if oType:
            testInstance = pm.nodetypes.Transform
        else:
            testInstance = pm.nodetypes.ObjectSet

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], testInstance):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning("The selected element is not a valid object")
        else:
            pm.displayWarning("Please select first the element to add.")

    def setCtlGrp(self):
        self._populate_object(self.stUIInst.ctlGrp_lineEdit, False)

    def setTweakParent(self):
        self._populate_object(self.stUIInst.parent_lineEdit)

    def _getIsAssetNameExtSize(self):
        size = self.stUIInst.size_doubleSpinBox.value()
        if self.stUIInst.customExt_checkBox.isChecked():
            nameExt = self.stUIInst.customExt_lineEdit.text()
        else:
            nameExt = "softMod"
        is_asset = self.stUIInst.isAsset_checkBox.isChecked()
        return is_asset, nameExt, size

    def autoTweak(self):
        is_asset, nameExt, size = self._getIsAssetNameExtSize()
        createAutoSoftTweak(size, nameExt, is_asset)
        self._refreshList()

    def newTweak(self):
        name = self.stUIInst.name_lineEdit.text()
        if not name:
            pm.displayWarning(
                "please define the name before create " "the softTweak."
            )
            return
        grp = self.stUIInst.ctlGrp_lineEdit.text()
        parent = self.stUIInst.parent_lineEdit.text()
        if parent:
            try:
                p = pm.PyNode(parent)
                trans = p.getMatrix(worldSpace=True)

            except RuntimeError:
                pm.displayWarning(
                    "{} is not a valid parent or doesn't "
                    "exist".format(parent)
                )
                return
        else:
            trans = datatypes.Matrix()
        try:
            oSel = [
                x
                for x in pm.selected()
                if x.getShape().type() in ["mesh", "nurbsSurface"]
            ]
        except RuntimeError:
            pm.displayError(
                "Some objects on the current selection are "
                "not valid. Please review the selection"
            )
            return

        is_asset, nameExt, size = self._getIsAssetNameExtSize()
        createSoftTweak(
            name,
            targets=oSel,
            parent=parent,
            t=trans,
            grp=grp,
            size=size,
            nameExt=nameExt,
            is_asset=is_asset,
        )
        self._refreshList()
        pm.select(oSel, r=True)

    # delete the selected tweaks and the relative controls
    # What happen if the controls have more child objects?
    # like tweaks under tweaks
    def deleteTweak(self):
        option = pm.confirmDialog(
            title="Delete Tweak,",
            message="Are you sure?",
            button=["Delete", "Cancel"],
            defaultButton="Delete",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if option == "Delete":
            softMods = self._getSelectedListIndexes()
            objs = _getPluggetObj(softMods, "ctlRoot")
            pm.delete(softMods)
            pm.delete(objs)
            self._refreshList()

    def selectectAffected(self):
        softMods = self._getSelectedListIndexes()
        aObj = _getAffectedObjects(softMods)
        pm.select(aObj, r=True)

    def selectBaseCtl(self):
        softMods = self._getSelectedListIndexes()
        objs = _getPluggetObj(softMods, "ctlBase")
        pm.select(objs, r=True)

    def selectCtl(self):
        softMods = self._getSelectedListIndexes()
        objs = _getPluggetObj(softMods, "ctlTweak")
        pm.select(objs, r=True)


def openSoftTweakManager(*args):
    pyqt.showDialog(softTweakManager, dockable=True)


if __name__ == "__main__":

    openSoftTweakManager()
