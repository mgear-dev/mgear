"""
Shifter's Component guide class.
"""
import ast
from functools import partial

import maya.cmds as cmds

# pyMel
import mgear.pymaya as pm
from mgear.pymaya import datatypes

# mgear
import mgear

from mgear.core import string
from mgear.core import node
from mgear.pymaya import versions

from mgear.core import dag, vector, transform, applyop, attribute, icon, pyqt

from mgear.shifter import guide, guide_manager
from . import chain_guide_initializer

from . import main_settings_ui as msui
from . import joint_names_ui as jnui

from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.anim_picker.gui import MAYA_OVERRIDE_COLOR


JOINT_NAME_DESCRIPTION = "jointNamesDescription"
JOINT_NAME_DESCRIPTION_CUSTOM = JOINT_NAME_DESCRIPTION + "_custom"
CTL_NAME_DESCRIPTION = "ctlNamesDescription"
CTL_NAME_DESCRIPTION_CUSTOM = CTL_NAME_DESCRIPTION + "_custom"
ALIAS_NAME_DESCRIPTION = "aliasNamesDescription"
ALIAS_NAME_DESCRIPTION_CUSTOM = ALIAS_NAME_DESCRIPTION + "_custom"

##########################################################
# COMPONENT GUIDE
##########################################################


