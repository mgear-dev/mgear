# Built-in
import datetime
import getpass
import json
import os
import sys
from functools import partial

# Maya
from maya import cmds, mel

# pymel
import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.pymaya import versions

# mgear
import mgear
from mgear.core import attribute, dag, vector, pyqt, skin, string, fcurve
from mgear.core import utils, curve
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
from mgear.anim_picker.gui import MAYA_OVERRIDE_COLOR

from . import guide_ui as guui
from . import naming_rules_ui as naui
from . import blueprint_tab_ui as btui
from . import naming
from . import custom_step_widget as csw

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


# =============================================================================
# Build Cancellation Support
# =============================================================================
# Module-level state for cancellation during guide validation
_cancel_enabled = False
_cancel_requested = False
_gMainProgressBar = None


def init_guide_cancel():
    """Initialize the guide cancellation mechanism.

    Enables ESC key cancellation during guide validation in interactive mode.
    In batch mode, cancellation is disabled since there's no UI.
    """
    global _cancel_enabled, _cancel_requested, _gMainProgressBar
    _cancel_requested = False
    _cancel_enabled = not cmds.about(batch=True)
    _gMainProgressBar = None

    if _cancel_enabled:
        try:
            _gMainProgressBar = mel.eval("$tmp = $gMainProgressBar")
            cmds.progressBar(
                _gMainProgressBar,
                edit=True,
                beginProgress=True,
                isInterruptable=True,
                status="Validating Guide...",
                maxValue=100,
            )
        except Exception:
            _cancel_enabled = False


def end_guide_cancel():
    """End the guide cancellation mechanism."""
    global _cancel_enabled, _gMainProgressBar
    if _cancel_enabled and _gMainProgressBar:
        try:
            cmds.progressBar(_gMainProgressBar, edit=True, endProgress=True)
        except Exception:
            pass


def check_guide_cancelled():
    """Check if guide validation was cancelled by user pressing ESC.

    Returns:
        bool: True if cancelled, False otherwise.
    """
    global _cancel_enabled, _cancel_requested, _gMainProgressBar
    if _cancel_requested:
        return True
    if _cancel_enabled and _gMainProgressBar:
        try:
            if cmds.progressBar(_gMainProgressBar, query=True, isCancelled=True):
                _cancel_requested = True
                pm.displayWarning("Guide validation cancelled by user")
                return True
        except Exception:
            pass
    return False


# Blueprint section settings mapping - defines which attributes belong to each section
OVERRIDE_SECTION_ATTRS = {
    "override_rig_settings": [
        "rig_name", "mode", "step"
    ],
    "override_anim_channels": [
        "proxyChannels", "classicChannelNames", "attrPrefixName"
    ],
    "override_base_rig_control": [
        "worldCtl", "world_ctl_name"
    ],
    "override_skinning": [
        "importSkin", "skin"
    ],
    "override_joint_settings": [
        "joint_rig", "joint_worldOri", "force_uniScale",
        "connect_joints", "force_SSC"
    ],
    "override_data_collector": [
        "data_collector", "data_collector_path",
        "data_collector_embedded", "data_collector_embedded_custom_joint"
    ],
    "override_color_settings": [
        "L_color_fk", "L_color_ik", "R_color_fk", "R_color_ik",
        "C_color_fk", "C_color_ik", "Use_RGB_Color",
        "L_RGB_fk", "L_RGB_ik", "R_RGB_fk", "R_RGB_ik",
        "C_RGB_fk", "C_RGB_ik"
    ],
    "override_naming_rules": [
        "ctl_name_rule", "joint_name_rule",
        "side_left_name", "side_right_name", "side_center_name",
        "side_joint_left_name", "side_joint_right_name",
        "side_joint_center_name", "ctl_name_ext", "joint_name_ext",
        "ctl_des_letter_case", "joint_des_letter_case"
    ],
    "override_pre_custom_steps": [
        "doPreCustomStep", "preCustomStep"
    ],
    "override_post_custom_steps": [
        "doPostCustomStep", "postCustomStep"
    ]
}


def resolve_blueprint_path(path):
    """Resolve blueprint guide file path.

    Supports:
        - Absolute paths (returned as-is if file exists)
        - Relative paths (resolved using MGEAR_SHIFTER_CUSTOMSTEP_PATH env var)

    Args:
        path (str): Path to the blueprint guide file (.sgt)

    Returns:
        str or None: Resolved absolute path if file exists, None otherwise
    """
    if not path:
        return None

    # If absolute path and file exists, return it
    if os.path.isabs(path):
        if os.path.isfile(path):
            return path
        return None

    # Try to resolve relative path using MGEAR_SHIFTER_CUSTOMSTEP_PATH
    custom_step_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY)
    if custom_step_path:
        # Split on path separator in case there are multiple paths
        for base_path in custom_step_path.split(os.pathsep):
            full_path = os.path.join(base_path, path)
            if os.path.isfile(full_path):
                return full_path

    # Try current working directory as fallback
    cwd_path = os.path.join(os.getcwd(), path)
    if os.path.isfile(cwd_path):
        return cwd_path

    return None


def make_blueprint_path_relative(path):
    """Convert an absolute blueprint path to relative if within custom step path.

    Args:
        path (str): Absolute or relative path to the blueprint guide file

    Returns:
        str: Relative path if within MGEAR_SHIFTER_CUSTOMSTEP_PATH, original otherwise
    """
    if not path:
        return path

    # Normalize path separators
    path = os.path.normpath(path)

    # If already relative, return as-is
    if not os.path.isabs(path):
        return path

    # Try to make it relative to MGEAR_SHIFTER_CUSTOMSTEP_PATH
    custom_step_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY)
    if custom_step_path:
        for base_path in custom_step_path.split(os.pathsep):
            base_path = os.path.normpath(base_path)
            # Use normcase for case-insensitive comparison on Windows
            if os.path.normcase(path).startswith(
                os.path.normcase(base_path + os.sep)
            ):
                return os.path.relpath(path, base_path)

    return path


