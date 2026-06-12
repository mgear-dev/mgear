import maya.cmds as cmds
import mgear.pymaya as pm

from mgear.core import attribute


ATTR_SLIDER_TYPES = ["long", "float", "double", "doubleLinear", "doubleAngle"]
DEFAULT_RANGE = 1000


# TODO: filter channel by color. By right click menu in a channel with color


def init_table_config_data():
    """Initialize the dictionary to store the channel master table data

    Items are the channels or attributes fullname in a list
    items_data is a dictionary with each channel configuration, the keys is the
    fullName

    Returns:
        dict: configuration dictionary
    """
    config_data = {}
    config_data["channels"] = []
    config_data["channels_data"] = {}

    return config_data


def init_channel_master_config_data():
    """Initialize the dictionary to store channel master tabs configuration"""
    config_data = {}
    config_data["tabs"] = []
    config_data["tabs_data"] = {}
    config_data["current_tab"] = 0

    return config_data


def get_keyable_attribute(node):
    """Get keyable attributes from node

    Args:
        node (str): name of the node that have the attribute

    Returns:
        list: list of keyable attributes
    """
    if cmds.nodeType(node) == "blendShape":
        attrs = cmds.listAttr("{}.w".format(node), m=True)
    else:
        attrs = cmds.listAttr(node, ud=False, k=True)

    return attrs


def get_single_attribute_config(node, attr):
    """Summary

    Args:
        node (str): name of the node that have the attribute
        attr (str): attribute name

    Returns:
        dict: attribute configuration
    """
    config = {}
    # config["ctl"] = node
    # config["ctl"] = pm.NameParser(node).stripNamespace().__str__()
    config["ctl"] = node
    config["color"] = None  # This is a place holder for the channel UI color
    try:
        config["type"] = cmds.attributeQuery(attr, node=node, attributeType=True)
    except:
        return

    # check it the attr is alias
    alias = cmds.aliasAttr(node, q=True)
    if alias and attr in alias:
        config["niceName"] = attr
        config["longName"] = attr
    else:
        config["niceName"] = cmds.attributeQuery(
            attr, node=node, niceName=True
        )
        config["longName"] = cmds.attributeQuery(
            attr, node=node, longName=True
        )

    config["fullName"] = config["ctl"] + "." + config["longName"]
    if config["type"] in ATTR_SLIDER_TYPES:
        if cmds.attributeQuery(attr, node=node, maxExists=True):
            config["max"] = cmds.attributeQuery(attr, node=node, max=True)[0]
        else:
            config["max"] = DEFAULT_RANGE
        if cmds.attributeQuery(attr, node=node, minExists=True):
            config["min"] = cmds.attributeQuery(attr, node=node, min=True)[0]
        else:
            config["min"] = DEFAULT_RANGE * -1
        config["default"] = cmds.attributeQuery(
            attr, node=node, listDefault=True
        )[0]
    elif config["type"] in ["enum"]:
        items = cmds.attributeQuery(attr, node=node, listEnum=True)[0]

        config["items"] = [x for x in items.split(":")]

    # Get value at channel creation time
    # this value can be different from the default value
    config["creationValue"] = cmds.getAttr("{}.{}".format(node, attr))

    return config


def get_attributes_config(node):
    """Get the configuration to all the keyable attributes

    Args:
        node (str): name of the node that have the attribute

    Returns:
        dict: All keyable attributes configuration
    """
    # attrs_config = {}
    keyable_attrs = get_keyable_attribute(node)
    config_data = init_table_config_data()
    if keyable_attrs:
        # attrs_config["_attrs"] = keyable_attrs
        for attr in keyable_attrs:
            config = get_single_attribute_config(node, attr)
            # attrs_config[attr] = config
            if config:
                config_data["channels"].append(config["fullName"])
                config_data["channels_data"][config["fullName"]] = config

    return config_data


def get_table_config_from_selection():
    oSel = pm.selected()
    attrs_config = None
    namespace = None
    if oSel:
        namespace = oSel[-1].namespace()
        ctl = oSel[-1].name()
        attrs_config = get_attributes_config(ctl)
    return attrs_config, namespace


def get_ctl_with_namespace(attr_config, namespace=None):

    if namespace:
        ctl = (
            namespace
            + pm.NameParser(attr_config["ctl"]).stripNamespace().__str__()
        )
    else:
        ctl = attr_config["ctl"]

    return ctl


