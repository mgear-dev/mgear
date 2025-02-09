# Built-in
import datetime
import getpass
import imp
import inspect
import json
import os
import shutil
import subprocess
import sys
import traceback
from functools import partial

# pymel
import pymel.core as pm
from pymel.core import datatypes
from pymel import versions

# mgear
import mgear
from mgear.core import attribute, dag, vector, pyqt, skin, string, fcurve
from mgear.core import utils, curve
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from mgear.anim_picker.gui import MAYA_OVERRIDE_COLOR

from . import guide_ui as guui
from . import custom_step_ui as csui
from . import naming_rules_ui as naui
from . import naming

# pyside
from maya.app.general.mayaMixin import MayaQDockWidget
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

GUIDE_UI_WINDOW_NAME = "guide_UI_window"
GUIDE_DOCK_NAME = "Guide_Components"

TYPE = "mgear_guide_root"

# gnx is for Gear Nexus (Serialized connected data)
DATA_COLLECTOR_EXT = ".gnx"

MGEAR_SHIFTER_CUSTOMSTEP_KEY = "MGEAR_SHIFTER_CUSTOMSTEP_PATH"

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)


class Main(object):
    """The main guide class

    Provide the methods to add parameters, set parameter values,
    create property...

    Attributes:
        paramNames (list): List of parameter name cause it's actually important
        to keep them sorted.
        paramDefs (dict): Dictionary of parameter definition.
        values (dict): Dictionary of options values.
        valid (bool): We will check a few things and make sure the guide we are
            loading is up to date. If parameters or object are missing a
            warning message will be display and the guide should be updated.

    """

    def __init__(self):

        self.paramNames = []
        self.paramDefs = {}
        self.values = {}
        self.valid = True

    def addPropertyParamenters(self, parent):
        """Add attributes from the parameter definition list

        Arguments:
            parent (dagNode): The object to add the attributes.

        Returns:
            dagNode: parent with the attributes.

        """

        for scriptName in self.paramNames:
            paramDef = self.paramDefs[scriptName]
            paramDef.create(parent)

        return parent

    def setParamDefValue(self, scriptName, value):
        """Set the value of parameter with matching scriptname.

        Arguments:
            scriptName (str): Scriptname of the parameter to edit.
            value (variant): New value.

        Returns:
            bool: False if the parameter wasn't found.

        """

        if scriptName not in self.paramDefs.keys():
            mgear.log(
                "Can't find parameter definition for : " + scriptName,
                mgear.sev_warning,
            )
            return False

        self.paramDefs[scriptName].value = value
        self.values[scriptName] = value

        return True

    def setParamDefValuesFromDict(self, values_dict):
        for scriptName, paramDef in self.paramDefs.items():
            if scriptName not in values_dict:
                # Data is old, lacks parameter that current definition has.
                continue
            paramDef.value = values_dict[scriptName]
            self.values[scriptName] = values_dict[scriptName]

    def setParamDefValuesFromProperty(self, node):
        """Set the parameter definition values from the attributes of an object

        Arguments:
            node (dagNode): The object with the attributes.
        """

        for scriptName, paramDef in self.paramDefs.items():
            if not pm.attributeQuery(scriptName, node=node, exists=True):
                mgear.log(
                    "Can't find parameter '%s' in %s" % (scriptName, node),
                    mgear.sev_warning,
                )
                self.valid = False
            else:
                cnx = pm.listConnections(
                    node + "." + scriptName, destination=False, source=True
                )
                if isinstance(paramDef, attribute.FCurveParamDef):
                    paramDef.value = fcurve.getFCurveValues(
                        cnx[0], self.get_divisions()
                    )
                    self.values[scriptName] = paramDef.value
                elif cnx:
                    paramDef.value = None
                    self.values[scriptName] = cnx[0]
                else:
                    paramDef.value = pm.getAttr(node + "." + scriptName)
                    self.values[scriptName] = pm.getAttr(
                        node + "." + scriptName
                    )

    def addColorParam(self, scriptName, value=False):
        """Add color paramenter to the paramenter definition Dictionary.

        Arguments:
            scriptName (str): The name of the color parameter.
            value (Variant): The default color value.

        Returns:
            paramDef: The newly create paramenter definition.
        """

        paramDef = attribute.colorParamDef(scriptName, value)
        self.paramDefs[scriptName] = paramDef
        self.paramNames.append(scriptName)

        return paramDef

    def addParam(
        self,
        scriptName,
        valueType,
        value,
        minimum=None,
        maximum=None,
        keyable=False,
        readable=True,
        storable=True,
        writable=True,
        niceName=None,
        shortName=None,
    ):
        """Add paramenter to the paramenter definition Dictionary.

        Arguments:
            scriptName (str): Parameter scriptname.
            valueType (str): The Attribute Type. Exp: 'string', 'bool',
                'long', etc..
            value (float or int): Default parameter value.
            niceName (str): Parameter niceName.
            shortName (str): Parameter shortName.
            minimum (float or int): mininum value.
            maximum (float or int): maximum value.
            keyable (boo): If true is keyable
            readable (boo): If true is readable
            storable (boo): If true is storable
            writable (boo): If true is writable

        Returns:
            paramDef: The newly create paramenter definition.

        """
        paramDef = attribute.ParamDef2(
            scriptName,
            valueType,
            value,
            niceName,
            shortName,
            minimum,
            maximum,
            keyable,
            readable,
            storable,
            writable,
        )
        self.paramDefs[scriptName] = paramDef
        self.values[scriptName] = value
        self.paramNames.append(scriptName)

        return paramDef

    def addFCurveParam(self, scriptName, keys, interpolation=0):
        """Add FCurve paramenter to the paramenter definition Dictionary.

        Arguments:
            scriptName (str): Attribute fullName.
            keys (list): The keyframes to define the function curve.
            interpolation (int): the curve interpolation.

        Returns:
            paramDef: The newly create paramenter definition.

        """
        paramDef = attribute.FCurveParamDef(scriptName, keys, interpolation)
        self.paramDefs[scriptName] = paramDef
        self.values[scriptName] = None
        self.paramNames.append(scriptName)

        return paramDef

    def addEnumParam(self, scriptName, enum, value=False):
        """Add FCurve paramenter to the paramenter definition Dictionary.

        Arguments:
            scriptName (str): Attribute fullName
            enum (list of str): The list of elements in the enumerate control.
            value (int): The default value.

        Returns:
            paramDef: The newly create paramenter definition.

        """
        paramDef = attribute.enumParamDef(scriptName, enum, value)
        self.paramDefs[scriptName] = paramDef
        self.values[scriptName] = value
        self.paramNames.append(scriptName)

        return paramDef

    def get_param_values(self):
        param_values = {}
        for pn in self.paramNames:
            pd = self.paramDefs[pn].get_as_dict()
            param_values[pn] = pd["value"]

        return param_values


##########################################################
# RIG GUIDE
##########################################################


