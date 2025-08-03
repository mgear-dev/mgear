"""
dagmenu mGear module contains all the logic to override Maya's right
click dag menu.
"""

# Stdlib imports
from __future__ import absolute_import

from functools import partial

# Maya imports
from maya import cmds, mel
import mgear.pymaya as pm
from mgear.pymaya import versions

# mGear imports
import mgear
from mgear.core.anim_utils import reset_all_keyable_attributes
from mgear.core.anim_utils import bindPose
from mgear.core.pickWalk import get_all_tag_children
from mgear.core.transform import resetTransform
from mgear.core.anim_utils import mirrorPose
from mgear.core.anim_utils import get_host_from_node
from mgear.core.anim_utils import change_rotate_order
from mgear.core.anim_utils import ikFkMatch_with_namespace
from mgear.core.anim_utils import ikFkMatch_with_namespace2
from mgear.core.anim_utils import get_ik_fk_controls
from mgear.core.anim_utils import get_ik_fk_controls_by_role
from mgear.core.anim_utils import IkFkTransfer
from mgear.core.anim_utils import changeSpace
from mgear.core.anim_utils import getNamespace
from mgear.core.anim_utils import stripNamespace
from mgear.core.anim_utils import ParentSpaceTransfer


from mgear import shifter
from mgear.shifter import guide_manager
from mgear.shifter import guide_manager_gui
from mgear.shifter import io
from mgear.shifter import guide_template

from .six import string_types

from mgear.vendor.Qt import QtWidgets


def __change_rotate_order_callback(*args):
    """Wrapper function to call mGears change rotate order function

    Args:
        list: callback from menuItem
    """

    # triggers rotate order change
    change_rotate_order(args[0], args[1])


def __keyframe_nodes_callback(*args):
    """Wrapper function to call Maya's setKeyframe command on given controls

    Args:
        list: callback from menuItem
    """

    cmds.setKeyframe(args[0])


def __mirror_flip_pose_callback(*args):
    """Wrapper function to call mGears mirroPose function

    Args:
        list: callback from menuItem
    """

    # cast controls into pymel object nodes
    controls = [pm.PyNode(x) for x in args[0]]

    # triggers mirror
    # we handle the mirror/flip each control individually even if the function
    # accepts several controls. Flipping on proxy attributes like blend
    # attributes cause an issue to rather than trying the complete list we do
    # one control to avoid the mirror to stop
    for ctl in controls:
        mirrorPose(flip=args[1], nodes=[ctl])


def _get_controls(switch_control, blend_attr, comp_ctl_list=None):
    # OBSOLETE:This function is obsolete and just keep for
    #          backward compatibility
    # replaced by get_ik_fk_controls_by_role in anim_utils module

    # first find controls from the ui host control
    ik_fk_controls = get_ik_fk_controls(
        switch_control, blend_attr, comp_ctl_list
    )

    # organise ik controls
    ik_controls = {"ik_control": None, "pole_vector": None, "ik_rot": None}

    # removes namespace from controls and order them in something usable
    # by the ikFkMatch function

    # - IKS
    for x in ik_fk_controls["ik_controls"]:
        control_name = x.split(":")[-1]
        # control_type = control_name.split("_")[-2]
        if "_ik" in control_name.lower():
            ik_controls["ik_control"] = control_name
        elif "_upv" in control_name.lower():
            ik_controls["pole_vector"] = control_name
        elif "_ikrot" in control_name.lower():
            ik_controls["ik_rot"] = control_name

    # - FKS
    fk_controls = [x.split(":")[-1] for x in ik_fk_controls["fk_controls"]]
    fk_controls = sorted(fk_controls)

    return ik_controls, fk_controls


def _is_valid_rig_root(node):
    """
    Simple exclusion of the buffer nodes and org nodes
    Args:
        node: str
    Returns: bool

    """
    short_name = node.split("|")[-1]
    long_name = cmds.ls(node, l=True)[0]
    return not (
        any(["controllers_org" in long_name, "controlBuffer" in short_name])
    )


def _list_rig_roots():
    """
    Return all the rig roots in the scene
    Returns: [str,]
    """
    return [
        n.split(".")[0]
        for n in cmds.ls("*.is_rig", r=True, l=True)
        if _is_valid_rig_root(n.split(".")[0])
    ]


def _find_rig_root(node):
    """
    Matches this node to the rig roots in the scene via a simple longName match
    Args:
        node: str
    Returns: str
    """
    long_name = cmds.ls(node, l=True)[0]
    roots = _list_rig_roots()
    for r in roots:
        if long_name.startswith(r):
            # this has to be a shortname otherwise IkFkTransfer will fail
            return r.split("|")[-1]
    return ""


