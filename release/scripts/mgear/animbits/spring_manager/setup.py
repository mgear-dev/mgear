import json

import mgear.pymaya as pm
import math

import mgear
from mgear.core import attribute
from mgear.core import transform
from mgear.core import primitive
from mgear.core import applyop
from mgear.core import icon
from mgear.core import node as cNode
from mgear import rigbits
from mgear.core.utils import one_undo, viewport_off

SPRING_ATTRS = [
    "springTotalIntensity",
    "springRigScale",
    "springTranslationalIntensity",
    "springTranslationalDamping",
    "springTranslationalStiffness",
    "springRotationalIntensity",
    "springRotationalDamping",
    "springRotationalStiffness",
    "springSetupMembers",
    "springConfig",
    "springTranslation",
    "springRotation",
    "springDirectionVis",
]

SPRING_PRESET_EXTENSION = ".spg"


def create_settings_attr(node, config):
    """Add specified spring attributes from a given Maya node.

    Args:
        node (str or PyNode): The name or PyNode of the node from which
                              to add attributes.
    """
    if isinstance(node, str):
        node = pm.PyNode(node)

    # Check if attr already exists at node
    if pm.attributeQuery("springTotalIntensity", node=node, exists=True):
        return False
    channelBox = True
    keyable = False
    # separator Attr
    attr_name = "springConfig"
    attribute.addEnumAttribute(
        node, attr_name, 0, ["Spring Config"], niceName="__________"
    )
    node.setAttr(attr_name, channelBox=channelBox, keyable=keyable)

    # Keyable attr

    attribute.addAttribute(
        node,
        "springTotalIntensity",
        "float",
        config["springTotalIntensity"],
        minValue=0,
        maxValue=1,
    )
    attribute.addAttribute(
        node,
        "springRigScale",
        "float",
        config["springRigScale"],
        minValue=0,
        maxValue=100,
    )
    # separator Attr
    attr_name = "springTranslation"
    attribute.addEnumAttribute(
        node, attr_name, 0, ["Spring Translation"], niceName="__________"
    )
    node.setAttr(attr_name, channelBox=channelBox, keyable=keyable)

    # Keyable attr
    attribute.addAttribute(
        node,
        "springTranslationalIntensity",
        "float",
        config["springTranslationalIntensity"],
        minValue=0,
        maxValue=1,
    )
    attribute.addAttribute(
        node,
        "springTranslationalDamping",
        "float",
        config["springTranslationalDamping"],
        minValue=0,
        maxValue=1,
    )
    attribute.addAttribute(
        node,
        "springTranslationalStiffness",
        "float",
        config["springTranslationalStiffness"],
        minValue=0,
        maxValue=1,
    )
    # separator Attr
    attr_name = "springRotation"
    attribute.addEnumAttribute(
        node, attr_name, 0, ["Spring Rotation"], niceName="__________"
    )
    node.setAttr(attr_name, channelBox=channelBox, keyable=keyable)

    # Keyable attr
    attribute.addAttribute(
        node,
        "springRotationalIntensity",
        "float",
        config["springRotationalIntensity"],
        minValue=0,
        maxValue=1,
    )
    attribute.addAttribute(
        node,
        "springRotationalDamping",
        "float",
        config["springRotationalDamping"],
        minValue=0,
        maxValue=1,
    )
    attribute.addAttribute(
        node,
        "springRotationalStiffness",
        "float",
        config["springRotationalStiffness"],
        minValue=0,
        maxValue=1,
    )

    # direction visibility Attr
    attr_name = "springDirectionVis"
    attribute.addAttribute(node, attr_name, "bool", True)
    node.setAttr(attr_name, channelBox=channelBox, keyable=keyable)

    # add message attr to node
    node.addAttr("springSetupMembers", at="message", m=True)

    return True