class Rig(Main):
    """Rig guide class.

    This is the class for complete rig guide definition.

        * It contains the component guide in correct hierarchy order and the
            options to generate the rig.
        * Provide the methods to add more component, import/export guide.

    Attributes:
        paramNames (list): List of parameter name cause it's actually important
            to keep them sorted.
        paramDefs (dict): Dictionary of parameter definition.
        values (dict): Dictionary of options values.
        valid (bool): We will check a few things and make sure the guide we are
            loading is up to date. If parameters or object are missing a
            warning message will be display and the guide should be updated.
        controllers (dict): Dictionary of controllers.
        components (dict): Dictionary of component. Keys are the component
            fullname (ie. 'arm_L0')
        componentsIndex (list): List of component name sorted by order
            creation (hierarchy order)
        parents (list): List of the parent of each component, in same order
            as self.components
    """

    def __init__(self):

        # Parameters names, definition and values.
        self.paramNames = []
        self.paramDefs = {}
        self.values = {}
        self.valid = True

        self.controllers = {}
        self.components = {}  # Keys are the component fullname (ie. 'arm_L0')
        self.componentsIndex = []
        self.parents = []

        self.guide_template_dict = {}  # guide template dict to export guides

        self.addParameters()

    def addParameters(self):
        """Parameters for rig options.

        Add more parameter to the parameter definition list.

        """
        # --------------------------------------------------
        # Main Tab
        self.pRigName = self.addParam("rig_name", "string", "rig")
        self.pMode = self.addEnumParam("mode", ["Final", "WIP"], 0)
        self.pStep = self.addEnumParam(
            "step",
            [
                "All Steps",
                "Objects",
                "Properties",
                "Operators",
                "Connect",
                "Joints",
                "Finalize",
            ],
            6,
        )
        self.pIsModel = self.addParam("ismodel", "bool", True)
        self.pClassicChannelNames = self.addParam(
            "classicChannelNames", "bool", False
        )
        self.pProxyChannels = self.addParam("proxyChannels", "bool", False)
        self.pAttributePrefixUseCompName = self.addParam(
            "attrPrefixName", "bool", False
        )
        self.pWorldCtl = self.addParam("worldCtl", "bool", False)
        self.pWorldCtl_name = self.addParam(
            "world_ctl_name", "string", "world_ctl"
        )

        if versions.current() >= 20220000:
            self.pGuideXRay = self.addParam("guide_x_ray", "bool", False)

        self.pGuideVis = self.addParam("guide_vis", "bool", True)
        self.pJointRadius = self.addParam(
            "joint_radius", "float", value=1.0, minimum=0
        )

        # --------------------------------------------------
        # skin
        self.pSkin = self.addParam("importSkin", "bool", False)
        self.pSkinPackPath = self.addParam("skin", "string", "")

        # --------------------------------------------------
        # data Collector
        self.pDataCollector = self.addParam("data_collector", "bool", False)
        self.pDataCollectorPath = self.addParam(
            "data_collector_path", "string", ""
        )
        self.pDataCollectorEmbedded = self.addParam(
            "data_collector_embedded", "bool", False
        )
        self.pDataCollectorEmbeddedCustomJoint = self.addParam(
            "data_collector_embedded_custom_joint", "string", ""
        )

        # --------------------------------------------------
        # Colors

        # Index color
        self.pLColorIndexfk = self.addParam("L_color_fk", "long", 6, 0, 31)
        self.pLColorIndexik = self.addParam("L_color_ik", "long", 18, 0, 31)
        self.pRColorIndexfk = self.addParam("R_color_fk", "long", 23, 0, 31)
        self.pRColorIndexik = self.addParam("R_color_ik", "long", 14, 0, 31)
        self.pCColorIndexfk = self.addParam("C_color_fk", "long", 13, 0, 31)
        self.pCColorIndexik = self.addParam("C_color_ik", "long", 17, 0, 31)

        # RGB colors for Maya 2015 and up
        self.pUseRGBColor = self.addParam("Use_RGB_Color", "bool", False)

        self.pLColorfk = self.addColorParam("L_RGB_fk", [0, 0, 1])
        self.pLColorik = self.addColorParam("L_RGB_ik", [0, 0.25, 1])
        self.pRColorfk = self.addColorParam("R_RGB_fk", [1, 0, 0])
        self.pRColorik = self.addColorParam("R_RGB_ik", [1, 0.1, 0.25])
        self.pCColorfk = self.addColorParam("C_RGB_fk", [1, 1, 0])
        self.pCColorik = self.addColorParam("C_RGB_ik", [0, 0.6, 0])

        # --------------------------------------------------
        # Settings
        self.pJointRig = self.addParam("joint_rig", "bool", True)
        self.pJointWorldOri = self.addParam("joint_worldOri", "bool", False)
        self.pJointRig = self.addParam("force_uniScale", "bool", True)
        self.pJointConnect = self.addParam("connect_joints", "bool", True)
        self.pJointSSC = self.addParam("force_SSC", "bool", False)
        self.pSynoptic = self.addParam("synoptic", "string", "")

        self.pDoPreCustomStep = self.addParam("doPreCustomStep", "bool", False)
        self.pDoPostCustomStep = self.addParam(
            "doPostCustomStep", "bool", False
        )
        self.pPreCustomStep = self.addParam("preCustomStep", "string", "")
        self.pPostCustomStep = self.addParam("postCustomStep", "string", "")

        # --------------------------------------------------
        # Comments
        self.pComments = self.addParam("comments", "string", "")
        self.pUser = self.addParam("user", "string", getpass.getuser())
        self.pDate = self.addParam(
            "date", "string", str(datetime.datetime.now())
        )
        self.pMayaVersion = self.addParam(
            "maya_version",
            "string",
            str(pm.mel.eval("getApplicationVersionAsFloat")),
        )
        self.pGearVersion = self.addParam(
            "gear_version", "string", mgear.getVersion()
        )

        # --------------------------------------------------
        # Naming rules
        self.p_ctl_name_rule = self.addParam(
            "ctl_name_rule", "string", naming.DEFAULT_NAMING_RULE
        )

        self.p_joint_name_rule = self.addParam(
            "joint_name_rule", "string", naming.DEFAULT_NAMING_RULE
        )

        self.p_side_left_name = self.addParam(
            "side_left_name", "string", naming.DEFAULT_SIDE_L_NAME
        )

        self.p_side_right_name = self.addParam(
            "side_right_name", "string", naming.DEFAULT_SIDE_R_NAME
        )

        self.p_side_center_name = self.addParam(
            "side_center_name", "string", naming.DEFAULT_SIDE_C_NAME
        )

        self.p_side_joint_left_name = self.addParam(
            "side_joint_left_name", "string", naming.DEFAULT_JOINT_SIDE_L_NAME
        )

        self.p_side_joint_right_name = self.addParam(
            "side_joint_right_name", "string", naming.DEFAULT_JOINT_SIDE_R_NAME
        )

        self.p_side_joint_center_name = self.addParam(
            "side_joint_center_name",
            "string",
            naming.DEFAULT_JOINT_SIDE_C_NAME,
        )

        self.p_ctl_name_ext = self.addParam(
            "ctl_name_ext", "string", naming.DEFAULT_CTL_EXT_NAME
        )
        self.p_joint_name_ext = self.addParam(
            "joint_name_ext", "string", naming.DEFAULT_JOINT_EXT_NAME
        )

        self.p_ctl_des_letter_case = self.addEnumParam(
            "ctl_description_letter_case",
            ["Default", "Upper Case", "Lower Case", "Capitalization"],
            0,
        )
        self.p_joint_des_letter_case = self.addEnumParam(
            "joint_description_letter_case",
            ["Default", "Upper Case", "Lower Case", "Capitalization"],
            0,
        )

        self.p_ctl_padding = self.addParam(
            "ctl_index_padding", "long", 0, 0, 99
        )
        self.p_joint_padding = self.addParam(
            "joint_index_padding", "long", 0, 0, 99
        )

    def setFromSelection(self):
        """Set the guide hierarchy from selection."""
        selection = pm.ls(selection=True)
        if not selection:
            selection = pm.ls("guide")
            if not selection:
                mgear.log(
                    "Not guide found or selected.\n"
                    + "Select one or more guide root or a guide model",
                    mgear.sev_error,
                )
                return
                self.valid = False
                return False

        for node in selection:
            self.setFromHierarchy(node, node.hasAttr("ismodel"))

        return True

    def setFromHierarchy(self, root, branch=True):
        """Set the guide from given hierarchy.

        Arguments:
            root (dagNode): The root of the hierarchy to parse.
            branch (bool): True to parse children components.

        """
        startTime = datetime.datetime.now()
        # Start
        mgear.log("Checking guide")

        # Get the model and the root
        self.model = root.getParent(generations=-1)
        while True:
            if root.hasAttr("comp_type") or self.model == root:
                break
            root = root.getParent()
            mgear.log(root)

        # ---------------------------------------------------
        # First check and set the options
        mgear.log("Get options")
        self.setParamDefValuesFromProperty(self.model)

        # ---------------------------------------------------
        # Get the controllers
        mgear.log("Get controllers")
        self.controllers_org = dag.findChild(self.model, "controllers_org")
        if self.controllers_org:
            for child in self.controllers_org.getChildren():
                self.controllers[child.name().split("|")[-1]] = child

        # ---------------------------------------------------
        # Components
        mgear.log("Get components")
        self.findComponentRecursive(root, branch)
        endTime = datetime.datetime.now()
        finalTime = endTime - startTime
        mgear.log("Find recursive in  [ " + str(finalTime) + " ]")
        # Parenting
        if self.valid:
            for name in self.componentsIndex:
                mgear.log("Get parenting for: " + name)
                # TODO: In the future should use connections to retrive this
                # data
                # We try the fastes aproach, will fail if is not the top node
                try:
                    # search for his parent
                    compParent = self.components[name].root.getParent()
                    if compParent and compParent.hasAttr("isGearGuide"):

                        names = naming.get_component_and_relative_name(
                            compParent.name(long=None)
                        )
                        pName = names[0]
                        pLocal = names[1]
                        pComp = self.components[pName]
                        self.components[name].parentComponent = pComp
                        self.components[name].parentLocalName = pLocal
                # This will scan the hierachy in reverse. It is much slower
                except KeyError:
                    # search children and set him as parent
                    compParent = self.components[name]
                    # for localName, element in compParent.getObjects(
                    #         self.model, False).items():
                    # NOTE: getObjects3 is an experimental function
                    for localName, element in compParent.getObjects3(
                        self.model
                    ).items():
                        for name in self.componentsIndex:
                            compChild = self.components[name]
                            compChild_parent = compChild.root.getParent()
                            if (
                                element is not None
                                and element == compChild_parent
                            ):
                                compChild.parentComponent = compParent
                                compChild.parentLocalName = localName

            # More option values
            self.addOptionsValues()

        # End
        if not self.valid:
            mgear.log(
                "The guide doesn't seem to be up to date."
                "Check logged messages and update the guide.",
                mgear.sev_warning,
            )

        endTime = datetime.datetime.now()
        finalTime = endTime - startTime
        mgear.log("Guide loaded from hierarchy in  [ " + str(finalTime) + " ]")

    def set_from_dict(self, guide_template_dict):

        self.guide_template_dict = guide_template_dict

        r_dict = guide_template_dict["guide_root"]

        self.setParamDefValuesFromDict(r_dict["param_values"])

        components_dict = guide_template_dict["components_dict"]
        self.componentsIndex = guide_template_dict["components_list"]

        for comp in self.componentsIndex:

            c_dict = components_dict[comp]

            # WIP  Now need to set each component from dict.
            comp_type = c_dict["param_values"]["comp_type"]
            comp_guide = self.getComponentGuide(comp_type)
            if comp_guide:
                self.components[comp] = comp_guide
                comp_guide.set_from_dict(c_dict)

            pName = c_dict["parent_fullName"]
            if pName:
                pComp = self.components[pName]
                self.components[comp].parentComponent = pComp
                p_local_name = c_dict["parent_localName"]
                self.components[comp].parentLocalName = p_local_name

    def get_guide_template_dict(self, meta=None):
        """Get the guide temaplate configuration dictionary

        Args:
            meta (dict, optional): Arbitraty metadata dictionary. This can
            be use to store any custom information in a dictionary format.

        Returns:
            dict: guide configuration dictionary
        """
        # Guide Root
        root_dict = {}
        root_dict["tra"] = self.model.getMatrix(worldSpace=True).get()
        root_dict["name"] = self.model.shortName()
        root_dict["param_values"] = self.get_param_values()
        self.guide_template_dict["guide_root"] = root_dict

        # Components
        components_list = []
        components_dict = {}
        for comp in self.componentsIndex:
            comp_guide = self.components[comp]
            c_name = comp_guide.fullName
            components_list.append(c_name)
            c_dict = comp_guide.get_guide_template_dict()
            components_dict[c_name] = c_dict
            if c_dict["parent_fullName"]:
                pn = c_dict["parent_fullName"]
                components_dict[pn]["child_components"].append(c_name)

        self.guide_template_dict["components_list"] = components_list
        self.guide_template_dict["components_dict"] = components_dict

        # controls shape buffers
        co = pm.ls("controllers_org")
        # before only collected the exported components ctl buffers.
        # Now with the new naming rules will collect anything named
        # *_controlBuffer.
        # this way will include any control extracted. Not only from guides
        # components.
        # I.E: controls generated in customs steps
        if co and co[0] in self.model.listRelatives(children=True):
            ctl_buffers = co[0].listRelatives(children=True)
            exp_ctl_buffers = []
            for cb in ctl_buffers:
                if cb.name().endswith("_controlBuffer"):
                    exp_ctl_buffers.append(cb)
            ctl_buffers_dict = curve.collect_curve_data(objs=exp_ctl_buffers)
            self.guide_template_dict["ctl_buffers_dict"] = ctl_buffers_dict

        else:
            pm.displayWarning(
                "Can't find controllers_org in order to retrieve"
                " the controls shapes buffer"
            )
            self.guide_template_dict["ctl_buffers_dict"] = None

        # Add metadata
        self.guide_template_dict["meta"] = meta

        return self.guide_template_dict

    def addOptionsValues(self):
        """Gather or change some options values according to some others.

        Note:
            For the moment only gets the rig size to adapt size of object to
            the scale of the character

        """
        # Get rig size to adapt size of object to the scale of the character
        maximum = 1
        v = datatypes.Vector()
        for comp in self.components.values():
            for pos in comp.apos:
                d = vector.getDistance(v, pos)
                maximum = max(d, maximum)

        self.values["size"] = max(maximum * 0.05, 0.1)

    def findComponentRecursive(self, node, branch=True):
        """Finds components by recursive search.

        Arguments:
            node (dagNode): Object frome where start the search.
            branch (bool): If True search recursive all the children.
        """

        if node.hasAttr("comp_type"):
            comp_type = node.getAttr("comp_type")
            comp_guide = self.getComponentGuide(comp_type)

            if comp_guide:
                comp_guide.setFromHierarchy(node)
                mgear.log(comp_guide.fullName + " (" + comp_type + ")")
                if not comp_guide.valid:
                    self.valid = False

                self.componentsIndex.append(comp_guide.fullName)
                self.components[comp_guide.fullName] = comp_guide

        if branch:
            for child in node.getChildren(type="transform"):
                self.findComponentRecursive(child)

    def getComponentGuide(self, comp_type):
        """Get the componet guide python object

        ie. Finds the guide.py of the component.

        Arguments:
            comp_type (str): The component type.

        Returns:
            The component guide instance class.
        """

        # Check component type
        """
        path = os.path.join(basepath, comp_type, "guide.py")
        if not os.path.exists(path):
            mgear.log("Can't find guide definition for : " + comp_type + ".\n"+
                path, mgear.sev_error)
            return False
        """

        # Import module and get class
        import mgear.shifter as shifter

        module = shifter.importComponentGuide(comp_type)

        ComponentGuide = getattr(module, "Guide")

        return ComponentGuide()

    # =====================================================
    # DRAW

    def initialHierarchy(self):
        """Create the initial rig guide hierarchy (model, options...)"""
        self.model = pm.group(n="guide", em=True, w=True)

        # Options
        self.options = self.addPropertyParamenters(self.model)

        # the basic org nulls (Maya groups)
        self.controllers_org = pm.group(
            n="controllers_org", em=True, p=self.model
        )
        self.controllers_org.attr("visibility").set(0)

    def drawNewComponent(self, parent, comp_type, showUI=True):
        """Add a new component to the guide.

        Arguments:
            parent (dagNode): Parent of this new component guide.
            compType (str): Type of component to add.

        """
        comp_guide = self.getComponentGuide(comp_type)

        if not comp_guide:
            mgear.log(
                "Not component guide of type: "
                + comp_type
                + " have been found.",
                mgear.sev_error,
            )
            return
        if parent is None:
            self.initialHierarchy()
            parent = self.model
        else:
            parent_root = parent
            while True:
                if parent_root.hasAttr("ismodel"):
                    break

                if parent_root.hasAttr("comp_type"):
                    parent_type = parent_root.attr("comp_type").get()
                    parent_side = parent_root.attr("comp_side").get()
                    parent_uihost = parent_root.attr("ui_host").get()
                    parent_ctlGrp = parent_root.attr("ctlGrp").get()

                    if parent_type in comp_guide.connectors:
                        comp_guide.setParamDefValue("connector", parent_type)

                    comp_guide.setParamDefValue("comp_side", parent_side)
                    comp_guide.setParamDefValue("ui_host", parent_uihost)
                    comp_guide.setParamDefValue("ctlGrp", parent_ctlGrp)

                    break

                parent_root = parent_root.getParent()

        comp_guide.drawFromUI(parent, showUI)

    def drawUpdate(self, oldRoot, parent=None):

        # Initial hierarchy
        if parent is None:
            self.initialHierarchy()
            parent = self.model
            newParentName = parent.name()

        # controls shape
        try:
            pm.delete(pm.PyNode(newParentName + "|controllers_org"))
            oldRootName = oldRoot.name().split("|")[0] + "|controllers_org"
            pm.parent(oldRootName, newParentName)
        except TypeError:
            pm.displayError("The guide don't have controllers_org")

        # Components
        for name in self.componentsIndex:
            comp_guide = self.components[name]
            oldParentName = comp_guide.root.getParent().name()

            try:
                parent = pm.PyNode(
                    oldParentName.replace(
                        oldParentName.split("|")[0], newParentName
                    )
                )
            except TypeError:
                pm.displayWarning("No parent for the guide")
                parent = self.model

            comp_guide.draw(parent)

    @utils.timeFunc
    def draw_guide(self, partial=None, initParent=None):
        """Draw a new guide from  the guide object.
        Usually the information of the guide have been set from a configuration
        Dictionary

        Args:
            partial (str or list of str, optional): If Partial starting
                component is defined, will try to add the guide to a selected
                guide part of an existing guide.
            initParent (dagNode, optional): Initial parent. If None, will
                create a new initial heirarchy

        Example:
            shifter.log_window()
            rig = shifter.Rig()
            rig.guide.set_from_dict(conf_dict)
            # draw complete guide
            rig.guide.draw_guide()
            # add to existing guide
            # rig.guide.draw_guide(None, pm.selected()[0])
            # draw partial guide
            # rig.guide.draw_guide(["arm_R0", "leg_L0"])
            # draw partial guide adding to existing guide
            # rig.guide.draw_guide(["arm_R0", "leg_L0"], pm.selected()[0])

        Returns:
            TYPE: Description
        """
        partial_components = None
        partial_components_idx = []
        parent = None

        if partial:
            if not isinstance(partial, list):
                partial = [partial]  # track the original partial components
            # clone list track all child partial
            partial_components = list(partial)

        if initParent:
            if initParent and initParent.getParent(-1).hasAttr("ismodel"):
                self.model = initParent.getParent(-1)
            else:
                pm.displayWarning(
                    "Current initial parent is not part of "
                    "a valid Shifter guide element"
                )
                return
        else:
            self.initialHierarchy()

        # Components
        pm.progressWindow(
            title="Drawing Guide Components",
            progress=0,
            max=len(self.components),
        )
        for name in self.componentsIndex:
            pm.progressWindow(e=True, step=1, status="\nDrawing: %s" % name)
            comp_guide = self.components[name]

            if comp_guide.parentComponent:
                try:
                    parent = pm.PyNode(
                        comp_guide.parentComponent.getName(
                            comp_guide.parentLocalName
                        )
                    )
                except pm.MayaNodeError:
                    # if we have a name clashing in the scene, it will try for
                    # find the parent by crawling the hierarchy. This will take
                    # longer time.
                    parent = dag.findChild(
                        self.model,
                        comp_guide.parentComponent.getName(
                            comp_guide.parentLocalName
                        ),
                    )
            else:
                parent = None

            if not parent and initParent:
                parent = initParent
            elif not parent:
                parent = self.model

            # Partial build logic
            if partial and name in partial_components:
                for chd in comp_guide.child_components:
                    partial_components.append(chd)

                # need to reset the parent for partial build since will loop
                # the guide from the root and will set again the parent to None
                if name in partial and initParent:
                    # Check if component is in initial partial to reset the
                    # parent
                    parent = initParent
                elif name in partial and not initParent:
                    parent = self.model
                elif not parent and initParent:
                    parent = initParent

                comp_guide.draw(parent)

                partial_components_idx.append(comp_guide.values["comp_index"])

            if not partial:  # if not partial will build all the components
                comp_guide.draw(parent)

        pm.progressWindow(e=True, endProgress=True)

        return partial_components, partial_components_idx

    def update(self, sel, force=False):
        """Update the guide if a parameter is missing"""

        if pm.attributeQuery("ismodel", node=sel, ex=True):
            self.model = sel
        else:
            pm.displayWarning("select the top guide node")
            return

        name = self.model.name()
        self.setFromHierarchy(self.model, True)
        if self.valid and not force:
            pm.displayInfo("The Guide is updated")
            return

        pm.rename(self.model, name + "_old")
        deleteLater = self.model
        self.drawUpdate(deleteLater)
        pm.rename(self.model, name)
        pm.displayInfo("The guide %s have been updated" % name)
        pm.delete(deleteLater)

    def duplicate(self, root, symmetrize=False):
        """Duplicate the guide hierarchy

        Note:
            Indeed this method is not duplicating.
            What it is doing is parse the compoment guide,
            and creating an new one base on the current selection.

        Warning:
            Don't use the default Maya's duplicate tool to duplicate a
            Shifter's guide.


        Arguments:
            root (dagNode): The guide root to duplicate.
            symmetrize (bool): If True, duplicate symmetrical in X axis.
            The guide have to be "Left" or "Right".

        """
        if not pm.attributeQuery("comp_type", node=root, ex=True):
            mgear.log("Select a component root to duplicate", mgear.sev_error)
            return

        self.setFromHierarchy(root)
        for name in self.componentsIndex:
            comp_guide = self.components[name]
            if symmetrize:
                if not comp_guide.symmetrize():
                    return

        # Draw
        if pm.attributeQuery("ismodel", node=root, ex=True):
            self.draw()

        else:

            for name in self.componentsIndex:
                comp_guide = self.components[name]

                if comp_guide.parentComponent is None:
                    parent = comp_guide.root.getParent()
                    if symmetrize:
                        parent = dag.findChild(
                            self.model,
                            string.convertRLName(
                                comp_guide.root.getParent().name()
                            ),
                        )
                        if not parent:
                            parent = comp_guide.root.getParent()

                    else:
                        parent = comp_guide.root.getParent()

                else:
                    parent = dag.findChild(
                        self.model,
                        comp_guide.parentComponent.getName(
                            comp_guide.parentLocalName
                        ),
                    )
                    if not parent:
                        mgear.log(
                            "Unable to find parent (%s.%s) for guide %s"
                            % (
                                comp_guide.parentComponent.getFullName,
                                comp_guide.parentLocalName,
                                comp_guide.getFullName,
                            )
                        )
                        parent = self.model

                # Reset the root so we force the draw to duplicate
                comp_guide.root = None

                comp_guide.setIndex(self.model)

                comp_guide.draw(parent)

        pm.select(self.components[self.componentsIndex[0]].root)

    def updateProperties(self, root, newName, newSide, newIndex):
        """Update the Properties of the component.

        Arguments:
            root (dagNode): Root of the component.
            newName (str): New name of the component
            newSide (str): New side of the component
            newIndex (str): New index of the component
        """

        if not pm.attributeQuery("comp_type", node=root, ex=True):
            mgear.log("Select a root to edit properties", mgear.sev_error)
            return
        self.setFromHierarchy(root, False)
        name = "_".join(root.name().split("|")[-1].split("_")[:-1])
        comp_guide = self.components[name]
        comp_guide.rename(root, newName, newSide, newIndex)


