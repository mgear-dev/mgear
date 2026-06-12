#!/usr/bin/env python
"""
Module for automatically fitting (mgear)guides to a bipedial mesh.

Attributes:
    DEFAULT_BIPED_FEET (list): based on template, default feet nodes
    DEFAULT_BIPED_POINTS (list): Nodes created from embedSkeleton command
    DEFAULT_BIPED_POINTS_SET (set): set version to allow for quick intersection
    DEFAULT_EMBED_GUIDE_ASSOCIATION (dict): based off template
    default interactive association from guide to embed points
    GUIDE_ROOT_NAME (str): default name of the guide root node
    IGNORE_GUIDE_NODES (list): nodes to ignore placement adjustments
    SETUP_GEO_SHAPE_NAME (str): default arbitrary single mensh name
    SIDE_MIRROR_INFO (dict): convenience dict for getting other side of given

Example:
from mgear.shifter import afg_tools, afg_tools_ui

min_height_nodes = ['foot_L0_heel',
 'foot_L0_inpivot',
 'foot_L0_outpivot',
 'foot_R0_heel',
 'foot_R0_inpivot',
 'foot_R0_outpivot']

setup_shape = 'skin_geo_setupShape'

embed_info = afg_tools.getEmbedInfoFromShape(setup_shape)
afg_tools.createNodeFromEmbedInfo(embed_info)
afg_tools.smartAdjustEmbedOutput(embed_info, favor_side='left')
mesh_info = afg_tools.getEmbedMeshInfoFromShape(setup_shape)
afg_tools.createMeshFromDescription(mesh_info)
afg_tools.matchGuidesToEmbedOutput(setup_geo=setup_shape,
                                   min_height_nodes=min_height_nodes)
"""

# Future
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

# standard
import json
import copy

# dcc
import maya.OpenMaya as OpenMaya
from maya import cmds
import mgear.pymaya as pm
import mgear.pymaya.datatypes as dt

# mgear
from mgear.shifter import io
from mgear.core import utils
from mgear.core import vector
from mgear.core import transform
from mgear.core import string as m_string


# constants -------------------------------------------------------------------
GUIDE_ROOT_NAME = "guide"
SETUP_GEO_SHAPE_NAME = "setup_C0_geoShape"

SIDE_MIRROR_INFO = {"left": "right", "right": "left"}

IGNORE_GUIDE_NODES = ["global_C0_root", "local_C0_root"]

# This order is very important
DEFAULT_BIPED_POINTS = ["hips",
                        "back",
                        "shoulders",
                        "head",
                        "left_thigh",
                        "left_knee",
                        "left_ankle",
                        "left_foot",
                        "left_shoulder",
                        "left_elbow",
                        "left_hand",
                        "right_thigh",
                        "right_knee",
                        "right_ankle",
                        "right_foot",
                        "right_shoulder",
                        "right_elbow",
                        "right_hand"]

DEFAULT_BIPED_POINTS_SET = set(DEFAULT_BIPED_POINTS)

# Default association based off the biped template
DEFAULT_EMBED_GUIDE_ASSOCIATION = {"back": ["spine_C0_eff"],
                                   "head": ["neck_C0_head"],
                                   "hips": ["body_C0_root"],
                                   "left_ankle": ["leg_L0_ankle"],
                                   "left_elbow": ["arm_L0_elbow"],
                                   "left_foot": ["foot_L0_0_loc"],
                                   "left_hand": ["arm_L0_wrist"],
                                   "left_knee": ["leg_L0_knee"],
                                   "left_shoulder": ["shoulder_L0_tip",
                                                     "arm_L0_root"],
                                   "left_thigh": ["leg_L0_root"],
                                   "right_ankle": ["leg_R0_ankle"],
                                   "right_elbow": ["arm_R0_elbow"],
                                   "right_foot": ["foot_R0_0_loc"],
                                   "right_hand": ["arm_R0_wrist"],
                                   "right_knee": ["leg_R0_knee"],
                                   "right_shoulder": ["shoulder_R0_tip",
                                                      "arm_R0_root"],
                                   "right_thigh": ["leg_R0_root"],
                                   "shoulders": ["shoulder_R0_root",
                                                 "shoulder_L0_root"]}