def remove_settings_attr(node):
    """
    Remove specified spring attributes from a given Maya node.

    Args:
        node (str or PyNode): The name or PyNode of the node from which
                              to remove attributes.

    Returns:
        None
    """
    # Convert to PyNode if node is given as a string
    if isinstance(node, str):
        node = pm.PyNode(node)

    # Loop through each attribute and attempt to remove it if it exists
    for attr in SPRING_ATTRS:
        if pm.attributeQuery(attr, node=node, exists=True):
            pm.deleteAttr(node.attr(attr))
            print("Removed attribute " + attr + " from " + str(node))
        else:
            print("Attribute " + attr + " does not exist on " + str(node))


def get_settings_attr_val(node):
    """
    Get the values of the spring attributes on a given Maya node.

    Args:
        node (str or PyNode): The name or PyNode of the node from which
                              to get the attribute values.

    Returns:
        dict: A dictionary of the attribute values.
    """
    # Convert to PyNode if node is given as a string
    if isinstance(node, str):
        node = pm.PyNode(node)

    # Create a dictionary to store the attribute values
    attr_vals = {}

    # Loop through each attribute and attempt to get its value
    for attr in SPRING_ATTRS[:-4]:
        if pm.attributeQuery(attr, node=node, exists=True):
            attr_vals[attr] = node.attr(attr).get()
        else:
            print("Attribute " + attr + " does not exist on " + str(node))

    return attr_vals


def set_settings_attr_val(node, attr_vals):
    """
    Set the values of the spring attributes on a given Maya node.

    Args:
        node (str or PyNode): The name or PyNode of the node on which
                              to set the attribute values.
        attr_vals (dict): A dictionary of the attribute values.

    Returns:
        None
    """
    # Convert to PyNode if node is given as a string
    if isinstance(node, str):
        node = pm.PyNode(node)

    # Loop through each attribute and attempt to set its value
    for attr in SPRING_ATTRS[:-4]:
        if pm.attributeQuery(attr, node=node, exists=True):
            node.attr(attr).set(attr_vals[attr])
        else:
            print("Attribute " + attr + " does not exist on " + str(node))


# check if object has spring by checking if has attr springSetupMembers
def has_spring(node):
    if pm.attributeQuery("springSetupMembers", node=node, exists=True):
        return True
    else:
        return False


def get_name(node, name):
    """
    Return a name composed of the node name + name.
    """

    if isinstance(node, str):
        node_name = node
    else:
        node_name = node.name()
    return node_name + "_" + name