def _get_switch_node_attrs(node, end_string):
    """
    returns list of attr names for given node that match the end_string arg and are not proxy attrs

    Args:
        node (TYPE): Description
        end_string (str or list): list of string suffix to search in the attr

    Returns:
        Returns: list of strings

    """
    attrs = []
    if not node:
        return []
    if not isinstance(end_string, list):
        end_string = [end_string]
    for end_str in end_string:
        for attr in cmds.listAttr(node, userDefined=True, keyable=True) or []:
            if not attr.lower().endswith(end_str) or cmds.addAttr(
                "{}.{}".format(node, attr), query=True, usedAsProxy=True
            ):
                continue
            attrs.append(attr)
    return attrs


def __range_switch_callback(*args):
    """Wrapper function to call mGears range fk/ik switch function

    Args:
        list: callback from menuItem
    """

    # instance for the range switch util
    range_switch = IkFkTransfer()

    switch_control = args[0].split("|")[-1]
    blend_attr = args[1]
    # blend attriute extension _blend, _switch or other
    # blend_attr_ext = args[2]

    # the gets root node for the given control
    # this assumes the rig is root is a root node.
    # But it's common practice to reference rigs into the scene
    # and use the reference group function to group incoming scene data.
    # Instead swap to _find_rig_root that will
    # do the same thing but account for potential parent groups.
    # root = cmds.ls(args[0], long=True)[0].split("|")[1]

    root = _find_rig_root(args[0])

    # ik_controls, fk_controls = _get_controls(switch_control, blend_attr)
    # search criteria to find all the components sharing the blend
    if "_Switch" in blend_attr:
        criteria = "*_id*_ctl_cnx"
    else:
        criteria = blend_attr.replace("_blend", "") + "_id*_ctl_cnx"
    #     component_ctl = [x for x in component_ctl if "leg" in x or "arm" in x]
    component_ctl = (
        cmds.listAttr(switch_control, ud=True, string=criteria) or []
    )
    if component_ctl:
        ik_list = []
        # fk_list = []
        # NOTE: with the new implemantation provably ikRot_list and upc_list
        # are not needed anymore since the controls will be passed with the
        #  ik_controls_complete_dict and fk_controls_complete_list
        ikRot_list = []
        upv_list = []

        ik_controls_complete_dict = {}
        fk_controls_complete_list = []
        for i, comp_ctl_list in enumerate(component_ctl):

            ik_controls, fk_controls = get_ik_fk_controls_by_role(
                switch_control, comp_ctl_list
            )
            fk_controls_complete_list = fk_controls_complete_list + fk_controls
            filtered_ik_controls = {
                k: v for k, v in ik_controls.items() if v is not None
            }
            ik_controls_complete_dict.update(filtered_ik_controls)
            if filtered_ik_controls:
                if "ik_control" in ik_controls_complete_dict.keys():
                    ik_list.append(ik_controls_complete_dict["ik_control"])
                if "pole_vector" in ik_controls_complete_dict.keys():
                    upv_list.append(ik_controls_complete_dict["pole_vector"])
                if "ik_rot" in ik_controls_complete_dict.keys():
                    ikRot_list.append(ik_controls_complete_dict["ik_rot"])

        # calls the ui
        range_switch.showUI(
            model=root,
            ikfk_attr=blend_attr,
            uihost=stripNamespace(switch_control),
            fks=fk_controls_complete_list,
            ik=ik_list,
            upv=upv_list,
            ikRot=ikRot_list,
        )


def __reset_all_transforms_callback(controls, *args):
    for c in controls:
        resetTransform(c, t=True, r=True, s=True)


def __reset_attributes_callback(*args):
    """Wrapper function to call mGears resetTransform function

    Args:
        list: callback from menuItem
    """

    attribute = args[1]

    for node in args[0]:
        control = pm.PyNode(node)

        if attribute == "translate":
            resetTransform(control, t=True, r=False, s=False)
        if attribute == "rotate":
            resetTransform(control, t=False, r=True, s=False)
        if attribute == "scale":
            resetTransform(control, t=False, r=False, s=True)


def __select_host_callback(*args):
    """Wrapper function to call mGears select host

    Args:
        list: callback from menuItem
    """

    cmds.select(get_host_from_node(args[0]))


def __select_nodes_callback(*args):
    """Wrapper function to call Maya select command

    Args:
        list: callback from menuItem
    """

    cmds.select(args[0], add=True)