DEFAULT_BIPED_FEET = ["foot_L0_heel",
                      "foot_L0_inpivot",
                      "foot_L0_outpivot",
                      "foot_R0_heel",
                      "foot_R0_inpivot",
                      "foot_R0_outpivot"]

# This allows user interaction to survive reloading
try:
    INTERACTIVE_ASSOCIATION_INFO
    REVERSE_INTERACTIVE_ASSOCIATION_INFO
except NameError:
    INTERACTIVE_ASSOCIATION_INFO = {}
    REVERSE_INTERACTIVE_ASSOCIATION_INFO = {}


def clearUserAssociations():
    """clear user intateravtive association
    """
    global INTERACTIVE_ASSOCIATION_INFO
    global REVERSE_INTERACTIVE_ASSOCIATION_INFO
    INTERACTIVE_ASSOCIATION_INFO = {}
    REVERSE_INTERACTIVE_ASSOCIATION_INFO = {}

# =============================================================================
# file i/o
# =============================================================================


def _importData(filePath):
    """Import json data

    Args:
        filePath (str): file path

    Returns:
        dict: json contents
    """
    try:
        with open(filePath, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)


def _exportData(data, filePath):
    """Save out data from dict to a json file

    Args:
        data (dict): data you wish stored
        filePath (str): Have it your way, burgerking.
    """
    try:
        with open(filePath, "w") as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)

# Utils ----------------------------------------------------------------------


def dot(x, y):
    """Dot product as sum of list comprehensiondoing
    element-wise multiplication
    """
    return sum(x_i * y_i for x_i, y_i in zip(x, y))


def constrainPointToVectorPlanar(point_a,
                                 point_b,
                                 driven_point,
                                 pcp=False,
                                 ws=True):
    """constrain a driven_point to the vector between two points

    Args:
        point_a (vector): point in space
        point_b (vector): point in space
        driven_point (str): target node to be constrained
        pcp (bool, optional): preserve child position
        ws (bool, optional): worldspace
    """
    point_a = pm.PyNode(point_a)
    point_b = pm.PyNode(point_b)
    drivent_point = pm.PyNode(driven_point)
    v = vector.linearlyInterpolate(point_a.getMatrix(ws=ws).translate,
                                   point_b.getMatrix(ws=ws).translate)
    v.normalize()

    p1 = v * dot(drivent_point.getMatrix(ws=ws).translate, v)
    # p1.normalize()
    if pcp:
        cmds.move(p1[0],
                  p1[1],
                  p1[2],
                  drivent_point.name(),
                  os=not ws,
                  pcp=True)
    else:
        drivent_point.setTranslation(p1, ws=True)


def lookAt(driven, driver, up=[0, 1, 0]):
    """aim constaint using math/python

    Args:
        driven (str): name of node to be constrained
        driver (str): name of node to look at
        up (list, optional): up vector

    Returns:
        list: rotations
    """
    # http://www.soup-dev.com/forum.html?p=post%2Faim-constraint-math-7885117
    # check if the "driven" object has parent
    try:
        parent = cmds.listRelatives(driven, pa=True, p=True)[0]
    except Exception:
        parent = None

    driven = cmds.getAttr("{}.worldMatrix".format(driven))
    driver = cmds.getAttr("{}.worldMatrix".format(driver))

    # build transformation matrix
    x = OpenMaya.MVector(driver[12] - driven[12],
                         driver[13] - driven[13],
                         driver[14] - driven[14])
    x.normalize()
    z = x ^ OpenMaya.MVector(-up[0], -up[1], -up[2])
    z.normalize()
    y = x ^ z
    y.normalize()
    m = OpenMaya.MMatrix()
    par_mat = [x.x, x.y, x.z, 0, y.x, y.y,
               y.z, 0, z.x, z.y, z.z, 0, 0, 0, 0, 1]
    OpenMaya.MScriptUtil.createMatrixFromList(par_mat, m)

    if parent:
       # transform the matrix in the local space of the parent object
        m2 = OpenMaya.MMatrix()
        par_mat = cmds.getAttr("{}.worldMatrix".format(parent))
        OpenMaya.MScriptUtil.createMatrixFromList(par_mat, m2)
        m *= m2.inverse()
    # retrieve the desired rotation for "driven" to aim at "driver", in degrees
    rot = OpenMaya.MTransformationMatrix(m).eulerRotation() * 57.2958

    return rot[0], rot[1], rot[2]