def reset_attribute(attr_config, namespace=None):
    """Reset the value of a given attribute for the attribute configuration

    Args:
        attr_config (dict): Attribute configuration
    """
    ctl = get_ctl_with_namespace(attr_config, namespace=namespace)
    obj = pm.PyNode(ctl)
    attr = attr_config["longName"]

    attribute.reset_selected_channels_value(objects=[obj], attributes=[attr])


def reset_creation_value_attribute(attr_config, namespace=None):
    """Reset the value of a given attribute for the attribute configuration

    Args:
        attr_config (dict): Attribute configuration
    """
    ctl = get_ctl_with_namespace(attr_config, namespace=namespace)
    attr = attr_config["longName"]
    fullname_attr = "{}.{}".format(ctl, attr)
    if "creationValue" in attr_config.keys():
        val = attr_config["creationValue"]
        cmds.setAttr(fullname_attr, val)
    else:
        pm.displayWarning(
            "Initial Creation Value was not originally stored for {}".format(
                fullname_attr
            )
        )


def sync_graph_editor(attr_configs, namespace=None):
    """sync the channels in the graph editor

    Args:
        attr_configs (list): list of attribute configuration
    """
    # select channel host controls
    ctls = []
    for ac in attr_configs:
        ctl = ac["ctl"]
        if ctl not in ctls:
            if namespace:
                ctl = namespace + pm.NameParser(ctl).stripNamespace().__str__()
            ctls.append(ctl)

    pm.select(ctls, r=True)

    # filter curves in graph editor\
    cnxs = []
    for ac in attr_configs:
        attr = ac["fullName"]
        if namespace:
            attr = namespace + pm.NameParser(attr).stripNamespace().__str__()
        cnxs.append(attr)

    def ge_update():
        pm.selectionConnection("graphEditor1FromOutliner", e=True, clear=True)
        for c in cnxs:
            cmds.selectionConnection(
                "graphEditor1FromOutliner", e=True, select=c
            )

    # we need to evalDeferred to allow grapheditor update the selection
    # highlight in grapheditor outliner
    pm.evalDeferred(ge_update)


################
# Keyframe utils
################


def current_frame_has_key(attr):
    """Check if the attribute has keyframe in the current frame

    Args:
        attr (str): Attribute fullName

    Returns:
        bool: Return true if the attribute has keyframe in the current frame
    """
    k = pm.keyframe(attr, query=True, time=pm.currentTime())
    if k:
        return True


def channel_has_animation(attr):
    """Check if the current channel has animaton

    Args:
        attr (str): Attribute fullName

    Returns:
         bool: Return true if the attribute has animation
    """
    k = cmds.keyframe(attr, query=True)
    if k:
        return True


def get_anim_value_at_current_frame(attr):
    """Get the animation value in the current framwe from a given attribute

    Args:
        attr (str): Attribute fullName

    Returns:
        bol, int or float: animation current value
    """
    val = cmds.keyframe(attr, query=True, eval=True)
    if val:
        return val[0]


def set_key(attr):
    """Keyframes the attribute at current frame

    Args:
        attr (str): Attribute fullName
    """
    cmds.setKeyframe(attr)


def remove_key(attr):
    """Remove the keyframe of an attribute at current frame

    Args:
        attr (str): Attribute fullName
    """
    pm.cutKey(attr, clear=True, time=pm.currentTime())


def remove_animation(attr):
    """Remove the animation of an attribute

    Args:
        attr (str): Attribute fullName
    """
    pm.cutKey(attr, clear=True)


def _go_to_keyframe(attr, which):
    frame = cmds.findKeyframe(attr, which=which)
    cmds.currentTime(frame, e=True)


def next_keyframe(attr):
    _go_to_keyframe(attr, which="next")


def previous_keyframe(attr):
    _go_to_keyframe(attr, which="previous")


def value_equal_keyvalue(attr, current_time=False):
    """Compare the animation value and the current value of a given attribute

    Args:
        attr (str): the attribute fullName

    Returns:
        bool: Return true is current value and animation value are the same
    """
    anim_val = get_anim_value_at_current_frame(attr)
    if current_time:
        val = cmds.getAttr(attr, time=current_time)
    else:
        val = cmds.getAttr(attr)
    if anim_val == val:
        return True