def __switch_fkik_callback(*args):
    """Wrapper function to call mGears switch fk/ik snap function

    Args:
        list: callback from menuItem
    """

    switch_control = args[0].split("|")[-1]
    keyframe = args[1]
    blend_attr = args[2]
    # blend attr extension. _blend, _switch or other
    blend_attr_ext = args[3]

    # gets namespace
    namespace = getNamespace(switch_control)

    # search criteria to find all the components sharing the blend
    # criteria = blend_attr.replace(blend_attr_ext, "") + "_id*_ctl_cnx"
    # criteria = "*_id*_ctl_cnx"
    if "_Switch" in blend_attr:
        criteria = "*_id*_ctl_cnx"
        component_ctl = (
            cmds.listAttr(switch_control, ud=True, string=criteria) or []
        )
        blend_fullname = "{}.{}".format(switch_control, blend_attr)
        # if blend_attr_ext == "_blend":
        #     ik_val = 1.0
        #     fk_val = 0.0
        # else:
        ik_val = False
        fk_val = True
        ik_controls_complete_dict = {}
        fk_controls_complete_list = []
        for i, comp_ctl_list in enumerate(component_ctl):

            ik_controls, fk_controls = get_ik_fk_controls_by_role(
                switch_control, comp_ctl_list
            )
            fk_controls_complete_list = fk_controls_complete_list + fk_controls
            filtered_ik_controls = {
                k: v for k, v in ik_controls.items() if v is not None
            }
            ik_controls_complete_dict.update(filtered_ik_controls)
        init_val = None
        if ik_controls["ik_control"] and fk_controls:
            # we need to set the original blend value for each ik/fk match
            if not init_val:
                init_val = cmds.getAttr(blend_fullname)
            else:
                cmds.setAttr(blend_fullname, init_val)
        # runs switch
        ikFkMatch_with_namespace2(
            namespace=namespace,
            ikfk_attr=blend_attr,
            ui_host=switch_control,
            fk_controls=fk_controls_complete_list,
            ik_controls=ik_controls_complete_dict,
            keyframe=keyframe,
            ik_val=ik_val,
            fk_val=fk_val,
        )

    else:  # _blend attr system
        criteria = blend_attr.replace("_blend", "") + "_id*_ctl_cnx"
        component_ctl = (
            cmds.listAttr(switch_control, ud=True, string=criteria) or []
        )
        blend_fullname = "{}.{}".format(switch_control, blend_attr)
        ik_val = 1.0
        fk_val = 0.0
        # if blend_attr_ext == "_blend":
        # else:
        #     ik_val = False
        #     fk_val = True
        for i, comp_ctl_list in enumerate(component_ctl):

            ik_controls, fk_controls = get_ik_fk_controls_by_role(
                switch_control, comp_ctl_list
            )
            init_val = None
            if ik_controls["ik_control"] and fk_controls:
                # we need to set the original blend value for each ik/fk match
                if not init_val:
                    init_val = cmds.getAttr(blend_fullname)
                else:
                    cmds.setAttr(blend_fullname, init_val)
                # runs switch
                ikFkMatch_with_namespace(
                    namespace=namespace,
                    ikfk_attr=blend_attr,
                    ui_host=switch_control,
                    fks=fk_controls,
                    ik=ik_controls["ik_control"],
                    upv=ik_controls["pole_vector"],
                    ik_rot=ik_controls["ik_rot"],
                    key=keyframe,
                    ik_controls=ik_controls,
                    ik_val=ik_val,
                    fk_val=fk_val,
                )