def orientAt(driven, driver, pcp=True, up=[0, 1, 0]):
    """convenience function to rotate the driven node at the driver

    Args:
        driven (str): name of driven
        driver (str): name of driver
        pcp (bool, optional): preserve child position
        up (list, optional): upvector
    """
    rot = lookAt(driven, driver, up=up)
    cmds.rotate(rot[0], rot[1], rot[2], driven, os=False, pcp=True)


def to_json(string_data):
    """convenience function to get the embed data from string format to dict

    Args:
        string_data (str): embedSkeleton return a long str

    Returns:
        dict: json data
    """
    return json.loads(string_data)


def createMeshFromDescription(mesh_info):
    """Create a mesh from the data generated by embedSkeleton

    Args:
        mesh_info (dict): information from embe skeleton

    Returns:
        str: name of the created shape
    """
    meshPoints = mesh_info["points"]
    meshFaces = mesh_info["faces"]
    factor = 1.0 / mesh_info["conversionFactor"]
    # Vertices
    vertexArray = OpenMaya.MFloatPointArray()
    for i in range(0, len(meshPoints), 3):
        vertex = OpenMaya.MFloatPoint(meshPoints[i] * factor,
                                      meshPoints[i + 1] * factor,
                                      meshPoints[i + 2] * factor)
        vertexArray.append(vertex)
    numVertices = vertexArray.length()
    # Faces
    polygonCounts = OpenMaya.MIntArray()
    polygonConnects = OpenMaya.MIntArray()
    for face in meshFaces:
        for i in face:
            polygonConnects.append(i)
        polygonCounts.append(len(face))
    numPolygons = polygonCounts.length()
    fnMesh = OpenMaya.MFnMesh()
    newMesh = fnMesh.create(numVertices,
                            numPolygons,
                            vertexArray,
                            polygonCounts,
                            polygonConnects)
    fnMesh.updateSurface()
    # Assign new mesh to default shading group
    nodeName = fnMesh.name()
    cmds.sets(nodeName, e=True, fe="initialShadingGroup")
    return nodeName


def createNodeFromEmbedInfo(embed_info, node_type=None):
    """create or update position of an embed node

    Args:
        embed_info (dict): point position in space
        node_type (str, optional): if none, default to joint. maya data type

    Returns:
        list: of created nodes
    """
    if not node_type:
        node_type = "joint"
    created_nodes = []
    for name, position in embed_info["joints"].items():
        if not cmds.objExists(name):
            name = cmds.createNode(node_type, name=name)
        cmds.xform(name, worldSpace=True, translation=position)
        created_nodes.append(name)
    for point in DEFAULT_BIPED_POINTS:
        cmds.reorder(point, back=True)
    return created_nodes


def resetNodesToEmbedInfo(nodes, embed_info):
    """move existing nodes to the position of the embed info

    Args:
        nodes (list): of nodes to move back to original position
        embed_info (dict): source info

    Returns:
        list: of skipped nodes
    """
    skipped = []
    for name in nodes:
        position = embed_info["joints"].get(name)
        if position:
            cmds.xform(name, worldSpace=True, translation=position)
        else:
            skipped.append(name)
    return skipped


def getEmbedMeshInfoFromShape(shape_name):
    """Get the embedSkeleton merged mesh information in json/dict format

    Args:
        shape_name (str): name of the shape, not transform

    Returns:
        dict: mesh information
    """
    # First select the shape, not the transform.
    cmds.select(cl=True)
    cmds.select(shape_name, r=True)
    cmds.skeletonEmbed()
    # For debugging: get the merged mesh that will be used
    merged_mesh_info = cmds.skeletonEmbed(query=True, mergedMesh=True)
    return to_json(merged_mesh_info)