class ComponentGuide(guide.Main):
    """Main class for component guide creation.

    This class handles all the parameters and objectDefs creation.
    It also know how to parse its own hierachy of object to retrieve position
    and transform.
    Finally it also now how to export itself as xml_node.

    Attributes:
        paramNames (list): List of parameter name cause it's actually important
            to keep them sorted.
        paramDefs (dic): Dictionary of parameter definition.
        values (dic): Dictionary of options values.
        valid (bool): We will check a few things and make sure the guide we are
            loading is up to date.
            If parameters or object are missing a warning message will be
                display and the guide should be updated.
        tra (dic): dictionary of global transform
        atra (list): list of global transform
        pos (dic): dictionary of global postion
        apos (list): list of global position
        prim (dic): dictionary of primitive
        blades (dic): dictionary of blades
        size (float): Size reference of the component. Default = .1
        save_transform (list): Transform of object name in this list will
            be saved
        save_primitive (list): Primitive of object name in this list will
            be saved
        save_blade (list): Normal and BiNormal of object will be saved
        minmax (dic): Define the min and max object for multi location objects

    """

    compType = "component"  # Component type
    compName = "component"  # Component default name
    compSide = "C"
    compIndex = 0  # Component default index

    description = ""  # Description of the component

    connectors = []
    compatible = []
    joint_names_description = []
    ctl_names_description = []
    alias_names_description = []
    ctl_grp = ""

    # ====================================================
    # Init method.
    def __init__(self):

        # Parameters names, definition and values.
        # List of parameter name cause it's actually important to keep
        # them sorted.
        self.paramNames = []
        # Dictionary of parameter definition.
        self.paramDefs = {}
        # Dictionary of options values.
        self.values = {}

        # We will check a few things and make sure the guide we are loading is
        # up to date.
        # If parameters or object are missing a warning message will be display
        # and the guide should be updated.
        self.valid = True

        self.root = None
        self.id = None

        # parent component identification
        self.parentComponent = None
        self.parentLocalName = None

        # direct child components
        self.child_components = []

        # List and dictionary used during the creation of the component
        self.tra = {}  # dictionary of global transform
        self.atra = []  # list of global transform
        self.pos = {}  # dictionary of global postion
        self.apos = []  # list of global position
        self.prim = {}  # dictionary of primitive
        self.blades = {}
        self.size = 0.1
        # self.root_size = None

        # List and dictionary used to define data of the guide that
        # should be saved
        # Transform of object name in this list will be saved
        self.save_transform = []
        # Primitive of object name in this list will be saved
        self.save_primitive = []
        # Normal and BiNormal of object will be saved
        self.save_blade = []
        # Define the min and max object for multi location objects
        self.minmax = {}
        self.minmax_blade = {}

        # store guide locators names
        self.guide_locators = []

        # Init the guide
        self.postInit()
        self.initialHierarchy()
        self.addParameters()

    def postInit(self):
        """Define the objects name and categories.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        self.save_transform = ["root"]
        return

    # ====================================================
    # OBJECTS AND PARAMETERS

    def initialHierarchy(self):
        """Initial hierachy.

        It's no more than the basic set of parameters and layout
        needed for the setting property.

        """
        # Parameters --------------------------------------
        # This are the necessary parameter for component guide definition
        self.pCompType = self.addParam("comp_type", "string", self.compType)
        self.pCompName = self.addParam("comp_name", "string", self.compName)
        self.pCompSide = self.addParam("comp_side", "string", self.compSide)
        self.pCompIndex = self.addParam("comp_index", "long", self.compIndex, 0)
        self.pConnector = self.addParam("connector", "string", "standard")
        self.pUIHost = self.addParam("ui_host", "string", "")
        self.pCtlGroup = self.addParam("ctlGrp", "string", "")
        self.pJointNames = self.addParam("joint_names", "string", "")
        if self.joint_names_description:
            self.pJointNamesDescription = self.addParam(
                JOINT_NAME_DESCRIPTION, "string", str(self.joint_names_description)
            )
            self.pJointNamesDescription_custom = self.addParam(
                JOINT_NAME_DESCRIPTION_CUSTOM,
                "string",
                str(self.joint_names_description),
            )
        if self.ctl_names_description:
            self.pCtlNamesDescription = self.addParam(
                CTL_NAME_DESCRIPTION, "string", str(self.ctl_names_description)
            )
            self.pCtlNamesDescription_custom = self.addParam(
                CTL_NAME_DESCRIPTION_CUSTOM, "string", str(self.ctl_names_description)
            )

        if self.alias_names_description:
            self.pAliasNamesDescription = self.addParam(
                ALIAS_NAME_DESCRIPTION, "string", str(self.alias_names_description)
            )
            self.pAliasNamesDescription_custom = self.addParam(
                ALIAS_NAME_DESCRIPTION_CUSTOM, "string", str(self.alias_names_description)
            )
        self.pJointRotOffX = self.addParam(
            "joint_rot_offset_x", "double", 0.0, -360.0, 360.0
        )
        self.pJointRotOffY = self.addParam(
            "joint_rot_offset_y", "double", 0.0, -360.0, 360.0
        )
        self.pJointRotOffZ = self.addParam(
            "joint_rot_offset_z", "double", 0.0, -360.0, 360.0
        )

        self.pOverrideComponentColor = self.addParam("Override_Color", "bool", False)
        self.pOverrideUseRGBColor = self.addParam("Use_RGB_Color", "bool", False)

        self.pOverrideColorIndexfk = self.addParam("color_fk", "long", 6, 0, 31)
        self.pOverrideColorIndexik = self.addParam("color_ik", "long", 18, 0, 31)

        self.pLColorfk = self.addColorParam("RGB_fk", [0, 0, 1])
        self.pLColorik = self.addColorParam("RGB_ik", [0, 0.25, 1])

        # Items -------------------------------------------
        typeItems = [self.compType, self.compType]
        for type in self.compatible:
            typeItems.append(type)
            typeItems.append(type)

        connectorItems = ["standard", "standard"]
        for item in self.connectors:
            connectorItems.append(item)
            connectorItems.append(item)

    def addObjects(self):
        """Create the objects of the guide.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        self.root = self.addRoot()

    def addParameters(self):
        """Create the parameter definitions of the guide.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    def postDraw(self):
        """Add anything to the guide after drawing it.

        Note:
            REIMPLEMENT. This method should be reimplemented in each component.

        """
        return

    def get_divisions(self):
        """Get the divisions to sample a Fcurve parameter definition.

        Note:
            REIMPLEMENT. This method should only if the component is using
            Fcurve paramDef.

        """
        return

    # ====================================================
    # SET / GET
    def setFromHierarchy(self, root):
        """Set the component guide from given hierarchy.

        Args:
            root (dagNode): The root of the hierarchy to parse.

        """
        self.root = root
        self.model = self.root.getParent(generations=-1)

        # ---------------------------------------------------
        # First check and set the settings
        if not self.root.hasAttr("comp_type"):
            mgear.log(
                "%s is not a proper guide." % self.root.longName(), mgear.sev_error
            )
            self.valid = False
            return

        self.setParamDefValuesFromProperty(self.root)

        # ---------------------------------------------------
        # Then get the objects
        for name in self.save_transform:
            if "#" in name:
                i = 0
                while not self.minmax[name].max > 0 or i < self.minmax[name].max:
                    localName = string.replaceSharpWithPadding(name, i)

                    node = dag.findChild(self.model, self.getName(localName))
                    if not node:
                        break

                    self.tra[localName] = node.getMatrix(worldSpace=True)
                    self.atra.append(node.getMatrix(worldSpace=True))
                    self.pos[localName] = node.getTranslation(space="world")
                    self.apos.append(node.getTranslation(space="world"))
                    self.guide_locators.append(node.name())

                    i += 1

                if i < self.minmax[name].min:
                    mgear.log(
                        "Minimum of object requiered for "
                        + name
                        + " hasn't been reached!!",
                        mgear.sev_warning,
                    )
                    self.valid = False
                    continue

            else:
                node = dag.findChild(self.model, self.getName(name))
                if not node:
                    mgear.log(
                        "Object missing : %s" % (self.getName(name)), mgear.sev_warning
                    )
                    self.valid = False
                    continue

                self.tra[name] = node.getMatrix(worldSpace=True)
                self.atra.append(node.getMatrix(worldSpace=True))
                self.pos[name] = node.getTranslation(space="world")
                self.apos.append(node.getTranslation(space="world"))
                self.guide_locators.append(node.name())

        for name in self.save_blade:
            if "#" in name:
                i = 0
                while (
                    not self.minmax_blade[name].max > 0
                    or i < self.minmax_blade[name].max
                ):
                    localName = string.replaceSharpWithPadding(name, i)

                    node = dag.findChild(self.model, self.getName(localName))
                    if not node:
                        break

                    self.blades[localName] = vector.Blade(
                        node.getMatrix(worldSpace=True)
                    )
                    i += 1

                if i < self.minmax_blade[name].min:
                    mgear.log(
                        "Minimum of object requiered for "
                        + localName
                        + " hasn't been reached!!",
                        mgear.sev_warning,
                    )
                    self.valid = False
                    continue
            else:
                node = dag.findChild(self.model, self.getName(name))
                if not node:
                    mgear.log(
                        "Object missing : %s" % (self.getName(name)), mgear.sev_warning
                    )
                    self.valid = False
                    continue

                self.blades[name] = vector.Blade(node.getMatrix(worldSpace=True))

        self.size = self.getSize()

    def set_from_dict(self, c_dict):

        self.setParamDefValuesFromDict(c_dict["param_values"])
        self.child_components = c_dict["child_components"]

        temp_dict = {}
        for k in c_dict["tra"].keys():
            temp_dict[k] = datatypes.Matrix(c_dict["tra"][k])
        self.tra = temp_dict

        self.atra = [datatypes.Matrix(t) for t in c_dict["atra"]]

        temp_dict = {}
        for k in c_dict["pos"].keys():
            temp_dict[k] = datatypes.Vector(c_dict["pos"][k])
        self.pos = temp_dict

        self.apos = [datatypes.Vector(v) for v in c_dict["apos"]]
        for b in c_dict["blade"].keys():
            self.blades[b] = vector.Blade(datatypes.Matrix(c_dict["blade"][b]))

        self.size = self.getSize()

    # TODO: Need to store all his children in order to import partial in an
    # existing guide
    def get_guide_template_dict(self):
        c_dict = {}
        c_dict["child_components"] = []
        c_dict["param_values"] = self.get_param_values()

        temp_dict = {}
        for k in self.tra.keys():
            temp_dict[k] = self.tra[k].get()
        c_dict["tra"] = temp_dict

        c_dict["atra"] = [t.get() for t in self.atra]
        temp_dict = {}
        for k in self.pos.keys():
            temp_dict[k] = self.pos[k].get()
        c_dict["pos"] = temp_dict

        c_dict["apos"] = [p.get() for p in self.apos]
        c_dict["blade"] = self.get_blades_transform()

        # NOTE: what happens if there is more than 1 component children of the
        # guide root?
        if self.parentComponent:  # if parent is the root of guide will be None
            c_dict["parent_fullName"] = self.parentComponent.fullName
            c_dict["parent_localName"] = self.parentLocalName
        else:
            c_dict["parent_fullName"] = None
            c_dict["parent_localName"] = None

        return c_dict

    def get_blades_transform(self):
        b_tra = {}
        for b in self.blades.keys():
            b_tra[b] = self.blades[b].transform.get()

        return b_tra

    # ====================================================
    # DRAW

    def draw(self, parent):
        """Draw the guide in the scene.

        Args:
            parent (dagNode): the parent of the component.

        """
        self.parent = parent
        self.setIndex(self.parent)
        self.addObjects()
        self.postDraw()
        pm.select(self.root)

        # TODO: add function to scale the points of the icons
        # Set the size of the root
        # self.root.size = self.root_size

    def drawFromUI(self, parent, showUI=True):
        """Draw the guide in the scene from the UI command.

        Args:
            parent (dagNode): the parent of the component.

        """
        if not self.modalPositions():
            mgear.log("aborded", mgear.sev_warning)
            return False

        self.draw(parent)
        transform.resetTransform(self.root, r=False, s=False)

        # reset size
        self.root.scale.set(1, 1, 1)

        if showUI:
            guide_manager.inspect_settings()

        return True

    def modalPositions(self):
        """Launch a modal dialog to set position of the guide."""
        self.sections_number = None
        self.dir_axis = None
        self.spacing = None

        for name in self.save_transform:

            if "#" in name:

                init_window = chain_guide_initializer.exec_window()
                if init_window:
                    self.sections_number = init_window.sections_number
                    self.dir_axis = init_window.dir_axis
                    self.spacing = init_window.spacing

                # None the action is cancel
                else:
                    return False
                if self.sections_number:
                    if self.dir_axis == 0:  # X
                        offVec = datatypes.Vector(self.spacing, 0, 0)
                    elif self.dir_axis == 3:  # -X
                        offVec = datatypes.Vector(self.spacing * -1, 0, 0)
                    elif self.dir_axis == 1:  # Y
                        offVec = datatypes.Vector(0, self.spacing, 0)
                    elif self.dir_axis == 4:  # -Y
                        offVec = datatypes.Vector(0, self.spacing * -1, 0)
                    elif self.dir_axis == 2:  # Z
                        offVec = datatypes.Vector(0, 0, self.spacing)
                    elif self.dir_axis == 5:  # -Z
                        offVec = datatypes.Vector(0, 0, self.spacing * -1)

                    newPosition = datatypes.Vector(0, 0, 0)
                    for i in range(self.sections_number):
                        newPosition = offVec + newPosition
                        localName = string.replaceSharpWithPadding(name, i)
                        self.tra[localName] = transform.getTransformFromPos(newPosition)
        return True

    # ====================================================
    # UPDATE

    def setIndex(self, model):
        """Update the component index to get the next valid one.

        Args:
            model (dagNode): The parent model of the guide.

        """
        self.model = model.getParent(generations=-1)

        # Find next index available
        while True:
            obj = dag.findChild(self.model, self.getName("root"))
            if not obj or (self.root and obj == self.root):
                break
            self.setParamDefValue("comp_index", self.values["comp_index"] + 1)

    def symmetrize(self):
        """Inverse the transform of each element of the guide."""

        if self.values["comp_side"] not in ["R", "L"]:
            mgear.log("Can't symmetrize central component", mgear.sev_error)
            return False
        for name, paramDef in self.paramDefs.items():
            if paramDef.valueType == "string":
                self.setParamDefValue(name, string.convertRLName(self.values[name]))
        for name, t in self.tra.items():
            self.tra[name] = transform.getSymmetricalTransform(t)
        for name, blade in self.blades.items():
            self.blades[name] = vector.Blade(
                transform.getSymmetricalTransform(blade.transform)
            )

        return True

    def rename(self, root, newName, newSide, newIndex):
        """Rename the component.

        Args:
            root (dagNode): The parent of the component
            newName (str): The new name.
            newSide (str): Side of the component.
            newIndex (int): index of the comonent.

        """
        self.parent = root

        # store old properties
        oldIndex = self.parent.attr("comp_index").get()
        oldSide = self.parent.attr("comp_side").get()
        oldName = self.parent.attr("comp_name").get()
        oldSideIndex = oldSide + str(oldIndex)

        # change attr side in root
        self.parent.attr("comp_name").set(newName)
        self.parent.attr("comp_side").set(newSide)
        # set new index and update to the next valid
        self.setParamDefValue("comp_name", newName)
        self.setParamDefValue("comp_side", newSide)

        self.setParamDefValue("comp_index", newIndex)
        self.setIndex(self.parent)

        self.parent.attr("comp_index").set(self.values["comp_index"])

        # objList = dag.findComponentChildren(self.parent,
        #                                     oldName, oldSideIndex)
        # NOTE: Experimenta  using findComponentChildren3
        objList = dag.findComponentChildren3(self.parent, oldName, oldSideIndex)
        newSideIndex = newSide + str(self.values["comp_index"])
        objList.append(self.parent)
        for obj in objList:
            tmpObjName = obj.name().split("|")[-1]
            suffix = tmpObjName.split("_")[-1]
            # if len(tmpObjName.split("_")) == 3:
            #     new_name = "_".join([newName, newSideIndex, suffix])
            #     print "new name = " + new_name
            # else:
            subIndex = tmpObjName.split("_")[-2]
            if subIndex == oldSideIndex:
                new_name = "_".join([newName, newSideIndex, suffix])
            else:
                new_name = "_".join([newName, newSideIndex, subIndex, suffix])
            pm.rename(obj, new_name)

    # ====================================================
    # ELEMENTS

    def connect_x_ray(self, loc):
        for oShape in loc.getShapes():
            # connecting the always draw shapes
            if versions.current() >= 20220000 and self.model.hasAttr("guide_x_ray") and not oShape.attr("alwaysDrawOnTop").listConnections():
                pm.connectAttr(
                    self.model.guide_x_ray, oShape.attr("alwaysDrawOnTop")
                )

    def addRoot(self):
        """Add a root object to the guide.

        This method can initialize the object or draw it.
        Root object is a simple transform with a specific display and a setting
        property.

        Returns:
            dagNode: The root

        """
        if "root" not in self.tra.keys():
            self.tra["root"] = transform.getTransformFromPos(datatypes.Vector(0, 0, 0))

        self.root = icon.guideRootIcon(
            self.parent, self.getName("root"), color=13, m=self.tra["root"]
        )

        # Add Parameters from parameter definition list.
        for scriptName in self.paramNames:
            paramDef = self.paramDefs[scriptName]
            paramDef.create(self.root)

        self.connect_x_ray(self.root)

        return self.root

    def add_ref_axis(self, loc, vis_attr=None, inverted=False, width=0.5):
        """Add a visual reference axis to a locator or root of the guide

        Shifter guides usually only take in consideration the position of the
        guide and the blade orientation to calculate all the orientation in
        the component. This design allows a quick placement without worry
        about orientation.
        But in some situation is more combinient to take the full rotation of
        the locator/root to be used in the rig build.
        This visual reference helps to improve readability and marks clearly
        the elements from where is used the full rotation

        Args:
            loc (dagNode): locator or guide root
            vis_attr (attr, optional): attribute to activate or deactivate
                the visual ref
            inverted (bool, optional): if we need to negate the attr
        """
        axis = icon.axis(
            loc, self.getName("axis"), width=width, m=loc.getMatrix(worldSpace=True)
        )
        pm.parent(axis, world=True)
        pm.makeIdentity(axis, apply=True, t=False, r=False, s=True, n=0)
        if vis_attr and inverted:
            vis_node = node.createReverseNode(vis_attr)
            vis_attr = vis_node.outputX

        for shp in axis.getShapes():
            if vis_attr:
                pm.connectAttr(vis_attr, shp.attr("visibility"))
            shp.isHistoricallyInteresting.set(False)

            shp.lineWidth.set(3)
            loc.addChild(shp, add=True, shape=True)
        self.connect_x_ray(loc)
        pm.delete(axis)

    def add_ref_joint(self, loc, vis_attr=None, width=0.5):
        """Add a visual reference joint to a locator or root of the guide

        Args:
            loc (dagNode): locator or guide root
            vis_attr (attr list, optional): attribute to activate or deactivate
                the visual ref. Should be a list [attr1, attr2]
            width (float, optional): icon width
        """
        add_ref_joint = icon.sphere(
            loc,
            self.getName("joint"),
            width=width,
            color=[0, 1, 0],
            m=loc.getMatrix(worldSpace=True),
        )
        pm.parent(add_ref_joint, world=True)
        pm.makeIdentity(add_ref_joint, apply=True, t=False, r=False, s=True, n=0)

        for shp in add_ref_joint.getShapes():
            if vis_attr:
                node.createMulNode(vis_attr[0], vis_attr[1], shp.attr("visibility"))
            shp.isHistoricallyInteresting.set(False)

            loc.addChild(shp, add=True, shape=True)
        self.connect_x_ray(loc)
        pm.delete(add_ref_joint)

    def addLoc(self, name, parent, position=None, color=17, width=.5):
        """Add a loc object to the guide.

        This mehod can initialize the object or draw it.
        Loc object is a simple null to define a position or a tranformation in
        the guide.

        Args:
            name (str): Local name of the element.
            parent (dagNode): The parent of the element.
            position (vector): The default position of the element.

        Returns:
            dagNode: The locator object.

        """
        if name not in self.tra.keys():
            self.tra[name] = transform.getTransformFromPos(position)
        if name in self.prim.keys():
            # this functionality is not implemented. The actual design from
            # softimage Gear should be review to fit in Maya.
            loc = self.prim[name].create(
                parent,
                self.getName(name),
                self.tra[name],
                color=color,
                width=width
            )
        else:
            loc = icon.guideLocatorIcon(
                parent,
                self.getName(name),
                color=color,
                m=self.tra[name],
                width=width
            )
        self.connect_x_ray(loc)
        return loc

    def addLocMulti(self, name, parent, updateParent=True):
        """Add multiple loc objects to the guide.

        This method can initialize the object or draw it.
        Loc object is a simple null to define a position or a tranformation in
        the guide.

        Args:
            name (str): Local name of the element.
            parent (dagNode): The parent of the element.
            minimum (int): The minimum number of loc.
            maximum (int): The maximum number of loc.
            updateParent (bool): if True update the parent reference. False,
                keep the same for all loc.

        Returns:
            list of dagNode: The created loc objects in a list.

        """
        if "#" not in name:
            mgear.log(
                "You need to put a '#' in the name of multiple location.",
                mgear.sev_error,
            )
            return False

        locs = []
        i = 0
        while True:
            localName = string.replaceSharpWithPadding(name, i)
            if localName not in self.tra.keys():
                break

            loc = icon.guideLocatorIcon(
                parent, self.getName(localName), color=17, m=self.tra[localName]
            )
            self.connect_x_ray(loc)
            locs.append(loc)
            if updateParent:
                parent = loc

            i += 1
        return locs

    def addBlade(self, name, parentPos, parentDir, wUp=None):
        """Add a blade object to the guide.

        This mehod can initialize the object or draw it.
        Blade object is a 3points curve to define a plan in the guide.

        Args:
            name (str): Local name of the element.
            parentPos (dagNode): The parent of the element.
            parentDir (dagNode): The direction constraint of the element.
            wUp (dagNode, optional): world up node. If None will be self.root

        Returns:
            dagNode: The created blade curve.

        """
        if name not in self.blades.keys():
            self.blades[name] = vector.Blade(
                transform.getTransformFromPos(datatypes.Vector(0, 0, 0))
            )
            offset = False
        else:
            offset = True

        if not wUp:
            wUp = self.root

        blade = icon.guideBladeIcon(
            parent=parentPos,
            name=self.getName(name),
            lenX=0.5,
            color=[0, 0, 1],
            m=self.blades[name].transform,
        )
        aim_cns = applyop.aimCns(
            blade,
            parentDir,
            axis="xy",
            wupType=2,
            wupVector=[0, 1, 0],
            wupObject=wUp,
            maintainOffset=offset,
        )
        pnt_cns = pm.pointConstraint(parentPos, blade)

        aim_cns.isHistoricallyInteresting.set(False)
        pnt_cns.isHistoricallyInteresting.set(False)

        offsetAttr = attribute.addAttribute(
            blade, "bladeRollOffset", "float", aim_cns.attr("offsetX").get()
        )
        pm.connectAttr(offsetAttr, aim_cns.attr("offsetX"))
        scaleAttr = attribute.addAttribute(
            blade, "bladeScale", "float", 1, minValue=0.1, maxValue=100
        )
        for axis in "xyz":
            pm.connectAttr(scaleAttr, blade.attr("s{}".format(axis)))
        attribute.lockAttribute(
            blade,
            attributes=[
                "tx",
                "ty",
                "tz",
                "rx",
                "ry",
                "rz",
                "sx",
                "sy",
                "sz",
                "v",
                "ro",
            ],
        )

        self.connect_x_ray(blade)
        return blade

    def addDispCurve(self, name, centers=[], degree=1):
        """Add a display curve object to the guide.

        Display curve object is a simple curve to show the connection between
        different guide element..

        Args:
            name (str): Local name of the element.
            centers (list of dagNode):  List of object to define the curve.
            degree (int): Curve degree. Default 1 = lineal.

        Returns:
            dagNode: The newly creted curve.

        """
        disp_crv = icon.connection_display_curve(self.getName(name), centers, degree)
        self.connect_x_ray(disp_crv)
        return disp_crv


    # ====================================================
    # MISC
    def getObjects(self, model, includeShapes=True):
        """Get the objects of the component.

        Args:
            model(dagNode): The root of the component.
            includeShapes (boo): If True, will include the shapes.

        Returns:
            list of dagNode: The list of the objects.

        """
        objects = {}
        if includeShapes:
            children = pm.listRelatives(model, ad=True)
        else:
            children = pm.listRelatives(model, ad=True, typ="transform")
        pm.select(children)
        for child in pm.ls(self.fullName + "_*", selection=True):
            objects[
                child[child.index(self.fullName + "_") + len(self.fullName + "_") :]
            ] = child

        return objects

    def getObjects2(self, model, includeShapes=True):
        """Get the objects of the component.

        Args:
            model(dagNode): The root of the component.
            includeShapes (boo): If True, will include the shapes.

        Returns:
            list of dagNode: The list of the objects.

        """
        objects = {}
        if includeShapes:
            children = [
                pm.PyNode(x)
                for x in cmds.listRelatives(model.longName(), ad=True, fullPath=True)
            ]
        else:
            children = [
                pm.PyNode(x)
                for x in cmds.listRelatives(
                    model.longName(), ad=True, typ="transform", fullPath=True
                )
            ]
        for child in children:
            cName = child.longName()
            if cName.startswith(self.fullName):
                objects[cName.split("_")[-1]] = child

        return objects

    def getObjects3(self, model):
        """
        NOTE: Experimental function
        Get the objects of the component.
        This version only get the transforms by Name using Maya Cmds

        Args:
            model(dagNode): The root of the component.

        Returns:
            list of dagNode: The list of the objects.

        """
        objects = {}

        for child in cmds.ls(self.fullName + "_*", type="transform"):
            if pm.PyNode(child).getParent(-1) == model:
                objects[
                    child[child.index(self.fullName + "_") + len(self.fullName + "_") :]
                ] = child

        return objects

    def addMinMax(self, name, minimum=1, maximum=-1):
        """Add minimun and maximum number of locator

        When we use the modal menu.

        """
        if "#" not in name:
            mgear.log(
                "Invalid definition for min/max. You should have a '#' in " "the name",
                mgear.sev_error,
            )
        self.minmax[name] = MinMax(minimum, maximum)

    def addMinMaxBlade(self, name, minimum=1, maximum=-1):
        """Add minimun and maximum number of blades

        When we use the modal menu.

        """
        if "#" not in name:
            mgear.log(
                "Invalid definition for min/max. You should have a '#' in " "the name",
                mgear.sev_error,
            )
        self.minmax_blade[name] = MinMax(minimum, maximum)

    def getSize(self):
        """Get the size of the component.

        Returns:
            float: the size

        """
        size = 0.01
        for pos in self.apos:
            d = vector.getDistance(self.pos["root"], pos)
            size = max(size, d)
        size = max(size, 0.01)

        return size

    def getName(self, name):
        """Return the fullname of given element of the component.

        Args:
            name (str): Localname of the element.

        Returns:
            str: Element fullname.
        """
        return self.fullName + "_" + name

    def getFullName(self):
        """Return the fullname of the component.

        Returns:
            str: Component fullname.

        """
        return (
            self.values["comp_name"]
            + "_"
            + self.values["comp_side"]
            + str(self.values["comp_index"])
        )

    def getType(self):
        """Return the type of the component.

        Returns:
            str: component type.

        """
        return self.compType

    def getObjectNames(self):
        """Get the objects names of the component

        Returns:
            set: The names set.

        """
        names = set()
        names.update(self.save_transform)
        names.update(self.save_primitive)
        names.update(self.save_blade)

        return names

    def getVersion(self):
        """Get the version of the component.

        Returns:
            str: versionof the component.

        """
        return ".".join([str(i) for i in self.version])

    fullName = property(getFullName)
    type = property(getType)
    objectNames = property(getObjectNames)


##########################################################
# OTHER CLASSES
##########################################################


class MinMax(object):
    """
    Minimun and maximum class.
    This class is used in addMinMax method.

    Attributes:
        minimum (int): minimum.
        maximum (int): maximum.
    """

    def __init__(self, minimum=1, maximum=-1):
        self.min = minimum
        self.max = maximum


##########################################################
# Setting Page
##########################################################


class mainSettingsTab(QtWidgets.QDialog, msui.Ui_Form):

    # ============================================
    # INIT
    def __init__(self, parent=None):
        super(mainSettingsTab, self).__init__()
        self.setupUi(self)


class NameDescriptor(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(NameDescriptor, self).__init__()

        self.setMinimumWidth(200)
        self.descriptors_lineEdit = []
        self.descriptors_label = []
        self.descriptors_layout = []
        self.main_layout = QtWidgets.QVBoxLayout(self)

    def create_descriptor(self, descriptor, d_custom):
        """Create descriptor widgets

        Args:
            descriptor (str): Name of the object descriptor
            d_custom (str): Custom name of the object descriptor when modified
                by the user
        """
        # widgets
        label = QtWidgets.QLabel(descriptor.capitalize())
        lineedit = QtWidgets.QLineEdit(d_custom)
        button = QtWidgets.QPushButton("Reset")

        self.descriptors_lineEdit.append(lineedit)
        self.descriptors_label.append(label)

        # layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(lineedit)
        layout.addWidget(button)

        # signal
        def reset_button():
            lineedit.setText(descriptor)
            self.set_descriptors_attr()

        button.clicked.connect(reset_button)
        lineedit.editingFinished.connect(self.set_descriptors_attr)

        self.descriptors_layout.append(layout)

    def create_widgets(self):
        for e, d in enumerate(self.d_names):
            self.create_descriptor(d, self.d_custom_names[e])

    def create_layouts(self):

        for d in self.descriptors_layout:
            self.main_layout.addLayout(d)

        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.main_layout.addItem(spacerItem)

    def set_descriptors_attr(self):
        descriptors_attr_val = []
        for e, d in enumerate(self.descriptors_lineEdit):
            # we use the label to determine if the name should filter  "#"
            if "#" in self.descriptors_label[e].text():
                d_name = string.normalize_with_padding(d.text())
            else:
                d_name = string.normalize2(d.text())
            d.setText(d_name)
            descriptors_attr_val.append(d_name)
            self.root.attr(self.descriptor_name_custom).set(str(descriptors_attr_val))


class jointNameDescriptor(NameDescriptor):
    def __init__(self, parent=None):
        super(jointNameDescriptor, self).__init__()

        self.root = pm.selected()[0]
        self.d_names = self.root.attr(JOINT_NAME_DESCRIPTION).get()
        self.d_names = ast.literal_eval(self.d_names)
        self.descriptor_name_custom = JOINT_NAME_DESCRIPTION_CUSTOM
        self.d_custom_names = self.root.attr(self.descriptor_name_custom).get()
        self.d_custom_names = ast.literal_eval(self.d_custom_names)

        self.setWindowTitle("joint Name Descriptor")

        self.create_widgets()
        self.create_layouts()


class CtlNameDescriptor(NameDescriptor):
    def __init__(self, parent=None):
        super(CtlNameDescriptor, self).__init__()

        self.root = pm.selected()[0]
        self.d_names = self.root.attr(CTL_NAME_DESCRIPTION).get()
        self.d_names = ast.literal_eval(self.d_names)
        self.descriptor_name_custom = CTL_NAME_DESCRIPTION_CUSTOM
        self.d_custom_names = self.root.attr(self.descriptor_name_custom).get()
        self.d_custom_names = ast.literal_eval(self.d_custom_names)

        self.setWindowTitle("CTL Name Descriptor")

        self.create_widgets()
        self.create_layouts()


class AliasNameDescriptor(NameDescriptor):
    def __init__(self, parent=None):
        super(AliasNameDescriptor, self).__init__()

        self.root = pm.selected()[0]
        self.d_names = self.root.attr(ALIAS_NAME_DESCRIPTION).get()
        self.d_names = ast.literal_eval(self.d_names)
        self.descriptor_name_custom = ALIAS_NAME_DESCRIPTION_CUSTOM
        self.d_custom_names = self.root.attr(self.descriptor_name_custom).get()
        self.d_custom_names = ast.literal_eval(self.d_custom_names)

        self.setWindowTitle("Space Alias Name Descriptor")

        self.create_widgets()
        self.create_layouts()


class componentMainSettings(QtWidgets.QDialog, guide.helperSlots):
    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(componentMainSettings, self).__init__()
        # the inspectSettings function set the current selection to the
        # component root before open the settings dialog
        self.root = pm.selected()[0]

        self.mainSettingsTab = mainSettingsTab()
        if self.root.hasAttr(JOINT_NAME_DESCRIPTION):
            self.jointNameDescriptor = jointNameDescriptor()
        if self.root.hasAttr(CTL_NAME_DESCRIPTION):
            self.CtlNameDescriptor = CtlNameDescriptor()
        if self.root.hasAttr(ALIAS_NAME_DESCRIPTION):
            self.AliasNameDescriptor = AliasNameDescriptor()

        self.create_controls()
        self.populate_controls()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def create_controls(self):
        """
        Create the controls for the component base

        """
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("settings_tab")

        # Close Button
        self.close_button = QtWidgets.QPushButton("Close")

    def populate_controls(self):
        """Populate Controls attribute values

        Populate the controls values from the custom attributes
        of the component.

        """
        # populate tab
        self.tabs.insertTab(0, self.mainSettingsTab, "Main Settings")

        # populate main settings
        self.mainSettingsTab.name_lineEdit.setText(self.root.attr("comp_name").get())
        sideSet = ["C", "L", "R"]
        sideIndex = sideSet.index(self.root.attr("comp_side").get())
        self.mainSettingsTab.side_comboBox.setCurrentIndex(sideIndex)
        self.mainSettingsTab.componentIndex_spinBox.setValue(
            self.root.attr("comp_index").get()
        )
        if self.root.attr("useIndex").get():
            self.mainSettingsTab.useJointIndex_checkBox.setCheckState(QtCore.Qt.Checked)
        else:
            self.mainSettingsTab.useJointIndex_checkBox.setCheckState(
                QtCore.Qt.Unchecked
            )
        self.mainSettingsTab.parentJointIndex_spinBox.setValue(
            self.root.attr("parentJointIndex").get()
        )
        self.mainSettingsTab.host_lineEdit.setText(self.root.attr("ui_host").get())
        self.mainSettingsTab.subGroup_lineEdit.setText(self.root.attr("ctlGrp").get())
        self.mainSettingsTab.joint_offset_x_doubleSpinBox.setValue(
            self.root.attr("joint_rot_offset_x").get()
        )
        self.mainSettingsTab.joint_offset_y_doubleSpinBox.setValue(
            self.root.attr("joint_rot_offset_y").get()
        )
        self.mainSettingsTab.joint_offset_z_doubleSpinBox.setValue(
            self.root.attr("joint_rot_offset_z").get()
        )

        # testing adding custom color per component
        self.mainSettingsTab.overrideColors_checkBox.setCheckState(
            QtCore.Qt.Checked if self.root.Override_Color.get() else QtCore.Qt.Unchecked
        )

        self.mainSettingsTab.useRGB_checkBox.setCheckState(
            QtCore.Qt.Checked if self.root.Use_RGB_Color.get() else QtCore.Qt.Unchecked
        )

        tab = self.mainSettingsTab

        index_widgets = (
            (tab.color_fk_spinBox, tab.color_fk_label, "color_fk"),
            (tab.color_ik_spinBox, tab.color_ik_label, "color_ik"),
        )

        rgb_widgets = (
            (tab.RGB_fk_pushButton, tab.RGB_fk_slider, "RGB_fk"),
            (tab.RGB_ik_pushButton, tab.RGB_ik_slider, "RGB_ik"),
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

        self.toggleRgbIndexWidgets(
            tab.useRGB_checkBox,
            (w for i in index_widgets for w in i[:2]),
            (w for i in rgb_widgets for w in i[:2]),
            "Use_RGB_Color",
            tab.useRGB_checkBox.isChecked(),
        )

        self.refresh_controls()

        # joint names tab
        if self.root.hasAttr(JOINT_NAME_DESCRIPTION):
            self.tabs.insertTab(2, self.jointNameDescriptor, "Joints Description Names")
            ctl_tab = 3
        else:
            ctl_tab = 2
        # ctl names tab
        if self.root.hasAttr(CTL_NAME_DESCRIPTION):
            self.tabs.insertTab(
                ctl_tab, self.CtlNameDescriptor, "Ctl Description Names"
            )
            ctl_tab += 1
        # alias names tab
        if self.root.hasAttr(ALIAS_NAME_DESCRIPTION):
            self.tabs.insertTab(
                ctl_tab, self.AliasNameDescriptor, "Space Alias Description Names"
            )

    def refresh_controls(self):
        joint_names = [
            name.strip() for name in self.root.attr("joint_names").get().split(",")
        ]
        if any(joint_names):
            summary = "<b>({0} set)</b>".format(sum(map(bool, joint_names)))
        else:
            summary = "(None)"
        self.mainSettingsTab.jointNames_label.setText("Joint Names " + summary)

    def create_layout(self):
        """
        Create the layout for the component base settings

        """
        return

    def create_connections(self):
        """
        Create the slots connections to the controls functions

        """
        self.close_button.clicked.connect(self.close_settings)

        self.mainSettingsTab.name_lineEdit.editingFinished.connect(
            self.updateComponentName
        )
        self.mainSettingsTab.side_comboBox.currentIndexChanged.connect(
            self.updateComponentName
        )
        self.mainSettingsTab.componentIndex_spinBox.valueChanged.connect(
            self.updateComponentName
        )
        self.mainSettingsTab.useJointIndex_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.mainSettingsTab.useJointIndex_checkBox,
                "useIndex",
            )
        )
        self.mainSettingsTab.parentJointIndex_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.mainSettingsTab.parentJointIndex_spinBox,
                "parentJointIndex",
            )
        )
        self.mainSettingsTab.host_pushButton.clicked.connect(
            partial(self.updateHostUI, self.mainSettingsTab.host_lineEdit, "ui_host")
        )
        self.mainSettingsTab.subGroup_lineEdit.editingFinished.connect(
            partial(
                self.updateLineEdit, self.mainSettingsTab.subGroup_lineEdit, "ctlGrp"
            )
        )
        self.mainSettingsTab.jointNames_pushButton.clicked.connect(
            self.joint_names_dialog
        )

        self.mainSettingsTab.joint_offset_x_doubleSpinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.mainSettingsTab.joint_offset_x_doubleSpinBox,
                "joint_rot_offset_x",
            )
        )
        self.mainSettingsTab.joint_offset_y_doubleSpinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.mainSettingsTab.joint_offset_y_doubleSpinBox,
                "joint_rot_offset_y",
            )
        )
        self.mainSettingsTab.joint_offset_z_doubleSpinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.mainSettingsTab.joint_offset_z_doubleSpinBox,
                "joint_rot_offset_z",
            )
        )

        tab = self.mainSettingsTab

        index_widgets = (
            (tab.color_fk_spinBox, tab.color_fk_label, "color_fk"),
            (tab.color_ik_spinBox, tab.color_ik_label, "color_ik"),
        )

        rgb_widgets = (
            (tab.RGB_fk_pushButton, tab.RGB_fk_slider, "RGB_fk"),
            (tab.RGB_ik_pushButton, tab.RGB_ik_slider, "RGB_ik"),
        )

        for spinBox, label, source_attr in index_widgets:
            spinBox.valueChanged.connect(
                partial(self.updateIndexColorWidgets, spinBox, source_attr, label)
            )

        for button, slider, source_attr in rgb_widgets:
            button.clicked.connect(
                partial(self.rgbColorEditor, button, source_attr, slider)
            )
            slider.valueChanged.connect(
                partial(self.rgbSliderValueChanged, button, source_attr)
            )

        tab.useRGB_checkBox.stateChanged.connect(
            partial(
                self.toggleRgbIndexWidgets,
                tab.useRGB_checkBox,
                tuple(w for i in index_widgets for w in i[:2]),
                tuple(w for i in rgb_widgets for w in i[:2]),
                "Use_RGB_Color",
            )
        )

        tab.overrideColors_checkBox.stateChanged.connect(
            partial(self.updateCheck, tab.overrideColors_checkBox, "Override_Color")
        )

    def joint_names_dialog(self):
        dialog = JointNames(self.root, self)
        dialog.setWindowTitle(self.windowTitle())
        dialog.attributeChanged.connect(self.refresh_controls)
        dialog.show()


class JointNames(QtWidgets.QDialog, jnui.Ui_Form):
    attributeChanged = QtCore.Signal()

    def __init__(self, root, parent=None):
        super(JointNames, self).__init__(parent)
        self.root = root

        self.setupUi(self)

        self.populate_controls()
        self.apply_names()
        self.create_connections()

    def populate_controls(self):
        jointNames = self.root.attr("joint_names").get().split(",")
        if jointNames[-1]:
            jointNames.append("")

        self.jointNamesList.clearContents()
        self.jointNamesList.setRowCount(0)

        for i, name in enumerate(jointNames):
            self.jointNamesList.insertRow(i)
            item = QtWidgets.QTableWidgetItem(name.strip())
            self.jointNamesList.setItem(i, 0, item)

    def create_connections(self):
        self.jointNamesList.cellChanged.connect(self.update_name)
        self.jointNamesList.itemActivated.connect(self.jointNamesList.editItem)

        self.add_pushButton.clicked.connect(self.add)
        self.remove_pushButton.clicked.connect(self.remove)
        self.removeAll_pushButton.clicked.connect(self.remove_all)

        self.moveUp_pushButton.clicked.connect(lambda: self.move(-1))
        self.moveDown_pushButton.clicked.connect(lambda: self.move(1))

    def apply_names(self):
        jointNames = []
        for i in range(self.jointNamesList.rowCount()):
            item = self.jointNamesList.item(i, 0)
            jointNames.append(item.text())

        value = ",".join(jointNames[0:-1])
        self.root.attr("joint_names").set(value)

        self.jointNamesList.setVerticalHeaderLabels(
            [str(i) for i in range(len(jointNames))]
        )

        self.attributeChanged.emit()

    def add(self):
        row = max(0, self.jointNamesList.currentRow() or 0)
        self.jointNamesList.insertRow(row)
        item = QtWidgets.QTableWidgetItem("")
        self.jointNamesList.setItem(row, 0, item)
        self.jointNamesList.setCurrentCell(row, 0)
        self.apply_names()

    def remove(self):
        row = self.jointNamesList.currentRow()
        if row + 1 < self.jointNamesList.rowCount() > 1:
            self.jointNamesList.removeRow(row)
            self.apply_names()
            self.jointNamesList.setCurrentCell(row, 0)

    def remove_all(self):
        self.jointNamesList.clearContents()
        self.jointNamesList.setRowCount(0)
        self.jointNamesList.insertRow(0)
        self.jointNamesList.setItem(0, 0, QtWidgets.QTableWidgetItem(""))
        self.jointNamesList.setCurrentCell(0, 0)
        self.apply_names()

    def move(self, step):
        row = self.jointNamesList.currentRow()
        if row + step < 0:
            return
        item1 = self.jointNamesList.item(row, 0).text()
        item2 = self.jointNamesList.item(row + step, 0).text()
        self.jointNamesList.item(row, 0).setText(item2)
        self.jointNamesList.item(row + step, 0).setText(item1)
        self.jointNamesList.setCurrentCell(row + step, 0)

    def update_name(self, row, column):
        item = self.jointNamesList.item(row, column)
        if row == self.jointNamesList.rowCount() - 1 and item.text():
            self.jointNamesList.insertRow(row + 1)
            self.jointNamesList.setItem(row + 1, 0, QtWidgets.QTableWidgetItem(""))
        self.apply_names()
        self.jointNamesList.setCurrentCell(row + 1, 0)
        self.jointNamesList.editItem(self.jointNamesList.currentItem())

    def keyPressEvent(self):
        pass