def load_blueprint_guide(path):
    """Load blueprint guide settings from a serialized guide file.

    Args:
        path (str): Path to the blueprint guide file (.sgt)

    Returns:
        dict or None: Guide settings dictionary, or None if loading fails
    """
    resolved_path = resolve_blueprint_path(path)
    if not resolved_path:
        mgear.log(
            "Blueprint guide file not found: {}".format(path),
            mgear.sev_warning
        )
        return None

    try:
        with open(resolved_path, 'r') as f:
            conf = json.load(f)
        return conf
    except (IOError, ValueError) as e:
        mgear.log(
            "Error loading blueprint guide: {}".format(str(e)),
            mgear.sev_error
        )
        return None


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
                    f"{node}.{scriptName}", destination=False, source=True
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
                    # Cache getAttr result to avoid redundant call
                    attr_value = pm.getAttr(f"{node}.{scriptName}")
                    paramDef.value = attr_value
                    self.values[scriptName] = attr_value

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
            value (float | int | str | bool): Default parameter value.
            niceName (str): Parameter niceName.
            shortName (str): Parameter shortName.
            minimum (float | int | None): mininum value.
            maximum (float | int | None): maximum value.
            keyable (bool): If true is keyable
            readable (bool): If true is readable
            storable (bool): If true is storable
            writable (bool): If true is writable

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

        # --------------------------------------------------
        # Blueprint Guide Settings
        self.pUseBlueprint = self.addParam("use_blueprint", "bool", False)
        self.pBlueprintPath = self.addParam("blueprint_path", "string", "")

        # Section override flags (when True, use local values instead of blueprint)
        self.pOverrideRigSettings = self.addParam(
            "override_rig_settings", "bool", False
        )
        self.pOverrideAnimChannels = self.addParam(
            "override_anim_channels", "bool", False
        )
        self.pOverrideBaseRigControl = self.addParam(
            "override_base_rig_control", "bool", False
        )
        self.pOverrideSkinning = self.addParam(
            "override_skinning", "bool", False
        )
        self.pOverrideJointSettings = self.addParam(
            "override_joint_settings", "bool", False
        )
        self.pOverrideDataCollector = self.addParam(
            "override_data_collector", "bool", False
        )
        self.pOverrideColorSettings = self.addParam(
            "override_color_settings", "bool", False
        )
        self.pOverrideNamingRules = self.addParam(
            "override_naming_rules", "bool", False
        )
        self.pOverridePreCustomSteps = self.addParam(
            "override_pre_custom_steps", "bool", False
        )
        self.pOverridePostCustomSteps = self.addParam(
            "override_post_custom_steps", "bool", False
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

    def getMergedOptions(self):
        """Get merged options combining local values with blueprint settings.

        When blueprint is enabled and a section is not overridden,
        values from the blueprint guide will be used instead of local values.

        Returns:
            dict: Merged options dictionary
        """
        # Start with a copy of local values
        merged = dict(self.values)

        # Check if blueprint is enabled
        use_blueprint = self.values.get("use_blueprint", False)
        blueprint_path = self.values.get("blueprint_path", "")

        if not use_blueprint or not blueprint_path:
            return merged

        # Load blueprint guide
        blueprint_conf = load_blueprint_guide(blueprint_path)
        if not blueprint_conf:
            mgear.log(
                "Could not load blueprint guide, using local settings",
                mgear.sev_warning
            )
            return merged

        # Get blueprint guide settings (stored under "guide_root" -> "param_values")
        guide_root = blueprint_conf.get("guide_root", {})
        blueprint_values = guide_root.get("param_values", {})
        if not blueprint_values:
            mgear.log(
                "No param_values found in blueprint guide_root",
                mgear.sev_warning
            )
            return merged

        # Define which settings belong to each section
        section_settings = {
            "override_rig_settings": [
                "rig_name", "mode", "step"
            ],
            "override_anim_channels": [
                "proxyChannels", "classicChannelNames", "attrPrefixName"
            ],
            "override_base_rig_control": [
                "worldCtl", "world_ctl_name"
            ],
            "override_skinning": [
                "importSkin", "skin"
            ],
            "override_joint_settings": [
                "joint_rig", "joint_worldOri", "force_uniScale",
                "connect_joints", "force_SSC"
            ],
            "override_data_collector": [
                "data_collector", "data_collector_path",
                "data_collector_embedded", "data_collector_embedded_custom_joint"
            ],
            "override_color_settings": [
                "L_color_fk", "L_color_ik", "R_color_fk", "R_color_ik",
                "C_color_fk", "C_color_ik", "Use_RGB_Color",
                "L_RGB_fk", "L_RGB_ik", "R_RGB_fk", "R_RGB_ik",
                "C_RGB_fk", "C_RGB_ik"
            ],
            "override_naming_rules": [
                "ctl_name_rule", "joint_name_rule",
                "side_left_name", "side_right_name", "side_center_name",
                "side_joint_left_name", "side_joint_right_name",
                "side_joint_center_name", "ctl_name_ext", "joint_name_ext",
                "ctl_description_letter_case", "joint_description_letter_case",
                "ctl_index_padding", "joint_index_padding"
            ],
            "override_pre_custom_steps": [
                "doPreCustomStep", "preCustomStep"
            ],
            "override_post_custom_steps": [
                "doPostCustomStep", "postCustomStep"
            ]
        }

        # For each section, if NOT overridden, use blueprint values
        for override_attr, settings in section_settings.items():
            is_overridden = self.values.get(override_attr, False)
            if not is_overridden:
                # Use blueprint values for this section
                for setting in settings:
                    if setting in blueprint_values:
                        merged[setting] = blueprint_values[setting]

        return merged

    def setFromHierarchy(self, root, branch=True):
        """Set the guide from given hierarchy.

        Arguments:
            root (dagNode): The root of the hierarchy to parse.
            branch (bool): True to parse children components.

        Can be cancelled by pressing ESC during execution.
        """
        init_guide_cancel()
        try:
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

            if check_guide_cancelled():
                self.valid = False
                return

            # ---------------------------------------------------
            # First check and set the options
            mgear.log("Get options")
            self.setParamDefValuesFromProperty(self.model)

            if check_guide_cancelled():
                self.valid = False
                return

            # ---------------------------------------------------
            # Get the controllers
            mgear.log("Get controllers")
            self.controllers_org = dag.findChild(self.model, "controllers_org")
            if self.controllers_org:
                for child in self.controllers_org.getChildren():
                    self.controllers[child.name().split("|")[-1]] = child

            if check_guide_cancelled():
                self.valid = False
                return

            # ---------------------------------------------------
            # Components
            mgear.log("Get components")
            self.findComponentRecursive(root, branch)

            if check_guide_cancelled():
                self.valid = False
                return

            endTime = datetime.datetime.now()
            finalTime = endTime - startTime
            mgear.log("Find recursive in  [ " + str(finalTime) + " ]")
            # Parenting
            if self.valid:
                for name in self.componentsIndex:
                    if check_guide_cancelled():
                        self.valid = False
                        return

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
                            # Handle name clashing when parsing the guide
                            # to determine the parent component
                            if "|" in pName:
                                pName = pName.rsplit("|", 1)[-1]
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
                        # Build parent lookup dict once to avoid O(n²) nested loop
                        parent_lookup = {}
                        for comp_name in self.componentsIndex:
                            comp = self.components[comp_name]
                            parent_lookup[comp.root.getParent()] = comp
                        # Now lookup is O(1) instead of O(n)
                        for localName, element in compParent.getObjects3(
                            self.model
                        ).items():
                            if element is not None and element in parent_lookup:
                                compChild = parent_lookup[element]
                                compChild.parentComponent = compParent
                                compChild.parentLocalName = localName

                # More option values
                self.addOptionsValues()
        finally:
            end_guide_cancel()

        # End
        if not self.valid:
            mgear.log(
                "The guide doesn't seem to be up to date."
                "Check logged messages and update the guide.",
                mgear.sev_warning,
            )

        endTime = datetime.datetime.now()
        finalTime = endTime - startTime
        mgear.log(f"Guide loaded from hierarchy in  [ {finalTime} ]")

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

        # More option values
        self.addOptionsValues()

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

        Can be cancelled by pressing ESC during execution.
        """
        if check_guide_cancelled():
            self.valid = False
            return

        # TODO: why mouth component is passing str node??
        if not isinstance(node, str):
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
                    if check_guide_cancelled():
                        self.valid = False
                        return
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

    @utils.one_undo
    def drawNewComponent(self, parent, comp_type, showUI=True):
        """Add a new component to the guide.

        Arguments:
            parent (dagNode): Parent of this new component guide.
            compType (str): Type of component to add.

        Returns:
            True if the component guide instance was created, False or None if not.

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
        if not parent:
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

        return comp_guide.drawFromUI(parent, showUI)

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
                except RuntimeError:
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
            pm.displayWarning("Select the top guide node.")
            return

        name = self.model.name()
        self.setFromHierarchy(self.model, True)
        if self.valid and not force:
            pm.displayInfo("The guide is up to date.")
            return

        pm.rename(self.model, name + "_old")
        deleteLater = self.model
        self.drawUpdate(deleteLater)
        pm.rename(self.model, name)
        pm.displayInfo(f"Guide successfully updated: {name}")
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
                else:
                    comp_guide.duplicate_symmetry_status = True

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


class GuideSettingsTab(QtWidgets.QDialog, guui.Ui_Form):
    def __init__(self, parent=None):
        super(GuideSettingsTab, self).__init__(parent)
        self.setupUi(self)


CustomStepTab = csw.CustomStepTab


class NamingRulesTab(QtWidgets.QDialog, naui.Ui_Form):
    def __init__(self, parent=None):
        super(NamingRulesTab, self).__init__(parent)
        self.setupUi(self)


class BlueprintTab(QtWidgets.QDialog, btui.Ui_BlueprintTab):
    def __init__(self, parent=None):
        super(BlueprintTab, self).__init__(parent)
        self.setupUi(self)


class GuideMainSettings(QtWidgets.QDialog, HelperSlots):
    """
    From Maya 2025 there is an issue with tripple ineritance on GuideSettings
    class GuideSettings(MayaQWidgetDockableMixin, QtWidgets.QDialog, HelperSlots)

    The source of the issue looks like is the HelperSlot. Maybe since is missing
    __init__ method
    This class is a workaround to pass first the QDialog and HelperSlot ineritance
    with the correct MRO and avoid this error:
        object.__init__() takes exactly one argument (the instance to initialize)

    """

    def __init__(self, parent=None):
        super(GuideMainSettings, self).__init__()


# class GuideSettings(MayaQWidgetDockableMixin, QtWidgets.QDialog, HelperSlots):
class GuideSettings(MayaQWidgetDockableMixin, csw.CustomStepMixin, GuideMainSettings):
    greenBrush = QtGui.QColor(0, 160, 0)
    redBrush = QtGui.QColor(180, 0, 0)
    whiteBrush = QtGui.QColor(255, 255, 255)
    whiteDownBrush = QtGui.QColor(160, 160, 160)
    orangeBrush = QtGui.QColor(240, 160, 0)

    def __init__(self, parent=None):
        self.toolName = TYPE
        # # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)
        super(GuideSettings, self).__init__(parent=parent)
        # the inspectSettings function set the current selection to the
        # component root before open the settings dialog
        self.root = pm.selected()[0]

        # Initialize blueprint custom steps state flags
        self._showing_blueprint_pre = False
        self._showing_blueprint_post = False

        self.guideSettingsTab = guideSettingsTab()
        self.customStepTab = customStepTab()
        self.namingRulesTab = NamingRulesTab()
        self.blueprintTab = BlueprintTab()

        self.setup_SettingWindow()
        self.create_controls()
        self.populate_controls()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

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

        # Create blueprint headers for Guide Settings and Naming Rules tabs
        self._create_guide_settings_blueprint_header()
        self._create_naming_rules_blueprint_header()

    def populate_controls(self):
        """Populate the controls values
        from the custom attributes of the component.

        """
        # populate tab
        self.tabs.insertTab(0, self.guideSettingsTab, "Guide Settings")
        self.tabs.insertTab(1, self.customStepTab, "Custom Steps")
        self.tabs.insertTab(2, self.namingRulesTab, "Naming Rules")
        self.tabs.insertTab(3, self.blueprintTab, "Blueprint")

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
            tap.useRGB_checkBox.isChecked(),
        )

        # populate custom steps settings
        self.populate_custom_step_controls()

        self.populate_naming_controls()

        self.populate_blueprint_controls()

        self.populate_override_controls()

    def populate_blueprint_controls(self):
        """Populate the blueprint tab controls."""
        tap = self.blueprintTab
        self.populateCheck(tap.useBlueprint_checkBox, "use_blueprint")
        # Convert to relative path for display if possible
        blueprint_path = self.root.attr("blueprint_path").get()
        relative_path = make_blueprint_path_relative(blueprint_path)
        tap.blueprint_lineEdit.setText(relative_path)
        # Also update the attribute if path was converted
        if relative_path != blueprint_path:
            self.root.attr("blueprint_path").set(relative_path)
        self.update_blueprint_status()

    def populate_override_controls(self):
        """Populate the override checkbox controls.

        For checkable GroupBoxes, we use setChecked() directly since they
        don't support setCheckState(). Regular QCheckBox uses populateCheck().
        """
        tap = self.guideSettingsTab

        # Checkable GroupBoxes - use setChecked directly
        tap.groupBox.setChecked(
            self.root.attr("override_rig_settings").get()
        )
        tap.groupBox_6.setChecked(
            self.root.attr("override_anim_channels").get()
        )
        tap.groupBox_7.setChecked(
            self.root.attr("override_base_rig_control").get()
        )
        tap.groupBox_2.setChecked(
            self.root.attr("override_skinning").get()
        )
        tap.groupBox_3.setChecked(
            self.root.attr("override_joint_settings").get()
        )
        tap.groupBox_8.setChecked(
            self.root.attr("override_data_collector").get()
        )
        tap.groupBox_5.setChecked(
            self.root.attr("override_color_settings").get()
        )

        # Naming Rules and Custom Steps tab overrides (regular checkboxes)
        self.populateCheck(
            self.namingRulesTab.override_namingRules_checkBox,
            "override_naming_rules"
        )
        self.populateCheck(
            self.customStepTab.override_preCustomSteps_checkBox,
            "override_pre_custom_steps"
        )
        self.populateCheck(
            self.customStepTab.override_postCustomSteps_checkBox,
            "override_post_custom_steps"
        )
        # Update section enabled states based on blueprint and override settings
        self.update_section_states()
        # Populate blueprint headers for Guide Settings and Naming Rules
        self._populate_blueprint_headers()

    def update_blueprint_status(self):
        """Update the blueprint status label based on current path."""
        tap = self.blueprintTab
        path = tap.blueprint_lineEdit.text()

        if not path:
            tap.blueprint_status_label.setText("")
            tap.blueprint_status_label.setStyleSheet("")
            return

        resolved_path = resolve_blueprint_path(path)
        if resolved_path:
            tap.blueprint_status_label.setText(
                "Found: {}".format(resolved_path)
            )
            tap.blueprint_status_label.setStyleSheet(
                "color: rgb(100, 200, 100);"
            )
        else:
            tap.blueprint_status_label.setText(
                "File not found"
            )
            tap.blueprint_status_label.setStyleSheet(
                "color: rgb(200, 100, 100);"
            )

    def update_section_states(self):
        """Update the enabled/disabled state of sections based on blueprint settings.

        For checkable GroupBoxes, we use setCheckable(False) to hide the checkbox
        when Blueprint is disabled, and setCheckable(True) to show it when enabled.
        The titles are also updated to include "Local Override:" prefix when active.
        """
        use_blueprint = self.root.attr("use_blueprint").get()
        tap = self.guideSettingsTab

        # Guide Settings tab checkable GroupBoxes with their base titles and attribute names
        groupbox_data = [
            (tap.groupBox, "Rig Settings", "override_rig_settings"),
            (tap.groupBox_6, "Animation Channels Settings", "override_anim_channels"),
            (tap.groupBox_7, "Base Rig Control", "override_base_rig_control"),
            (tap.groupBox_2, "Skinning Settings", "override_skinning"),
            (tap.groupBox_3, "Joint Settings", "override_joint_settings"),
            (tap.groupBox_8, "Post Build Data Collector", "override_data_collector"),
            (tap.groupBox_5, "Color Settings", "override_color_settings"),
        ]

        # Stylesheet for blue title and tooltip when blueprint is active
        blue_title_style = (
            "QGroupBox::title { color: rgb(100, 180, 255); }"
            "QToolTip { background-color: black; color: rgb(100, 180, 255); }"
        )

        # Blueprint tooltip text
        blueprint_tooltip = (
            '<p style="background-color: black; color: rgb(100, 180, 255);">'
            "When checked, local settings are used.<br/>"
            "When unchecked, settings are inherited from blueprint.</p>"
        )

        # If blueprint is not enabled, disable checkable mode and reset styling
        if not use_blueprint:
            for groupBox, baseTitle, attrName in groupbox_data:
                # Disable checkable mode (hides the checkbox in the title)
                groupBox.setCheckable(False)
                # Reset to original title
                groupBox.setTitle(baseTitle)
                # Clear any styling and tooltip
                groupBox.setStyleSheet("")
                groupBox.setToolTip("")

            # Also reset Naming Rules tab
            self.namingRulesTab.override_namingRules_checkBox.setVisible(False)
            self.namingRulesTab.override_namingRules_checkBox.setToolTip("")
            self.namingRulesTab.override_namingRules_checkBox.setStyleSheet("")
            self.namingRulesTab.setStyleSheet("")
            for child in self.namingRulesTab.findChildren(QtWidgets.QWidget):
                if child != self.namingRulesTab.override_namingRules_checkBox:
                    child.setEnabled(True)

            # Reset Custom Steps tab (Pre and Post sections)
            self.customStepTab.override_preCustomSteps_checkBox.setVisible(False)
            self.customStepTab.override_postCustomSteps_checkBox.setVisible(False)
            self.customStepTab.override_preCustomSteps_checkBox.setToolTip("")
            self.customStepTab.override_postCustomSteps_checkBox.setToolTip("")
            self.customStepTab.override_preCustomSteps_checkBox.setStyleSheet("")
            self.customStepTab.override_postCustomSteps_checkBox.setStyleSheet("")
            self.customStepTab.preCollapsible.setStyleSheet("")
            self.customStepTab.postCollapsible.setStyleSheet("")
            # Reset collapsible titles to original (remove [Blueprint] prefix)
            self.customStepTab.preCollapsible.header_wgt.set_text("Pre Custom Step")
            self.customStepTab.postCollapsible.header_wgt.set_text("Post Custom Step")
            for child in self.customStepTab.preCollapsible.findChildren(QtWidgets.QWidget):
                child.setEnabled(True)
            for child in self.customStepTab.postCollapsible.findChildren(QtWidgets.QWidget):
                child.setEnabled(True)

            # Reset show blueprint state flags and restore local view
            self._showing_blueprint_pre = False
            self._showing_blueprint_post = False
            # Restore local custom steps view if blueprint view was active
            self._restore_local_custom_steps_view()
        else:
            # Enable checkable mode with "Local Override:" prefix and blue styling
            for groupBox, baseTitle, attrName in groupbox_data:
                # Block signals to prevent toggled signal from overwriting Maya attribute
                groupBox.blockSignals(True)
                groupBox.setCheckable(True)
                # Set checked state from Maya attribute (default is False = inherit from blueprint)
                groupBox.setChecked(self.root.attr(attrName).get())
                groupBox.blockSignals(False)
                groupBox.setTitle("Local Override: " + baseTitle)
                groupBox.setStyleSheet(blue_title_style)
                groupBox.setToolTip(blueprint_tooltip)
                self.update_section_enabled_state(groupBox, groupBox)

            # Also update Naming Rules tab
            self.namingRulesTab.override_namingRules_checkBox.setVisible(True)
            self.namingRulesTab.override_namingRules_checkBox.setToolTip(blueprint_tooltip)
            self.namingRulesTab.override_namingRules_checkBox.setStyleSheet(
                "color: rgb(100, 180, 255);"
            )
            self.update_tab_enabled_state(
                self.namingRulesTab,
                self.namingRulesTab.override_namingRules_checkBox
            )

            # Update Custom Steps Pre and Post sections
            self.customStepTab.override_preCustomSteps_checkBox.setVisible(True)
            self.customStepTab.override_postCustomSteps_checkBox.setVisible(True)
            self.customStepTab.override_preCustomSteps_checkBox.setToolTip(blueprint_tooltip)
            self.customStepTab.override_postCustomSteps_checkBox.setToolTip(blueprint_tooltip)
            self.customStepTab.override_preCustomSteps_checkBox.setStyleSheet(
                "color: rgb(100, 180, 255);"
            )
            self.customStepTab.override_postCustomSteps_checkBox.setStyleSheet(
                "color: rgb(100, 180, 255);"
            )
            self.update_custom_step_section_state(
                self.customStepTab.preCollapsible,
                self.customStepTab.override_preCustomSteps_checkBox
            )
            self.update_custom_step_section_state(
                self.customStepTab.postCollapsible,
                self.customStepTab.override_postCustomSteps_checkBox
            )

            # Blueprint menu is always visible - handlers check use_blueprint state

    def update_section_enabled_state(self, groupBox, overrideCheckBox):
        """Enable/disable a section based on its override checkbox.

        For checkable GroupBoxes, Qt automatically enables/disables child widgets
        when the GroupBox is checked/unchecked. We just need to apply visual styling.

        Args:
            groupBox: The QGroupBox to enable/disable
            overrideCheckBox: The override checkbox controlling this section
                              (for checkable GroupBoxes, this is the same as groupBox)
        """
        is_overridden = overrideCheckBox.isChecked()
        # Base style for blue title and tooltip
        base_style = (
            "QGroupBox::title { color: rgb(100, 180, 255); }"
            "QToolTip { background-color: black; color: rgb(100, 180, 255); }"
        )
        # Apply visual style - keep blue title, add grey background when not overridden
        if is_overridden:
            groupBox.setStyleSheet(base_style)
        else:
            groupBox.setStyleSheet(
                base_style +
                "QGroupBox { background-color: rgba(100, 100, 100, 30); }"
            )

    def update_tab_enabled_state(self, tab, overrideCheckBox):
        """Enable/disable a tab's contents based on its override checkbox.

        Args:
            tab: The tab widget to enable/disable
            overrideCheckBox: The override checkbox controlling this tab
        """
        is_overridden = overrideCheckBox.isChecked()

        # Get list of widgets to exclude from disabling (blueprint header and its children)
        exclude_widgets = set()
        if hasattr(self, 'naming_rules_blueprint_header'):
            exclude_widgets.add(self.naming_rules_blueprint_header)
            for child in self.naming_rules_blueprint_header.findChildren(QtWidgets.QWidget):
                exclude_widgets.add(child)

        # Enable children widgets (except the override checkbox and blueprint header)
        for child in tab.findChildren(QtWidgets.QWidget):
            if child != overrideCheckBox and child not in exclude_widgets:
                child.setEnabled(is_overridden)
        # Tooltip style for consistency
        tooltip_style = "QToolTip { background-color: black; color: rgb(100, 180, 255); }"
        # Apply visual style
        if is_overridden:
            tab.setStyleSheet(tooltip_style)
        else:
            tab.setStyleSheet(
                tooltip_style +
                "background-color: rgba(100, 100, 100, 30);"
            )

    def update_custom_step_section_state(self, collapsible, overrideCheckBox):
        """Enable/disable a custom step section based on its override checkbox.

        Args:
            collapsible: The collapsible widget (preCollapsible or postCollapsible)
            overrideCheckBox: The override checkbox controlling this section
        """
        is_overridden = overrideCheckBox.isChecked()
        # Enable children widgets
        for child in collapsible.findChildren(QtWidgets.QWidget):
            child.setEnabled(is_overridden)
        # Tooltip style for consistency
        tooltip_style = "QToolTip { background-color: black; color: rgb(100, 180, 255); }"
        # Apply visual style
        if is_overridden:
            collapsible.setStyleSheet(tooltip_style)
        else:
            collapsible.setStyleSheet(
                tooltip_style +
                "background-color: rgba(100, 100, 100, 30);"
            )

    # =========================================================================
    # Blueprint Header Methods (Guide Settings & Naming Rules)
    # =========================================================================

    def _create_guide_settings_blueprint_header(self):
        """Create the blueprint header widget for Guide Settings tab."""
        self.guide_settings_blueprint_header = QtWidgets.QFrame()
        self.guide_settings_blueprint_header.setObjectName(
            "guide_settings_blueprint_header"
        )
        self.guide_settings_blueprint_header.setFrameShape(QtWidgets.QFrame.NoFrame)

        header_layout = QtWidgets.QHBoxLayout(self.guide_settings_blueprint_header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        # Blueprint indicator icon (small colored square)
        self.guide_settings_blueprint_indicator = QtWidgets.QLabel()
        self.guide_settings_blueprint_indicator.setFixedSize(12, 12)
        self.guide_settings_blueprint_indicator.setStyleSheet(
            "background-color: #4682B4; border-radius: 2px;"
        )
        self.guide_settings_blueprint_indicator.setToolTip(
            "Blueprint is active for Guide Settings"
        )
        header_layout.addWidget(self.guide_settings_blueprint_indicator)

        # Info label
        self.guide_settings_blueprint_label = QtWidgets.QLabel("Blueprint Active")
        self.guide_settings_blueprint_label.setStyleSheet(
            "color: rgb(100, 180, 255); font-weight: bold;"
        )
        header_layout.addWidget(self.guide_settings_blueprint_label)

        # View Blueprint Settings button
        self.guide_settings_view_pushButton = QtWidgets.QPushButton("View")
        self.guide_settings_view_pushButton.setObjectName(
            "guide_settings_view_pushButton"
        )
        self.guide_settings_view_pushButton.setToolTip(
            "View blueprint settings for Guide Settings"
        )
        self.guide_settings_view_pushButton.setMaximumWidth(50)
        header_layout.addWidget(self.guide_settings_view_pushButton)

        # Copy button
        self.guide_settings_copy_pushButton = QtWidgets.QPushButton("Copy")
        self.guide_settings_copy_pushButton.setObjectName(
            "guide_settings_copy_pushButton"
        )
        self.guide_settings_copy_pushButton.setToolTip(
            "Copy blueprint settings to local and enable local override"
        )
        self.guide_settings_copy_pushButton.setMaximumWidth(50)
        header_layout.addWidget(self.guide_settings_copy_pushButton)

        header_layout.addStretch()

        # Store blueprint data reference
        self.guide_settings_blueprint_data = None
        # Hidden by default until blueprint is enabled
        self.guide_settings_blueprint_header.setVisible(False)

    def _create_naming_rules_blueprint_header(self):
        """Create the blueprint header widget for Naming Rules tab."""
        self.naming_rules_blueprint_header = QtWidgets.QFrame()
        self.naming_rules_blueprint_header.setObjectName(
            "naming_rules_blueprint_header"
        )
        self.naming_rules_blueprint_header.setFrameShape(QtWidgets.QFrame.NoFrame)

        header_layout = QtWidgets.QHBoxLayout(self.naming_rules_blueprint_header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        # Blueprint indicator icon (small colored square)
        self.naming_rules_blueprint_indicator = QtWidgets.QLabel()
        self.naming_rules_blueprint_indicator.setFixedSize(12, 12)
        self.naming_rules_blueprint_indicator.setStyleSheet(
            "background-color: #4682B4; border-radius: 2px;"
        )
        self.naming_rules_blueprint_indicator.setToolTip(
            "Blueprint is active for Naming Rules"
        )
        header_layout.addWidget(self.naming_rules_blueprint_indicator)

        # Info label
        self.naming_rules_blueprint_label = QtWidgets.QLabel("Blueprint Active")
        self.naming_rules_blueprint_label.setStyleSheet(
            "color: rgb(100, 180, 255); font-weight: bold;"
        )
        header_layout.addWidget(self.naming_rules_blueprint_label)

        # View Blueprint Settings button
        self.naming_rules_view_pushButton = QtWidgets.QPushButton("View")
        self.naming_rules_view_pushButton.setObjectName(
            "naming_rules_view_pushButton"
        )
        self.naming_rules_view_pushButton.setToolTip(
            "View blueprint settings for Naming Rules"
        )
        self.naming_rules_view_pushButton.setMaximumWidth(50)
        header_layout.addWidget(self.naming_rules_view_pushButton)

        # Copy button
        self.naming_rules_copy_pushButton = QtWidgets.QPushButton("Copy")
        self.naming_rules_copy_pushButton.setObjectName(
            "naming_rules_copy_pushButton"
        )
        self.naming_rules_copy_pushButton.setToolTip(
            "Copy blueprint settings to local and enable local override"
        )
        self.naming_rules_copy_pushButton.setMaximumWidth(50)
        header_layout.addWidget(self.naming_rules_copy_pushButton)

        header_layout.addStretch()

        # Store blueprint data reference
        self.naming_rules_blueprint_data = None
        # Hidden by default until blueprint is enabled
        self.naming_rules_blueprint_header.setVisible(False)

    def _populate_blueprint_headers(self):
        """Populate blueprint headers based on guide blueprint settings."""
        use_blueprint = self.root.attr("use_blueprint").get()
        blueprint_path = self.root.attr("blueprint_path").get()

        # Check if blueprint is enabled and valid
        if not use_blueprint or not blueprint_path:
            self._set_guide_settings_header_inactive()
            self._set_naming_rules_header_inactive()
            return

        # Load blueprint data
        blueprint_data = load_blueprint_guide(blueprint_path)
        if not blueprint_data:
            self._set_guide_settings_header_inactive()
            self._set_naming_rules_header_inactive()
            return

        # Store blueprint data for later use
        self.guide_settings_blueprint_data = blueprint_data
        self.naming_rules_blueprint_data = blueprint_data

        # Activate headers
        self._set_guide_settings_header_active()
        self._set_naming_rules_header_active()

    def _set_guide_settings_header_inactive(self):
        """Set the Guide Settings blueprint header to inactive state."""
        self.guide_settings_blueprint_header.setVisible(False)
        self.guide_settings_blueprint_data = None

    def _set_guide_settings_header_active(self):
        """Set the Guide Settings blueprint header to active state."""
        self.guide_settings_blueprint_header.setVisible(True)
        self.guide_settings_blueprint_header.setStyleSheet(
            "QFrame#guide_settings_blueprint_header { "
            "background-color: rgba(70, 130, 180, 40); border-radius: 2px; }"
        )

    def _set_naming_rules_header_inactive(self):
        """Set the Naming Rules blueprint header to inactive state."""
        self.naming_rules_blueprint_header.setVisible(False)
        self.naming_rules_blueprint_data = None

    def _set_naming_rules_header_active(self):
        """Set the Naming Rules blueprint header to active state."""
        self.naming_rules_blueprint_header.setVisible(True)
        self.naming_rules_blueprint_header.setStyleSheet(
            "QFrame#naming_rules_blueprint_header { "
            "background-color: rgba(70, 130, 180, 40); border-radius: 2px; }"
        )
        # Insert header into Naming Rules tab layout at the top
        layout = self.namingRulesTab.verticalLayout_3
        if self.naming_rules_blueprint_header.parent() != self.namingRulesTab:
            layout.insertWidget(0, self.naming_rules_blueprint_header)

    def _on_view_guide_settings_blueprint(self):
        """Show a dialog with the blueprint settings for Guide Settings."""
        if not self.guide_settings_blueprint_data:
            QtWidgets.QMessageBox.warning(
                self,
                "Blueprint Settings",
                "No blueprint data available."
            )
            return

        # Get all Guide Settings section attributes from OVERRIDE_SECTION_ATTRS
        guide_settings_attrs = []
        for section in ["override_rig_settings", "override_anim_channels",
                        "override_base_rig_control", "override_skinning",
                        "override_joint_settings", "override_data_collector",
                        "override_color_settings"]:
            guide_settings_attrs.extend(
                OVERRIDE_SECTION_ATTRS.get(section, [])
            )

        self._show_blueprint_values_dialog(
            "Guide Settings",
            guide_settings_attrs
        )

    def _on_view_naming_rules_blueprint(self):
        """Show a dialog with the blueprint settings for Naming Rules."""
        if not self.naming_rules_blueprint_data:
            QtWidgets.QMessageBox.warning(
                self,
                "Blueprint Settings",
                "No blueprint data available."
            )
            return

        naming_rules_attrs = OVERRIDE_SECTION_ATTRS.get("override_naming_rules", [])
        self._show_blueprint_values_dialog(
            "Naming Rules",
            naming_rules_attrs
        )

    def _show_blueprint_values_dialog(self, title, attr_list):
        """Show a dialog displaying blueprint values for the specified attributes.

        Args:
            title: Dialog title
            attr_list: List of attribute names to display
        """
        blueprint_data = self.guide_settings_blueprint_data

        # Get param_values from guide_root in blueprint data
        param_values = {}
        if blueprint_data:
            guide_root = blueprint_data.get("guide_root", {})
            param_values = guide_root.get("param_values", {})

        # Create dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Blueprint Settings - {}".format(title))
        dialog.resize(450, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Info label
        info_label = QtWidgets.QLabel(
            "Settings from the blueprint guide for {}:".format(title)
        )
        layout.addWidget(info_label)

        # Settings tree
        tree = QtWidgets.QTreeWidget()
        tree.setHeaderLabels(["Parameter", "Value"])
        tree.setColumnCount(2)

        for attr_name in sorted(attr_list):
            if attr_name in param_values:
                value = param_values[attr_name]
                item = QtWidgets.QTreeWidgetItem([str(attr_name), str(value)])
                tree.addTopLevelItem(item)

        tree.resizeColumnToContents(0)
        layout.addWidget(tree)

        # Close button
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec_()

    def _on_copy_guide_settings_from_blueprint(self):
        """Copy blueprint settings to local Guide Settings and enable overrides."""
        if not self.guide_settings_blueprint_data:
            QtWidgets.QMessageBox.warning(
                self,
                "Copy from Blueprint",
                "No blueprint data available."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Copy from Blueprint",
            "This will copy all Guide Settings from the blueprint to local "
            "and enable all local overrides.\n\nContinue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        blueprint_data = self.guide_settings_blueprint_data

        # Get param_values from guide_root in blueprint data
        param_values = {}
        if blueprint_data:
            guide_root = blueprint_data.get("guide_root", {})
            param_values = guide_root.get("param_values", {})

        # Copy settings from blueprint to local for each section
        sections_to_copy = [
            "override_rig_settings",
            "override_anim_channels",
            "override_base_rig_control",
            "override_skinning",
            "override_joint_settings",
            "override_data_collector",
            "override_color_settings"
        ]

        for section in sections_to_copy:
            attr_list = OVERRIDE_SECTION_ATTRS.get(section, [])
            for attr_name in attr_list:
                if attr_name in param_values:
                    try:
                        self.root.attr(attr_name).set(param_values[attr_name])
                    except Exception:
                        pass  # Skip attributes that can't be set

            # Enable the override for this section
            try:
                self.root.attr(section).set(True)
            except Exception:
                pass

        # Refresh UI
        self.populate_controls()

        QtWidgets.QMessageBox.information(
            self,
            "Copy from Blueprint",
            "Blueprint settings have been copied to local.\n"
            "All Guide Settings local overrides are now enabled."
        )

    def _on_copy_naming_rules_from_blueprint(self):
        """Copy blueprint settings to local Naming Rules and enable override."""
        if not self.naming_rules_blueprint_data:
            QtWidgets.QMessageBox.warning(
                self,
                "Copy from Blueprint",
                "No blueprint data available."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Copy from Blueprint",
            "This will copy all Naming Rules from the blueprint to local "
            "and enable local override.\n\nContinue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        blueprint_data = self.naming_rules_blueprint_data

        # Get param_values from guide_root in blueprint data
        param_values = {}
        if blueprint_data:
            guide_root = blueprint_data.get("guide_root", {})
            param_values = guide_root.get("param_values", {})

        attr_list = OVERRIDE_SECTION_ATTRS.get("override_naming_rules", [])

        for attr_name in attr_list:
            if attr_name in param_values:
                try:
                    self.root.attr(attr_name).set(param_values[attr_name])
                except Exception:
                    pass

        # Enable the naming rules override
        try:
            self.root.attr("override_naming_rules").set(True)
        except Exception:
            pass

        # Refresh UI
        self.populate_controls()

        QtWidgets.QMessageBox.information(
            self,
            "Copy from Blueprint",
            "Blueprint settings have been copied to local.\n"
            "Naming Rules local override is now enabled."
        )

    # =========================================================================
    # Blueprint Custom Steps Methods
    # =========================================================================

    def _restore_local_custom_steps_view(self):
        """Restore the local custom steps view (called when blueprint is disabled)."""
        # This method ensures local custom steps are displayed
        # by triggering a refresh of the custom step lists
        if hasattr(self, '_showing_blueprint_pre') and self._showing_blueprint_pre:
            self._showing_blueprint_pre = False
            self._refresh_pre_custom_steps_list()
        if hasattr(self, '_showing_blueprint_post') and self._showing_blueprint_post:
            self._showing_blueprint_post = False
            self._refresh_post_custom_steps_list()

    def _get_blueprint_custom_steps(self):
        """Load custom steps from the blueprint guide file.

        Returns:
            tuple: (pre_custom_steps, post_custom_steps, do_pre, do_post)
                   or (None, None, False, False) if blueprint not available
        """
        blueprint_path = self.root.attr("blueprint_path").get()
        if not blueprint_path:
            return None, None, False, False

        blueprint_conf = load_blueprint_guide(blueprint_path)
        if not blueprint_conf:
            return None, None, False, False

        guide_root = blueprint_conf.get("guide_root", {})
        param_values = guide_root.get("param_values", {})

        pre_steps = param_values.get("preCustomStep", "")
        post_steps = param_values.get("postCustomStep", "")
        do_pre = param_values.get("doPreCustomStep", False)
        do_post = param_values.get("doPostCustomStep", False)

        return pre_steps, post_steps, do_pre, do_post

    def on_show_blueprint_pre_custom_steps(self, checked):
        """Handle Show Blueprint Pre Custom Steps action toggle.

        Args:
            checked: Whether the action is checked (True = show blueprint)
        """
        # Early exit if blueprint is not enabled
        if not self.root.attr("use_blueprint").get():
            try:
                self.customStepTab.showBlueprintPre_action.setChecked(False)
            except RuntimeError:
                pass
            return

        self._showing_blueprint_pre = checked

        if checked:
            # When showing blueprint, uncheck local override (we're viewing blueprint, not local)
            checkbox = self.customStepTab.override_preCustomSteps_checkBox
            if checkbox.isChecked():
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
                self.root.attr("override_pre_custom_steps").set(False)
                self.update_custom_step_section_state(
                    self.customStepTab.preCollapsible,
                    checkbox
                )

            # Load and display blueprint pre custom steps (read-only)
            pre_steps, _, do_pre, _ = self._get_blueprint_custom_steps()
            if pre_steps is not None:
                self._display_blueprint_custom_steps(
                    self.customStepTab.preCustomStep_listWidget,
                    self.customStepTab.preCustomStep_checkBox,
                    pre_steps,
                    do_pre,
                    is_pre=True
                )
            else:
                mgear.log("Could not load blueprint custom steps", mgear.sev_warning)
                try:
                    self.customStepTab.showBlueprintPre_action.setChecked(False)
                except RuntimeError:
                    pass
                self._showing_blueprint_pre = False
        else:
            # Restore local pre custom steps
            self._refresh_pre_custom_steps_list()

    def on_show_blueprint_post_custom_steps(self, checked):
        """Handle Show Blueprint Post Custom Steps action toggle.

        Args:
            checked: Whether the action is checked (True = show blueprint)
        """
        # Early exit if blueprint is not enabled
        if not self.root.attr("use_blueprint").get():
            try:
                self.customStepTab.showBlueprintPost_action.setChecked(False)
            except RuntimeError:
                pass
            return

        self._showing_blueprint_post = checked

        if checked:
            # When showing blueprint, uncheck local override (we're viewing blueprint, not local)
            checkbox = self.customStepTab.override_postCustomSteps_checkBox
            if checkbox.isChecked():
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
                self.root.attr("override_post_custom_steps").set(False)
                self.update_custom_step_section_state(
                    self.customStepTab.postCollapsible,
                    checkbox
                )

            # Load and display blueprint post custom steps (read-only)
            _, post_steps, _, do_post = self._get_blueprint_custom_steps()
            if post_steps is not None:
                self._display_blueprint_custom_steps(
                    self.customStepTab.postCustomStep_listWidget,
                    self.customStepTab.postCustomStep_checkBox,
                    post_steps,
                    do_post,
                    is_pre=False
                )
            else:
                mgear.log("Could not load blueprint custom steps", mgear.sev_warning)
                try:
                    self.customStepTab.showBlueprintPost_action.setChecked(False)
                except RuntimeError:
                    pass
                self._showing_blueprint_post = False
        else:
            # Restore local post custom steps
            self._refresh_post_custom_steps_list()

    def _display_blueprint_custom_steps(self, listWidget, enableCheckbox,
                                         steps_string, is_enabled, is_pre):
        """Display blueprint custom steps in read-only mode.

        Args:
            listWidget: The CustomStepListWidget to populate
            enableCheckbox: The enable checkbox for this section
            steps_string: The custom steps string from blueprint
            is_enabled: Whether the custom steps are enabled in blueprint
            is_pre: True for pre custom steps, False for post
        """
        # Clear existing items
        listWidget.clear()

        # Set the enable checkbox state (but don't save to Maya attribute)
        enableCheckbox.blockSignals(True)
        enableCheckbox.setChecked(is_enabled)
        enableCheckbox.blockSignals(False)

        # Parse and display the steps using the list widget's loadFromJson
        listWidget.loadFromJson(steps_string)

        # Make list read-only by disabling edit actions
        listWidget.setEnabled(False)
        enableCheckbox.setEnabled(False)

        # Update the collapsible title to indicate blueprint view
        collapsible = (self.customStepTab.preCollapsible if is_pre
                      else self.customStepTab.postCollapsible)
        base_title = "Pre Custom Step" if is_pre else "Post Custom Step"
        collapsible.header_wgt.set_text("[Blueprint] " + base_title)
        collapsible.setStyleSheet(
            "background-color: rgba(100, 180, 255, 30);"
        )

    def _refresh_pre_custom_steps_list(self):
        """Refresh the pre custom steps list with local values."""
        listWidget = self.customStepTab.preCustomStep_listWidget
        enableCheckbox = self.customStepTab.preCustomStep_checkBox

        # Re-enable widgets
        listWidget.setEnabled(True)
        enableCheckbox.setEnabled(True)

        # Restore title
        self.customStepTab.preCollapsible.header_wgt.set_text("Pre Custom Step")

        # Reload from Maya attribute
        steps_string = self.root.attr("preCustomStep").get()
        listWidget.loadFromJson(steps_string)

        # Restore enable state
        enableCheckbox.blockSignals(True)
        enableCheckbox.setChecked(self.root.attr("doPreCustomStep").get())
        enableCheckbox.blockSignals(False)

        # Update styling based on override state
        use_blueprint = self.root.attr("use_blueprint").get()
        if use_blueprint:
            self.update_custom_step_section_state(
                self.customStepTab.preCollapsible,
                self.customStepTab.override_preCustomSteps_checkBox
            )
        else:
            self.customStepTab.preCollapsible.setStyleSheet("")

    def _refresh_post_custom_steps_list(self):
        """Refresh the post custom steps list with local values."""
        listWidget = self.customStepTab.postCustomStep_listWidget
        enableCheckbox = self.customStepTab.postCustomStep_checkBox

        # Re-enable widgets
        listWidget.setEnabled(True)
        enableCheckbox.setEnabled(True)

        # Restore title
        self.customStepTab.postCollapsible.header_wgt.set_text("Post Custom Step")

        # Reload from Maya attribute
        steps_string = self.root.attr("postCustomStep").get()
        listWidget.loadFromJson(steps_string)

        # Restore enable state
        enableCheckbox.blockSignals(True)
        enableCheckbox.setChecked(self.root.attr("doPostCustomStep").get())
        enableCheckbox.blockSignals(False)

        # Update styling based on override state
        use_blueprint = self.root.attr("use_blueprint").get()
        if use_blueprint:
            self.update_custom_step_section_state(
                self.customStepTab.postCollapsible,
                self.customStepTab.override_postCustomSteps_checkBox
            )
        else:
            self.customStepTab.postCollapsible.setStyleSheet("")

    def on_make_pre_custom_steps_local(self):
        """Copy blueprint pre custom steps to local configuration."""
        # Early exit if blueprint is not enabled
        if not self.root.attr("use_blueprint").get():
            return

        pre_steps, _, do_pre, _ = self._get_blueprint_custom_steps()
        if pre_steps is None:
            mgear.log("Could not load blueprint custom steps", mgear.sev_warning)
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Make Pre Custom Steps Local",
            "This will replace your local pre custom steps configuration "
            "with the blueprint's configuration.\n\n"
            "Do you want to continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if result != QtWidgets.QMessageBox.Yes:
            return

        # Copy to local Maya attributes
        self.root.attr("preCustomStep").set(pre_steps)
        self.root.attr("doPreCustomStep").set(do_pre)

        # Check the override checkbox (now using local values)
        self.customStepTab.override_preCustomSteps_checkBox.setChecked(True)

        # Turn off blueprint view if active
        try:
            if self.customStepTab.showBlueprintPre_action.isChecked():
                self.customStepTab.showBlueprintPre_action.setChecked(False)
        except RuntimeError:
            pass
        self._showing_blueprint_pre = False

        # Refresh the display
        self._refresh_pre_custom_steps_list()

        mgear.log("Pre custom steps copied from blueprint to local")

    def on_make_post_custom_steps_local(self):
        """Copy blueprint post custom steps to local configuration."""
        # Early exit if blueprint is not enabled
        if not self.root.attr("use_blueprint").get():
            return

        _, post_steps, _, do_post = self._get_blueprint_custom_steps()
        if post_steps is None:
            mgear.log("Could not load blueprint custom steps", mgear.sev_warning)
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Make Post Custom Steps Local",
            "This will replace your local post custom steps configuration "
            "with the blueprint's configuration.\n\n"
            "Do you want to continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if result != QtWidgets.QMessageBox.Yes:
            return

        # Copy to local Maya attributes
        self.root.attr("postCustomStep").set(post_steps)
        self.root.attr("doPostCustomStep").set(do_post)

        # Check the override checkbox (now using local values)
        self.customStepTab.override_postCustomSteps_checkBox.setChecked(True)

        # Turn off blueprint view if active
        try:
            if self.customStepTab.showBlueprintPost_action.isChecked():
                self.customStepTab.showBlueprintPost_action.setChecked(False)
        except RuntimeError:
            pass
        self._showing_blueprint_post = False

        # Refresh the display
        self._refresh_post_custom_steps_list()

        mgear.log("Post custom steps copied from blueprint to local")

    def browse_blueprint_path(self):
        """Open file browser to select blueprint guide file."""
        # Get starting directory from environment variable
        start_dir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        if start_dir:
            # Use first path if multiple paths are specified
            start_dir = start_dir.split(os.pathsep)[0]

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Blueprint Guide",
            start_dir,
            "Shifter Guide Template (*.sgt);;All Files (*.*)"
        )

        if file_path:
            # Convert to relative path if within MGEAR_SHIFTER_CUSTOMSTEP_PATH
            file_path = make_blueprint_path_relative(file_path)

            self.blueprintTab.blueprint_lineEdit.setText(file_path)
            self.root.attr("blueprint_path").set(file_path)
            self.update_blueprint_status()
            self.update_section_states()
            self._populate_blueprint_headers()

    def on_blueprint_enabled_changed(self, *args):
        """Handle blueprint enabled checkbox state change."""
        self.updateCheck(
            self.blueprintTab.useBlueprint_checkBox, "use_blueprint"
        )
        self.update_section_states()
        self._populate_blueprint_headers()

    def on_override_changed(self, overrideCheckBox, groupBox, attrName, *args):
        """Handle override checkbox state change.

        Args:
            overrideCheckBox: The override checkbox that was changed
            groupBox: The QGroupBox to enable/disable
            attrName: The attribute name to update
        """
        self.updateCheck(overrideCheckBox, attrName)
        self.update_section_enabled_state(groupBox, overrideCheckBox)

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

        # Add Guide Settings blueprint header inside the Guide Settings tab
        # Insert at the top of mainLayout (above the grid container)
        self.guideSettingsTab.mainLayout.insertWidget(
            0, self.guide_settings_blueprint_header
        )

    def create_connections(self):
        """Create the slots connections to the controls functions"""
        self.close_button.clicked.connect(self.close_settings)

        # Setting Tab
        tap = self.guideSettingsTab
        tap.rigName_lineEdit.editingFinished.connect(
            partial(self.updateLineEdit2, tap.rigName_lineEdit, "rig_name")
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
            partial(
                self.updateCheck, tap.jointWorldOri_checkBox, "joint_worldOri"
            )
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

        # Custom Step Tab
        self.create_custom_step_connections()

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

        # Blueprint Tab connections
        self.create_blueprint_connections()

        # Override checkbox connections
        self.create_override_connections()

    def create_blueprint_connections(self):
        """Create signal connections for the blueprint tab."""
        tap = self.blueprintTab
        tap.useBlueprint_checkBox.stateChanged.connect(
            self.on_blueprint_enabled_changed
        )
        tap.blueprint_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEditPath,
                tap.blueprint_lineEdit,
                "blueprint_path"
            )
        )
        tap.blueprint_lineEdit.editingFinished.connect(
            self.update_blueprint_status
        )
        tap.blueprint_lineEdit.editingFinished.connect(
            self.update_section_states
        )
        tap.blueprint_lineEdit.editingFinished.connect(
            self._populate_blueprint_headers
        )
        tap.blueprint_pushButton.clicked.connect(
            self.browse_blueprint_path
        )

        # Blueprint header button connections (Guide Settings and Naming Rules)
        self.guide_settings_view_pushButton.clicked.connect(
            self._on_view_guide_settings_blueprint
        )
        self.guide_settings_copy_pushButton.clicked.connect(
            self._on_copy_guide_settings_from_blueprint
        )
        self.naming_rules_view_pushButton.clicked.connect(
            self._on_view_naming_rules_blueprint
        )
        self.naming_rules_copy_pushButton.clicked.connect(
            self._on_copy_naming_rules_from_blueprint
        )

    def create_override_connections(self):
        """Create signal connections for override checkboxes.

        Note: For Guide Settings sections, the GroupBox itself is checkable,
        so the checkbox reference points to the GroupBox. We use the 'toggled'
        signal for checkable GroupBoxes.
        """
        tap = self.guideSettingsTab

        # Connect each checkable GroupBox (override checkbox = groupBox)
        # The override_xxx_checkBox references ARE the GroupBoxes now
        override_mappings = [
            (tap.groupBox, "override_rig_settings"),
            (tap.groupBox_6, "override_anim_channels"),
            (tap.groupBox_7, "override_base_rig_control"),
            (tap.groupBox_2, "override_skinning"),
            (tap.groupBox_3, "override_joint_settings"),
            (tap.groupBox_8, "override_data_collector"),
            (tap.groupBox_5, "override_color_settings"),
        ]

        for groupBox, attrName in override_mappings:
            groupBox.toggled.connect(
                partial(
                    self.on_override_changed,
                    groupBox,
                    groupBox,
                    attrName
                )
            )

        # Tab override connections (Naming Rules)
        self.namingRulesTab.override_namingRules_checkBox.stateChanged.connect(
            partial(
                self.on_tab_override_changed,
                self.namingRulesTab.override_namingRules_checkBox,
                self.namingRulesTab,
                "override_naming_rules"
            )
        )

        # Custom Steps Pre and Post override connections
        self.customStepTab.override_preCustomSteps_checkBox.stateChanged.connect(
            partial(
                self.on_custom_step_override_changed,
                self.customStepTab.override_preCustomSteps_checkBox,
                self.customStepTab.preCollapsible,
                "override_pre_custom_steps"
            )
        )
        self.customStepTab.override_postCustomSteps_checkBox.stateChanged.connect(
            partial(
                self.on_custom_step_override_changed,
                self.customStepTab.override_postCustomSteps_checkBox,
                self.customStepTab.postCollapsible,
                "override_post_custom_steps"
            )
        )

        # Blueprint menu connections for Custom Steps
        try:
            self.customStepTab.showBlueprintPre_action.triggered.connect(
                self.on_show_blueprint_pre_custom_steps
            )
            self.customStepTab.showBlueprintPost_action.triggered.connect(
                self.on_show_blueprint_post_custom_steps
            )
            self.customStepTab.makePreLocal_action.triggered.connect(
                self.on_make_pre_custom_steps_local
            )
            self.customStepTab.makePostLocal_action.triggered.connect(
                self.on_make_post_custom_steps_local
            )
            # Sync menu state when menu is about to show
            self.customStepTab.blueprintMenu.aboutToShow.connect(
                self._sync_blueprint_menu_state
            )
        except RuntimeError:
            mgear.log("Blueprint menu actions not available", mgear.sev_warning)

    def on_tab_override_changed(self, overrideCheckBox, tab, attrName, *args):
        """Handle tab override checkbox state change.

        Args:
            overrideCheckBox: The override checkbox that was changed
            tab: The tab widget to enable/disable
            attrName: The attribute name to update
        """
        self.updateCheck(overrideCheckBox, attrName)
        self.update_tab_enabled_state(tab, overrideCheckBox)

    def on_custom_step_override_changed(self, overrideCheckBox, collapsible, attrName, *args):
        """Handle custom step section override checkbox state change.

        Args:
            overrideCheckBox: The override checkbox that was changed
            collapsible: The collapsible widget to enable/disable
            attrName: The attribute name to update
        """
        self.updateCheck(overrideCheckBox, attrName)
        self.update_custom_step_section_state(collapsible, overrideCheckBox)

        # When local override is enabled, uncheck "Show Blueprint" and show local steps
        is_checked = overrideCheckBox.isChecked()
        if is_checked:
            if attrName == "override_pre_custom_steps":
                # Uncheck the show blueprint action
                self._uncheck_show_blueprint_action("pre")
                # Always update state and refresh
                self._showing_blueprint_pre = False
                self._refresh_pre_custom_steps_list()
            elif attrName == "override_post_custom_steps":
                # Uncheck the show blueprint action
                self._uncheck_show_blueprint_action("post")
                # Always update state and refresh
                self._showing_blueprint_post = False
                self._refresh_post_custom_steps_list()

    def _uncheck_show_blueprint_action(self, which):
        """Uncheck a Show Blueprint menu action by updating internal state.

        The actual menu action state will be synced when the menu is shown
        via _sync_blueprint_menu_state().

        Args:
            which: "pre" or "post" to indicate which action to uncheck
        """
        # Update internal state - menu will sync when shown
        if which == "pre":
            self._showing_blueprint_pre = False
        else:
            self._showing_blueprint_post = False

    def _sync_blueprint_menu_state(self):
        """Sync the Blueprint menu action states with internal tracking.

        Called when the Blueprint menu is about to show, to ensure the
        checkable actions reflect the current state.
        """
        try:
            # Sync pre action state
            pre_action = self.customStepTab.showBlueprintPre_action
            if pre_action is not None:
                pre_action.blockSignals(True)
                pre_action.setChecked(self._showing_blueprint_pre)
                pre_action.blockSignals(False)

            # Sync post action state
            post_action = self.customStepTab.showBlueprintPost_action
            if post_action is not None:
                post_action.blockSignals(True)
                post_action.setChecked(self._showing_blueprint_post)
                post_action.blockSignals(False)
        except (RuntimeError, AttributeError):
            # Actions may have been garbage collected
            pass

    def eventFilter(self, sender, event):
        if self.custom_step_event_filter(sender, event):
            return True
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
        for key in config:
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

    # def populateAvailableSynopticTabs(self):

    #     import mgear.shifter as shifter

    #     defPath = os.environ.get("MGEAR_SYNOPTIC_PATH", None)
    #     if not defPath or not os.path.isdir(defPath):
    #         defPath = shifter.SYNOPTIC_PATH

    #     # Sanity check for folder existence.
    #     if not os.path.isdir(defPath):
    #         return

    #     tabsDirectories = [
    #         name
    #         for name in os.listdir(defPath)
    #         if os.path.isdir(os.path.join(defPath, name))
    #     ]
    #     # Quick clean the first empty item
    #     if tabsDirectories and not tabsDirectories[0]:
    #         self.guideSettingsTab.available_listWidget.takeItem(0)

    #     itemsList = self.root.attr("synoptic").get().split(",")
    #     for tab in sorted(tabsDirectories):
    #         if tab not in itemsList:
    #             self.guideSettingsTab.available_listWidget.addItem(tab)

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



# Backwards compatibility aliases
MainGuide = Main
RigGuide = Rig
helperSlots = HelperSlots
guideSettingsTab = GuideSettingsTab
customStepTab = CustomStepTab
guideSettings = GuideSettings