def getEmbedInfoFromShape(shape_name,
                          segmentationMethod=3,
                          segmentationResolution=128):
    """get the embed point position information from the shape

    Args:
        shape_name (str): name of the shape, not the transform
        segmentationMethod (int, optional): 0-3 types of information gathering
        segmentationResolution (int, optional): resolution, in voxels

    Returns:
        dict: information of embed points
    """
    # First select the shape, not the transform.
    cmds.select(cl=True)
    cmds.select(shape_name, r=True)
    cmds.skeletonEmbed()
    # Embed skeleton using polygon soup and 512 resolution.
    cmds.skeletonEmbed(segmentationMethod=segmentationMethod,
                       segmentationResolution=segmentationResolution)
    # This method creates a few joints to see the embedding.
    embed_info = cmds.skeletonEmbed()
    return to_json(embed_info)


def scaleNodeAToNodeB(nodeA, nodeB, manual_scale=False):
    """Scale node A to match the approximate size of node B. Will skip if the
    nodes are within a range of similarity

    Args:
        nodeA (str): node to scale
        nodeB (str): node to match
        manual_scale (int, optional): override scale with provided int

    Returns:
        float: the amount scaled by
    """
    cmds.showHidden([nodeA, nodeB], a=True)
    cmds.setAttr("{}.v".format(nodeA), 1)
    guide_min = cmds.getAttr("{}.boundingBoxMin".format(nodeA))[0]
    guide_max = cmds.getAttr("{}.boundingBoxMax".format(nodeA))[0]
    # guide_length = math.sqrt(math.pow(guide_min[1] - guide_max[1], 2))
    guide_length = (dt.Vector(guide_min[1]) - dt.Vector(guide_max[1])).length()

    cmds.setAttr("{}.v".format(nodeB), 1)
    mesh_min = cmds.getAttr("{}.boundingBoxMin".format(nodeB))[0]
    mesh_max = cmds.getAttr("{}.boundingBoxMax".format(nodeB))[0]
    # mesh_length = math.sqrt(math.pow(mesh_min[1] - mesh_max[1], 2))
    mesh_length = (dt.Vector(mesh_min[1]) - dt.Vector(mesh_max[1])).length()

    scale_factor = mesh_length / guide_length
    if manual_scale:
        scale_factor = manual_scale
    if .5 <= scale_factor <= 2:
        print("Skipping scale...")
        return
    cmds.setAttr("{}.sx".format(nodeA), scale_factor)
    cmds.setAttr("{}.sy".format(nodeA), scale_factor)
    cmds.setAttr("{}.sz".format(nodeA), scale_factor)

    return scale_factor


def interactiveAssociationMatch(*args):
    """convenience function for callbacks

    Args:
        *args: catch all for difference types of callbacks
    """
    interactiveAssociation(matchTransform=True, *args)


def interactiveAssociation(matchTransform=False, *args):
    """to be used with callbacks for recording user associations with
    joints and guides

    Args:
        matchTransform (bool, optional): should the guide match embed position
        *args: catch all for difference callbacks

    Returns:
        n/a: return if criteria not met
    """
    selection = cmds.ls(sl=True, type=["transform"])
    if len(selection) > 1:
        sel_set = set(selection)
        guide = sel_set - DEFAULT_BIPED_POINTS_SET
        default_point = sel_set.intersection(DEFAULT_BIPED_POINTS_SET)
        if not guide or not default_point:
            return
        guide = list(guide)
        default_point = list(default_point)[0]
        INTERACTIVE_ASSOCIATION_INFO[default_point] = guide
        if matchTransform:
            [cmds.matchTransform(x, default_point, pos=True) for x in guide]
        cmds.select(cl=True)


def mirrorInteractiveAssociation():
    """mirror the left side of the interactive association to the right
    """
    global INTERACTIVE_ASSOCIATION_INFO
    mirrored = makeAssoicationInfoSymmetrical(INTERACTIVE_ASSOCIATION_INFO)
    INTERACTIVE_ASSOCIATION_INFO = mirrored