# TODO: Node is also in config as string, so not need to pass here
@one_undo
def create_spring(node=None, config=None):
    if node is None and config is not None:
        node = config["node"]

    if isinstance(node, str):
        node = pm.PyNode(node)

    def get_name(name, node=node):
        """
        Return a name composed of the node name + name.
        """

        if isinstance(node, str):
            node_name = node
        else:
            node_name = node.name()
        return node_name + "_" + name

    # add settings attr
    result = create_settings_attr(node, config)
    if not result:
        mgear.log("Spring already exists at {}".format(node.name()))
        return False

    # Get node transform
    t = transform.getTransform(node)

    parent = node.getParent()

    # create root
    root = primitive.addTransform(parent, get_name("sprg_root"), t)
    root.rotateOrder.set(node.rotateOrder.get())

    # translate spring
    trans_sprg = primitive.addTransform(root, get_name("sprg_trans"), t)

    # aim direction root
    aim_root = primitive.addTransform(trans_sprg, get_name("sprg_aim"), t)

    # aim direction goal
    aim_goal = primitive.addTransform(aim_root, get_name("sprg_goal"), t)

    # the  list represents the following attr
    # translation axis aim
    # translation value for aim
    # aimconstrain config axis and up-vector
    directions = {
        "x": ["tx", 1, "xy", [0, 1, 0]],
        "y": ["ty", 1, "yx", [1, 0, 0]],
        "z": ["tz", 1, "zy", [0, 1, 0]],
        "-x": ["tx", -1, "-xy", [0, 1, 0]],
        "-y": ["ty", -1, "-yx", [1, 0, 0]],
        "-z": ["tz", -1, "-zy", [0, 1, 0]],
    }
    try:
        direction = directions[config["direction"]]
    except KeyError:
        raise KeyError("Invalid direction specified in config.")

    # aim_root.attr(direction[0]).set(direction[1] * config["springRigScale"])
    # aim_goal.attr(direction[0]).set(direction[1] * config["springRigScale"])

    cNode.createMulNode(
        node.attr(SPRING_ATTRS[1]),
        direction[1],
        aim_root.attr(direction[0]),
    )

    # spring driver
    driver = primitive.addTransform(trans_sprg, get_name("sprg_driver"), t)

    # connect metadata
    attribute.connect_message(
        [root, trans_sprg, aim_root, aim_goal, driver], node.springSetupMembers
    )

    # position spring
    sprg_pos_node = applyop.gear_spring_op(trans_sprg)

    # atter to track spring setups from spring node
    sprg_pos_node.addAttr("springSetupDriven", at="message", m=False)
    pm.connectAttr(node.message, sprg_pos_node.attr("springSetupDriven"))

    # direction spring
    sprg_rot_node = applyop.gear_spring_op(aim_goal)

    # aim direction
    applyop.aimCns(
        driver, aim_goal, direction[2], 2, direction[3], trans_sprg, False
    )

    # connect attrs
    driven_attr = [
        sprg_pos_node.intensity,
        sprg_pos_node.damping,
        sprg_pos_node.stiffness,
        sprg_rot_node.intensity,
        sprg_rot_node.damping,
        sprg_rot_node.stiffness,
    ]
    for at, dat in zip(SPRING_ATTRS[2:], driven_attr):
        pm.connectAttr(node.attr(at), dat)

    cNode.createMulNode(
        [
            node.attr(SPRING_ATTRS[0]),
            node.attr(SPRING_ATTRS[0]),
        ],
        [
            node.attr(SPRING_ATTRS[2]),
            node.attr(SPRING_ATTRS[5]),
        ],
        [
            sprg_pos_node.intensity,
            sprg_rot_node.intensity,
        ],
    )

    # add direction visual arrow

    arrow = icon.direction_arrow(
        axis=config["direction"],
        name=get_name("sprg_arrowDirection"),
        parent_name=driver.name()
    )
    transform.resetTransform(arrow)
    arrow.attr("overrideEnabled").set(1)
    arrow.attr("overrideDisplayType").set(1)
    # connect arrow scale
    pm.connectAttr(node.attr(SPRING_ATTRS[1]), arrow.sx)
    pm.connectAttr(node.attr(SPRING_ATTRS[1]), arrow.sy)
    pm.connectAttr(node.attr(SPRING_ATTRS[1]), arrow.sz)
    # connect arrow vis
    for shp in arrow.getShapes():
        pm.connectAttr(node.springDirectionVis, shp.visibility)

    # move animation curvers
    move_animation_curves(node, root)

    # connect driver to node
    cns = applyop.parentCns(driver, node, maintain_offset=False)
    cns.isHistoricallyInteresting.set(False)

    pm.select(cl=True)

    return driver, node


# init the configuration to create a spring
"""
config = {
    "node" : "node_name",
    "direction" : "x",
    "scale" : 1,
    "springTotalIntensity": 1,
    "springTranslationalIntensity": 0,
    "springTranslationalDamping": 0.5,
    "springTranslationalStiffness": 0.5,
    "springRotationalIntensity": 1,
    "springRotationalDamping": 0.5,
    "springRotationalStiffness": 0.5,

}
"""


def init_config(node, direction, scale):
    # if node is pynode get node str name
    if not isinstance(node, str):
        node = node.name()
    config = {
        "node": node,
        "direction": direction,
        "springRigScale": scale,
        "springTotalIntensity": 1,
        "springTranslationalIntensity": 0,
        "springTranslationalDamping": 0.5,
        "springTranslationalStiffness": 0.5,
        "springRotationalIntensity": 1,
        "springRotationalDamping": 0.5,
        "springRotationalStiffness": 0.5,
        "springDirectionVis": True,
    }
    return config


