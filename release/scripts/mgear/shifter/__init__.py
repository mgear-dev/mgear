"""Shifters Rig Main class."""
import datetime
import getpass
import os.path
import sys
import json

# Maya
import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.pymaya import versions

# mgear
import mgear
import mgear.core.utils
from . import guide, component

from mgear.core import primitive, attribute, skin, dag, icon, node
from mgear import shifter_classic_components
from mgear import shifter_epic_components
from mgear.shifter import naming
import importlib
from mgear.core import utils

PY2 = sys.version_info[0] == 2

# check if we have loaded the necessary plugins
if not pm.pluginInfo("mgear_solvers", q=True, loaded=True):
    try:
        pm.loadPlugin("mgear_solvers")
    except RuntimeError:
        pm.displayError("You need the mgear_solvers plugin!")
if not pm.pluginInfo("matrixNodes", q=True, loaded=True):
    pm.loadPlugin("matrixNodes")

COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "component")
TEMPLATE_PATH = os.path.join(COMPONENT_PATH, "templates")

SHIFTER_COMPONENT_ENV_KEY = "MGEAR_SHIFTER_COMPONENT_PATH"


def log_window():
    if mgear.logMode and mgear.use_log_window:
        log_window_name = "mgear_shifter_build_log_window"
        log_window_field_reporter = "mgear_shifter_log_field_reporter"

        # call pm.window(log_window_name, exists=True) 2 times to avoid
        # false check in Maya 2024
        pm.window(log_window_name, exists=True)

        if not pm.window(log_window_name, exists=True):
            log_win = pm.window(
                log_window_name,
                title="Shifter Build Log",
                iconName="Shifter Log",
                width=800,
                height=500,
            )
            form = pm.formLayout()
            reporter = pm.cmdScrollFieldReporter(
                log_window_field_reporter, width=400, height=200, clr=True
            )

            btn_close = pm.button(
                label="Close",
                command=lambda *args: pm.deleteUI(log_win, window=True),
            )

            margin_v = 5
            margin_h = 5
            pm.formLayout(
                form,
                e=True,
                attachForm=[
                    (reporter, "top", margin_v),
                    (reporter, "right", margin_h),
                    (reporter, "left", margin_h),
                    (btn_close, "bottom", margin_v),
                    (btn_close, "right", margin_h),
                    (btn_close, "left", margin_h),
                ],
                attachControl=[
                    (reporter, "bottom", margin_v, btn_close),
                ],
            )

            pm.setParent("..")
            pm.showWindow(log_win)
        else:
            pm.cmdScrollFieldReporter(
                log_window_field_reporter, e=True, clr=True
            )
            pm.showWindow(log_window_name)
        mgear.logInfos()


def getComponentDirectories():
    """Get the components directory"""
    # TODO: ready to support multiple default directories
    return mgear.core.utils.gatherCustomModuleDirectories(
        SHIFTER_COMPONENT_ENV_KEY,
        [
            os.path.join(os.path.dirname(shifter_classic_components.__file__)),
            os.path.join(os.path.dirname(shifter_epic_components.__file__)),
        ],
    )
    # return mgear.core.utils.gatherCustomModuleDirectories(
    #     SHIFTER_COMPONENT_ENV_KEY,
    #     os.path.join(os.path.dirname(shifter_classic_components.__file__)))


def importComponentGuide(comp_type):
    """Import the Component guide"""
    dirs = getComponentDirectories()
    defFmt = "mgear.shifter.component.{}.guide"
    customFmt = "{}.guide"

    module = mgear.core.utils.importFromStandardOrCustomDirectories(
        dirs, defFmt, customFmt, comp_type
    )
    return module


def importComponent(comp_type):
    """Import the Component"""
    dirs = getComponentDirectories()
    defFmt = "mgear.shifter.component.{}"
    customFmt = "{}"

    module = mgear.core.utils.importFromStandardOrCustomDirectories(
        dirs, defFmt, customFmt, comp_type
    )
    return module