def makeAssoicationInfoSymmetrical(association_info, favor_side="left"):
    """ensures the association information provided is equal on both sides

    Args:
        association_info (dict): embed point: guide name
        favor_side (str, optional): side to mirror from

    Returns:
        dict: symmetrical association info
    """
    replace = SIDE_MIRROR_INFO[favor_side]
    mirrored_association_info = copy.deepcopy(association_info)
    for embed, guides in association_info.items():
        if embed.startswith(favor_side):
            mirror_embed = embed.replace(favor_side, replace)
            mirrored_guides = []
            for guide in guides:
                mirror = m_string.convertRLName(guide)
                if cmds.objExists(mirror):
                    mirrored_guides.append(mirror)
                else:
                    mirrored_guides.append(guide)
            mirrored_association_info[mirror_embed] = mirrored_guides
    return mirrored_association_info


@utils.one_undo
def mirrorEmbedNodes(node, target=None, search="left", replace="right"):
    """mirror node position to target. Specifically for embed nodes

    Args:
        node (str): embed nodes
        target (str, optional): if none provided, it will be lft vs right
        search (str, optional): token to search for and replace
        replace (str, optional): replace token with
    """
    node = pm.PyNode(node)
    if target:
        target_node = pm.PyNode(target)
    else:
        target_node = node.name().replace(search, replace)
        try:
            target_node = pm.PyNode(target_node)
        except Exception as e:
            print(e)
            return
    src_mat = node.getTransformation()
    target_mat = transform.getSymmetricalTransform(src_mat)
    target_mat.rotateTo([0, 0, 0])
    target_node.setTransformation(target_mat)


@utils.one_undo
def mirrorSelectedEmbedNodes():
    """convenience, take selection and mirror. Specific to embed nodes
    """
    for node in cmds.ls(sl=True):
        if node in DEFAULT_BIPED_POINTS:
            if node.startswith("left"):
                mirrorEmbedNodes(node)
            elif node.startswith("right"):
                mirrorEmbedNodes(node, search="right", replace="left")


@utils.one_undo
def mirrorEmbedNodesSide(search="left", replace="right"):
    """mirror all embed nodes of search/side to the other/replace

    Args:
        search (str, optional): left
        replace (str, optional): right
    """
    for node in DEFAULT_BIPED_POINTS:
        if node.startswith(search):
            mirrorEmbedNodes(node, search=search, replace=replace)


def linerlyInterperlateNodes(a, b, nodes):
    """place the nodes on a vector between point a and b, evenly spaced

    Args:
        a (str): name of node
        b (str): name of node b
        nodes (list): of nodes to place on vector
    """
    blend = 0
    blend_step = .5
    a = pm.PyNode(a)
    b = pm.PyNode(b)
    if len(nodes) > 1:
        blend_step = 1.0 / (len(nodes) + 1)
    for node in nodes:
        blend += blend_step
        node = pm.PyNode(node)
        a_trans = a.getMatrix(ws=True).translate
        b_trans = b.getMatrix(ws=True).translate
        interp_vector = vector.linearlyInterpolate(a_trans,
                                                   b_trans,
                                                   blend=blend)
        node.setTranslation(interp_vector)


def linerlyInterpSelected():
    """convenience function to interpolate selected. Select A and B then the
    rest of the nodes to constrain
    """
    selected = cmds.ls(sl=True)
    if not len(selected) > 2:
        return
    a = selected[0]
    b = selected[1]
    nodes = selected[2:]
    linerlyInterperlateNodes(a, b, nodes)


# highly specific and hardcoded funcs -----------------------------------------
# embed point menipulation --------------------------------------------------

def alignSpineToHips():
    """put the back, shoulder and head on the same plane
    """
    tx_val = cmds.getAttr("hips.tx")
    cmds.setAttr("back.tx", tx_val)
    cmds.setAttr("shoulders.tx", tx_val)
    cmds.setAttr("head.tx", tx_val)


def centerHips():
    """center the hips between both legs
    """
    linerlyInterperlateNodes("left_thigh", "right_thigh", ["hips"])


