
""" flex.update

flex.update module handles the updating rig process

:module: flex.update
"""

# imports
from __future__ import absolute_import

from maya import cmds

from mgear.flex import logger
from mgear.flex.attributes import BLENDSHAPE_TARGET
from mgear.flex.attributes import COMPONENT_DISPLAY_ATTRIBUTES
from mgear.flex.attributes import OBJECT_DISPLAY_ATTRIBUTES
from mgear.flex.attributes import RENDER_STATS_ATTRIBUTES
from mgear.flex.decorators import timer
from mgear.flex.query import get_deformers
from mgear.flex.query import get_matching_shapes_from_group
from mgear.flex.query import get_missing_shapes_from_group
from mgear.flex.query import get_parent
from mgear.flex.query import get_shape_orig
from mgear.flex.query import is_lock_attribute
from mgear.flex.query import is_matching_bouding_box
from mgear.flex.query import is_matching_count
from mgear.flex.query import is_matching_type
from mgear.flex.query import lock_unlock_attribute
from mgear.flex.update_utils import add_attribute
from mgear.flex.update_utils import copy_cluster_weights
from mgear.flex.update_utils import copy_map1_name
from mgear.flex.update_utils import copy_skin_weights
from mgear.flex.update_utils import create_deformers_backups
from mgear.flex.update_utils import delete_transform_from_nodes
from mgear.flex.update_utils import set_deformer_state
from mgear.flex.update_utils import update_shape
import mgear.pymaya as pm


def update_attribute(source, target, attribute_name):
    """ Updates the given attribute value

    ..note:: This in a generic method to **setAttr** all type of attributes
             inside Maya. Using the getSetAttrCmds from the MPLug class allows
             avoiding to create one method for each type of attribute inside
             Maya as the setAttr command will differ depending on the
             attribute type and data.

    This method is faster than using PyMel attribute set property.

    :param source: the maya source node
    :type source: str

    :param target: the maya target node
    :type target: str

    :param attribute_name: the attribute name to set in the given target
    :type attribute_name: str
    """

    if not cmds.objExists("{}.{}".format(target, attribute_name)):
        logger.warning("The current target {} does not have attribute: {}"
                       .format(target, attribute_name))
        return

    # checks for locking
    lock = is_lock_attribute(target, attribute_name)

    if not lock_unlock_attribute(target, attribute_name, False):
        logger.warning("The given attribute {} can't be updated on {}"
                       .format(attribute_name, target))
        return

    # creates pymel nodes to get and apply attributes from
    # I am using pymel as they managed to handle default attributes on
    # referenced nodes correctly. When using MPlug.getSetAttrCmd with kAll
    # this doesn't return the command correctly when nodes in reference have
    # the attribute left as default
    py_source = pm.PyNode(source)
    py_target = pm.PyNode(target)

    # sets the attribute value
    try:
        attr_value = py_source.attr(attribute_name).get()
        py_target.attr(attribute_name).set(attr_value)

    except Exception as e:
        logger.warning("The given attribute ({}) can't be updated on {}"
                       .format(attribute_name, target))
        return e

    if lock:
        lock_unlock_attribute(target, attribute_name, True)


def update_blendshapes_nodes(source_nodes, target_nodes):
    """ Update all target shapes with the given source shapes

    :param source_nodes: source blendshape nodes
    :type source_nodes: list(str)

    :param target_nodes: target blendshape nodes
    :type target_nodes: list(str)
    """

    if not source_nodes and not target_nodes:
        return

    if not source_nodes and target_nodes:
        logger.error('No backup blendshapes found for {}'.format(target_nodes))
        return

    for node in target_nodes:
        # finds matching node name on the source nodes
        match_node = [x for x in source_nodes if node in x] or None

        if not match_node:
            continue

        # gets source and targets indices
        targets_idx = cmds.getAttr("{}.weight".format(node), multiIndices=True)
        source_idx = cmds.getAttr("{}.weight".format(match_node[0]),
                                  multiIndices=True)

        for idx in targets_idx:
            # blendshape target name
            target_name = cmds.aliasAttr("{}.weight[{}]".format(node, idx),
                                         query=True)

            # gets corresponding source idx
            match_idx = [x for x in source_idx if cmds.aliasAttr(
                "{}.weight[{}]".format(match_node[0], x),
                query=True) == target_name]

            if not match_idx:
                continue

            # input target group attribute
            source_name = (BLENDSHAPE_TARGET.format(match_node[0],
                                                    match_idx[0]))
            target_name = (BLENDSHAPE_TARGET.format(node, idx))

            # loop on actual targets and in-between targets
            for target in cmds.getAttr(target_name, multiIndices=True):
                # target attribute name
                source_attr = "{}[{}]".format(source_name, target)
                target_attr = "{}[{}]".format(target_name, target)

                cmds.connectAttr(source_attr, target_attr, force=True)
                cmds.disconnectAttr(source_attr, target_attr)