def __switch_parent_callback(*args):
    """Wrapper function to call mGears change space function

    Args:
        list: callback from menuItem
    """

    # creates a map for non logical components controls
    control_map = {"elbow": ["mid"], "rot":[ "orbit"], "knee": ["mid"], "ik": ["headIK"]}

    # switch_control = args[0].split("|")[-1].split(":")[-1]
    switch_control = args[0].split("|")[-1]
    uiHost = pm.PyNode(switch_control)  # UiHost is switch PyNode pointer
    switch_attr = args[1]
    switch_idx = args[2]
    search_token = switch_attr.split("_")[-1].split("ref")[0].split("Ref")[0]
    target_control = None

    # control_01 attr don't standard name ane need to be check
    attr_split_name = switch_attr.split("_")
    if len(attr_split_name) <= 2:
        attr_name = attr_split_name[0]
    else:
        attr_name = "_".join(attr_split_name[:-1])
    # search criteria to find all the components sharing the name
    criteria = attr_name + "_id*_ctl_cnx"
    component_ctl = (
        cmds.listAttr(switch_control, ud=True, string=criteria) or []
    )

    target_control_list = []
    for comp_ctl_list in component_ctl:

        # first search for tokens match in all controls. If not token is found
        # we will use all controls for the switch
        # this token match is a filter for components like arms or legs
        for ctl in uiHost.attr(comp_ctl_list).listConnections():
            if ctl.ctl_role.get() == search_token:
                target_control = ctl.stripNamespace()
                break
            elif (
                search_token in control_map.keys()
                and ctl.ctl_role.get() in control_map[search_token]
            ):
                target_control = ctl.stripNamespace()
                break

        if target_control:
            target_control_list.append(target_control)
        else:
            # token didn't match with any target control. We will add all
            # found controls for the match.
            # This is needed for regular ik match in Control_01
            for ctl in uiHost.attr(comp_ctl_list).listConnections():

                target_control_list.append(ctl.stripNamespace())

    if search_token in ["follow"] and not target_control_list:
        # in this case we asume that the control holds is own space
        # switch attr. This attr is also expected to have simple name
        # witout description to witch component belongs. This works only
        # if the attr is on a control of the same component that is not a
        # genearal uiHost for other components
        target_control = uiHost.stripNamespace()
        target_control_list.append(target_control)

    # gets root node for the given control
    namespace_value = args[0].split("|")[-1].split(":")
    if len(namespace_value) > 1:
        namespace_value = namespace_value[0]
    else:
        namespace_value = ""

    root = None

    current_parent = cmds.listRelatives(args[0], fullPath=True, parent=True)
    if current_parent:
        current_parent = current_parent[0]

    while not root:

        if cmds.objExists("{}.is_rig".format(current_parent)):
            root = cmds.ls("{}.is_rig".format(current_parent))[0]
        else:
            try:
                current_parent = cmds.listRelatives(
                    current_parent, fullPath=True, parent=True
                )[0]
            except TypeError:
                break

    if not root or not target_control_list:
        pm.displayInfo("Not root or target control list for space transfer")
        return

    autokey = cmds.listConnections(
        "{}.{}".format(switch_control, switch_attr), type="animCurve"
    )

    if autokey:
        for target_control in target_control_list:
            cmds.setKeyframe(
                "{}:{}".format(namespace_value, target_control),
                "{}.{}".format(switch_control, switch_attr),
                time=(cmds.currentTime(query=True) - 1.0),
            )

    # triggers switch
    changeSpace(
        root, switch_control, switch_attr, switch_idx, target_control_list
    )

    if autokey:
        for target_control in target_control_list:
            cmds.setKeyframe(
                "{}:{}".format(namespace_value, target_control),
                "{}.{}".format(switch_control, switch_attr),
                time=(cmds.currentTime(query=True)),
            )


def __space_transfer_callback(*args):
    """Wrapper function to call mGears change space function

    Args:
        list: callback from menuItem
    """

    # creates a map for non logical components controls
    control_map = {"elbow": ["mid"], "rot": ["orbit", "fk0"], "knee": ["mid"]}

    # switch_control = args[0].split("|")[-1].split(":")[-1]
    switch_control = args[0].split("|")[-1]
    uiHost = pm.PyNode(switch_control)  # UiHost is switch PyNode pointer
    switch_attr = args[1]
    combo_box = args[2]
    search_token = switch_attr.split("_")[-1].split("ref")[0].split("Ref")[0]
    print(search_token)
    target_control = None

    # control_01 attr don't standard name ane need to be check
    attr_split_name = switch_attr.split("_")
    if len(attr_split_name) <= 2:
        attr_name = attr_split_name[0]
    else:
        attr_name = "_".join(attr_split_name[:-1])
    # search criteria to find all the components sharing the name
    criteria = attr_name + "_id*_ctl_cnx"
    component_ctl = (
        cmds.listAttr(switch_control, ud=True, string=criteria) or []
    )

    target_control_list = []
    for comp_ctl_list in component_ctl:

        # first search for tokens match in all controls. If not token is found
        # we will use all controls for the switch
        # this token match is a filter for components like arms or legs
        for ctl in uiHost.attr(comp_ctl_list).listConnections():
            if ctl.ctl_role.get() == search_token:
                target_control = ctl.stripNamespace()
                break
            elif (
                search_token in control_map.keys()
                and ctl.ctl_role.get() in control_map[search_token]
            ):
                target_control = ctl.stripNamespace()
                break

        if target_control:
            target_control_list.append(target_control)
        else:
            # token didn't match with any target control. We will add all
            # found controls for the match.
            # This is needed for regular ik match in Control_01
            for ctl in uiHost.attr(comp_ctl_list).listConnections():

                target_control_list.append(ctl.stripNamespace())

    # gets root node for the given control
    namespace_value = args[0].split("|")[-1].split(":")
    if len(namespace_value) > 1:
        namespace_value = namespace_value[0]
    else:
        namespace_value = ""

    root = None

    current_parent = cmds.listRelatives(args[0], fullPath=True, parent=True)
    if current_parent:
        current_parent = current_parent[0]

    while not root:

        if cmds.objExists("{}.is_rig".format(current_parent)):
            root = cmds.ls("{}.is_rig".format(current_parent))[0]
        else:
            try:
                current_parent = cmds.listRelatives(
                    current_parent, fullPath=True, parent=True
                )[0]
            except TypeError:
                break

    if not root or not target_control_list:
        pm.displayInfo("Not root or target control list for space transfer")
        return

    # autokey = cmds.listConnections(
    #     "{}.{}".format(switch_control, switch_attr), type="animCurve"
    # )

    # if autokey:
    #     print("Autokey run")
    #     for target_control in target_control_list:
    #         cmds.setKeyframe(
    #             "{}:{}".format(namespace_value, target_control),
    #             "{}.{}".format(switch_control, switch_attr),
    #             time=(cmds.currentTime(query=True) - 1.0),
    #         )

    # triggers switch
    ParentSpaceTransfer.showUI(
        combo_box,
        switch_control,
        stripNamespace(switch_control),
        switch_attr,
        target_control_list[0],
    )

    # if autokey:
    #     for target_control in target_control_list:
    #         cmds.setKeyframe(
    #             "{}:{}".format(namespace_value, target_control),
    #             "{}.{}".format(switch_control, switch_attr),
    #             time=(cmds.currentTime(query=True)),
    #         )