@utils.one_undo
def adjustBackPointPosition(blend=.6, height_only=True):
    """constrain nodes of the back on a vector distributed evenly

    Args:
        blend (float, optional): defaulted to .6 to mimic a sternum
        height_only (bool, optional): only adjust the height of nodes
    """
    a = pm.PyNode("hips")
    b = pm.PyNode("shoulders")
    back_point = pm.PyNode("back")
    interp_vector = vector.linearlyInterpolate(a.getMatrix(ws=True).translate,
                                               b.getMatrix(ws=True).translate,
                                               blend=blend)
    if height_only:
        back_mat = back_point.getMatrix(ws=True)
        interp_vector[0] = back_mat.translate[0]
        interp_vector[2] = back_mat.translate[2]
    back_point.setTranslation(interp_vector)


@utils.one_undo
def makeEmbedArmsPlanar(shoulder="left_shoulder",
                        wrist="left_hand",
                        elbow="left_elbow",
                        favor_side="left"):
    """specific to the arms only. Try to align the arms on a plane for more
    ideal results when the guides are applied

    Args:
        shoulder (str, optional): shoulder, root of chain
        wrist (str, optional): wrist, end of chain
        elbow (str, optional): position elbow
        favor_side (str, optional): left or right
    """
    if favor_side == "right":
        shoulder = m_string.convertRLName(shoulder)
        wrist = m_string.convertRLName(wrist)
        elbow = m_string.convertRLName(elbow)
    constrainPointToVectorPlanar(shoulder, wrist, elbow, ws=True)


@utils.one_undo
def smartAdjustEmbedOutput(make_limbs_planar=True,
                           mirror_side=True,
                           favor_side="left",
                           center_hips=True,
                           align_spine=True,
                           adjust_Back_pos=True,
                           spine_blend=.6,
                           spine_height_only=True):
    """run a series of functions to intelligently(?) adjust the embed output
    to be more favorable to rig with.

    Args:
        make_limbs_planar (bool, optional): align limbs to a plane
        mirror_side (bool, optional): mirror the results to a the other side
        favor_side (str, optional): side to favor and mirror over
        center_hips (bool, optional): center the hips between leg rooms
        align_spine (bool, optional): align spince to place
        adjust_Back_pos (bool, optional): move up to mimic sternum
        spine_blend (float, optional): how high to position the back/sternum
        spine_height_only (bool, optional): only adjust spine y axis
    """
    if make_limbs_planar:
        makeEmbedArmsPlanar()

    if mirror_side:
        mirrorEmbedNodesSide(search=favor_side,
                             replace=SIDE_MIRROR_INFO[favor_side])
    if center_hips:
        centerHips()
    if align_spine:
        alignSpineToHips()
    if adjust_Back_pos:
        adjustBackPointPosition(blend=spine_blend,
                                height_only=spine_height_only)


# guide mannipulation ---------------------------------------------------------

@utils.viewport_off
@utils.one_undo
def enforceMinimumHeight(nodes, lowest_point_node=GUIDE_ROOT_NAME):
    """Enforce minimum negative height. Most used for 0, if you do not want
    nodes in -y

    Args:
        nodes (list): of nodes to restrict height
        lowest_point_node (TYPE, optional): node to extract lowest point from
    """
    lowest_vector = pm.PyNode(lowest_point_node).getMatrix(ws=True).translate
    for node in nodes:
        node = pm.PyNode(node)
        node_vector = node.getTranslation(space="world")
        node_vector[1] = lowest_vector[1]
        node.setTranslation(node_vector, space="world")


@utils.one_undo
def orientChainNodes(nodes_in_order):
    """orient nodes in order, so it points to the next on the list

    Args:
        nodes_in_order (list): of nodes to orient looking at each other
    """
    num_nodes = len(nodes_in_order) - 1
    for index, node in enumerate(nodes_in_order):
        if index == num_nodes:
            break
        orientAt(node, nodes_in_order[index + 1])