def reloadComponents(*args):
    """Reload all componets

    Args:
        *args: Dummy
    """
    compDir = getComponentDirectories()

    for x in compDir:
        for com in compDir[x]:
            try:
                if PY2:
                    reload(importComponent(com)) # type: ignore
                    reload(importComponentGuide(com)) # type: ignore
                else:
                    importlib.reload(importComponent(com))
                    importlib.reload(importComponentGuide(com))
                print("reload : {}.{}".format(os.path.basename(x), com))
            except ImportError:
                pass


class Rig(object):
    """The main rig class.

    Attributes:
        guide: guide.Rig() initialization.
        groups (dic): Rig groups (Maya sets)
        components (dic): Dictionary for the rig components.
            Keys are the component fullname (ie. 'arm_L0')
        componentsIndex (list): Components index list.

    """

    def __init__(self):

        self.guide = guide.Rig()

        self.groups = {}
        self.subGroups = {}

        self.bindPlanes = {}
        self.combinedBindPlanes = {}

        self.components = {}
        self.componentsIndex = []

        self.customStepDic = {}

        self.build_data = {}

    @utils.one_undo
    def buildFromDict(self, conf_dict):
        log_window()
        startTime = datetime.datetime.now()
        mgear.log("\n" + "= SHIFTER RIG SYSTEM " + "=" * 46)

        self.stopBuild = False

        self.guide.set_from_dict(conf_dict)
        endTime = datetime.datetime.now()
        finalTime = endTime - startTime
        mgear.log(
            "\n"
            + "= SHIFTER FILE READ {} [ {} ] {}".format(
                "=" * 16, finalTime, "=" * 7
            )
        )

        # Build
        mgear.log("\n" + "= BUILDING RIG " + "=" * 46)
        self.from_dict_custom_step(conf_dict, pre=True)
        self.build()
        self.from_dict_custom_step(conf_dict, pre=False)
        # Collect post-build data
        if self.options["data_collector_embedded"] or self.options["data_collector"]:
            build_data = self.collect_build_data()
        else:
            build_data = None

        endTime = datetime.datetime.now()
        finalTime = endTime - startTime
        # pm.flushUndo()
        # pm.displayInfo(
        #     "Undo history have been flushed to avoid "
        #     "possible crash after rig is build. \n"
        #     "More info: "
        #     "https://github.com/miquelcampos/mgear/issues/72"
        # )
        mgear.log(
            "\n"
            + "= SHIFTER BUILD RIG DONE {} [ {} ] {}".format(
                "=" * 16, finalTime, "=" * 7
            )
        )

        return build_data

    @utils.one_undo
    def buildFromSelection(self):
        """Build the rig from selected guides."""

        startTime = datetime.datetime.now()
        mgear.log("\n" + "= SHIFTER RIG SYSTEM " + "=" * 46)

        self.stopBuild = False
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

        # check if is partial build or full guide build
        ismodel = False
        if selection[0].hasAttr("ismodel"):
            self.preCustomStep(selection)
            ismodel = True

        if not self.stopBuild:
            mgear.log("\n" + "= GUIDE VALIDATION " + "=" * 46)
            # Check guide is valid
            self.guide.setFromSelection()
            if not self.guide.valid:
                return

            # Build
            mgear.log("\n" + "= BUILDING RIG " + "=" * 46)
            self.build()
            if ismodel:
                self.postCustomStep()

            # Collect post-build data
            if self.options["data_collector_embedded"] or self.options["data_collector"]:
                build_data = self.collect_build_data()
            else:
                build_data = None

            endTime = datetime.datetime.now()
            finalTime = endTime - startTime
            # pm.flushUndo()
            # pm.displayInfo(
            #     "Undo history have been flushed to avoid "
            #     "possible crash after rig is build. \n"
            #     "More info: "
            #     "https://github.com/miquelcampos/mgear/issues/72"
            # )
            mgear.log(
                "\n"
                + "= SHIFTER BUILD RIG DONE {} [ {} ] {}".format(
                    "=" * 16, finalTime, "=" * 7
                )
            )

        return build_data

    def build(self):
        """Build the rig."""

        self.options = self.guide.values
        self.guides = self.guide.components

        self.customStepDic["mgearRun"] = self

        self.initialHierarchy()
        self.processComponents()
        self.finalize()

        return self.model

    def stepsList(self, checker, attr):
        if self.options[checker] and self.options[attr]:
            return self.options[attr].split(",")
        else:
            return None

    def from_dict_custom_step(self, conf_dict, pre=True):
        if pre:
            pre_post = "doPreCustomStep"
            pre_post_path = "preCustomStep"
        else:
            pre_post = "doPostCustomStep"
            pre_post_path = "postCustomStep"
        p_val = conf_dict["guide_root"]["param_values"]
        if p_val[pre_post]:
            customSteps = p_val[pre_post_path]
            self.customStep(customSteps.split(","))

    def customStep(self, customSteps=None):
        if customSteps:
            for step in customSteps:
                if not self.stopBuild:
                    if step.startswith("*"):
                        continue
                    self.stopBuild = guide.helperSlots.runStep(
                        step.split("|")[-1][1:], self.customStepDic
                    )
                else:
                    pm.displayWarning("Build Stopped")
                    break

    def preCustomStep(self, selection):
        if (
            selection[0].hasAttr("ismodel")
            and selection[0].attr("doPreCustomStep").get()
        ):
            customSteps = selection[0].attr("preCustomStep").get()
            if customSteps:
                mgear.log("\n" + "= PRE CUSTOM STEPS " + "=" * 46)
                # use forward slash for OS compatibility
                if sys.platform.startswith("darwin"):
                    customSteps = [
                        cs.replace("\\", "/") for cs in customSteps.split(",")
                    ]
                    self.customStep(customSteps)
                else:
                    self.customStep(customSteps.split(","))

    def postCustomStep(self):
        customSteps = self.stepsList("doPostCustomStep", "postCustomStep")
        if customSteps:
            mgear.log("\n" + "= POST CUSTOM STEPS " + "=" * 46)
            # use forward slash for OS compatibility
            if sys.platform.startswith("darwin"):
                customSteps = [cs.replace("\\", "/") for cs in customSteps]
            self.customStep(customSteps)

    # @utils.timeFunc
    def get_guide_data(self):
        """Get the guide data

        Returns:
            str: The guide data
        """
        if self.guide.guide_template_dict:
            return json.dumps(self.guide.guide_template_dict)
        else:
            return json.dumps(self.guide.get_guide_template_dict())

    def initialHierarchy(self):
        """Build the initial hierarchy of the rig.

        Create the rig model, the main properties,
        and a couple of base organisation nulls.
        Get the global size of the rig.

        """
        mgear.log("Initial Hierarchy")

        # --------------------------------------------------
        # Model
        self.model = primitive.addTransformFromPos(
            None, self.options["rig_name"]
        )

        lockAttrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
        attribute.lockAttribute(self.model, attributes=lockAttrs)

        # --------------------------------------------------
        # INFOS
        self.isRig_att = attribute.addAttribute(
            self.model, "is_rig", "bool", True
        )
        self.rigName_att = attribute.addAttribute(
            self.model, "rig_name", "string", self.options["rig_name"]
        )
        self.user_att = attribute.addAttribute(
            self.model, "user", "string", getpass.getuser()
        )
        self.isWip_att = attribute.addAttribute(
            self.model, "wip", "bool", self.options["mode"] != 0
        )
        self.date_att = attribute.addAttribute(
            self.model, "date", "string", str(datetime.datetime.now())
        )
        self.mayaVersion_att = attribute.addAttribute(
            self.model,
            "maya_version",
            "string",
            str(pm.mel.eval("getApplicationVersionAsFloat")),
        )
        self.gearVersion_att = attribute.addAttribute(
            self.model, "gear_version", "string", mgear.getVersion()
        )
        self.comments_att = attribute.addAttribute(
            self.model, "comments", "string", str(self.options["comments"])
        )
        self.ctlVis_att = attribute.addAttribute(
            self.model, "ctl_vis", "bool", True
        )
        if versions.current() >= 201650:
            self.ctlVisPlayback_att = attribute.addAttribute(
                self.model, "ctl_vis_on_playback", "bool", True
            )
        self.jntVis_att = attribute.addAttribute(
            self.model, "jnt_vis", "bool", True
        )
        # adding the always draw shapes on top to global attribute
        if versions.current() >= 20220000:
            self.ctlXRay_att = attribute.addAttribute(
                self.model, "ctl_x_ray", "bool", False
            )

        self.qsA_att = attribute.addAttribute(
            self.model, "quickselA", "string", ""
        )
        self.qsB_att = attribute.addAttribute(
            self.model, "quickselB", "string", ""
        )
        self.qsC_att = attribute.addAttribute(
            self.model, "quickselC", "string", ""
        )
        self.qsD_att = attribute.addAttribute(
            self.model, "quickselD", "string", ""
        )
        self.qsE_att = attribute.addAttribute(
            self.model, "quickselE", "string", ""
        )
        self.qsF_att = attribute.addAttribute(
            self.model, "quickselF", "string", ""
        )

        self.rigGroups = self.model.addAttr("rigGroups", at="message", m=1)
        self.rigPoses = self.model.addAttr("rigPoses", at="message", m=1)
        self.rigCtlTags = self.model.addAttr("rigCtlTags", at="message", m=1)
        self.rigScriptNodes = self.model.addAttr(
            "rigScriptNodes", at="message", m=1
        )

        self.guide_data_att = attribute.addAttribute(
            self.model, "guide_data", "string", self.get_guide_data()
        )

        # ------------------------- -------------------------
        # Global Ctl
        if self.options["worldCtl"]:
            if self.options["world_ctl_name"]:
                name = self.options["world_ctl_name"]
            else:
                name = "world_ctl"

            icon_shape = "circle"

        else:
            name = "global_C0_ctl"
            icon_shape = "crossarrow"

        self.global_ctl = self.addCtl(
            self.model,
            name,
            datatypes.Matrix(),
            self.options["C_color_fk"],
            icon_shape,
            w=10,
        )
        attribute.setRotOrder(self.global_ctl, "ZXY")

        # Connect global visibility
        pm.connectAttr(self.ctlVis_att, self.global_ctl.attr("visibility"))
        if versions.current() >= 201650:
            pm.connectAttr(
                self.ctlVisPlayback_att, self.global_ctl.attr("hideOnPlayback")
            )
        attribute.lockAttribute(self.global_ctl, ["v"])

        # --------------------------------------------------
        # Setup in world Space
        self.setupWS = primitive.addTransformFromPos(self.model, "setup")
        attribute.lockAttribute(self.setupWS)
        # --------------------------------------------------
        # Basic set of null
        if self.options["joint_rig"]:
            self.root_joint = None
            self.jnt_org = primitive.addTransformFromPos(self.model, "jnt_org")
            if self.options["force_SSC"]:
                self.global_ctl.s >> self.jnt_org.s
            pm.connectAttr(self.jntVis_att, self.jnt_org.attr("visibility"))

    def processComponents(self):
        """
        Process the components of the rig, following the creation steps.
        """

        # Init
        self.components_infos = {}

        for comp in self.guide.componentsIndex:
            guide_ = self.guides[comp]
            mgear.log("Init : " + guide_.fullName + " (" + guide_.type + ")")

            module = importComponent(guide_.type)
            Component = getattr(module, "Component")

            comp = Component(self, guide_)
            if comp.fullName not in self.componentsIndex:
                self.components[comp.fullName] = comp
                self.componentsIndex.append(comp.fullName)

                self.components_infos[comp.fullName] = [
                    guide_.compType,
                    guide_.getVersion(),
                    guide_.author,
                ]

        # Creation steps
        self.steps = component.Main.steps
        for i, name in enumerate(self.steps):
            # for count, compName in enumerate(self.componentsIndex):
            for compName in self.componentsIndex:
                comp = self.components[compName]
                mgear.log(
                    name + " : " + comp.fullName + " (" + comp.type + ")"
                )
                comp.stepMethods[i]()

            if self.options["step"] >= 1 and i >= self.options["step"] - 1:
                break

    def finalize(self):
        """Finalize the rig."""
        groupIdx = 0

        # Properties --------------------------------------
        mgear.log("Finalize")

        # clean jnt_org --------------------------------------
        if self.options["joint_rig"]:
            mgear.log("Cleaning jnt org")
            jnt_org_child = dag.findChildrenPartial(self.jnt_org, "org")
            if jnt_org_child:
                for jOrg in jnt_org_child:
                    if not jOrg.listRelatives(c=True):
                        pm.delete(jOrg)

        # Groups ------------------------------------------
        mgear.log("Creating groups")
        # Retrieve group content from components
        for name in self.componentsIndex:
            component_ = self.components[name]
            for name, objects in component_.groups.items():
                self.addToGroup(objects, name)
            for name, objects in component_.subGroups.items():
                self.addToSubGroup(objects, name)

        # Create master set to group all the groups
        masterSet = pm.sets(n=self.model.name() + "_sets_grp", em=True)
        pm.connectAttr(masterSet.message, self.model.rigGroups[groupIdx])
        groupIdx += 1

        # Creating all groups
        pm.select(cl=True)
        for name, objects in self.groups.items():
            s = pm.sets(n=self.model.name() + "_" + name + "_grp")
            s.union(objects)
            pm.connectAttr(s.message, self.model.rigGroups[groupIdx])
            groupIdx += 1
            masterSet.add(s)
        for parentGroup, subgroups in self.subGroups.items():
            pg = pm.PyNode(self.model.name() + "_" + parentGroup + "_grp")
            for sg in subgroups:
                sub = pm.PyNode(self.model.name() + "_" + sg + "_grp")
                if sub in masterSet.members():
                    masterSet.remove(sub)
                pg.add(sub)

        # create geo group

        geoSet = pm.sets(n=self.model.name() + "_geo_grp", em=True)
        pm.connectAttr(geoSet.message, self.model.rigGroups[groupIdx])
        masterSet.add(geoSet)
        groupIdx += 1

        # Bind pose ---------------------------------------
        # controls_grp = self.groups["controllers"]
        # pprint(controls_grp, stream=None, indent=1, width=100)
        ctl_master_grp = pm.PyNode(self.model.name() + "_controllers_grp")
        pm.select(ctl_master_grp, replace=True)
        dag_node = pm.dagPose(save=True, selection=True)
        pm.connectAttr(dag_node.message, self.model.rigPoses[0])
        print(dag_node)

        # hide all DG nodes inputs in channel box -----------------------
        # only hides if components_finalize or All steps are done
        # if not WIP mode we will hide all the inputs
        if not self.options["mode"]:
            for c in self.model.listHistory(ac=True, f=True):
                if c.type() != "transform":
                    c.isHistoricallyInteresting.set(False)
            try:
                # hide a guide if the guide_vis pram is turned off
                if self.guide.model.hasAttr("guide_vis"):
                    if not self.guide.model.guide_vis.get():
                        self.guide.model.hide()
            except AttributeError:
                # catch error in case we build from serialized guide
                pass

        # Bind skin re-apply
        if self.options["importSkin"]:
            try:
                pm.displayInfo("Importing Skin")
                skin.importSkin(self.options["skin"])

            except RuntimeError:
                pm.displayWarning(
                    "Skin doesn't exist or is not correct. "
                    + self.options["skin"]
                    + " Skipped!"
                )

    def collect_build_data(self):
        """Collect post build data

        by default the data is stored in the root joint.

        Returns:
            dict: The collected data
        """
        # print("self.guide.guide_template_dict>>>>>>>>>>>>>>>>>")
        # print(self.guide.guide_template_dict["guide_root"]["param_values"])
        # options in dictionary form
        # self.options_dict = self.guide.guide_template_dict["guide_root"]["param_values"]
        # print(self.options)
        # print(self.guide.guide_template_dict["guide_root"]["param_values"])
        # print(self.options)
        self.build_data["MainSettings"] = self.guide.guide_template_dict["guide_root"]["param_values"]
        self.build_data["MainSettings"]["size"] = self.options["size"]
        # print(self.build_data["MainSettings"])

        # replace the MVector with his value in a list
        # keys_to_update = [
        #     'L_RGB_fk', 'L_RGB_ik',
        #     'R_RGB_fk', 'R_RGB_ik',
        #     'C_RGB_fk', 'C_RGB_ik'
        #     ]
        # for key in keys_to_update:
        #     self.build_data["MainSettings"][key] == self.guide.guide_template_dict["guide_root"]["param_values"][key]
        # print(self.build_data["MainSettings"])
        # self.build_data["MainSettings"] = self.guide.guide_template_dict["guide_root"]["param_values"]
        self.build_data["Components"] = []
        for c, comp in self.customStepDic["mgearRun"].components.items():
            self.build_data["Components"].append(comp.build_data)

        if self.options["data_collector_embedded"]:
            root_jnt = self.get_root_jnt_embbeded()
            self.add_collected_data_to_root_jnt(root_jnt=root_jnt)
        if self.options["data_collector"]:
            self.data_collector_output(self.options["data_collector_path"])
        return self.build_data

    def data_collector_output(self, file_path=None):
        """Output collected data to a Json file

        Args:
            file_path (Str, optional): Output path for the Json File
        """
        if not file_path:
            ext_filter = "Shifter Collected data (*{})".format(
                guide.DATA_COLLECTOR_EXT
            )
            file_path = pm.fileDialog2(fileMode=0, fileFilter=ext_filter)[0]
        with open(file_path, "w") as f:
            f.write(json.dumps(self.build_data, indent=4))
            file_path = None

    def add_collected_data_to_root_jnt(self, root_jnt=None):
        """Add collected data to root joint
        Root joint is the first joint generated in the rig.
        """
        if not root_jnt:
            for c in self.componentsIndex:
                comp = self.customStepDic["mgearRun"].components[c]
                if not root_jnt and comp.jointList:
                    root_jnt = comp.jointList[0]
                    break
        if root_jnt:
            attribute.addAttribute(
                root_jnt,
                "collected_data",
                "string",
                str(json.dumps(self.build_data)),
            )

    def get_root_jnt_embbeded(self):
        """Get the root joint to embbed the data

        Returns:
            pyNode: Joint
        """
        j_name = self.options["data_collector_embedded_custom_joint"]
        if j_name:
            try:
                return pm.PyNode(j_name)
            except pm.MayaNodeError:
                pm.displayError(
                    "{} doesn't exist or is not unique".format(j_name)
                )

    def addCtl(self, parent, name, m, color, iconShape, **kwargs):
        """Create the control and apply the shape, if this is alrealdy stored
        in the guide controllers grp.

        Args:
            parent (dagNode): The control parent
            name (str): The control name.
            m (matrix): The transfromation matrix for the control.
            color (int or list of float): The color for the control in index
                or RGB.
            iconShape (str): The controls default shape.
            kwargs (variant): Other arguments for the iconShape type variations

        Returns:
            dagNode: The Control.

        """
        if "degree" not in kwargs.keys():
            kwargs["degree"] = 1

        bufferName = name + "_controlBuffer"
        if bufferName in self.guide.controllers.keys():
            ctl_ref = self.guide.controllers[bufferName]
            ctl = primitive.addTransform(parent, name, m)
            for shape in ctl_ref.getShapes():
                ctl.addChild(shape, shape=True, add=True)
                pm.rename(shape, name + "Shape")
        else:
            ctl = icon.create(parent, name, m, color, iconShape, **kwargs)

        self.addToGroup(ctl, "controllers")

        # Set the control shapes isHistoricallyInteresting
        for oShape in ctl.getShapes():
            oShape.isHistoricallyInteresting.set(False)
            # connecting the always draw shapes on top to global attribute
            if versions.current() >= 20220000:
                pm.connectAttr(
                    self.ctlXRay_att, oShape.attr("alwaysDrawOnTop")
                )

        # set controller tag
        if versions.current() >= 201650:
            pm.controller(ctl)
            self.add_controller_tag(ctl, None)

        attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
        attribute.addAttribute(
            ctl, "ctl_role", "string", keyable=False, value="world_ctl"
        )

        return ctl

    def addToGroup(self, objects, names=["hidden"]):
        """Add the object in a collection for later group creation.

        Args:
            objects (dagNode or list of dagNode): Object to put in the group.
            names (str or list of str): Names of the groups to create.

        """
        if not isinstance(names, list):
            names = [names]

        if not isinstance(objects, list):
            objects = [objects]

        for name in names:
            if name not in self.groups.keys():
                self.groups[name] = []

            self.groups[name].extend(objects)

    def addToSubGroup(self, subGroups, parentGroups=["hidden"]):
        """Add the object in a collection for later SubGroup creation.

        Args:
            subGroups (dagNode or list of dagNode): Groups (core set) to add
                as a Subgroup.
            namparentGroupses (str or list of str): Names of the parent groups
                to create.

        """

        if not isinstance(parentGroups, list):
            parentGroups = [parentGroups]

        if not isinstance(subGroups, list):
            subGroups = [subGroups]

        for pg in parentGroups:
            if pg not in self.subGroups.keys():
                self.subGroups[pg] = []
            self.subGroups[pg].extend(subGroups)

    def add_controller_tag(self, ctl, tagParent):
        ctt = node.add_controller_tag(ctl, tagParent)
        if ctt:
            ni = attribute.get_next_available_index(self.model.rigCtlTags)
            pm.connectAttr(
                ctt.message, self.model.attr("rigCtlTags[{}]".format(str(ni)))
            )

    def getLocalName(self, guideName):
        """This function return the local name, cutting the Maya fullname
        and taking the latest part.

            ie. "parentA|parentB|arm_C0_root" will return "arm_C0_root"

        Args:
            guideName (str): The guide name.

        Returns:
            str: The local Name

        """
        if guideName is None:
            return None
        localName = guideName.split("|")[-1]
        return localName

    def getComponentName(self, guideName, local=True):
        """
        This function return the component name

            ie. "arm_C0_root" return "arm_C0"

        Args:
            guideName (str): The guide name.

        Returns:
            str: The compnent Name
        """

        if guideName is None:
            return None

        if local:
            guideName = self.getLocalName(guideName)

        names = naming.get_component_and_relative_name(guideName)
        if names:
            return names[0]

    def getRelativeName(self, guideName):
        """This function return the name of the relative in the guide

            ie. "arm_C0_root" return "root"

        Args:
            guideName (str): The guide name.

        Returns:
            str: The relative Name

        """
        if guideName is None:
            return None

        localName = self.getLocalName(guideName)
        names = naming.get_component_and_relative_name(localName)
        if names:
            return names[1]

    def findRelative(self, guideName, relatives_map={}):
        """Return the objects in the rig matching the guide object.

        Args:
            guideName (str): Name of the guide object.
            relatives_map (dict, optional): Custom relative mapping to
                    point any object in a component. For example used to point
                    Auto in upvector reference.

        Returns:
            transform: The relative object

        """
        if guideName is None:
            return self.global_ctl

        if guideName in relatives_map.keys():
            return relatives_map[guideName]

        comp_name = self.getComponentName(guideName)
        relative_name = self.getRelativeName(guideName)

        if comp_name not in self.components.keys():
            return self.global_ctl
        return self.components[comp_name].getRelation(relative_name)

    def findControlRelative(self, guideName):
        """Return the control objects in the rig matching the guide object.

        Args:
            guideName (str): Name of the guide object.

        Returns:
           transform: The relative control object

        """

        if guideName is None:
            return self.global_ctl

        # localName = self.getLocalName(guideName)
        comp_name = self.getComponentName(guideName)
        relative_name = self.getRelativeName(guideName)

        if comp_name not in self.components.keys():
            return self.global_ctl
        return self.components[comp_name].getControlRelation(relative_name)

    # TODO: update findComponent and other find methods with new funtions like
    # comp_name and others.  Better composability
    def findComponent(self, guideName):
        """Return the component from a guide Name.

        Args:
            guideName (str): Name of the guide object.

        Returns:
           transform: The component

        """
        if guideName is None:
            return None

        comp_name = self.getComponentName(guideName, False)
        # comp_name = "_".join(guideName.split("_")[:2])

        if comp_name not in self.components.keys():
            return None

        return self.components[comp_name]

    def findUIHost(self, guideName):
        """Return the UI host of the compoent

        Args:
            guideName (str): Name of the guide object.

        Returns:
           transform: The relative object

        """

        if guideName is None:
            return self.ui

        comp_name = self.getComponentName(guideName, False)
        # comp_name = "_".join(guideName.split("_")[:2])

        if comp_name not in self.components.keys():
            return self.ui

        if self.components[comp_name].ui is None:
            self.components[comp_name].ui = pm.UIHost(
                self.components[comp_name].root
            )

        return self.components[comp_name].ui