def __switch_xray_ctl_callback(*args):
    rig_root = None
    if pm.selected():
        ctl = pm.selected()[0]
        if ctl.hasAttr("isCtl"):
            tag = ctl.message.listConnections(type="controller")[0]
            rig_root = tag.message.listConnections()[0]
            if rig_root.hasAttr("is_rig") and rig_root.hasAttr("ctl_x_ray"):
                if rig_root.ctl_x_ray.get():
                    rig_root.ctl_x_ray.set(False)
                else:
                    rig_root.ctl_x_ray.set(True)


def get_option_var_state():
    """Gets dag menu option variable

    Maya's optionVar command installs a variable that is kept on Maya's
    settings so that you can use it on future sessions.

    Maya's optionVar are a quick and simple way to store a custom variable on
    Maya's settings but beware that they are kept even after mGear's uninstall
    so you will need to run the following commands.

    Returns:
        bool: Whether or not mGear's dag menu override is used

    Example:
        The following removes mgears dag menu optionVar

        .. code-block:: python

           from maya import cmds

           if not cmds.optionVar(exists="mgear_dag_menu_OV"):
               cmds.optionVar(remove="mgear_dag_menu_OV")
    """

    # if there is no optionVar the create one that will live during maya
    # current and following sessions
    if not cmds.optionVar(exists="mgear_dag_menu_OV"):
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 0))

    return cmds.optionVar(query="mgear_dag_menu_OV")


def install():
    """Installs dag menu option"""

    # get state
    state = get_option_var_state()

    cmds.setParent(mgear.menu_id, menu=True)
    cmds.menuItem(divider=True)
    cmds.menuItem(
        "mgear_dagmenu_menuitem",
        label="mGear Viewport Menu ",
        command=run,
        checkBox=state,
    )

    run(state)


def mgear_dagmenu_callback(*args, **kwargs):  # @UnusedVariable
    """Triggers dag menu display

    If selection is ends with **_ctl** then display mGear's contextual menu.
    Else display Maya's standard right click dag menu

    Args:
        *args: Parent Menu path name / Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        str: Menu object name/path that is passed to the function
    """

    # cast args into more descend variable name
    parent_menu = args[0]

    # if second argument if not a bool then means that we are running
    # the override
    if not isinstance(args[1], bool):
        sel = cmds.ls(selection=True, long=True, type="transform")

        if sel:
            isCtl = cmds.objExists("{}.isCtl".format(sel[0]))
            isGuide = cmds.objExists("{}.rig_name".format(sel[0]))
            isGearGuide = cmds.objExists("{}.isGearGuide".format(sel[0]))

        if sel and isCtl:
            # cleans menu
            _parent_menu = parent_menu.replace('"', "")
            cmds.menu(_parent_menu, edit=True, deleteAllItems=True)

            # fills menu
            mgear_dagmenu_fill(_parent_menu, sel[0])

        elif sel and isGuide or sel and isGearGuide:
            # cleans menu
            _parent_menu = parent_menu.replace('"', "")
            cmds.menu(_parent_menu, edit=True, deleteAllItems=True)

            # fills menu
            mgear_dagmenu_guide_fill(_parent_menu, sel[0])
        else:
            mel.eval("buildObjectMenuItemsNow " + parent_menu)

    # always return parent menu path
    return parent_menu