def update_clusters_nodes(shape, weight_files):
    """ Updates the given shape cluster weights using the given files

    :param shape: the shape node name containing the cluster deformers
    :type shape: str

    :param weight_files: weight files names for each cluster deformer
    :type weight_files: list(str)
    """

    if not shape and not weight_files:
        return

    if shape and not weight_files:
        return

    logger.info("Copying cluster weights on {}".format(shape))

    # update cluster weights
    copy_cluster_weights(shape, weight_files)


@timer
def update_deformed_mismatching_shape(source, target, shape_orig):
    """ Updates the target shape with the given source shape content

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str

    :param shape_orig: shape orig on the target shape
    :type shape_orig: str
    """

    logger.debug("Running update deformed mismatched shapes")

    # gets all deformers on the target shape (supported by flex)
    deformers = get_deformers(target)

    if len(deformers["skinCluster"]) > 1:
        logger.warning("Dual skinning is yet not supported. {} will be used"
                       .format(deformers["skinCluster"][0]))

    # Turns all deformers envelope off
    set_deformer_state(deformers, False)

    # creates deformers backups
    bs_nodes, skin_nodes, cluster_nodes = create_deformers_backups(source,
                                                                   target,
                                                                   shape_orig,
                                                                   deformers)
    # updates target shape
    update_shape(source, shape_orig)

    # updates skinning nodes
    update_skincluster_node(skin_nodes, deformers["skinCluster"])

    # updates blendshapes nodes
    update_blendshapes_nodes(bs_nodes, deformers["blendShape"])

    # update cluster nodes
    update_clusters_nodes(target, cluster_nodes)

    # updates uv sets on target shape
    update_uvs_sets(target)

    # Turns all deformers envelope ON
    set_deformer_state(deformers, True)

    # deletes backups
    delete_transform_from_nodes(set(bs_nodes).union(skin_nodes))


def update_deformed_shape(source, target, mismatching_topology=True):
    """ Updates the target shape with the given source shape content

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str

    :param mismatching_topology: ignore or not mismatching topologies
    :type mismatching_topology: bool
    """

    # gets orig shape
    deform_origin = get_shape_orig(target)

    # returns as target is not a deformed shape
    if not deform_origin:
        return

    logger.debug("Deformed shape found: {}".format(target))

    # returns if source and target shapes don't match
    if not is_matching_type(source, target):
        logger.warning("{} and {} don't have same shape type. passing..."
                       .format(source, target))
        return

    # returns if vertices count isn't equal and mismatching isn't requested
    if not mismatching_topology and not is_matching_count(source, target):
        logger.warning("{} and {} don't have same shape vertices count."
                       "passing...".format(source, target))
        return

    deform_origin = deform_origin[0]

    # updates map1 name
    copy_map1_name(source, deform_origin)

    # updates on mismatching topology
    if mismatching_topology and not is_matching_count(source, target):
        update_deformed_mismatching_shape(source, target, deform_origin)
        return

    # update the shape
    update_shape(source, deform_origin)

    # update uvs set on target
    update_uvs_sets(target)


def update_maya_attributes(source, target, attributes):
    """ Updates all maya attributes from the given source to the target

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str

    :param attributes: list of Maya attributes to be updated
    :type attributes: list
    """

    for attribute in attributes:
        update_attribute(source, target, attribute)


def update_plugin_attributes(source, target):
    """ Updates all maya plugin defined attributes

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str
    """

    source_attrs = cmds.listAttr(source, fromPlugin=True) or []
    taget_attrs = cmds.listAttr(target, fromPlugin=True) or []

    logger.debug("Updating  plugin attributes on {}".format(target))
    for attribute in source_attrs:
        if attribute in taget_attrs:
            update_attribute(source, target, attribute)


