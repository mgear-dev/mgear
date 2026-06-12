import os
import re
import json
import tempfile
from glob import glob
import mgear.pymaya as pm

try:
    from mgear.shifter import io
    from mgear.shifter import guide_manager
    from mgear.core import skin
except:
    pm.warning("Failed to load Plebes as mGear was not found")


class Plebes:
    """Quickly rig various character generator plebes with mGear"""

    def __init__(self):
        self.template_menu_entries = {}
        self.template = {}

    def template_change(self, selected_template):
        """Update the Template, when a new one is selected from the menu"""
        self.set_template(self.template_menu_entries.get(selected_template))

    def gui(self):
        """GUI for Plebes"""
        if pm.window("plebesDialog", exists=True):
            pm.deleteUI("plebesDialog")
        win = pm.window("plebesDialog", title="Rig Plebe", sizeable=True)
        pm.window(win, edit=True, height=475, width=300)

        pm.frameLayout(
            height=475,
            width=300,
            marginHeight=10,
            marginWidth=10,
            labelVisible=False,
        )

        pm.text(label="Choose a Character Template:")
        self.template_menu = pm.optionMenu(
            "template_menu", changeCommand=self.template_change
        )

        self.help = pm.scrollField(
            editable=False, wordWrap=True, height=200, text=" "
        )

        self.populate_template_menu(self.template_menu)

        # Import FBX button
        pm.button(
            label="Import FBX",
            command=lambda _: self.import_fbx(),
            annotation="Import the FBX of your skinned character.",
        )

        # Fix FBX Naming button
        pm.button(
            label="Fix FBX Naming",
            command=lambda _: self.fix_fbx_naming(),
            annotation=(
                "Replaces FBXASCxxx with '_' in node names from imported FBX \n"
                "files. This is needed when the FBX uses characters that are \n"
                "not supported in Maya."
            ),
        )

        # Separator
        pm.separator(style="in")

        # Import Guides button
        pm.button(
            label="Import Guides",
            command=lambda _: self.import_guides(),
            annotation="Import a mGear biped guide template.",
        )

        # Align Guides button
        pm.button(
            label="Align Guides",
            command=lambda _: self.align_guides(),
            annotation=(
                "Position the guides to match your character.\n\n"
                "You will need to adjust the heel and foot width guides\n"
                "manually, and check that knees and elbows are pointing in the\n"
                "right direction."
            ),
        )

        # Build Rig button
        pm.button(
            label="Build Rig",
            command=lambda _: self.rig(),
            annotation="Build the mGear rig based on the guides.",
        )

        # Add row layout for constrain and skin buttons
        pm.rowLayout(
            numberOfColumns=3,
            adjustableColumn=2,
            columnAttach=[(1, "both", 0), (2, "both", 10), (3, "both", 10)],
        )

        # Constrain to Rig button
        pm.button(
            label="Constrain to Rig",
            width=125,
            command=lambda _: self.constrain_to_rig(),
            annotation="Constrain the characters joints to the mGear rig.",
        )

        # OR label
        pm.text(label=" OR ")

        # Column layout for Skin button and export checkbox
        pm.columnLayout(width=105)
        pm.button(
            label="Skin to Rig",
            width=105,
            command=lambda _: self.skin_to_rig(),
            annotation=(
                "Transfer skinning to the mGear rig.\n\n"
                "This is done by first exporting the weights and then remapping\n"
                "the export to matching mGear joints before bringing it in."
            ),
        )

        # Export Only checkbox
        self.export_only_check = pm.checkBox(
            label="Export Only",
            annotation=(
                "Exports the skin weights, but doesn't re-apply them. You can\n"
                "use mGear>Skin and Weights>Import Skin Pack to manually\n"
                "bring them in later.\n\n"
                "See the script editor for where to find the skin pack."
            ),
        )

        # Show the window
        pm.showWindow(win)

    def populate_template_menu(self, template_menu):
        """Populate the template menu from PLEBE_TEMPLATES_DIR environment"""
        template_paths = []
        if os.getenv("PLEBE_TEMPLATES_DIR"):
            template_paths = os.getenv("PLEBE_TEMPLATES_DIR").split(":")
        template_paths.append(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "plebes_templates"
            )
        )
        for template_path in template_paths:
            template_pattern = os.path.join(template_path, "*.json")
            for filename in sorted(glob(template_pattern)):
                template_name = (
                    os.path.basename(filename)
                    .replace(".json", "")
                    .replace("_", " ")
                    .title()
                )
                self.template_menu_entries[template_name] = filename
                pm.menuItem(
                    "templateMenuItem_{name}".format(name=template_name),
                    label=template_name,
                    parent=template_menu,
                    command=pm.Callback(self.set_template, filename),
                )

        current_value = pm.optionMenu(template_menu, query=True, value=True)
        default_template = self.template_menu_entries.get(current_value)
        if default_template:
            self.set_template(default_template)

    def import_fbx(self):
        """Import a FBX"""
        fbx_filter = "FBX (*.fbx)"
        fbx = pm.fileDialog2(
            fileFilter=fbx_filter,
            caption="Import FBX",
            okCaption="Import",
            fileMode=1,
        )
        if fbx:
            pm.displayInfo("Importing: {fbx}".format(fbx=fbx))
            pm.importFile(fbx[0])

    def fix_fbx_naming(self):
        """Fixes naming of imported FBX's that use unsopperted characters"""
        nodes = []
        for node in pm.ls("*FBXASC*", long=True):
            new_name = re.sub(r"FBXASC[0-9][0-9][0-9]", "_", node.name())
            pm.displayInfo(
                "Renaming '{old_name}' to '{new_name}'".format(
                    old_name=node.name(), new_name=new_name
                )
            )
            node.rename(new_name)
            nodes.append(node)
        if len(nodes) < 1:
            pm.displayInfo(
                "No node names with FBXASCxxx found. Nothing to do."
            )

    def clear_transforms(self, input_node):
        """Clears out keys, locks and limits on trans, rot, scale and vis"""
        # TODO! Do I need to unset Segment Scale Compensate on the joints?
        node = pm.PyNode(input_node)
        node.translateX.unlock()
        node.translateY.unlock()
        node.translateZ.unlock()
        node.rotateX.unlock()
        node.rotateY.unlock()
        node.rotateZ.unlock()
        node.scaleX.unlock()
        node.scaleY.unlock()
        node.scaleZ.unlock()
        node.visibility.unlock()
        node.translateX.disconnect()
        node.translateY.disconnect()
        node.translateZ.disconnect()
        node.rotateX.disconnect()
        node.rotateY.disconnect()
        node.rotateZ.disconnect()
        node.scaleX.disconnect()
        node.scaleY.disconnect()
        node.scaleZ.disconnect()
        node.visibility.disconnect()
        node.minTransLimitEnable.set(False, False, False)
        node.maxTransLimitEnable.set(False, False, False)
        node.minRotLimitEnable.set(False, False, False)
        node.maxRotLimitEnable.set(False, False, False)
        node.minScaleLimitEnable.set(False, False, False)
        node.maxScaleLimitEnable.set(False, False, False)

    def check_for_guides(self):
        """Check if the mGear guides are in the scene"""
        if pm.objExists("guide"):
            return True
        else:
            return False

    def import_guides(self):
        """Import mGear's Biped Template guides"""
        if pm.objExists("guide"):
            pm.warning("There is already a guide in the scene. Skipping!")
        else:
            io.import_sample_template("biped.sgt")

    def rig(self):
        """Build the mGear rig from guides"""
        # Sanity check
        if len(pm.ls("rig", assemblies=True)) > 0:
            pm.warning(
                "The character has already been rigged. "
                "You can delete the rig and re-build it if you need to"
            )
            return False

        pm.select(pm.PyNode("guide"), replace=True)
        guide_manager.build_from_selection()

    def set_template(self, template):
        """
        Set which template to use
        """
        pm.displayInfo(
            "Setting template to: {template}".format(template=template)
        )
        with open(template) as json_file:
            self.template = json.load(json_file)
        pm.scrollField(self.help, edit=True, text=self.template.get("help"))

    def get_target(self, search_guide):
        """Get's the joint matching the guide"""
        for pairs in self.template.get("guides"):
            for guide, target in pairs.items():
                if guide == search_guide:
                    return pm.PyNode(target)

    def get_joint(self, search_joint):
        """Get's the joint matching the guide"""
        for pairs in self.template.get("joints"):
            for joint, target in pairs.items():
                if joint == search_joint:
                    return pm.PyNode(target)

    def align_guides(self):
        """Align the mGear guide to character based on the selected template"""
        # Sanity checking
        if not pm.objExists("guide"):
            pm.warning("You need to import guides first")
            return False
        if not pm.objExists(self.template.get("root")):
            pm.warning(
                "Unable to find '{character}' in scene! ".format(
                    character=self.template.get("root")
                ),
                "Check that you have the correct template selected",
            )
            return False
        warnings = False

        # Scale the guides
        factor = 16.741  # Height of guide head
        head_pos = self.get_target("neck_C0_head").getTranslation(
            space="world"
        )
        scale = head_pos.y / factor
        pm.PyNode("guide").setScale(pm.datatypes.Vector(scale, scale, scale))

        # Match guides to joints based on template
        for pairs in self.template.get("guides"):
            for guide, target in pairs.items():
                g = pm.PyNode(guide)
                if target == "PARENT_OFFSET":
                    # Offset by the same amount the parent is from it's parent
                    gparent = g.getParent()
                    parent = self.get_target(gparent)
                    ggrandparent = gparent.getParent()
                    grandparent = self.get_target(ggrandparent)
                    parent_pos = parent.getTranslation(space="world")
                    grandparent_pos = grandparent.getTranslation(space="world")
                    offset = parent_pos - grandparent_pos + parent_pos
                    g.setTranslation(offset, space="world")
                elif isinstance(target, list):
                    # Average position between targets
                    pos = pm.datatypes.Vector((0.0, 0.0, 0.0))
                    for t in target:
                        pos = pm.PyNode(t).getTranslation(space="world") + pos
                    g.setTranslation(pos / len(target), space="world")
                else:
                    try:
                        t = pm.PyNode(target)
                        g.setTranslation(
                            t.getTranslation(space="world"), space="world"
                        )
                    except:
                        warnings = True
                        pm.warning(
                            "Target '{target}' not found in scene. "
                            "Unable to align the '{guide}' guide".format(
                                target=target, guide=guide
                            )
                        )

        # Adjust the setgings on the guides
        try:
            for pairs in self.template.get("settings"):
                for guide, settings in pairs.items():
                    for setting in settings:
                        for attribute, value in setting.items():
                            try:
                                pm.PyNode(guide).attr(attribute).set(value)
                            except:
                                warnings = True
                                pm.warning(
                                    "Unable to set attribute '{attr}' "
                                    "on guide '{guide}' to '{value}'"
                                    "".format(
                                        attr=attribute,
                                        guide=guide,
                                        value=value,
                                    )
                                )
        except:
            pm.displayInfo("No guide settings defined in template")
        pm.displayInfo(
            "Remember to align heels and direction of blades."
            "Not everything can be automated."
        )
        if warnings:
            pm.warning(
                "Some guides failed to align correctly. "
                "See the script editor for details!"
            )

    def constrain_to_rig(self, *args, **kwargs):
        """Constrain the plebe to the mGear rig using constraints"""
        # Sanity checking
        if not pm.objExists(self.template.get("root")):
            pm.warning(
                "Unable to find '{character}' in scene! ".format(
                    character=self.template.get("root")
                ),
                "Check that you have the correct template selected",
            )
            return False
        if not pm.objExists("global_C0_ctl"):
            pm.warning("You need to build the rig first!")
            return False
        warnings = False

        for pairs in self.template.get("joints"):
            for source, target in pairs.items():
                if not pm.objExists(target.get("joint")):
                    warnings = True
                    pm.warning(
                        "Joint '{joint}' not found, so it won't be "
                        "connected to the rig.".format(
                            joint=target.get("joint")
                        )
                    )
                    continue
                self.clear_transforms(target.get("joint"))
                if (
                    target.get("constrain")[0] == "1"
                    and target.get("constrain")[1] == "1"
                ):
                    pm.parentConstraint(
                        source,
                        target.get("joint"),
                        maintainOffset=True,
                        decompRotationToChild=True,
                    )
                elif target.get("constrain")[0] == "1":
                    pm.pointConstraint(
                        source, target.get("joint"), maintainOffset=True
                    )
                elif target.get("constrain")[1] == "1":
                    pm.orientConstraint(
                        source, target.get("joint"), maintainOffset=True
                    )
                if target.get("constrain")[2] == "1":
                    pm.scaleConstraint(
                        source, target.get("joint"), maintainOffset=True
                    )
        pm.displayInfo("Done attaching the character to the rig")
        if warnings:
            pm.warning(
                "Some joints failed to attach to the rig. "
                "See the script editor for details!"
            )

    def skin_to_rig(self, *args, **kwargs):
        """Transfer skinning from the plebe to the mGear rig"""
        # Sanity checking
        if not pm.objExists(self.template.get("root")):
            pm.warning(
                "Unable to find '{character}' in scene! ".format(
                    character=self.template.get("root")
                ),
                "Check that you have the correct template selected",
            )
            return False
        if not pm.objExists("global_C0_ctl"):
            pm.warning("You need to build the rig first!")
            return False

        # Check and prune selection
        selection = []
        for sel in pm.ls(selection=True):
            skin_cluster = skin.getSkinCluster(sel)
            if skin_cluster:
                selection.append(sel)
                # Hack to get around incorrect skinning method from MakeHuman
                if skin_cluster.skinningMethod.get() < 0:
                    skin_cluster.skinningMethod.set(0)
        if not selection:
            pm.error("Please select the geometry you want to skin to the rig.")
        pm.select(selection, replace=True)

        # Export a Skin Pack
        if pm.sceneName():
            filename = os.path.splitext(os.path.basename(pm.sceneName()))[0]
        else:
            filename = "untitled"
        skin_dir = os.path.join(tempfile.gettempdir(), "skin_tmp", filename)
        if not os.path.exists(skin_dir):
            os.makedirs(skin_dir)
        pack_file = os.path.join(skin_dir, filename + ".gSkinPack")
        skin.exportJsonSkinPack(packPath=pack_file)

        # Adding weights from two joints to one
        def add_dict(a, b):
            c = {}
            keys = list(set(list(a.keys()) + list(b.keys())))
            for key in keys:
                if key in a and key in b:
                    c[key] = a[key] + b[key]
                elif key in a:
                    c[key] = a[key]
                else:
                    c[key] = b[key]
            return c

        # Edit the skin pack
        with open(pack_file) as pack_json:
            skin_pack = json.load(pack_json)
        for jSkin in skin_pack.get("packFiles"):
            skin_file = os.path.join(skin_dir, jSkin)
            with open(skin_file) as skin_json:
                skin_weights = json.load(skin_json)
            weights = skin_weights.get("objDDic")[0].get("weights")

            # Prints skinned joints that are missing from the template
            in_template = []
            for item in self.template.get("skinning"):
                for i in item[1]:
                    if i not in in_template:
                        in_template.append(i)
            missing = []
            for joint in skin_weights.get("objDDic")[0].get("weights").keys():
                if joint not in in_template:
                    if joint not in missing:
                        missing.append(joint)
            if missing:
                pm.displayInfo(
                    "The following joints are missing from the template."
                )
                for m in missing:
                    print(m)

            for item in self.template.get("skinning"):
                values = {}
                for joint in item[1]:
                    if joint in weights:
                        value = weights.pop(joint)
                        if value:
                            values = add_dict(value, values)
                            weights[item[0]] = values
                        else:
                            pm.displayInfo(
                                "{joint} has no weights. Ignoring.".format(
                                    joint=item[1]
                                )
                            )

            with open(skin_file, "w") as skin_json:
                skin_json.write(json.dumps(skin_weights))

        if not self.export_only_check.getValue():
            for sel in selection:
                pm.skinCluster(sel, e=True, unbind=True)

            # Import the modified skin pack
            skin.importSkinPack(filePath=pack_file)
            pm.displayInfo(
                "Skinning transferred from old rig to mGear joints."
            )


def plebes_gui():
    """Open the Plebes interface"""
    plebes = Plebes()
    plebes.gui()