def get_child_axis_direction(child_node):
    """
    Get the axis direction ('x', 'y', 'z', '-x', '-y', '-z') of a child node
    relative to its parent node.

    Args:
        child_node (str or PyNode): The child node name or PyNode object.

    Returns:
        str: The axis direction ('x', 'y', 'z', '-x', '-y', '-z')
             or 'ambiguous' if the direction is not clear.
    """

    # Convert to PyNode if the child node is given as a string
    if isinstance(child_node, str):
        child_node = pm.PyNode(child_node)

    # Get the parent node
    parent_node = pm.listRelatives(child_node, p=True)
    if not parent_node:
        return "No parent found"
    parent_node = parent_node[0]

    # Get local translation of the child relative to the parent
    local_translation = child_node.getTranslation(space="object")

    # Determine axis direction
    axis = None
    max_val = 0
    for ax, val in zip(
        ["x", "y", "z"],
        [local_translation.x, local_translation.y, local_translation.z],
    ):
        if math.fabs(val) > max_val:
            max_val = math.fabs(val)
            axis = ax

    if max_val == 0:
        return "ambiguous"

    # Check for the sign of the maximum value along the axis
    axis_value = getattr(local_translation, axis)
    if axis_value < 0:
        axis = "-" + axis

    return axis


def get_rig_scale_value(child_node):
    """Get the rig scale value based on the distance offset of the child node

    Args:
        child_node (str or PyNode): The child node name or PyNode object

    Returns:
        float: scale value distance
    """
    # Convert to PyNode if the child node is given as a string
    if isinstance(child_node, str):
        child_node = pm.PyNode(child_node)
    axis = get_child_axis_direction(child_node)
    return abs(child_node.getAttr("t{}".format(axis[-1])))


def get_config(node):
    # get config dict from node attrs
    if not isinstance(node, str):
        node_name = node.stripNamespace()
    else:
        node_name = node
    # TODO: get child node name from the spring members
    # child_node = pm.listRelatives(node, c=True)
    if not pm.hasAttr(node, "springSetupMembers"):
        print("{} doesn't have springSetupMembers attr".format(node))
        return False
    child_node = pm.listConnections(node.springSetupMembers[2])[0]
    direction = get_child_axis_direction(child_node)
    scale = get_rig_scale_value(child_node)
    config = {
        "node": node_name,
        "namespace": node.namespace(),
        "direction": direction,
    }
    attr_val = get_settings_attr_val(node)
    config.update(attr_val)
    return config


# store preset configuration
def store_preset(nodes, filePath=None):
    preset_dic = {}
    preset_dic["nodes"] = [node.name() for node in nodes]
    preset_dic["namespaces"] = list({node.namespace() for node in nodes})
    preset_dic["configs"] = {}

    for node in nodes:
        node_config = get_config(node)
        if node_config is False:
            pm.warning("Node '{}' is not a spring.".format(node.name()))
            preset_dic["nodes"].remove(node.name())
            continue
        preset_dic["configs"][node.name()] = node_config

    print("file_path = {}".format(filePath))

    data_string = json.dumps(preset_dic, indent=4, sort_keys=True)
    with open(filePath, "w") as f:
        f.write(data_string)

    return preset_dic


# store preset configuration, from selected springs
def store_preset_from_selection(filePath=None):
    nodes = pm.selected()
    store_preset(nodes, filePath)


# apply spring from a  preset
def apply_preset(preset_file_path, namespace_cb):
    """ "
    Applies preset.
    """
    affected_nodes = []
    with open(preset_file_path, "r") as fp:
        preset_dic = json.load(fp)

    # if there's only one namespace, check if user wants to apply to all nodes with the same name
    selection = pm.ls(sl=1)
    check_for_remap = len(preset_dic["namespaces"]) == 1 and len(selection) > 0
    preset_namespace = preset_dic["namespaces"][0]
    selection_namespace = ""

    replace_namespace = False
    # check if selection namespace matches with preset namespace
    if check_for_remap:
        selection_namespace = selection[-1].namespace()
        if selection_namespace != preset_namespace:
            if namespace_cb(preset_namespace, selection_namespace):
                replace_namespace = True
                print(
                    "Processing configs with new namespace {}".format(
                        selection_namespace
                    )
                )

    for key, config in preset_dic["configs"].items():
        node = key
        if replace_namespace:
            if ":" not in node:
                node = selection_namespace + node
            else:
                node = node.replace(preset_namespace, selection_namespace)
        if not pm.objExists(node):
            mgear.log("Node '{}' does not exist, skipping".format(node))
            continue
        result = create_spring(node=node, config=config)
        if result is not False:
            affected_nodes.append(result[1])
    pm.select(cl=True)
    return affected_nodes