@utils.one_undo
def orientAdjustArms():
    """orient the guide nodes on the arm to point down the chain
    """
    # arm_guides = ["arm_L0_root", "arm_L0_elbow", "arm_L0_wrist", "arm_L0_eff"]
    arm_guides = ["arm_L0_root", "arm_L0_elbow", "arm_L0_eff"]
    orientChainNodes(arm_guides)
    arm_guides1 = ["arm_L0_wrist", "arm_L0_eff"]
    orientChainNodes(arm_guides1)
    arm_guides = [m_string.convertRLName(x) for x in arm_guides]
    arm_guides1 = [m_string.convertRLName(x) for x in arm_guides1]
    orientChainNodes(arm_guides)
    orientChainNodes(arm_guides1)


@utils.one_undo
def adjustHandPosition(wrist="arm_L0_wrist",
                       metacarpal="arm_L0_eff",
                       favor_side="left"):
    """estimate the position of the hand. The embed nodes only provide an end
    point for the arm and no position for the wrist.

    Args:
        wrist (str, optional): node to position
        metacarpal (str, optional): end of the guide arm, hand
        favor_side (str, optional): left or right
    """
    if favor_side != "left":
        wrist = m_string.convertRLName(wrist)
        metacarpal = m_string.convertRLName(metacarpal)
    a = pm.PyNode(wrist)
    a.setRotation([0, 0, 0])
    b = pm.PyNode(metacarpal)
    b.setRotation([0, 0, 0])

    diff_vect = b.getMatrix(ws=True).translate - a.getMatrix(ws=True).translate

    mat = a.getMatrix(ws=True).translate - (diff_vect)
    a.setTranslation(mat, space="world")


@utils.one_undo
def adjustWristPosition(elbow="left_elbow",
                        wrist_guide="arm_L0_wrist",
                        metacarpal="left_hand",
                        favor_side="left"):
    """After adjusting the hand position we need to constrain the wrist to a
    a vector between the meta and elbow

    Args:
        elbow (str, optional): elbow or knee
        wrist_guide (str, optional): will be constrained
        metacarpal (str, optional): end of the chain
        favor_side (str, optional): left or right
    """
    constrainPointToVectorPlanar(elbow,
                                 metacarpal,
                                 wrist_guide,
                                 ws=True,
                                 pcp=True)


@utils.viewport_off
@utils.one_undo
def simpleMatchGuideToEmbed(guide_association_info):
    """match position of the embed guides with the guides

    Args:
        guide_association_info (dict): association info
    """
    for point in DEFAULT_BIPED_POINTS:
        if point not in guide_association_info:
            continue
        for guide in guide_association_info[point]:
            cmds.matchTransform(guide, point, pos=True)


@utils.viewport_off
@utils.one_undo
def matchGuidesToEmbedOutput(guide_association_info=DEFAULT_EMBED_GUIDE_ASSOCIATION,
                             guide_root=GUIDE_ROOT_NAME,
                             setup_geo=SETUP_GEO_SHAPE_NAME,
                             scale_guides=True,
                             manual_scale=False,
                             lowest_point_node=None,
                             min_height_nodes=None,
                             adjust_hand_position=True,
                             orient_adjust_arms=True):
    """convenience function to matchTransform of trhe guides to the embed nodes

    Args:
        guide_association_info (dict, optional): embed: guide dict
        guide_root (str, optional): name of the root guide
        setup_geo (str, optional): name of the source geometry shape
        scale_guides (bool, optional): should the guides be scaled at all
        manual_scale (bool, optional): if scale, manual override
        lowest_point_node (str, optional): node to extract lowest point from
        min_height_nodes (list, optional): nodes to enforce minimum height to
        adjust_hand_position (bool, optional): move a hand poistion on the guides
        orient_adjust_arms (bool, optional): orient arms down the chain
    """
    if scale_guides:
        scaleNodeAToNodeB(guide_root, setup_geo, manual_scale=manual_scale)

    simpleMatchGuideToEmbed(guide_association_info)

    if min_height_nodes:
        if not lowest_point_node:
            lowest_point_node = guide_root
        enforceMinimumHeight(min_height_nodes,
                             lowest_point_node=lowest_point_node)

    if orient_adjust_arms:
        orientAdjustArms()

    if adjust_hand_position:
        adjustHandPosition()
        adjustHandPosition(favor_side="right")
        adjustWristPosition()
        adjustWristPosition(elbow="right_elbow",
                            wrist_guide="arm_R0_wrist",
                            metacarpal="right_hand")

    if orient_adjust_arms:
        orientAdjustArms()