class HelperSlots(object):
    def updateHostUI(self, lEdit, targetAttr):
        oType = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oType) and oSel[0].hasAttr("isGearGuide"):
                lEdit.setText(oSel[0].name())
                self.root.attr(targetAttr).set(lEdit.text())
            else:
                pm.displayWarning(
                    "The selected element is not a "
                    "valid object or not from a guide"
                )
        else:
            pm.displayWarning("Not guide element selected.")
            if lEdit.text():
                lEdit.clear()
                self.root.attr(targetAttr).set("")
                pm.displayWarning("The previous UI host has been " "cleared")

    def updateLineEdit(self, lEdit, targetAttr):
        name = string.removeInvalidCharacter(lEdit.text())
        lEdit.setText(name)
        self.root.attr(targetAttr).set(name)

    def updateLineEdit2(self, lEdit, targetAttr):
        # nomralize the text to be Maya naming compatible
        # replace invalid characters with "_"
        name = string.normalize2(lEdit.text())
        lEdit.setText(name)
        self.root.attr(targetAttr).set(name)

    def updateLineEditPath(self, lEdit, targetAttr):
        self.root.attr(targetAttr).set(lEdit.text())

    def updateNameRuleLineEdit(self, lEdit, targetAttr):
        # nomralize the text to be Maya naming compatible
        # replace invalid characters with "_"
        name = naming.normalize_name_rule(lEdit.text())
        lEdit.setText(name)
        self.root.attr(targetAttr).set(name)
        self.naming_rule_validator(lEdit)

    def naming_rule_validator(self, lEdit, log=True):
        Palette = QtGui.QPalette()
        if not naming.name_rule_validator(
            lEdit.text(), naming.NAMING_RULE_TOKENS, log=log
        ):

            Palette.setBrush(QtGui.QPalette.Text, self.redBrush)
        else:
            Palette.setBrush(QtGui.QPalette.Text, self.whiteDownBrush)
        lEdit.setPalette(Palette)

    def addItem2listWidget(self, listWidget, targetAttr=None):

        items = pm.selected()
        itemsList = [
            i.text() for i in listWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        # Quick clean the first empty item
        if itemsList and not itemsList[0]:
            listWidget.takeItem(0)

        for item in items:
            if len(item.name().split("|")) != 1:
                pm.displayWarning(
                    "Not valid obj: %s, name is not unique." % item.name()
                )
                continue

            if item.name() not in itemsList:
                if item.hasAttr("isGearGuide"):
                    listWidget.addItem(item.name())

                else:
                    pm.displayWarning(
                        "The object: %s, is not a valid"
                        " reference, Please select only guide componet"
                        " roots and guide locators." % item.name()
                    )
            else:
                pm.displayWarning(
                    "The object: %s, is already in the list." % item.name()
                )

        if targetAttr:
            self.updateListAttr(listWidget, targetAttr)

    def removeSelectedFromListWidget(self, listWidget, targetAttr=None):
        for item in listWidget.selectedItems():
            listWidget.takeItem(listWidget.row(item))
        if targetAttr:
            self.updateListAttr(listWidget, targetAttr)

    def moveFromListWidget2ListWidget(
        self,
        sourceListWidget,
        targetListWidget,
        targetAttrListWidget,
        targetAttr=None,
    ):
        # Quick clean the first empty item
        itemsList = [
            i.text()
            for i in targetAttrListWidget.findItems(
                "", QtCore.Qt.MatchContains
            )
        ]
        if itemsList and not itemsList[0]:
            targetAttrListWidget.takeItem(0)

        for item in sourceListWidget.selectedItems():
            targetListWidget.addItem(item.text())
            sourceListWidget.takeItem(sourceListWidget.row(item))

        if targetAttr:
            self.updateListAttr(targetAttrListWidget, targetAttr)

    def copyFromListWidget(
        self, sourceListWidget, targetListWidget, targetAttr=None
    ):
        targetListWidget.clear()
        itemsList = [
            i.text()
            for i in sourceListWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        for item in itemsList:
            targetListWidget.addItem(item)
        if targetAttr:
            self.updateListAttr(sourceListWidget, targetAttr)

    def updateListAttr(self, sourceListWidget, targetAttr):
        """Update the string attribute with values separated by commas"""
        newValue = ",".join(
            [
                i.text()
                for i in sourceListWidget.findItems(
                    "", QtCore.Qt.MatchContains
                )
            ]
        )
        self.root.attr(targetAttr).set(newValue)

    def updateComponentName(self):

        newName = self.mainSettingsTab.name_lineEdit.text()
        # remove invalid characters in the name and update
        # newName = string.removeInvalidCharacter(newName)
        print(newName)
        newName = string.normalize2(newName)
        print(newName)
        self.mainSettingsTab.name_lineEdit.setText(newName)
        sideSet = ["C", "L", "R"]
        sideIndex = self.mainSettingsTab.side_comboBox.currentIndex()
        newSide = sideSet[sideIndex]
        newIndex = self.mainSettingsTab.componentIndex_spinBox.value()
        guide = Rig()
        guide.updateProperties(self.root, newName, newSide, newIndex)
        pm.select(self.root, r=True)
        # sync index
        self.mainSettingsTab.componentIndex_spinBox.setValue(
            self.root.attr("comp_index").get()
        )

    def updateConnector(self, sourceWidget, itemsList, *args):
        self.root.attr("connector").set(itemsList[sourceWidget.currentIndex()])

    def populateCheck(self, targetWidget, sourceAttr, *args):
        if self.root.attr(sourceAttr).get():
            targetWidget.setCheckState(QtCore.Qt.Checked)
        else:
            targetWidget.setCheckState(QtCore.Qt.Unchecked)

    def updateCheck(self, sourceWidget, targetAttr, *args):
        self.root.attr(targetAttr).set(sourceWidget.isChecked())

    def updateSpinBox(self, sourceWidget, targetAttr, *args):
        self.root.attr(targetAttr).set(sourceWidget.value())
        return True

    def updateSlider(self, sourceWidget, targetAttr, *args):
        self.root.attr(targetAttr).set(float(sourceWidget.value()) / 100)

    def updateComboBox(self, sourceWidget, targetAttr, *args):
        self.root.attr(targetAttr).set(sourceWidget.currentIndex())

    def updateControlShape(self, sourceWidget, ctlList, targetAttr, *args):
        curIndx = sourceWidget.currentIndex()
        self.root.attr(targetAttr).set(ctlList[curIndx])

    def updateIndexColorWidgets(
        self, sourceWidget, targetAttr, colorWidget, *args
    ):
        self.updateSpinBox(sourceWidget, targetAttr)
        self.updateWidgetStyleSheet(
            colorWidget,
            (i / 255.0 for i in MAYA_OVERRIDE_COLOR[sourceWidget.value()]),
        )

    def updateRgbColorWidgets(self, buttonWidget, rgb, sliderWidget):
        self.updateWidgetStyleSheet(buttonWidget, rgb)
        sliderWidget.blockSignals(True)
        sliderWidget.setValue(sorted(rgb)[2] * 255)
        sliderWidget.blockSignals(False)

    def updateWidgetStyleSheet(self, sourceWidget, rgb):
        color = ", ".join(
            str(i * 255) for i in pm.colorManagementConvert(toDisplaySpace=rgb)
        )
        sourceWidget.setStyleSheet("* {background-color: rgb(" + color + ")}")

    def rgbSliderValueChanged(self, buttonWidget, targetAttr, value):
        rgb = self.root.attr(targetAttr).get()
        hsv_value = sorted(rgb)[2]
        if hsv_value:
            new_rgb = tuple(
                i / (hsv_value / 1.0) * (value / 255.0) for i in rgb
            )
        else:
            new_rgb = tuple(
                (
                    1.0 * (value / 255.0),
                    1.0 * (value / 255.0),
                    1.0 * (value / 255.0),
                )
            )
        self.updateWidgetStyleSheet(buttonWidget, new_rgb)
        self.root.attr(targetAttr).set(new_rgb)

    def rgbColorEditor(self, sourceWidget, targetAttr, sliderWidget, *args):
        pm.colorEditor(rgb=self.root.attr(targetAttr).get())
        if pm.colorEditor(query=True, result=True):
            rgb = pm.colorEditor(query=True, rgb=True)
            self.root.attr(targetAttr).set(rgb)
            self.updateRgbColorWidgets(sourceWidget, rgb, sliderWidget)

    def toggleRgbIndexWidgets(
        self, checkBox, idx_widgets, rgb_widgets, targetAttr, checked
    ):
        show_widgets, hide_widgets = (
            (rgb_widgets, idx_widgets)
            if checked
            else (idx_widgets, rgb_widgets)
        )
        for widget in show_widgets:
            widget.show()
        for widget in hide_widgets:
            widget.hide()
        self.updateCheck(checkBox, targetAttr)

    def setProfile(self):
        pm.select(self.root, r=True)
        pm.runtime.GraphEditor()

    def close_settings(self):
        self.close()
        pyqt.deleteInstances(self, MayaQDockWidget)

    def get_cs_file_fullpath(self, cs_data):
        filepath = cs_data.split("|")[-1][1:]
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            fullpath = os.path.join(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""), filepath
            )
        else:
            fullpath = filepath

        return fullpath

    def editFile(self, widgetList):
        for cs in widgetList.selectedItems():
            try:
                cs_data = cs.text()
                fullpath = self.get_cs_file_fullpath(cs_data)

                if fullpath:
                    if sys.platform.startswith("darwin"):
                        subprocess.call(("open", fullpath))
                    elif os.name == "nt":
                        os.startfile(fullpath)
                    elif os.name == "posix":
                        subprocess.call(("xdg-open", fullpath))
                else:
                    pm.displayWarning("Please select one item from the list")
            except Exception:
                pm.displayError("The step can't be find or does't exists")

    def format_info(self, data):
        data_parts = data.split("|")
        cs_name = data_parts[0]
        if cs_name.startswith("*"):
            cs_status = "Deactivated"
            cs_name = cs_name[1:]
        else:
            cs_status = "Active"

        cs_fullpath = self.get_cs_file_fullpath(data)
        if "_shared" in data:
            cs_shared_owner = self.shared_owner(cs_fullpath)
            cs_shared_status = "Shared"
        else:
            cs_shared_status = "Local"
            cs_shared_owner = "None"

        info = '<html><head/><body><p><span style=" font-weight:600;">\
        {0}</span></p><p>------------------</p><p><span style=" \
        font-weight:600;">Status</span>: {1}</p><p><span style=" \
        font-weight:600;">Shared Status:</span> {2}</p><p><span \
        style=" font-weight:600;">Shared Owner:</span> \
        {3}</p><p><span style=" font-weight:600;">Full Path</span>: \
        {4}</p></body></html>'.format(
            cs_name, cs_status, cs_shared_status, cs_shared_owner, cs_fullpath
        )
        return info

    def shared_owner(self, cs_fullpath):

        scan_dir = os.path.abspath(os.path.join(cs_fullpath, os.pardir))
        while not scan_dir.endswith("_shared"):
            scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
            # escape infinite loop
            if scan_dir == "/":
                break
        scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
        return os.path.split(scan_dir)[1]

    @classmethod
    def get_steps_dict(self, itemsList):
        stepsDict = {}
        stepsDict["itemsList"] = itemsList
        for item in itemsList:
            step = open(item, "r")
            data = step.read()
            stepsDict[item] = data
            step.close()

        return stepsDict

    @classmethod
    def runStep(self, stepPath, customStepDic):
        try:
            with pm.UndoChunk():
                pm.displayInfo("EXEC: Executing custom step: %s" % stepPath)
                # use forward slash for OS compatibility
                if sys.platform.startswith("darwin"):
                    stepPath = stepPath.replace("\\", "/")

                fileName = os.path.split(stepPath)[1].split(".")[0]

                if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                    runPath = os.path.join(
                        os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""),
                        stepPath,
                    )
                else:
                    runPath = stepPath

                customStep = imp.load_source(fileName, runPath)
                if hasattr(customStep, "CustomShifterStep"):
                    argspec = inspect.getargspec(
                        customStep.CustomShifterStep.__init__
                    )
                    if "stored_dict" in argspec.args:
                        cs = customStep.CustomShifterStep(customStepDic)
                        cs.setup()
                        cs.run()
                    else:
                        cs = customStep.CustomShifterStep()
                        cs.run(customStepDic)
                    customStepDic[cs.name] = cs
                    pm.displayInfo(
                        "SUCCEED: Custom Shifter Step Class: %s. "
                        "Succeed!!" % stepPath
                    )
                else:
                    pm.displayInfo(
                        "SUCCEED: Custom Step simple script: %s. "
                        "Succeed!!" % stepPath
                    )

        except Exception as ex:
            template = "An exception of type {0} occurred. "
            "Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            pm.displayError(message)
            pm.displayError(traceback.format_exc())
            cont = pm.confirmBox(
                "FAIL: Custom Step Fail",
                "The step:%s has failed. Continue with next step?" % stepPath
                + "\n\n"
                + message
                + "\n\n"
                + traceback.format_exc(),
                "Continue",
                "Stop Build",
                "Try Again!",
            )
            if cont == "Stop Build":
                # stop Build
                return True
            elif cont == "Try Again!":
                try:  # just in case there is nothing to undo
                    pm.undo()
                except Exception:
                    pass
                pm.displayInfo("Trying again! : {}".format(stepPath))
                inception = self.runStep(stepPath, customStepDic)
                if inception:  # stops build from the recursion loop.
                    return True
            else:
                return False

    def runManualStep(self, widgetList):
        selItems = widgetList.selectedItems()
        for item in selItems:
            self.runStep(item.text().split("|")[-1][1:], customStepDic={})