def get_preset_targets(preset_file_path, namespace_cb=None):
    with open(preset_file_path, "r") as fp:
        preset_dic = json.load(fp)
        replace_namespace = False
        if namespace_cb:
            # if there's only one namespace, check if user wants to apply to all nodes with the same name
            selection = pm.ls(sl=1)
            check_for_remap = (
                len(preset_dic["namespaces"]) == 1 and len(selection) > 0
            )
            preset_namespace = preset_dic["namespaces"][0]
            selection_namespace = ""

            # check if selection namespace matches with preset namespace
            if check_for_remap:
                selection_namespace = selection[-1].namespace()
                if selection_namespace != preset_namespace:
                    if namespace_cb(preset_namespace, selection_namespace):
                        replace_namespace = True
                        print(
                            "Processing configs with new namespace {}".format(
                                selection_namespace
                            )
                        )
        if replace_namespace:
            nodes = []
            for node in preset_dic["nodes"]:
                if ":" not in node:
                    node = selection_namespace + node
                else:
                    node = node.replace(preset_namespace, selection_namespace)
                if pm.objExists(node):
                    nodes.append(node)

            return nodes
        else:
            return [node for node in preset_dic["nodes"] if pm.objExists(node)]


@one_undo
@viewport_off
def bake(nodes=None):
    """
    Bakes the rotation and translation animation of the specified or selected
    objects within the current time range, filtering nodes based on custom
    spring attributes.

    Args:
        nodes (list): List of nodes to bake. If None, uses the selected nodes.

    Returns:
        bool: True if successful, False otherwise.
    """
    # Get the current time range
    start_time = pm.playbackOptions(query=True, minTime=True)
    end_time = pm.playbackOptions(query=True, maxTime=True)

    pm.currentTime(start_time)

    if not nodes:
        # Get selected objects
        nodes = pm.selected()

    # Check if any objects are selected
    if not nodes:
        print("No objects selected.")
        return False

    # Initialize attributes to bake
    attributes_to_bake = []

    # Filter nodes and determine attributes to bake
    nodes_to_bake = []
    for node in nodes:
        has_spring = (
            node.hasAttr("springTotalIntensity")
            and node.attr("springTotalIntensity").get() > 0
        )

        if has_spring:
            # Check individual spring attributes
            if (
                node.hasAttr("springTranslationalIntensity")
                and node.attr("springTranslationalIntensity").get() > 0
            ):
                if "translateX" not in attributes_to_bake:
                    attributes_to_bake.extend(
                        ["translateX", "translateY", "translateZ"]
                    )

            if (
                node.hasAttr("springRotationalIntensity")
                and node.attr("springRotationalIntensity").get() > 0
            ):
                if "rotateX" not in attributes_to_bake:
                    attributes_to_bake.extend(
                        ["rotateX", "rotateY", "rotateZ"]
                    )

            # # Stop checking if both translation and rotation are already added
            # if {"translateX", "rotateX"}.issubset(attributes_to_bake):
            #     break

            nodes_to_bake.append(node)

    # Perform the bake operation if there are nodes to process
    if not nodes_to_bake:
        print("No nodes meet the criteria for baking.")
        return False

    try:
        pm.bakeResults(
            nodes_to_bake,
            time=(start_time, end_time),
            attribute=attributes_to_bake,
            simulation=True,
            sampleBy=1,
            oversamplingRate=1,
            disableImplicitControl=True,
            preserveOutsideKeys=True,
            sparseAnimCurveBake=False,
            removeBakedAttributeFromLayer=False,
            removeBakedAnimFromLayer=False,
            bakeOnOverrideLayer=False,
            minimizeRotation=True,
            controlPoints=False,
            shape=True,
        )
        delete_spring_setup(nodes_to_bake, transfer_animation=False)
        for node in nodes_to_bake:
            remove_settings_attr(node)
        print("Successfully baked filtered nodes.")
        pm.select(cl=True)
        return True
    except Exception as e:
        print("Failed to bake filtered nodes: {}".format(e))
        pm.select(cl=True)
        return False


