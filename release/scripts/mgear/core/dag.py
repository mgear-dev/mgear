"""Navigate the DAG hierarchy"""

from typing import List

import maya.cmds as cmds
import mgear.pymaya as pm

#############################################
# DAG
#############################################


def getTopParent(node):
    """Returns the first parent of the hierarchy.

    usually the 'Model' in Softimage terminology

    Arguments:
        node (dagNode): The input node to search.

    Returns:
        dagNode: The top parent of the input node

    """
    return node.getParent(generations=-1)


def getShapes(node):
    """Returns the shape of the dagNode

    Arguments:
        node (dagNode): The input node to search the shape

    Returns:
        list: The shapes of the node

    """
    return node.listRelatives(shapes=True, fullPath=True)


def findChild(node, name):
    """Returns the first child of input node, with a matching name.

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search

    Returns:
        dagNode: The first child

    >>>  parent = dag.findChild(self.model,
                                mgear.string.convertRLName(
                                    comp_guide.root.name()))

    """
    # return __findChildren(node, name, True)
    return __findChild(node, name)


def findChildren(node, name):
    """Returns all the children  of input node, with a matching name.

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search

    Returns:
        dagNode list: The children dagNodes

    """
    return __findChildren(node, name, False)


def findChildrenPartial(node, name):
    """
    Returns the children of input node, with a partial matching name.

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search

    Returns:
        dagNode list: The children dagNodes

    """
    return __findChildren(node, name, False, True)


def __findChildren(node, name, firstOnly=False, partialName=False):

    if partialName:
        children = [item for item
                    in node.listRelatives(allDescendents=True,
                                          type="transform", fullPath=True)
                    if item.split("|")[-1].split("_")[-1] == name]
    else:
        children = [item for item
                    in node.listRelatives(allDescendents=True,
                                          type="transform", fullPath=True)
                    if item.split("|")[-1] == name]
    if not children:
        return False
    if firstOnly:
        return children[0]

    return children


def __findChild(node, name):
    """This find children function will stop search after first
     child found.child

    This is a faster version of __findchildren

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search

    Returns:
        dagNode: Children node
    """
    try:
        for item in cmds.listRelatives(node.name(),
                                       allDescendents=True,
                                       type="transform", fullPath=True):
            if item.split("|")[-1] == name:
                return pm.PyNode(item)
    except pm.MayaNodeError:
        for item in node.listRelatives(allDescendents=True,
                                       type="transform", fullPath=True):
            if item.split("|")[-1] == name:
                return item

    return False


def __findChildren2(node, name, firstOnly=False, partialName=False):
    """This function is using Maya cmds instead of PyMel

    Arguments:
        node (TYPE): Description
        name (TYPE): Description
        firstOnly (bool, optional): Description
        partialName (bool, optional): Description

    Returns:
        TYPE: Description
    """
    oName = node.name()
    if partialName:
        children = [item for item
                    in cmds.listRelatives(oName, allDescendents=True,
                                          type="transform")
                    if item.split("|")[-1].split("_")[-1] == name]
    else:
        children = [item for item
                    in cmds.listRelatives(oName, allDescendents=True,
                                          type="transform")
                    if item.split("|")[-1] == name]
    if not children:
        return False
    if firstOnly:
        return pm.PyNode(children[0])

    return [pm.PyNode(x) for x in children]


def findComponentChildren(node, name, sideIndex):
    """Returns the component children of input component root.

    Note:
        This method is specific to work with shifter guides naming conventions

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search
        sideIndex (str): the side

    Returns:
        dagNode list: The children dagNodes

    >>> objList =  dag.findComponentChildren(self.parent,
                                             oldName,
                                             oldSideIndex)

    """
    children = []
    for item in node.listRelatives(allDescendents=True,
                                   type="transform", fullPath=True):
        checkName = item.split("|")[-1].split("_")
        if checkName[0] == name and checkName[1] == sideIndex:
            children.append(item)

    return children


def findComponentChildren2(node, name, sideIndex):
    """Returns the component children of input component root.

    This function is using Maya cmds instead of PyMel

    Note:
        This method is specific to work with shifter guides naming conventions

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search
        sideIndex (str): the side

    Returns:
        dagNode list: The children dagNodes

    >>> objList =  dag.findComponentChildren(self.parent,
                                             oldName,
                                             oldSideIndex)

    """
    children = []
    for item in cmds.listRelatives(node.name(), allDescendents=True,
                                   fullPath=True, type="transform"):
        checkName = item.split("|")[-1].split("_")
        if checkName[0] == name and checkName[1] == sideIndex:
            children.append(item)

    return [pm.PyNode(x) for x in children]


def findComponentChildren3(node, name, sideIndex):
    """Returns the component children of input component root.

    This function is using Maya cmds instead of PyMel

    Note:
        This method is specific to work with shifter guides naming conventions

    Arguments:
        node (dagNode): The input node to search
        name (str): The name to search
        sideIndex (str): the side

    Returns:
        dagNode list: The children dagNodes

    >>> objList =  dag.findComponentChildren(self.parent,
                                             oldName,
                                             oldSideIndex)

    """
    children = []
    for item in cmds.listRelatives(node.name(), allDescendents=True,
                                   fullPath=True, type="transform") or []:
        checkName = item.split("|")[-1]
        in_name = "_".join([name, sideIndex])

        if in_name in checkName:
            children.append(item)

    return [pm.PyNode(x) for x in children]


def findComponentChildren4(node: pm.PyNode, name: str, sideIndex: str) -> List[pm.PyNode]:
    """
    Return all transform DAG nodes that belong to a given component.

    :param pm.PyNode node: The root node whose hierarchy to search.
    :param str name: Component name, for example "root" or "ik_hand_root".
    :param str sideIndex: Side or index string, for example "C0".
    :return: Matching transform nodes belonging to the component.
    :rtype: list[pm.PyNode]
    """
    name_tokens = name.split("_")
    prefix_len = len(name_tokens) + 1
    children = set()

    # -- All descendant transforms plus the node itself
    paths = pm.listRelatives(node.name(),
                             allDescendents=True,
                             fullPath=True,
                             type="transform") or []

    for path in paths:
        check_name = path.split("|")[-1]
        parts = check_name.split("_")

        # -- Check if transform belongs to the component
        is_component = (len(parts) >= prefix_len
                        and parts[:prefix_len - 1] == name_tokens
                        and parts[prefix_len - 1] == sideIndex)

        if is_component:
            children.add(path)

    return [pm.PyNode(x) for x in children]