class GuideSettingsTab(QtWidgets.QDialog, guui.Ui_Form):
    def __init__(self, parent=None):
        super(GuideSettingsTab, self).__init__(parent)
        self.setupUi(self)


class CustomStepTab(QtWidgets.QDialog, csui.Ui_Form):
    def __init__(self, parent=None):
        super(CustomStepTab, self).__init__(parent)
        self.setupUi(self)


class NamingRulesTab(QtWidgets.QDialog, naui.Ui_Form):
    def __init__(self, parent=None):
        super(NamingRulesTab, self).__init__(parent)
        self.setupUi(self)


class GuideSettings(MayaQWidgetDockableMixin, QtWidgets.QDialog, HelperSlots):
    greenBrush = QtGui.QColor(0, 160, 0)
    redBrush = QtGui.QColor(180, 0, 0)
    whiteBrush = QtGui.QColor(255, 255, 255)
    whiteDownBrush = QtGui.QColor(160, 160, 160)
    orangeBrush = QtGui.QColor(240, 160, 0)

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)
        # super(self.__class__, self).__init__(parent=parent)
        super(guideSettings, self).__init__()
        # the inspectSettings function set the current selection to the
        # component root before open the settings dialog
        self.root = pm.selected()[0]

        self.guideSettingsTab = guideSettingsTab()
        self.customStepTab = customStepTab()
        self.namingRulesTab = NamingRulesTab()

        self.setup_SettingWindow()
        self.create_controls()
        self.populate_controls()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        # hover info
        self.pre_cs = self.customStepTab.preCustomStep_listWidget
        self.pre_cs.setMouseTracking(True)
        self.pre_cs.entered.connect(self.pre_info)

        self.post_cs = self.customStepTab.postCustomStep_listWidget
        self.post_cs.setMouseTracking(True)
        self.post_cs.entered.connect(self.post_info)

    def pre_info(self, index):
        self.hover_info_item_entered(self.pre_cs, index)

    def post_info(self, index):
        self.hover_info_item_entered(self.post_cs, index)

    def hover_info_item_entered(self, view, index):
        if index.isValid():
            info_data = self.format_info(index.data())
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                info_data,
                view.viewport(),
                view.visualRect(index),
            )

    def setup_SettingWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(500, 615)

    def create_controls(self):
        """Create the controls for the component base"""
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("settings_tab")

        # Close Button
        self.close_button = QtWidgets.QPushButton("Close")

    def populate_controls(self):
        """Populate the controls values
        from the custom attributes of the component.

        """
        # populate tab
        self.tabs.insertTab(0, self.guideSettingsTab, "Guide Settings")
        self.tabs.insertTab(1, self.customStepTab, "Custom Steps")
        self.tabs.insertTab(2, self.namingRulesTab, "Naming Rules")

        # populate main settings
        self.guideSettingsTab.rigName_lineEdit.setText(
            self.root.attr("rig_name").get()
        )
        self.guideSettingsTab.mode_comboBox.setCurrentIndex(
            self.root.attr("mode").get()
        )
        self.guideSettingsTab.step_comboBox.setCurrentIndex(
            self.root.attr("step").get()
        )
        self.populateCheck(
            self.guideSettingsTab.proxyChannels_checkBox, "proxyChannels"
        )

        self.populateCheck(self.guideSettingsTab.worldCtl_checkBox, "worldCtl")
        self.guideSettingsTab.worldCtl_lineEdit.setText(
            self.root.attr("world_ctl_name").get()
        )

        self.populateCheck(
            self.guideSettingsTab.classicChannelNames_checkBox,
            "classicChannelNames",
        )
        self.populateCheck(
            self.guideSettingsTab.attrPrefix_checkBox, "attrPrefixName"
        )
        self.populateCheck(
            self.guideSettingsTab.importSkin_checkBox, "importSkin"
        )
        self.guideSettingsTab.skin_lineEdit.setText(
            self.root.attr("skin").get()
        )
        self.populateCheck(
            self.guideSettingsTab.dataCollector_checkBox, "data_collector"
        )
        self.guideSettingsTab.dataCollectorPath_lineEdit.setText(
            self.root.attr("data_collector_path").get()
        )
        self.populateCheck(
            self.guideSettingsTab.dataCollectorEmbbeded_checkBox,
            "data_collector_embedded",
        )
        self.guideSettingsTab.dataCollectorCustomJoint_lineEdit.setText(
            self.root.attr("data_collector_embedded_custom_joint").get()
        )
        self.populateCheck(
            self.guideSettingsTab.jointRig_checkBox, "joint_rig"
        )
        self.populateCheck(
            self.guideSettingsTab.jointWorldOri_checkBox, "joint_worldOri"
        )
        self.populateCheck(
            self.guideSettingsTab.force_uniScale_checkBox, "force_uniScale"
        )
        self.populateCheck(
            self.guideSettingsTab.connect_joints_checkBox, "connect_joints"
        )
        # self.populateCheck(
        #     self.guideSettingsTab.force_SSC_joints_checkBox, "force_SSC")
        self.populateAvailableSynopticTabs()

        for item in self.root.attr("synoptic").get().split(","):
            self.guideSettingsTab.rigTabs_listWidget.addItem(item)

        tap = self.guideSettingsTab

        index_widgets = (
            (tap.L_color_fk_spinBox, tap.L_color_fk_label, "L_color_fk"),
            (tap.L_color_ik_spinBox, tap.L_color_ik_label, "L_color_ik"),
            (tap.C_color_fk_spinBox, tap.C_color_fk_label, "C_color_fk"),
            (tap.C_color_ik_spinBox, tap.C_color_ik_label, "C_color_ik"),
            (tap.R_color_fk_spinBox, tap.R_color_fk_label, "R_color_fk"),
            (tap.R_color_ik_spinBox, tap.R_color_ik_label, "R_color_ik"),
        )

        rgb_widgets = (
            (tap.L_RGB_fk_pushButton, tap.L_RGB_fk_slider, "L_RGB_fk"),
            (tap.L_RGB_ik_pushButton, tap.L_RGB_ik_slider, "L_RGB_ik"),
            (tap.C_RGB_fk_pushButton, tap.C_RGB_fk_slider, "C_RGB_fk"),
            (tap.C_RGB_ik_pushButton, tap.C_RGB_ik_slider, "C_RGB_ik"),
            (tap.R_RGB_fk_pushButton, tap.R_RGB_fk_slider, "R_RGB_fk"),
            (tap.R_RGB_ik_pushButton, tap.R_RGB_ik_slider, "R_RGB_ik"),
        )

        for spinBox, label, source_attr in index_widgets:
            color_index = self.root.attr(source_attr).get()
            spinBox.setValue(color_index)
            self.updateWidgetStyleSheet(
                label, [i / 255.0 for i in MAYA_OVERRIDE_COLOR[color_index]]
            )

        for button, slider, source_attr in rgb_widgets:
            self.updateRgbColorWidgets(
                button, self.root.attr(source_attr).get(), slider
            )

        # forceing the size of the color buttons/label to keep ui clean
        for widget in tuple(i[0] for i in rgb_widgets) + tuple(
            i[1] for i in index_widgets
        ):
            widget.setFixedSize(pyqt.dpi_scale(30), pyqt.dpi_scale(20))

        self.populateCheck(tap.useRGB_checkBox, "Use_RGB_Color")
        self.toggleRgbIndexWidgets(
            tap.useRGB_checkBox,
            (w for i in index_widgets for w in i[:2]),
            (w for i in rgb_widgets for w in i[:2]),
            "Use_RGB_Color",
            tap.useRGB_checkBox.checkState(),
        )

        # pupulate custom steps sttings
        self.populateCheck(
            self.customStepTab.preCustomStep_checkBox, "doPreCustomStep"
        )
        for item in self.root.attr("preCustomStep").get().split(","):
            self.customStepTab.preCustomStep_listWidget.addItem(item)
        self.refreshStatusColor(self.customStepTab.preCustomStep_listWidget)

        self.populateCheck(
            self.customStepTab.postCustomStep_checkBox, "doPostCustomStep"
        )
        for item in self.root.attr("postCustomStep").get().split(","):
            self.customStepTab.postCustomStep_listWidget.addItem(item)
        self.refreshStatusColor(self.customStepTab.postCustomStep_listWidget)

        self.populate_naming_controls()

    def populate_naming_controls(self):
        # populate name settings
        self.namingRulesTab.ctl_name_rule_lineEdit.setText(
            self.root.attr("ctl_name_rule").get()
        )
        self.naming_rule_validator(self.namingRulesTab.ctl_name_rule_lineEdit)
        self.namingRulesTab.joint_name_rule_lineEdit.setText(
            self.root.attr("joint_name_rule").get()
        )
        self.naming_rule_validator(
            self.namingRulesTab.joint_name_rule_lineEdit
        )

        self.namingRulesTab.side_left_name_lineEdit.setText(
            self.root.attr("side_left_name").get()
        )
        self.namingRulesTab.side_right_name_lineEdit.setText(
            self.root.attr("side_right_name").get()
        )
        self.namingRulesTab.side_center_name_lineEdit.setText(
            self.root.attr("side_center_name").get()
        )

        self.namingRulesTab.side_joint_left_name_lineEdit.setText(
            self.root.attr("side_joint_left_name").get()
        )
        self.namingRulesTab.side_joint_right_name_lineEdit.setText(
            self.root.attr("side_joint_right_name").get()
        )
        self.namingRulesTab.side_joint_center_name_lineEdit.setText(
            self.root.attr("side_joint_center_name").get()
        )

        self.namingRulesTab.ctl_name_ext_lineEdit.setText(
            self.root.attr("ctl_name_ext").get()
        )
        self.namingRulesTab.joint_name_ext_lineEdit.setText(
            self.root.attr("joint_name_ext").get()
        )

        self.namingRulesTab.ctl_des_letter_case_comboBox.setCurrentIndex(
            self.root.attr("ctl_description_letter_case").get()
        )

        self.namingRulesTab.joint_des_letter_case_comboBox.setCurrentIndex(
            self.root.attr("joint_description_letter_case").get()
        )

        self.namingRulesTab.ctl_padding_spinBox.setValue(
            self.root.attr("ctl_index_padding").get()
        )
        self.namingRulesTab.joint_padding_spinBox.setValue(
            self.root.attr("joint_index_padding").get()
        )

    def create_layout(self):
        """
        Create the layout for the component base settings

        """
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_connections(self):
        """Create the slots connections to the controls functions"""
        self.close_button.clicked.connect(self.close_settings)

        # Setting Tab
        tap = self.guideSettingsTab
        tap.rigName_lineEdit.editingFinished.connect(
            partial(self.updateLineEdit, tap.rigName_lineEdit, "rig_name")
        )
        tap.mode_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, tap.mode_comboBox, "mode")
        )
        tap.step_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, tap.step_comboBox, "step")
        )
        tap.proxyChannels_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.proxyChannels_checkBox, "proxyChannels"
            )
        )
        tap.worldCtl_checkBox.stateChanged.connect(
            partial(self.updateCheck, tap.worldCtl_checkBox, "worldCtl")
        )
        tap.worldCtl_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2, tap.worldCtl_lineEdit, "world_ctl_name"
            )
        )
        tap.classicChannelNames_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                tap.classicChannelNames_checkBox,
                "classicChannelNames",
            )
        )
        tap.attrPrefix_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.attrPrefix_checkBox, "attrPrefixName"
            )
        )
        tap.dataCollector_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.dataCollector_checkBox, "data_collector"
            )
        )
        tap.dataCollectorPath_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEditPath,
                tap.dataCollectorPath_lineEdit,
                "data_collector_path",
            )
        )
        tap.dataCollectorEmbbeded_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                tap.dataCollectorEmbbeded_checkBox,
                "data_collector_embedded",
            )
        )
        tap.dataCollectorCustomJoint_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEditPath,
                tap.dataCollectorCustomJoint_lineEdit,
                "data_collector_embedded_custom_joint",
            )
        )
        tap.jointRig_checkBox.stateChanged.connect(
            partial(self.updateCheck, tap.jointRig_checkBox, "joint_rig")
        )
        tap.jointWorldOri_checkBox.stateChanged.connect(
            partial(self.updateCheck, tap.jointWorldOri_checkBox, "joint_worldOri")
        )
        tap.force_uniScale_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.force_uniScale_checkBox, "force_uniScale"
            )
        )
        tap.connect_joints_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.connect_joints_checkBox, "connect_joints"
            )
        )
        # tap.force_SSC_joints_checkBox.stateChanged.connect(
        #     partial(self.updateCheck,
        #             tap.force_SSC_joints_checkBox,
        #             "force_SSC"))
        tap.addTab_pushButton.clicked.connect(
            partial(
                self.moveFromListWidget2ListWidget,
                tap.available_listWidget,
                tap.rigTabs_listWidget,
                tap.rigTabs_listWidget,
                "synoptic",
            )
        )
        tap.removeTab_pushButton.clicked.connect(
            partial(
                self.moveFromListWidget2ListWidget,
                tap.rigTabs_listWidget,
                tap.available_listWidget,
                tap.rigTabs_listWidget,
                "synoptic",
            )
        )
        tap.importSkin_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, tap.importSkin_checkBox, "importSkin"
            )
        )
        tap.loadSkinPath_pushButton.clicked.connect(self.skinLoad)
        tap.dataCollectorPath_pushButton.clicked.connect(
            self.data_collector_path
        )
        tap.dataCollectorPathEmbbeded_pushButton.clicked.connect(
            self.data_collector_pathEmbbeded
        )
        tap.rigTabs_listWidget.installEventFilter(self)

        # colors connections
        index_widgets = (
            (tap.L_color_fk_spinBox, tap.L_color_fk_label, "L_color_fk"),
            (tap.L_color_ik_spinBox, tap.L_color_ik_label, "L_color_ik"),
            (tap.C_color_fk_spinBox, tap.C_color_fk_label, "C_color_fk"),
            (tap.C_color_ik_spinBox, tap.C_color_ik_label, "C_color_ik"),
            (tap.R_color_fk_spinBox, tap.R_color_fk_label, "R_color_fk"),
            (tap.R_color_ik_spinBox, tap.R_color_ik_label, "R_color_ik"),
        )

        rgb_widgets = (
            (tap.L_RGB_fk_pushButton, tap.L_RGB_fk_slider, "L_RGB_fk"),
            (tap.L_RGB_ik_pushButton, tap.L_RGB_ik_slider, "L_RGB_ik"),
            (tap.C_RGB_fk_pushButton, tap.C_RGB_fk_slider, "C_RGB_fk"),
            (tap.C_RGB_ik_pushButton, tap.C_RGB_ik_slider, "C_RGB_ik"),
            (tap.R_RGB_fk_pushButton, tap.R_RGB_fk_slider, "R_RGB_fk"),
            (tap.R_RGB_ik_pushButton, tap.R_RGB_ik_slider, "R_RGB_ik"),
        )

        for spinBox, label, source_attr in index_widgets:
            spinBox.valueChanged.connect(
                partial(
                    self.updateIndexColorWidgets, spinBox, source_attr, label
                )
            )

        for button, slider, source_attr in rgb_widgets:
            button.clicked.connect(
                partial(self.rgbColorEditor, button, source_attr, slider)
            )
            slider.valueChanged.connect(
                partial(self.rgbSliderValueChanged, button, source_attr)
            )

        tap.useRGB_checkBox.stateChanged.connect(
            partial(
                self.toggleRgbIndexWidgets,
                tap.useRGB_checkBox,
                tuple(w for i in index_widgets for w in i[:2]),
                tuple(w for i in rgb_widgets for w in i[:2]),
                "Use_RGB_Color",
            )
        )

        # custom Step Tab
        csTap = self.customStepTab
        csTap.preCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.preCustomStep_checkBox,
                "doPreCustomStep",
            )
        )
        csTap.preCustomStepAdd_pushButton.clicked.connect(self.addCustomStep)
        csTap.preCustomStepNew_pushButton.clicked.connect(self.newCustomStep)
        csTap.preCustomStepDuplicate_pushButton.clicked.connect(
            self.duplicateCustomStep
        )
        csTap.preCustomStepExport_pushButton.clicked.connect(
            self.exportCustomStep
        )
        csTap.preCustomStepImport_pushButton.clicked.connect(
            self.importCustomStep
        )
        csTap.preCustomStepRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                csTap.preCustomStep_listWidget,
                "preCustomStep",
            )
        )
        csTap.preCustomStep_listWidget.installEventFilter(self)
        csTap.preCustomStepRun_pushButton.clicked.connect(
            partial(self.runManualStep, csTap.preCustomStep_listWidget)
        )
        csTap.preCustomStepEdit_pushButton.clicked.connect(
            partial(self.editFile, csTap.preCustomStep_listWidget)
        )

        csTap.postCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.postCustomStep_checkBox,
                "doPostCustomStep",
            )
        )
        csTap.postCustomStepAdd_pushButton.clicked.connect(
            partial(self.addCustomStep, False)
        )
        csTap.postCustomStepNew_pushButton.clicked.connect(
            partial(self.newCustomStep, False)
        )
        csTap.postCustomStepDuplicate_pushButton.clicked.connect(
            partial(self.duplicateCustomStep, False)
        )
        csTap.postCustomStepExport_pushButton.clicked.connect(
            partial(self.exportCustomStep, False)
        )
        csTap.postCustomStepImport_pushButton.clicked.connect(
            partial(self.importCustomStep, False)
        )
        csTap.postCustomStepRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                csTap.postCustomStep_listWidget,
                "postCustomStep",
            )
        )
        csTap.postCustomStep_listWidget.installEventFilter(self)
        csTap.postCustomStepRun_pushButton.clicked.connect(
            partial(self.runManualStep, csTap.postCustomStep_listWidget)
        )
        csTap.postCustomStepEdit_pushButton.clicked.connect(
            partial(self.editFile, csTap.postCustomStep_listWidget)
        )

        # right click menus
        csTap.preCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.preCustomStep_listWidget.customContextMenuRequested.connect(
            self.preCustomStepMenu
        )
        csTap.postCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.postCustomStep_listWidget.customContextMenuRequested.connect(
            self.postCustomStepMenu
        )

        # search hightlight
        csTap.preSearch_lineEdit.textChanged.connect(self.preHighlightSearch)
        csTap.postSearch_lineEdit.textChanged.connect(self.postHighlightSearch)

        # Naming Tab
        tap = self.namingRulesTab

        # names rules
        tap.ctl_name_rule_lineEdit.editingFinished.connect(
            partial(
                self.updateNameRuleLineEdit,
                tap.ctl_name_rule_lineEdit,
                "ctl_name_rule",
            )
        )
        tap.joint_name_rule_lineEdit.editingFinished.connect(
            partial(
                self.updateNameRuleLineEdit,
                tap.joint_name_rule_lineEdit,
                "joint_name_rule",
            )
        )

        # sides names
        tap.side_left_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_left_name_lineEdit,
                "side_left_name",
            )
        )
        tap.side_right_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_right_name_lineEdit,
                "side_right_name",
            )
        )
        tap.side_center_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_center_name_lineEdit,
                "side_center_name",
            )
        )

        tap.side_joint_left_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_joint_left_name_lineEdit,
                "side_joint_left_name",
            )
        )
        tap.side_joint_right_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_joint_right_name_lineEdit,
                "side_joint_right_name",
            )
        )
        tap.side_joint_center_name_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.side_joint_center_name_lineEdit,
                "side_joint_center_name",
            )
        )

        # names extensions
        tap.ctl_name_ext_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2, tap.ctl_name_ext_lineEdit, "ctl_name_ext"
            )
        )
        tap.joint_name_ext_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit2,
                tap.joint_name_ext_lineEdit,
                "joint_name_ext",
            )
        )

        # description letter case
        tap.ctl_des_letter_case_comboBox.currentIndexChanged.connect(
            partial(
                self.updateComboBox,
                tap.ctl_des_letter_case_comboBox,
                "ctl_description_letter_case",
            )
        )
        tap.joint_des_letter_case_comboBox.currentIndexChanged.connect(
            partial(
                self.updateComboBox,
                tap.joint_des_letter_case_comboBox,
                "joint_description_letter_case",
            )
        )

        # reset naming rules
        tap.reset_ctl_name_rule_pushButton.clicked.connect(
            partial(
                self.reset_naming_rule,
                tap.ctl_name_rule_lineEdit,
                "ctl_name_rule",
            )
        )
        tap.reset_joint_name_rule_pushButton.clicked.connect(
            partial(
                self.reset_naming_rule,
                tap.joint_name_rule_lineEdit,
                "joint_name_rule",
            )
        )

        # reset naming sides
        tap.reset_side_name_pushButton.clicked.connect(self.reset_naming_sides)

        tap.reset_joint_side_name_pushButton.clicked.connect(
            self.reset_joint_naming_sides
        )

        # reset naming extension
        tap.reset_name_ext_pushButton.clicked.connect(
            self.reset_naming_extension
        )

        # index padding
        tap.ctl_padding_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                tap.ctl_padding_spinBox,
                "ctl_index_padding",
            )
        )
        tap.joint_padding_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                tap.joint_padding_spinBox,
                "joint_index_padding",
            )
        )

        # import name configuration
        tap.load_naming_configuration_pushButton.clicked.connect(
            self.import_name_config
        )

        # export name configuration
        tap.save_naming_configuration_pushButton.clicked.connect(
            self.export_name_config
        )

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.guideSettingsTab.rigTabs_listWidget:
                self.updateListAttr(sender, "synoptic")
            elif sender == self.customStepTab.preCustomStep_listWidget:
                self.updateListAttr(sender, "preCustomStep")
            elif sender == self.customStepTab.postCustomStep_listWidget:
                self.updateListAttr(sender, "postCustomStep")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    # Slots ########################################################

    def export_name_config(self, file_path=None):
        # set focus to the save button to ensure all values are updated
        # if the cursor stay in other lineEdit since the edition is not
        # finished will not take the last edition

        self.namingRulesTab.save_naming_configuration_pushButton.setFocus(
            QtCore.Qt.MouseFocusReason
        )

        config = {}
        config["ctl_name_rule"] = self.root.attr("ctl_name_rule").get()
        config["joint_name_rule"] = self.root.attr("joint_name_rule").get()
        config["side_left_name"] = self.root.attr("side_left_name").get()
        config["side_right_name"] = self.root.attr("side_right_name").get()
        config["side_center_name"] = self.root.attr("side_center_name").get()
        config["side_joint_left_name"] = self.root.attr(
            "side_joint_left_name"
        ).get()
        config["side_joint_right_name"] = self.root.attr(
            "side_joint_right_name"
        ).get()
        config["side_joint_center_name"] = self.root.attr(
            "side_joint_center_name"
        ).get()
        config["ctl_name_ext"] = self.root.attr("ctl_name_ext").get()
        config["joint_name_ext"] = self.root.attr("joint_name_ext").get()
        config["ctl_description_letter_case"] = self.root.attr(
            "ctl_description_letter_case"
        ).get()
        config["joint_description_letter_case"] = self.root.attr(
            "joint_description_letter_case"
        ).get()
        config["ctl_index_padding"] = self.root.attr("ctl_index_padding").get()
        config["joint_index_padding"] = self.root.attr(
            "joint_index_padding"
        ).get()

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = pm.workspace(q=True, rootDirectory=True)
        data_string = json.dumps(config, indent=4, sort_keys=True)
        if not file_path:
            file_path = pm.fileDialog2(
                fileMode=0,
                startingDirectory=startDir,
                fileFilter="Naming Configuration .naming (*%s)" % ".naming",
            )
        if not file_path:
            return
        if not isinstance(file_path, string_types):
            file_path = file_path[0]
        f = open(file_path, "w")
        f.write(data_string)
        f.close()

    def import_name_config(self, file_path=None):
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = pm.workspace(q=True, rootDirectory=True)
        if not file_path:
            file_path = pm.fileDialog2(
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="Naming Configuration .naming (*%s)" % ".naming",
            )
        if not file_path:
            return
        if not isinstance(file_path, string_types):
            file_path = file_path[0]
        config = json.load(open(file_path))
        for key in config.keys():
            self.root.attr(key).set(config[key])
        self.populate_naming_controls()

    def reset_naming_rule(self, rule_lineEdit, target_attr):
        rule_lineEdit.setText(naming.DEFAULT_NAMING_RULE)
        self.updateNameRuleLineEdit(rule_lineEdit, target_attr)

    def reset_naming_sides(self):
        self.namingRulesTab.side_left_name_lineEdit.setText(
            naming.DEFAULT_SIDE_L_NAME
        )
        self.namingRulesTab.side_right_name_lineEdit.setText(
            naming.DEFAULT_SIDE_R_NAME
        )
        self.namingRulesTab.side_center_name_lineEdit.setText(
            naming.DEFAULT_SIDE_C_NAME
        )
        self.root.attr("side_left_name").set(naming.DEFAULT_SIDE_L_NAME)
        self.root.attr("side_right_name").set(naming.DEFAULT_SIDE_R_NAME)
        self.root.attr("side_center_name").set(naming.DEFAULT_SIDE_C_NAME)

    def reset_joint_naming_sides(self):
        self.namingRulesTab.side_joint_left_name_lineEdit.setText(
            naming.DEFAULT_JOINT_SIDE_L_NAME
        )
        self.namingRulesTab.side_joint_right_name_lineEdit.setText(
            naming.DEFAULT_JOINT_SIDE_R_NAME
        )
        self.namingRulesTab.side_joint_center_name_lineEdit.setText(
            naming.DEFAULT_JOINT_SIDE_C_NAME
        )
        self.root.attr("side_joint_left_name").set(
            naming.DEFAULT_JOINT_SIDE_L_NAME
        )
        self.root.attr("side_joint_right_name").set(
            naming.DEFAULT_JOINT_SIDE_R_NAME
        )
        self.root.attr("side_joint_center_name").set(
            naming.DEFAULT_JOINT_SIDE_C_NAME
        )

    def reset_naming_extension(self):
        self.namingRulesTab.ctl_name_ext_lineEdit.setText(
            naming.DEFAULT_CTL_EXT_NAME
        )
        self.namingRulesTab.joint_name_ext_lineEdit.setText(
            naming.DEFAULT_JOINT_EXT_NAME
        )
        self.root.attr("ctl_name_ext").set(naming.DEFAULT_CTL_EXT_NAME)
        self.root.attr("joint_name_ext").set(naming.DEFAULT_JOINT_EXT_NAME)

    def populateAvailableSynopticTabs(self):

        import mgear.shifter as shifter

        defPath = os.environ.get("MGEAR_SYNOPTIC_PATH", None)
        if not defPath or not os.path.isdir(defPath):
            defPath = shifter.SYNOPTIC_PATH

        # Sanity check for folder existence.
        if not os.path.isdir(defPath):
            return

        tabsDirectories = [
            name
            for name in os.listdir(defPath)
            if os.path.isdir(os.path.join(defPath, name))
        ]
        # Quick clean the first empty item
        if tabsDirectories and not tabsDirectories[0]:
            self.guideSettingsTab.available_listWidget.takeItem(0)

        itemsList = self.root.attr("synoptic").get().split(",")
        for tab in sorted(tabsDirectories):
            if tab not in itemsList:
                self.guideSettingsTab.available_listWidget.addItem(tab)

    def skinLoad(self, *args):
        startDir = self.root.attr("skin").get()
        filePath = pm.fileDialog2(
            fileMode=1,
            startingDirectory=startDir,
            okc="Apply",
            fileFilter="mGear skin (*%s)" % skin.FILE_EXT,
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        self.root.attr("skin").set(filePath)
        self.guideSettingsTab.skin_lineEdit.setText(filePath)

    def _data_collector_path(self, *args):
        ext_filter = "Shifter Collected data (*{})".format(DATA_COLLECTOR_EXT)
        filePath = pm.fileDialog2(fileMode=0, fileFilter=ext_filter)
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        return filePath

    def data_collector_path(self, *args):
        """Set the path to external file in json format containing the
        collected data

        Args:
            *args: Description
        """
        filePath = self._data_collector_path()

        if filePath:
            self.root.attr("data_collector_path").set(filePath)
            self.guideSettingsTab.dataCollectorPath_lineEdit.setText(filePath)

    def data_collector_pathEmbbeded(self, *args):
        """Set the joint whre the data will be embbded

        Args:
            *args: Description
        """
        oSel = pm.selected()
        if oSel and oSel[0].type() in ["joint", "transform"]:
            j_name = oSel[0].name()
            self.root.attr("data_collector_embedded_custom_joint").set(j_name)
            self.guideSettingsTab.dataCollectorCustomJoint_lineEdit.setText(
                j_name
            )
        else:
            pm.displayWarning(
                "Nothing selected or selection is not joint or Transform type"
            )

    def addCustomStep(self, pre=True, *args):
        """Add a new custom step

        Arguments:
            pre (bool, optional): If true adds the steps to the pre step list
            *args: Maya's Dummy

        Returns:
            None: None
        """

        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Check if we have a custom env for the custom steps initial folder
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePaths = pm.fileDialog2(
            fileMode=4,
            startingDirectory=startDir,
            okc="Add",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePaths:
            return

        # Quick clean the first empty item
        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)
        for filePath in filePaths:
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                filePath = os.path.abspath(filePath)
                baseReplace = os.path.abspath(
                    os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
                )
                # backslashes (windows paths) can cause escape characters
                filePath = filePath.replace(baseReplace, "").replace("\\", "/")
                # remove front forward
                if "/" == filePath[0]:
                    filePath = filePath[1:]

            fileName = os.path.split(filePath)[1].split(".")[0]
            stepWidget.addItem(fileName + " | " + filePath)
        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def newCustomStep(self, pre=True, *args):
        """Creates a new custom step

        Arguments:
            pre (bool, optional): If true adds the steps to the pre step list
            *args: Maya's Dummy

        Returns:
            None: None
        """

        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Check if we have a custom env for the custom steps initial folder
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        n, e = os.path.splitext(filePath)
        stepName = os.path.split(n)[-1]
        # raw custome step string
        rawString = r'''import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{stepName}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "{stepName}"

    def run(self):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        return'''.format(
            stepName=stepName
        )
        f = open(filePath, "w")
        f.write(rawString + "\n")
        f.close()

        # Quick clean the first empty item
        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            filePath = os.path.abspath(filePath)
            baseReplace = os.path.abspath(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            )
            filePath = filePath.replace(baseReplace, "")[1:]

        fileName = os.path.split(filePath)[1].split(".")[0]
        stepWidget.addItem(fileName + " | " + filePath)
        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def duplicateCustomStep(self, pre=True, *args):
        """Duplicate the selected step

        Arguments:
            pre (bool, optional): If true adds the steps to the pre step list
            *args: Maya's Dummy

        Returns:
            None: None
        """

        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Check if we have a custom env for the custom steps initial folder
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        if stepWidget.selectedItems():
            sourcePath = (
                stepWidget.selectedItems()[0].text().split("|")[-1][1:]
            )

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            sourcePath = os.path.join(startDir, sourcePath)
        shutil.copy(sourcePath, filePath)

        # Quick clean the first empty item
        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            filePath = os.path.abspath(filePath)
            baseReplace = os.path.abspath(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            )
            filePath = filePath.replace(baseReplace, "")[1:]

        fileName = os.path.split(filePath)[1].split(".")[0]
        stepWidget.addItem(fileName + " | " + filePath)
        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def exportCustomStep(self, pre=True, *args):
        """Export custom steps to a json file

        Arguments:
            pre (bool, optional): If true takes the steps from the
                pre step list
            *args: Maya's Dummy

        Returns:
            None: None

        """

        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Quick clean the first empty item
        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        # Check if we have a custom env for the custom steps initial folder
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            itemsList = [
                os.path.join(startDir, i.text().split("|")[-1][1:])
                for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
            ]
        else:
            itemsList = [
                i.text().split("|")[-1][1:]
                for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
            ]
            if itemsList:
                startDir = os.path.split(itemsList[-1])[0]
            else:
                pm.displayWarning("No custom steps to export.")
                return
        stepsDict = self.get_steps_dict(itemsList)

        data_string = json.dumps(stepsDict, indent=4, sort_keys=True)
        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]
        f = open(filePath, "w")
        f.write(data_string)
        f.close()

    def importCustomStep(self, pre=True, *args):
        """Import custom steps from a json file

        Arguments:
            pre (bool, optional): If true import to pre steps list
            *args: Maya's Dummy

        Returns:
            None: None

        """

        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # option import only paths or unpack steps
        option = pm.confirmDialog(
            title="Shifter Custom Step Import Style",
            message="Do you want to import only the path or"
            " unpack and import?",
            button=["Only Path", "Unpack", "Cancel"],
            defaultButton="Only Path",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if option in ["Only Path", "Unpack"]:
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            else:
                startDir = pm.workspace(q=True, rootDirectory=True)

            filePath = pm.fileDialog2(
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
            )
            if not filePath:
                return
            if not isinstance(filePath, string_types):
                filePath = filePath[0]
            stepDict = json.load(open(filePath))
            stepsList = []

        if option == "Only Path":
            for item in stepDict["itemsList"]:
                stepsList.append(item)

        elif option == "Unpack":
            unPackDir = pm.fileDialog2(fileMode=2, startingDirectory=startDir)
            if not filePath:
                return
            if not isinstance(unPackDir, string_types):
                unPackDir = unPackDir[0]

            for item in stepDict["itemsList"]:
                fileName = os.path.split(item)[1]
                fileNewPath = os.path.join(unPackDir, fileName)
                stepsList.append(fileNewPath)
                f = open(fileNewPath, "w")
                f.write(stepDict[item])
                f.close()

        if option in ["Only Path", "Unpack"]:

            for item in stepsList:
                # Quick clean the first empty item
                itemsList = [
                    i.text()
                    for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
                ]
                if itemsList and not itemsList[0]:
                    stepWidget.takeItem(0)

                if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                    item = os.path.abspath(item)
                    baseReplace = os.path.abspath(
                        os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
                    )
                    item = item.replace(baseReplace, "")[1:]

                fileName = os.path.split(item)[1].split(".")[0]
                stepWidget.addItem(fileName + " | " + item)
                self.updateListAttr(stepWidget, stepAttr)

    def _customStepMenu(self, cs_listWidget, stepAttr, QPos):
        "right click context menu for custom step"
        currentSelection = cs_listWidget.currentItem()
        if currentSelection is None:
            return
        self.csMenu = QtWidgets.QMenu()
        parentPosition = cs_listWidget.mapToGlobal(QtCore.QPoint(0, 0))
        menu_item_01 = self.csMenu.addAction("Toggle Custom Step")
        self.csMenu.addSeparator()
        menu_item_02 = self.csMenu.addAction("Turn OFF Selected")
        menu_item_03 = self.csMenu.addAction("Turn ON Selected")
        self.csMenu.addSeparator()
        menu_item_04 = self.csMenu.addAction("Turn OFF All")
        menu_item_05 = self.csMenu.addAction("Turn ON All")

        menu_item_01.triggered.connect(
            partial(self.toggleStatusCustomStep, cs_listWidget, stepAttr)
        )
        menu_item_02.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, False)
        )
        menu_item_03.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, True)
        )
        menu_item_04.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, False, False
            )
        )
        menu_item_05.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, True, False
            )
        )

        self.csMenu.move(parentPosition + QPos)
        self.csMenu.show()

    def preCustomStepMenu(self, QPos):
        self._customStepMenu(
            self.customStepTab.preCustomStep_listWidget, "preCustomStep", QPos
        )

    def postCustomStepMenu(self, QPos):
        self._customStepMenu(
            self.customStepTab.postCustomStep_listWidget,
            "postCustomStep",
            QPos,
        )

    def toggleStatusCustomStep(self, cs_listWidget, stepAttr):
        items = cs_listWidget.selectedItems()
        for item in items:
            if item.text().startswith("*"):
                item.setText(item.text()[1:])
                item.setForeground(self.whiteDownBrush)
            else:
                item.setText("*" + item.text())
                item.setForeground(self.redBrush)

        self.updateListAttr(cs_listWidget, stepAttr)
        self.refreshStatusColor(cs_listWidget)

    def setStatusCustomStep(
        self, cs_listWidget, stepAttr, status=True, selected=True
    ):
        if selected:
            items = cs_listWidget.selectedItems()
        else:
            items = self.getAllItems(cs_listWidget)
        for item in items:
            off = item.text().startswith("*")
            if status and off:
                item.setText(item.text()[1:])
            elif not status and not off:
                item.setText("*" + item.text())
            self.setStatusColor(item)
        self.updateListAttr(cs_listWidget, stepAttr)
        self.refreshStatusColor(cs_listWidget)

    def getAllItems(self, cs_listWidget):
        return [cs_listWidget.item(i) for i in range(cs_listWidget.count())]

    def setStatusColor(self, item):
        if item.text().startswith("*"):
            item.setForeground(self.redBrush)
        elif "_shared" in item.text():
            item.setForeground(self.greenBrush)
        else:
            item.setForeground(self.whiteDownBrush)

    def refreshStatusColor(self, cs_listWidget):
        items = self.getAllItems(cs_listWidget)
        for i in items:
            self.setStatusColor(i)

    # Highligter filter
    def _highlightSearch(self, cs_listWidget, searchText):
        items = self.getAllItems(cs_listWidget)
        for i in items:
            if searchText and searchText.lower() in i.text().lower():
                i.setBackground(QtGui.QColor(128, 128, 128, 255))
            else:
                i.setBackground(QtGui.QColor(255, 255, 255, 0))

    def preHighlightSearch(self):
        searchText = self.customStepTab.preSearch_lineEdit.text()
        self._highlightSearch(
            self.customStepTab.preCustomStep_listWidget, searchText
        )

    def postHighlightSearch(self):
        searchText = self.customStepTab.postSearch_lineEdit.text()
        self._highlightSearch(
            self.customStepTab.postCustomStep_listWidget, searchText
        )


# Backwards compatibility aliases
MainGuide = Main
RigGuide = Rig
helperSlots = HelperSlots
guideSettingsTab = GuideSettingsTab
customStepTab = CustomStepTab
guideSettings = GuideSettings