@one_undo
def bake_all():
    spring_driven = []
    for sn in pm.ls(type="mgear_springNode"):
        if sn.hasAttr("springSetupDriven"):
            connections = pm.listConnections(
                sn.attr("springSetupDriven"), plugs=True
            )
            if connections:
                spring_driven.append(connections[0].node())
    if spring_driven:
        bake(spring_driven)


@one_undo
def delete_spring_setup(nodes=None, transfer_animation=True):
    """
    Delete the node connected to the 'springSetupMembers' attribute at index 0
    for a given list of nodes.

    Args:
        transfer_animation (bool): transfer back animation
        nodes (list): A list of node names to process.

    Returns:
        None
    """
    if not nodes:
        nodes = pm.ls(sl=1)

    for node in nodes:
        # Check if node exists
        if not pm.objExists(node):
            print("Node {} does not exist.".format(node))
            continue

        # Check if attribute exists
        attr_name = "{}.springSetupMembers[0]".format(node)
        if not pm.attributeQuery("springSetupMembers", node=node, exists=True):
            print(
                "Attribute springSetupMembers does not exist on {}.".format(
                    node
                )
            )
            continue

        # Get connections
        connections = pm.listConnections(attr_name, plugs=True)

        if not connections:
            print("No connections found for attribute {}.".format(attr_name))
            continue

        # Delete connected node
        connected_node = connections[0].node()
        pm.delete(
            pm.parentConstraint(node, query=1)
        )  # deletes constraint to avoid weird offsets
        if transfer_animation:
            move_animation_curves(connected_node, node)

        pm.delete(connected_node)
        print("Deleted node connected to {}.".format(attr_name))

        remove_settings_attr(node)


def get_spring_targets():
    """Get all the spring target controls

    Returns:
        set: spring target controls in the scene
    """
    spring_nodes = pm.ls(type="mgear_springNode")
    nodes = set()
    for spring_node in spring_nodes:
        source = pm.listConnections(spring_node.damping, source=True)[0]
        nodes.add(source)

    return nodes


@one_undo
def delete_all_springs():
    delete_spring_setup(get_spring_targets())


@one_undo
def select_all_springs_targets():
    pm.select(get_spring_targets())


def move_animation_curves(source_node, target_node):
    """
    Move animation curves connected to one node to another node.

    Args:
        source_node (str): The name of the node with the animation curves.
        target_node (str): The name of the node to which animation curves
                           should be moved.

    Returns:
        None
    """

    attributes_to_check = ["translate", "rotate"]

    for attr in attributes_to_check:
        for axis in ["X", "Y", "Z"]:
            compound_attr = "{}{}".format(attr, axis)
            source_plug = "{}.{}".format(source_node, compound_attr)
            target_plug = "{}.{}".format(target_node, compound_attr)

            # Check if the attribute exists and is animated
            if pm.attributeQuery(compound_attr, node=source_node, exists=True):
                anim_curves = pm.listConnections(source_plug)
                anim_curves = pm.listConnections(source_plug, p=True, d=False)
                for curve in anim_curves:
                    # Disconnect curve from source node and connect to target node
                    pm.disconnectAttr(curve, source_plug)
                    pm.connectAttr(curve, target_plug)

        compound_attr = (
            attr  # for compound plugs like 'translate', 'rotate', 'scale'
        )
        source_plug = "{}.{}".format(source_node, compound_attr)
        target_plug = "{}.{}".format(target_node, compound_attr)

        # Check if the attribute exists and is animated
        if pm.attributeQuery(compound_attr, node=source_node, exists=True):
            anim_curves = pm.listConnections(source_plug, p=True, d=False)
            for curve in anim_curves:
                # Disconnect curve from source node and connect to target node
                pm.disconnectAttr(curve, source_plug)
                pm.connectAttr(curve, target_plug)