def mgear_dagmenu_guide_fill(parent_menu, current_guide_locator):
    """Fill the given menu with mGear's custom guide menu

    Args:
        parent_menu(str): Parent Menu path name
        current_guide_locator(str): current selected mGear guide locator
    """

    # gets current selection to use later on
    _current_selection = cmds.ls(selection=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Settings",
        command=partial(guide_manager.inspect_settings, 0),
        image="mgear_sliders.svg",
    )
    cmds.menuItem(parent=parent_menu, divider=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Build From Selection",
        command=guide_manager.build_from_selection,
        image="mgear_play.svg",
    )
    cmds.menuItem(parent=parent_menu, divider=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Duplicate",
        command=partial(guide_manager.duplicate, False),
        image="mgear_copy.svg",
    )
    cmds.menuItem(
        parent=parent_menu,
        label="Duplicate Symme",
        command=partial(guide_manager.duplicate, True),
        image="mgear_duplicate_sym.svg",
    )
    cmds.menuItem(parent=parent_menu, divider=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Guide Manager",
        command=guide_manager_gui.show_guide_manager,
        image="mgear_list.svg",
    )
    cmds.menuItem(parent=parent_menu, divider=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Export Guide From Selection",
        command=partial(io.export_guide_template, None, None),
        image="mgear_log-out.svg",
    )
    cmds.menuItem(parent=parent_menu, divider=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Update Guide",
        command=guide_template.updateGuide,
        image="mgear_loader.svg",
    )
    cmds.menuItem(
        parent=parent_menu,
        label="Reload Components",
        command=shifter.reloadComponents,
        image="mgear_refresh-cw.svg",
    )
    if versions.current() >= 20220000:
        cmds.menuItem(parent=parent_menu, divider=True)
        cmds.menuItem(
            parent=parent_menu,
            label="X-Ray Guide Toggle",
            command=guide_template.guide_toggle_xray,
            image="mgear_x.svg",
        )