@timer
def update_rig(source, target, options):
    """ Updates all shapes from the given source group to the target group

    :param source: maya transform node
    :type source: str

    :param target: maya transform node
    :type target: str

    :param options: update options
    :type options: dict
    """

    # gets the matching shapes
    matching_shapes = get_matching_shapes_from_group(source, target)

    logger.info("-" * 90)
    logger.info("Matching shapes: {}" .format(matching_shapes))
    logger.info("-" * 90)

    for shape in matching_shapes:
        logger.debug("-" * 90)
        logger.debug("Updating: {}".format(matching_shapes[shape]))

        if options["deformed"]:
            update_deformed_shape(shape, matching_shapes[shape],
                                  options["mismatched_topologies"])

        if options["transformed"]:
            update_transformed_shape(shape, matching_shapes[shape],
                                     options["hold_transform_values"])

        if options["user_attributes"]:
            update_user_attributes(shape, matching_shapes[shape])

        if options["object_display"]:
            logger.debug("Updating object display attributes on {}"
                         .format(matching_shapes[shape]))
            update_maya_attributes(shape, matching_shapes[shape],
                                   OBJECT_DISPLAY_ATTRIBUTES)

        if options["component_display"]:
            logger.debug("Updating component display attributes on {}"
                         .format(matching_shapes[shape]))
            update_maya_attributes(shape, matching_shapes[shape],
                                   COMPONENT_DISPLAY_ATTRIBUTES)

        if options["render_attributes"]:
            logger.debug("Updating render attributes on {}"
                         .format(matching_shapes[shape]))
            update_maya_attributes(shape, matching_shapes[shape],
                                   RENDER_STATS_ATTRIBUTES)

        if options["plugin_attributes"]:
            update_plugin_attributes(shape, matching_shapes[shape])

    logger.info("-" * 90)
    logger.info("Source missing shapes: {}" .format(
        get_missing_shapes_from_group(source, target)))
    logger.info("Target missing shapes: {}" .format(
        get_missing_shapes_from_group(target, source)))
    logger.info("-" * 90)


def update_skincluster_node(source_skin, target_skin):
    """ Updates the skin weights on the given target skin from the source skin

    :param source_skin: the source skin cluster node name
    :type source_skin: str

    :param target_skin: the target skin cluster node name
    :type target_skin: str
    """

    if not source_skin and not target_skin:
        return

    if not source_skin and target_skin:
        logger.error('No backup skinning found for {}'.format(target_skin))
        return

    logger.info("Copying skinning from {} to {}".format(source_skin[0],
                                                        target_skin))

    # copy skin weights
    copy_skin_weights(source_skin[0], target_skin[0])


def update_transform(source, target):
    """ Updates the transform node on target

    This method creates a duplicate of the transform node on source and
    uses is as the new parent transform for the target shape

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str
    """

    logger.debug("Updating transform node on {} from {}".format(target,
                                                                source))

    # create duplicate of the source transform
    holder = cmds.duplicate(source, parentOnly=True,
                            name="mgear_flex_holder")[0]

    # adds the target shape duplicate into the holder transform node
    cmds.parent(target, holder, add=True, shape=True)

    # unlock locked attributes on holder transform node
    for attr in cmds.listAttr(holder, locked=True) or []:
        cmds.setAttr("{}.{}".format(holder, attr), lock=False)

    # updates the shape
    update_shape(source, target)

    # parents new shape under the correct place
    target_parent = get_parent(target)[0]
    target_parent_parent = get_parent(target_parent)[0]
    cmds.parent(holder, target_parent_parent)
    cmds.delete(target_parent)
    cmds.rename(holder, "{}".format(target_parent.split("|")[-1].split(":")
                                    [-1]))


def update_transformed_shape(source, target, hold_transform):
    """ Updates the target shape with the given source shape content

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str

    :param hold_transform: keeps the transform node position values
    :type hold_transform: bool
    """

    deform_origin = get_shape_orig(target)

    if deform_origin:
        return

    logger.debug("Transformed shape found: {}".format(target))

    # maintain transform on target
    if hold_transform:
        update_shape(source, target)

    # update target transform
    else:
        update_transform(source, target)


def update_user_attributes(source, target):
    """ Updates the target shape attributes with the given source shape content

    :param source: maya shape node
    :type source: str

    :param target: maya shape node
    :type target: str

    .. note:: This method loops twice on the use attributes. One time to add
              the missing attributes and the second to set their value. This
              allows avoiding issues when dealing with child attributes.
    """

    # get user defined attributes
    user_attributes = cmds.listAttr(source, userDefined=True)

    if not user_attributes:
        return

    logger.debug("Updating user attributes on {}".format(target))

    # loop on user defined attributes if any to ---> addAttr
    for attr in user_attributes:
        # adds attribute on shape
        add_attribute(source, target, attr)

    # loop on user defined attributes if any to ---> setAttr
    for attr in user_attributes:
        # updates the attribute values
        update_attribute(source, target, attr)


def update_uvs_sets(shape):
    """ Forces a given mesh shape uvs to update
    """

    if cmds.objectType(shape) != "mesh":
        return

    # forces uv refresh
    cmds.setAttr("{}.outForceNodeUVUpdate ".format(shape), True)