@utils.viewport_off
@utils.one_undo
def runAllEmbed(guide_association_info,
                setup_geo,
                guide_root,
                segmentationMethod=3,
                segmentationResolution=128,
                scale_guides=True,
                lowest_point_node=None,
                min_height_nodes=None,
                smart_adjust=True,
                adjust_hand_position=True,
                orient_adjust_arms=True,
                mirror_embed_side="left"):
    """convenience function to matchTransform of trhe guides to the embed nodes

    Args:
        guide_association_info (dict, optional): embed: guide dict
        guide_root (str, optional): name of the root guide
        setup_geo (str, optional): name of the source geometry shape
        scale_guides (bool, optional): should the guides be scaled at all
        manual_scale (bool, optional): if scale, manual override
        lowest_point_node (str, optional): node to extract lowest point from
        min_height_nodes (list, optional): nodes to enforce minimum height to
        adjust_hand_position (bool, optional): move a hand poistion on the guides
        orient_adjust_arms (bool, optional): orient arms down the chain
    """
    embed_info = getEmbedInfoFromShape(setup_geo,
                                       segmentationMethod=segmentationMethod,
                                       segmentationResolution=segmentationResolution)
    createNodeFromEmbedInfo(embed_info)
    if smart_adjust:
        smartAdjustEmbedOutput(make_limbs_planar=True,
                               mirror_side=bool(mirror_embed_side),
                               favor_side=mirror_embed_side,
                               center_hips=True,
                               align_spine=True,
                               adjust_Back_pos=True,
                               spine_blend=.6,
                               spine_height_only=True)

    matchGuidesToEmbedOutput(guide_association_info=guide_association_info,
                             guide_root=guide_root,
                             setup_geo=setup_geo,
                             scale_guides=scale_guides,
                             lowest_point_node=lowest_point_node,
                             min_height_nodes=min_height_nodes,
                             adjust_hand_position=adjust_hand_position,
                             orient_adjust_arms=orient_adjust_arms)
    return embed_info


@utils.one_undo
def runAllEmbedFromPaths(model_filepath,
                         guide_filepath,
                         guide_association_info,
                         setup_geo,
                         guide_root,
                         scale_guides=True,
                         lowest_point_node=None,
                         min_height_nodes=None,
                         adjust_hand_position=True,
                         orient_adjust_arms=True,
                         mirror_embed_side="left"):
    """convenience function to matchTransform of trhe guides to the embed nodes

    Args:
        model_filepath (dict, optional): embed: guide dict filepaths
        guide_filepath (str, optional): name of the root guide filepaths
        setup_geo (str, optional): name of the source geometry shape
        scale_guides (bool, optional): should the guides be scaled at all
        manual_scale (bool, optional): if scale, manual override
        lowest_point_node (str, optional): node to extract lowest point from
        min_height_nodes (list, optional): nodes to enforce minimum height to
        adjust_hand_position (bool, optional): move a hand poistion
        on the guides orient_adjust_arms (bool, optional):
        orient arms down the chain
    """
    cmds.file(model_filepath, i=True)
    io.import_guide_template(filePath=guide_filepath)
    if type(guide_association_info) != dict:
        guide_association_info = _importData(guide_association_info)
    runAllEmbed(guide_association_info,
                setup_geo,
                guide_root,
                scale_guides=scale_guides,
                lowest_point_node=lowest_point_node,
                min_height_nodes=min_height_nodes,
                adjust_hand_position=adjust_hand_position,
                orient_adjust_arms=orient_adjust_arms)


@utils.one_undo
def deleteEmbedNodes():
    """Delete the created nodes from the embedSkeleton command
    """
    nodes = cmds.ls(DEFAULT_BIPED_POINTS)
    if nodes:
        cmds.delete(nodes)