def mgear_dagmenu_fill(parent_menu, current_control):
    """Fill the given menu with mGear's custom animation menu

    Args:
        parent_menu(str): Parent Menu path name
        current_control(str): current selected mGear control
    """

    # gets current selection to use later on
    _current_selection = cmds.ls(selection=True)

    # get child controls
    child_controls = []
    for ctl in _current_selection:
        [
            child_controls.append(x)
            for x in get_all_tag_children(ctl)
            if x not in child_controls
        ]
        # [child_controls.append(x)
        #  for x in get_all_tag_children(cmds.ls(cmds.listConnections(ctl),
        #                                        type="controller"))
        #  if x not in child_controls]

    child_controls.append(current_control)
    attrs = _get_switch_node_attrs(current_control, "_blend")
    attrs2 = _get_switch_node_attrs(current_control, "ref")
    attrs3 = _get_switch_node_attrs(current_control, "_switch")
    # attrs4 = _get_switch_node_attrs(current_control, "follow")

    if attrs or attrs2 or attrs3:
        ui_host = current_control

    else:
        try:
            ui_host = cmds.listConnections(
                "{}.uiHost_cnx".format(current_control)
            )[0]
            attrs = _get_switch_node_attrs(ui_host, "_blend")
            attrs2 = _get_switch_node_attrs(ui_host, "ref")
            attrs3 = _get_switch_node_attrs(ui_host, "_switch")
            attrs4 = _get_switch_node_attrs(ui_host, "follow")
            if not attrs and not attrs2 and not attrs3 and not attrs4:
                ui_host = None
        except ValueError:
            ui_host = None
        except TypeError:
            ui_host = None

    # check is given control is an mGear control
    if cmds.objExists("{}.uiHost".format(current_control)):
        # select ui host
        cmds.menuItem(
            parent=parent_menu,
            label="Select host",
            command=partial(__select_host_callback, current_control),
            image="hotkeySetSettings.png",
        )

        # divider
        cmds.menuItem(parent=parent_menu, divider=True)

    def add_menu_items(attrs, attr_extension="_blend"):
        for attr in attrs:
            # found attribute so get current state
            current_state = cmds.getAttr("{}.{}".format(ui_host, attr))
            if attr_extension == "_blend":
                states = {0: "Fk", 1: "Ik"}
            else:
                states = {0: "IK", 1: "Fk"}

            rvs_state = states[int(not current_state)]

            cmds.menuItem(
                parent=parent_menu,
                label="Switch {} to {}".format(
                    attr.split(attr_extension)[0], rvs_state
                ),
                command=partial(
                    __switch_fkik_callback,
                    ui_host,
                    False,
                    attr,
                    attr_extension,
                ),
                image="kinReroot.png",
            )

            cmds.menuItem(
                parent=parent_menu,
                label="Switch {} to {} + Key".format(
                    attr.split(attr_extension)[0], rvs_state
                ),
                command=partial(
                    __switch_fkik_callback, ui_host, True, attr, attr_extension
                ),
                image="character.svg",
            )

            cmds.menuItem(
                parent=parent_menu,
                label="Range switch",
                command=partial(
                    __range_switch_callback, ui_host, attr, attr_extension
                ),
            )

            # divider
            cmds.menuItem(parent=parent_menu, divider=True)

    if attrs:
        add_menu_items(attrs)
    if attrs3:
        add_menu_items(attrs3, attr_extension="_switch")

    # select all function
    cmds.menuItem(
        parent=parent_menu,
        label="Select child controls",
        command=partial(__select_nodes_callback, child_controls),
        image="dagNode.svg",
    )

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # reset selected
    cmds.menuItem(
        parent=parent_menu,
        label="Reset",
        command=partial(reset_all_keyable_attributes, _current_selection),
        image="holder.svg",
    )

    resetOption = cmds.menuItem(
        parent=parent_menu,
        subMenu=True,
        tearOff=False,
        label="Reset Option",
    )

    # reset all
    selection_set = cmds.ls(
        cmds.listConnections(current_control), type="objectSet"
    )
    all_rig_controls = cmds.sets(selection_set, query=True)
    cmds.menuItem(
        parent=resetOption,
        label="Reset all",
        command=partial(reset_all_keyable_attributes, all_rig_controls),
    )

    # reset all below
    cmds.menuItem(
        parent=resetOption,
        label="Reset all below",
        command=partial(reset_all_keyable_attributes, child_controls),
    )

    # bindpose
    cmds.menuItem(
        parent=resetOption,
        label="Reset To BindPose",
        command=partial(bindPose, _current_selection[0]),
    )

    # divider
    cmds.menuItem(parent=resetOption, divider=True)

    # reset all SRT
    cmds.menuItem(
        parent=resetOption,
        label="Reset All SRT",
        command=partial(__reset_all_transforms_callback, all_rig_controls),
    )

    # add transform resets
    k_attrs = cmds.listAttr(current_control, keyable=True) or []
    for attr in ("translate", "rotate", "scale"):
        # checks if the attribute is a maya transform attribute
        if [x for x in k_attrs if attr in x and len(x) == len(attr) + 1]:
            icon = "{}_M.png".format(attr)
            if attr == "translate":
                icon = "move_M.png"
            cmds.menuItem(
                parent=resetOption,
                label="Reset {}".format(attr),
                command=partial(
                    __reset_attributes_callback, _current_selection, attr
                ),
                image=icon,
            )

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # add mirror
    cmds.menuItem(
        parent=parent_menu,
        label="Mirror",
        command=partial(
            __mirror_flip_pose_callback, _current_selection, False
        ),
        image="redrawPaintEffects.png",
    )
    cmds.menuItem(
        parent=parent_menu,
        label="Mirror all below",
        command=partial(__mirror_flip_pose_callback, child_controls, False),
    )

    # add flip
    cmds.menuItem(
        parent=parent_menu,
        label="Flip",
        command=partial(__mirror_flip_pose_callback, _current_selection, True),
        image="redo.png",
    )
    cmds.menuItem(
        parent=parent_menu,
        label="Flip all below",
        command=partial(__mirror_flip_pose_callback, child_controls, True),
    )

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # rotate order
    if (
        cmds.getAttr("{}.rotateOrder".format(current_control), channelBox=True)
        or cmds.getAttr("{}.rotateOrder".format(current_control), keyable=True)
        and not cmds.getAttr(
            "{}.rotateOrder".format(current_control), lock=True
        )
    ):
        _current_r_order = cmds.getAttr(
            "{}.rotateOrder".format(current_control)
        )
        _rot_men = cmds.menuItem(
            parent=parent_menu,
            subMenu=True,
            tearOff=False,
            label="Rotate Order switch",
        )
        cmds.radioMenuItemCollection(parent=_rot_men)
        orders = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
        for idx, order in enumerate(orders):
            if idx == _current_r_order:
                state = True
            else:
                state = False
            cmds.menuItem(
                parent=_rot_men,
                label=order,
                radioButton=state,
                command=partial(
                    __change_rotate_order_callback, current_control, order
                ),
            )

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # handles constrains attributes (constrain switches)
    space_attrs = _get_switch_node_attrs(ui_host, ["ref", "follow"])
    ui_hosts = [ui_host for x in space_attrs]

    # in case is not uiHost but also contain space attr like follow or ref
    if current_control != ui_host:
        space_attr_out_of_uiHost = _get_switch_node_attrs(
            current_control, ["ref", "follow"]
        )
        out_ui_hosts = [current_control for x in space_attr_out_of_uiHost]
        if space_attr_out_of_uiHost:
            space_attrs = space_attrs + space_attr_out_of_uiHost
            ui_hosts = ui_hosts + out_ui_hosts

    if ui_hosts:
        for attr, uih in zip(space_attrs, ui_hosts):

            part, ctl = (
                attr.split("_")[0],
                attr.split("_")[-1].split("Ref")[0].split("ref")[0],
            )
            _p_switch_menu = cmds.menuItem(
                parent=parent_menu,
                subMenu=True,
                tearOff=False,
                label="Parent {} {}".format(part, ctl),
                image="dynamicConstraint.svg",
            )
            cmds.radioMenuItemCollection(parent=_p_switch_menu)
            k_values = cmds.addAttr(
                "{}.{}".format(uih, attr), query=True, enumName=True
            ).split(":")
            current_state = cmds.getAttr("{}.{}".format(uih, attr))

            combo_box = QtWidgets.QComboBox()

            for idx, k_val in enumerate(k_values):
                combo_box.addItem(k_val)
                if idx == current_state:
                    state = True
                    combo_box.setCurrentIndex(idx)
                else:
                    state = False
                cmds.menuItem(
                    parent=_p_switch_menu,
                    label=k_val,
                    radioButton=state,
                    command=partial(
                        __switch_parent_callback, uih, attr, idx, k_val
                    ),
                )

            combo_box.addItem("__")  # required to include the last item
            cmds.menuItem(
                parent=_p_switch_menu,
                label="++ Space Transfer ++",
                command=partial(
                    __space_transfer_callback, uih, attr, combo_box
                ),
            )

    # select all rig controls
    selection_set = cmds.ls(
        cmds.listConnections(current_control), type="objectSet"
    )
    all_rig_controls = cmds.sets(selection_set, query=True)
    cmds.menuItem(
        parent=parent_menu,
        label="Select all controls",
        command=partial(__select_nodes_callback, all_rig_controls),
    )

    # key all below function
    cmds.menuItem(
        parent=parent_menu,
        label="Keyframe child controls",
        command=partial(__keyframe_nodes_callback, child_controls),
        image="setKeyframe.png",
    )

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # x-ray ctl toggle
    if versions.current() >= 20220000:
        cmds.menuItem(parent=parent_menu, divider=True)
        cmds.menuItem(
            parent=parent_menu,
            label="X-Ray CTL Toggle",
            command=__switch_xray_ctl_callback,
            image="mgear_x.svg",
        )


