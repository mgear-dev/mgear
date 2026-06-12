import mgear.pymaya as pm
import maya.OpenMaya as om

from mgear.pymaya import datatypes

##################
# Helper functions
##################
namePrefix = "pCns"


def setName(name, side="C", idx=None):
    namesList = [namePrefix, side, name]
    if idx is not None:
        namesList[1] = side + str(idx)
    name = "_".join(namesList)
    return name


def getDagPath(node=None):
    sel = om.MSelectionList()
    sel.add(node)
    d = om.MDagPath()
    sel.getDagPath(0, d)
    return d


def getLocalOffset(parent, child):
    parentWorldMatrix = getDagPath(parent).inclusiveMatrix()
    childWorldMatrix = getDagPath(child).inclusiveMatrix()
    return childWorldMatrix * parentWorldMatrix.inverse()


def decomposeMatrixConnect(node=None,
                           child=None,
                           transform='srt'):
    if node and child:
        dm_node = pm.createNode('decomposeMatrix',
                                name=setName(child + "_decompMatrix"))
        pm.connectAttr(node + ".matrixSum",
                       dm_node + ".inputMatrix")
        if 't' in transform:
            pm.connectAttr(dm_node + ".outputTranslate",
                           child.attr("translate"), f=True)
        if 'r' in transform:
            pm.connectAttr(dm_node + ".outputRotate",
                           child.attr("rotate"), f=True)
        if 's' in transform:
            pm.connectAttr(dm_node + ".outputScale",
                           child.attr("scale"), f=True)


def matrixConstraint(parent=None,
                     child=None,
                     transform='srt',
                     offset=False):
    """Create constraint based on Maya Matrix node.

    """
    if parent and child:
        node = pm.createNode('multMatrix',
                             name=setName(parent + "_multMatrix"))
        if offset:
            localOffset = getLocalOffset(parent.name(), child.name())
            pm.setAttr(node + ".matrixIn[0]",
                       [localOffset(i, j) for i in range(4) for j in range(4)],
                       type="matrix")
            mId = ["[1]", "[2]"]
        else:
            mId = ["[0]", "[1]"]

        for m, mi, mx in zip([parent, child],
                             ['matrixIn' + mId[0], 'matrixIn' + mId[1]],
                             [".worldMatrix", ".parentInverseMatrix"]):
            m = m + mx
            if isinstance(m, datatypes.Matrix):
                pm.setAttr(node.attr(mi), m)
            else:
                pm.connectAttr(m, node.attr(mi))

        decomposeMatrixConnect(node, child, transform)

        return node


# the last one is the child
def matrixBlendConstraint(parent=None,  # should be a list
                          child=None,
                          weights=None,  # should be a list
                          transform='rt',
                          offset=False,
                          host=None):
    if parent and child:
        if not isinstance(parent, (list,)):
            pm.displayWarning(
                "matrixBlendConstraint [parent] variable should be a list.")
            return

        if weights:
            if isinstance(parent, (list,)):
                if len(weights) != len(parent):
                    pm.displayWarning(
                        "weights list should be equal to parents list.")
                    return
            else:
                pm.displayWarning(
                    "matrixBlendConstraint [weights] "
                    "variable should be a list.")
                return
        else:
            weights = []
            weight = 1.0 / len(parent)
            for p in parent:
                weights.append(weight)

        wtMat_node = pm.createNode('wtAddMatrix',
                                   name=setName(child + "_wtAddMatrix"))

        x = 0
        for p in parent:
            if offset:
                localOffset = getLocalOffset(p.name(), child.name())
                offset_node = pm.createNode(
                    'multMatrix',
                    name=setName(p + "_offsetMultMatrix"))
                pm.setAttr(
                    offset_node + ".matrixIn[0]",
                    [localOffset(i, j) for i in range(4) for j in range(4)],
                    type="matrix")
                pm.connectAttr(p + ".worldMatrix[0]",
                               offset_node + ".matrixIn[1]")
                pm.connectAttr(offset_node + ".matrixSum",
                               wtMat_node + ".wtMatrix[{}].matrixIn".format(x))
            else:
                pm.connectAttr(p + ".worldMatrix[0]",
                               wtMat_node + ".wtMatrix[{}].matrixIn".format(x))

            # set weights
            if host:
                name = setName(p + "_wtWeight")
                host.addAttr(name,
                             keyable=True,
                             attributeType='float',
                             min=0.0,
                             max=1.0)
                pm.connectAttr(host + "." + name,
                               wtMat_node + ".wtMatrix[{}].weightIn".format(x))
                pm.setAttr(host + "." + name, weights[x])
            else:
                wtMat_node.attr(
                    'wtMatrix[{}]'.format(x)).weightIn.set(weights[x])

            x += 1

        decomposeMatrixConnect(wtMat_node, child, transform)

        return wtMat_node