def mgear_dagmenu_toggle(state):
    """Set on or off the mgear dag menu override

    This function is responsible for turning ON or OFF mgear's right click
    menu override. When turned on this will interact with dag nodes that
    have **_ctl** at the end of their name.

    Args:
        state (bool): Whether or not to override Maya's dag menu with mGear's
                      dag menu
    """

    # First loop on Maya menus as Maya's dag menu is a menu
    for maya_menu in cmds.lsUI(menus=True):

        # We now get the menu's post command which is a command used for
        # dag menu
        menu_cmd = cmds.menu(maya_menu, query=True, postMenuCommand=True) or []

        # If state is set top True then override Maya's dag menu
        if state and isinstance(menu_cmd, string_types):
            if "buildObjectMenuItemsNow" in menu_cmd:
                # Maya's dag menu post command has the parent menu in it
                parent_menu = menu_cmd.split(" ")[-1]
                # Override dag menu with custom command call
                cmds.menu(
                    maya_menu,
                    edit=True,
                    postMenuCommand=partial(
                        mgear_dagmenu_callback, parent_menu
                    ),
                )

        # If state is set to False then put back Maya's dag menu
        # This is tricky because Maya's default menu command is a MEL call
        # The override part uses a python function partial call and because of
        # this we need to do some small hack on mGear_dag_menu_callback to give
        # back the default state of Maya's dag menu
        elif not state and type(menu_cmd) == partial:
            # we now check if the command override is one from us
            # here because we override original function we need
            # to get the function name by using partial.func
            if "mgear_dagmenu_callback" in menu_cmd.func.__name__:
                # we call the mGear_dag_menu_callback with the future state
                # this will return the original menu parent so that we
                # can put Maya's original dag menu command in mel
                parent_menu = menu_cmd(state)

                # we set the old mel command
                # don't edit any space or syntax here as this is what Maya
                # expects
                mel.eval(
                    "menu -edit -postMenuCommand "
                    '"buildObjectMenuItemsNow '
                    + parent_menu.replace('"', "")
                    + '"'
                    + maya_menu
                )


def run(*args, **kwargs):  # @UnusedVariable
    """Menu run execution

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """

    # get check-box state
    state = args[0]

    if state:
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 1))
    else:
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 0))

    # runs dag menu right click mgear's override
    mgear_dagmenu_toggle(state)
