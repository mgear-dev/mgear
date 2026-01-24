"""Functions to create and connect nodes."""


import mgear.pymaya as pm
from mgear.pymaya import versions
import mgear.pymaya.datatypes as datatypes
from mgear.core import attribute

from .six import PY2, string_types

# Type tuple for faster isinstance checks (used frequently in node creation)
_CONNECTABLE_TYPES = None


def _is_connectable(value):
    """Check if value is a connectable attribute (string or pm.Attribute).

    This is used frequently in node creation functions to determine
    whether to connect or set a value.
    """
    global _CONNECTABLE_TYPES
    if _CONNECTABLE_TYPES is None:
        _CONNECTABLE_TYPES = (string_types, pm.Attribute)
    return isinstance(value, _CONNECTABLE_TYPES)


#############################################
# CREATE SIMPLE NODES
#############################################


def createMultMatrixNode(mA, mB, target=False, transform="srt"):
    """Create Maya multiply Matrix node.

    Note:
        This node have same functionality as the default Maya matrix
        multiplication.

    Arguments:
        mA (matrix): input matrix A.
        mB (matrix): input matrix B.
        target (dagNode): object target to apply the transformation
        transform (str): if target is True. out transform  to SRT valid
            value s r t

    Returns:
        pyNode: Newly created mGear_multMatrix node

    """

    if isinstance(mA, str):
        mA = pm.PyNode(mA)
    if isinstance(mB, str):
        mB = pm.PyNode(mB)
    if isinstance(target, str):
        target = pm.PyNode(target)

    node = pm.createNode("multMatrix")
    for m, mi in zip([mA, mB], ["matrixIn[0]", "matrixIn[1]"]):
        if isinstance(m, datatypes.Matrix):
            pm.setAttr(node.attr(mi), m)
        else:
            pm.connectAttr(m, node.attr(mi))
    if target:
        dm_node = pm.createNode("decomposeMatrix")
        pm.connectAttr(node + ".matrixSum", dm_node + ".inputMatrix")
        if "t" in transform:
            pm.connectAttr(
                dm_node + ".outputTranslate", target.attr("translate"), f=True
            )
        if "r" in transform:
            pm.connectAttr(
                dm_node + ".outputRotate", target.attr("rotate"), f=True
            )
        if "s" in transform:
            pm.connectAttr(
                dm_node + ".outputScale", target.attr("scale"), f=True
            )

    return node


def createDecomposeMatrixNode(m):
    """
    Create and connect a decomposeMatrix node.

    Arguments:
        m(str or attr): The matrix attribute name.

    Returns:
        pyNode: the newly created node.

    >>> dm_node = nod.createDecomposeMatrixNode(mulmat_node+".output")

    """
    node = pm.createNode("decomposeMatrix")

    pm.connectAttr(m, node + ".inputMatrix")

    return node


def createDistNode(objA, objB, output=None):
    """Create and connect a distance node.

    Arguments:
        objA (dagNode): The dagNode A.
        objB (dagNode): The dagNode B.
        output (attr): Output attribute.

    Returns:
        pyNode: the newly created node.

    >>> distA_node = nod.createDistNode(self.tws0_loc, self.tws1_loc)

    """
    node = pm.createNode("distanceBetween")

    dm_nodeA = pm.createNode("decomposeMatrix")
    dm_nodeB = pm.createNode("decomposeMatrix")

    pm.connectAttr(objA + ".worldMatrix", dm_nodeA + ".inputMatrix")
    pm.connectAttr(objB + ".worldMatrix", dm_nodeB + ".inputMatrix")

    pm.connectAttr(dm_nodeA + ".outputTranslate", node + ".point1")
    pm.connectAttr(dm_nodeB + ".outputTranslate", node + ".point2")

    if output:
        pm.connectAttr(node + ".distance", output)

    return node


def createConditionNode(
    firstTerm=False, secondTerm=False, operator=0, ifTrue=False, ifFalse=False
):
    """Create and connect a condition node.

    ========    ======
    operator    index
    ========    ======
    ==          0
    !=          1
    >           2
    >=          3
    <           4
    <=          5
    ========    ======

    Arguments:
        firstTerm (attr): The attribute string name for the first
            conditions.
        secondTerm (attr): The attribute string for the second
            conditions.
        operator (int): The operator to make the condition.
        ifTrue (bool or attr): If an attribute is provided will connect
            ifTrue output.
        ifFalse (bool or attr): If an attribute is provided will connect
            ifFalse output.

    Returns:
        pyNode: the newly created node.

    >>> cond1_node = nod.createConditionNode(self.soft_attr,
                                             0,
                                             2,
                                             subtract3_node+".output1D",
                                             plusTotalLength_node+".output1D")

    """
    check_list = [pm.Attribute, str]
    if PY2:
        check_list.append(unicode)
    node = pm.createNode("condition")
    pm.setAttr(node + ".operation", operator)
    if firstTerm:
        attribute.connectSet(firstTerm, node + ".firstTerm", check_list)

    if secondTerm:
        attribute.connectSet(secondTerm, node + ".secondTerm", check_list)

    if ifTrue:
        attribute.connectSet(ifTrue, node + ".colorIfTrueR", check_list)

    if ifFalse:
        attribute.connectSet(ifFalse, node + ".colorIfFalseR", check_list)

    return node


def createBlendNode(inputA, inputB, blender=0.5):
    """Create and connect a createBlendNode node.

    Arguments:
        inputA (attr or list of 3 attr): The attribute input A
        inputB (attr or list of 3 attr): The attribute input B
        blender (float or attr): Float in 0 to 1 range or attribute
            string name.


    Returns:
        pyNode: the newly created node.

    >>> blend_node = nod.createBlendNode(
            [dm_node+".outputRotate%s"%s for s in "XYZ"],
            [cns+".rotate%s"%s for s in "XYZ"],
            self.lock_ori_att)

    """
    node = pm.createNode("blendColors")

    if not isinstance(inputA, list):
        inputA = [inputA]

    if not isinstance(inputB, list):
        inputB = [inputB]

    for item, s in zip(inputA, "RGB"):
        if isinstance(item, string_types) or isinstance(item, pm.Attribute):
            pm.connectAttr(item, node + ".color1" + s)
        else:
            pm.setAttr(node + ".color1" + s, item)

    for item, s in zip(inputB, "RGB"):
        if isinstance(item, string_types) or isinstance(item, pm.Attribute):
            pm.connectAttr(item, node + ".color2" + s)
        else:
            pm.setAttr(node + ".color2" + s, item)

    if isinstance(blender, string_types) or isinstance(blender, pm.Attribute):
        pm.connectAttr(blender, node + ".blender")
    else:
        pm.setAttr(node + ".blender", blender)

    return node


def createPairBlend(
    inputA=None,
    inputB=None,
    blender=0.5,
    rotInterpolation=0,
    output=None,
    trans=True,
    rot=True,
):
    """Create and connect a PairBlend node.

    Arguments:
        inputA (dagNode): The transfomr input 1
        inputB (dagNode): The transfomr input 2
        blender (float or attr): Float in 0 to 1 range or attribute
            string name.
        rotInterpolation (int): Rotation interpolation option. 0=Euler.
            1=Quaternion.
        output (dagNode): The output node with the blend transfomr
            applied.
        trans (bool): If true connects translation.
        rot (bool): If true connects rotation.

    Returns:
        pyNode: the newly created node.

    Example:
        .. code-block:: python

            blend_node = nod.createPairBlend(self.legBonesFK[i],
                                             self.legBonesIK[i],
                                             self.blend_att,
                                             1)
            pm.connectAttr(blend_node + ".outRotate", x+".rotate")
            pm.connectAttr(blend_node + ".outTranslate", x+".translate")

    """
    node = pm.createNode("pairBlend")
    node.attr("rotInterpolation").set(rotInterpolation)

    if inputA:
        if trans:
            pm.connectAttr(inputA + ".translate", node + ".inTranslate1")
        if rot:
            pm.connectAttr(inputA + ".rotate", node + ".inRotate1")

    if inputB:
        if trans:
            pm.connectAttr(inputB + ".translate", node + ".inTranslate2")
        if rot:
            pm.connectAttr(inputB + ".rotate", node + ".inRotate2")

    if isinstance(blender, string_types) or isinstance(blender, pm.Attribute):
        pm.connectAttr(blender, node + ".weight")
    else:
        pm.setAttr(node + ".weight", blender)

    if output:
        if rot:
            pm.connectAttr(node + ".outRotate", output + ".rotate")
        if trans:
            pm.connectAttr(node + ".outTranslate", output + ".translate")

    return node


def createSetRangeNode(
    input, oldMin, oldMax, newMin=0, newMax=1, output=None, name="setRange"
):
    """Create Set Range Node"""

    node = pm.createNode("setRange", n=name)

    if not isinstance(input, list):
        input = [input]

    for item, s in zip(input, "XYZ"):
        if isinstance(item, string_types) or isinstance(item, pm.Attribute):
            pm.connectAttr(item, node + ".value" + s)
        else:
            pm.setAttr(node + ".value" + s, item)

        if isinstance(oldMin, string_types) or isinstance(
            oldMin, pm.Attribute
        ):
            pm.connectAttr(oldMin, node + ".oldMin" + s)
        else:
            pm.setAttr(node + ".oldMin" + s, oldMin)

        if isinstance(oldMax, string_types) or isinstance(
            oldMax, pm.Attribute
        ):
            pm.connectAttr(oldMax, node + ".oldMax" + s)
        else:
            pm.setAttr(node + ".oldMax" + s, oldMax)

        if isinstance(newMin, string_types) or isinstance(
            newMin, pm.Attribute
        ):
            pm.connectAttr(newMin, node + ".min" + s)
        else:
            pm.setAttr(node + ".min" + s, newMin)

        if isinstance(newMax, string_types) or isinstance(
            newMax, pm.Attribute
        ):
            pm.connectAttr(newMax, node + ".max" + s)
        else:
            pm.setAttr(node + ".max" + s, newMax)

    if output:
        if not isinstance(output, list):
            output = [output]
        for out, s in zip(output, "XYZ"):
            pm.connectAttr(node + ".outValue" + s, out, f=True)

    return node


def createReverseNode(input, output=None):
    """Create and connect a reverse node.

    Arguments:
        input (attr or list of 3 attr): The attribute input.
        output (attr or list of 3 attr): The attribute to connect the
            output.

    Returns:
        pyNode: the newly created node.

    >>> fkvis_node = nod.createReverseNode(self.blend_att)

    """
    node = pm.createNode("reverse")

    if not isinstance(input, list):
        input = [input]

    for item, s in zip(input, "XYZ"):
        if isinstance(item, string_types) or isinstance(item, pm.Attribute):
            pm.connectAttr(item, node + ".input" + s)
        else:
            pm.setAttr(node + ".input" + s, item)

    if output:
        if not isinstance(output, list):
            output = [output]
        for out, s in zip(output, "XYZ"):
            pm.connectAttr(node + ".output" + s, out, f=True)

    return node


def createCurveInfoNode(crv):
    """Create and connect a curveInfo node.

    Arguments:
        crv (dagNode): The curve.

    Returns:
        pyNode: the newly created node.

    >>> crv_node = nod.createCurveInfoNode(self.slv_crv)

    """
    node = pm.createNode("curveInfo")

    shape = pm.listRelatives(crv, shapes=True)[0]

    pm.connectAttr(shape + ".local", node + ".inputCurve")

    return node


def createAddDL():
    # Maya 2026 changed and removed some node names
    if pm.versions.current() >= 20260000:
        node = pm.createNode("addDL")
    else:
        node = pm.createNode("addDoubleLinear")

    return node


# TODO: update using plusMinusAverage node
def createAddNode(inputA, inputB):
    """Create and connect a addition node.

    Arguments:
        inputA (attr or float): The attribute input A
        inputB (attr or float): The attribute input B

    Returns:
        pyNode: the newly created node.

    >>> add_node = nod.createAddNode(self.roundness_att, .001)

    """
    node = createAddDL()

    if isinstance(inputA, string_types) or isinstance(inputA, pm.Attribute):
        pm.connectAttr(inputA, node + ".input1")
    else:
        pm.setAttr(node + ".input1", inputA)

    if isinstance(inputB, string_types) or isinstance(inputB, pm.Attribute):
        pm.connectAttr(inputB, node + ".input2")
    else:
        pm.setAttr(node + ".input2", inputB)

    return node


# TODO: update using plusMinusAverage node
def createSubNode(inputA, inputB):
    """Create and connect a subtraction node.

    Arguments:
        inputA (attr or float): The attribute input A
        inputB (attr or float): The attribute input B

    Returns:
        pyNode: the newly created node.

    >>> sub_nod = nod.createSubNode(self.roll_att, angle_outputs[i-1])

    """
    node = createAddDL()

    if isinstance(inputA, string_types) or isinstance(inputA, pm.Attribute):
        pm.connectAttr(inputA, node + ".input1")
    else:
        pm.setAttr(node + ".input1", inputA)

    if isinstance(inputB, string_types) or isinstance(inputB, pm.Attribute):
        neg_node = pm.createNode("multiplyDivide")
        pm.connectAttr(inputB, neg_node + ".input1X")
        pm.setAttr(neg_node + ".input2X", -1)
        pm.connectAttr(neg_node + ".outputX", node + ".input2")
    else:
        pm.setAttr(node + ".input2", -inputB)

    return node


def createPowNode(inputA, inputB, output=None):
    """Create and connect a power node.

    Arguments:
        inputA (attr, float or list of float): The attribute input A
        inputB (attr, float or list of float): The attribute input B
        output (attr or list of attr): The attribute to connect the
            output.

    Returns:
        pyNode: the newly created node.

    """
    return createMulDivNode(inputA, inputB, 3, output)


def createMulNode(inputA, inputB, output=None):
    """Create and connect a Multiply node.

    Arguments:
        inputA (attr, float or list of float): The attribute input A
        inputB (attr, float or list of float): The attribute input B
        output (attr or list of attr): The attribute to connect the
            output.

    Returns:
        pyNode: the newly created node.

    """
    return createMulDivNode(inputA, inputB, 1, output)


def createDivNode(inputA, inputB, output=None):
    """Create and connect a Divide node.

    Arguments:
        inputA (attr, float or list of float): The attribute input A
        inputB (attr, float or list of float): The attribute input B
        output (attr or list of attr): The attribute to connect the
            output.

    Returns:
        pyNode: the newly created node.

    Example:
        .. code-block:: python

            # Classic Maya style creation and connection = 4 lines
            div1_node = pm.createNode("multiplyDivide")
            div1_node.setAttr("operation", 2)
            div1_node.setAttr("input1X", 1)
            pm.connectAttr(self.rig.global_ctl+".sx",
                           div1_node+".input2X")

            # mGear style = 1 line
            div1_node = nod.createDivNode(1.0,
                                          self.rig.global_ctl+".sx")

    """
    return createMulDivNode(inputA, inputB, 2, output)


def createMulDivNode(inputA, inputB, operation=1, output=None):
    """Create and connect a Multiply or Divide node.

    Arguments:
        inputA (attr, float or list of float): The attribute input A
        inputB (attr, float or list of float): The attribute input B
        output (attr or list of attr): The attribute to connect the
            output.

    Returns:
        pyNode: the newly created node.

    """
    node = pm.createNode("multiplyDivide")
    pm.setAttr(f"{node}.operation", operation)

    if not isinstance(inputA, list):
        inputA = [inputA]

    if not isinstance(inputB, list):
        inputB = [inputB]

    for item, s in zip(inputA, "XYZ"):
        if _is_connectable(item):
            try:
                pm.connectAttr(item, f"{node}.input1{s}", f=True)
            except (UnicodeEncodeError, RuntimeError):
                # Maya in Japanese have an issue with unicodeEndoce
                # UnicodeEncodeError is a workaround
                pm.connectAttr(item, f"{node}.input1", f=True)
                break

        else:
            pm.setAttr(f"{node}.input1{s}", item)

    for item, s in zip(inputB, "XYZ"):
        if _is_connectable(item):
            try:
                pm.connectAttr(item, f"{node}.input2{s}", f=True)
            except (UnicodeEncodeError, RuntimeError):
                # Maya in Japanese have an issue with unicodeEndoce
                # UnicodeEncodeError is a workaround
                pm.connectAttr(item, f"{node}.input2", f=True)
                break
        else:
            pm.setAttr(f"{node}.input2{s}", item)

    if output:
        if not isinstance(output, list):
            output = [output]

        for item, s in zip(output, "XYZ"):
            pm.connectAttr(node + ".output" + s, item, f=True)

    return node


def createClampNode(input, in_min, in_max):
    """Create and connect a clamp node

    Arguments:
        input (attr, float or list): The input value to clamp
        in_min (float): The minimun value to clamp
        in_max (float): The maximun value to clamp

    Returns:
        pyNode: the newly created node.

    >>> clamp_node = nod.createClampNode(
        [self.roll_att, self.bank_att, self.bank_att],
        [0, -180, 0],
        [180,0,180])

    """
    node = pm.createNode("clamp")

    if not isinstance(input, list):
        input = [input]
    if not isinstance(in_min, list):
        in_min = [in_min]
    if not isinstance(in_max, list):
        in_max = [in_max]

    for in_item, min_item, max_item, s in zip(input, in_min, in_max, "RGB"):

        if _is_connectable(in_item):
            pm.connectAttr(in_item, f"{node}.input{s}")
        else:
            pm.setAttr(f"{node}.input{s}", in_item)

        if _is_connectable(min_item):
            pm.connectAttr(min_item, f"{node}.min{s}")
        else:
            pm.setAttr(f"{node}.min{s}", min_item)

        if _is_connectable(max_item):
            pm.connectAttr(max_item, f"{node}.max{s}")
        else:
            pm.setAttr(f"{node}.max{s}", max_item)

    return node


def createPlusMinusAverage1D(input, operation=1, output=None):
    """Create a multiple average node 1D.
    Arguments:
        input (attr, float or list): The input values.
        operation (int): Node operation. 0=None, 1=sum, 2=subtract,
            3=average
        output (attr): The attribute to connect the result.

    Returns:
        pyNode: the newly created node.

    """
    if not isinstance(input, list):
        input = [input]

    node = pm.createNode("plusMinusAverage")
    node.attr("operation").set(operation)

    for i, x in enumerate(input):
        try:
            pm.connectAttr(x, f"{node}.input1D[{i}]")
        except RuntimeError:
            pm.setAttr(f"{node}.input1D[{i}]", x)

    if output:
        pm.connectAttr(f"{node}.output1D", output)

    return node


def createVertexPositionNode(
    inShape, vId=0, output=None, name="mgear_vertexPosition"
):
    """Creates a mgear_vertexPosition node"""
    node = pm.createNode("mgear_vertexPosition", n=name)
    inShape.worldMesh.connect(node.inputShape)
    node.vertex.set(vId)
    if output:
        pm.connectAttr(
            output.parentInverseMatrix, node.drivenParentInverseMatrix
        )
        pm.connectAttr(node.output, output.translate)

    return node


#############################################
# CREATE MULTI NODES
#############################################


def createNegateNodeMulti(name, inputs=[]):
    """Create and connect multiple negate nodes

    Arguments:
        name (str): The name for the new node.
        inputs (list of attr): The list of attributes to negate

    Returns:
        list: The output attributes list.

    """
    s = "XYZ"
    count = 0
    i = 0
    outputs = []
    for input in inputs:
        if count == 0:
            real_name = name + "_" + str(i)
            node_name = pm.createNode("multiplyDivide", n=real_name)
            i += 1

        pm.connectAttr(input, node_name + ".input1" + s[count], f=True)
        pm.setAttr(node_name + ".input2" + s[count], -1)

        outputs.append(node_name + ".output" + s[count])
        count = (count + 1) % 3

    return outputs


def createAddNodeMulti(inputs=[]):
    """Create and connect multiple add nodes

    Arguments:
        inputs (list of attr): The list of attributes to add

    Returns:
        list: The output attributes list.

    >>> angle_outputs = nod.createAddNodeMulti(self.angles_att)

    """
    outputs = [inputs[0]]

    for i, input in enumerate(inputs[1:]):
        node_name = createAddDL()

        if isinstance(outputs[-1], string_types) or isinstance(
            outputs[-1], pm.Attribute
        ):
            pm.connectAttr(outputs[-1], node_name + ".input1", f=True)
        else:
            pm.setAttr(node_name + ".input1", outputs[-1])

        if isinstance(input, string_types) or isinstance(input, pm.Attribute):
            pm.connectAttr(input, node_name + ".input2", f=True)
        else:
            pm.setAttr(node_name + ".input2", input)

        outputs.append(node_name + ".output")

    return outputs


def createMulNodeMulti(name, inputs=[]):
    """Create and connect multiple multiply nodes

    Arguments:
        name (str): The name for the new node.
        inputs (list of attr): The list of attributes to multiply

    Returns:
        list: The output attributes list.

    """
    outputs = [inputs[0]]

    for i, input in enumerate(inputs[1:]):
        real_name = name + "_" + str(i)
        node_name = pm.createNode("multiplyDivide", n=real_name)
        pm.setAttr(node_name + ".operation", 1)

        if isinstance(outputs[-1], string_types) or isinstance(
            outputs[-1], pm.Attribute
        ):
            pm.connectAttr(outputs[-1], node_name + ".input1X", f=True)
        else:
            pm.setAttr(node_name + ".input1X", outputs[-1])

        if isinstance(input, string_types) or isinstance(input, pm.Attribute):
            pm.connectAttr(input, node_name + ".input2X", f=True)
        else:
            pm.setAttr(node_name + ".input2X", input)

        outputs.append(node_name + ".output")

    return outputs


def createDivNodeMulti(name, inputs1=[], inputs2=[]):
    """Create and connect multiple divide nodes

    Arguments:
        name (str): The name for the new node.
        inputs1 (list of attr): The list of attributes to divide (numerators)
        inputs2 (list of attr): The list of attributes to divide by (denominators)

    Returns:
        list: The output attributes list.

    """
    outputs = [inputs1[0]]
    for i, input in enumerate(inputs2[1:]):
        real_name = f"{name}_{i}"
        node_name = pm.createNode("multiplyDivide", n=real_name)
        pm.setAttr(f"{node_name}.operation", 2)

        if isinstance(outputs[-1], (string_types, pm.Attribute)):
            pm.connectAttr(outputs[-1], f"{node_name}.input1X", f=True)
        else:
            pm.setAttr(f"{node_name}.input1X", outputs[-1])

        if isinstance(input, (string_types, pm.Attribute)):
            pm.connectAttr(input, f"{node_name}.input2X", f=True)
        else:
            pm.setAttr(f"{node_name}.input2X", input)

        outputs.append(f"{node_name}.output")

    return outputs


def createClampNodeMulti(name, inputs=[], in_min=[], in_max=[]):
    """Create and connect multiple clamp nodes

    Arguments:
        name (str): The name for the new node.
        inputs (list of attr): The list of attributes
        in_min (list of attr): The list of attributes
        in_max (list of attr): The list of attributes

    Returns:
        list: The output attributes list.

    """
    s = "RGB"
    count = 0
    i = 0
    outputs = []
    for input, min, max in zip(inputs, in_min, in_max):
        if count == 0:
            real_name = name + "_" + str(i)
            node_name = pm.createNode("clamp", n=real_name)
            i += 1

        pm.connectAttr(input, node_name + ".input" + s[count], f=True)

        if isinstance(min, string_types) or isinstance(min, pm.Attribute):
            pm.connectAttr(min, node_name + ".min" + s[count], f=True)
        else:
            pm.setAttr(node_name + ".min" + s[count], min)

        if isinstance(max, string_types) or isinstance(max, pm.Attribute):
            pm.connectAttr(max, node_name + ".max" + s[count], f=True)
        else:
            pm.setAttr(node_name + ".max" + s[count], max)

        outputs.append(node_name + ".output" + s[count])
        count = (count + 1) % 3

    return outputs


def createPickMatrix(
    m=None, out_m=None, scale=True, rotate=True, translate=True, shear=True
):
    """Summary

    Args:
        m (None, optional): input matrix
        out_m (None, optional): output matrix attr to connect
        scale (bool, optional): use scale
        rotate (bool, optional): use rotate
        translate (bool, optional): use translate
        shear (bool, optional): use shear
    """
    node = pm.createNode("pickMatrix")
    node.useScale.set(scale)
    node.useRotate.set(rotate)
    node.useTranslate.set(translate)
    node.useShear.set(shear)
    if m:
        pm.connectAttr(m, node.inputMatrix)
    if out_m:
        pm.connectAttr(node.outputMatrix, m)

    return node


#############################################
# Ctl tag node
#############################################


def add_controller_tag(ctl, tagParent=None):
    """Add a controller tag

    Args:
        ctl (dagNode): Controller to add the tar
        tagParent (dagNode): tag parent for the connection
    """
    if versions.current() >= 201650:
        pm.controller(ctl)
        ctt = pm.PyNode(pm.controller(ctl, q=True)[0])
        if tagParent:
            controller_tag_connect(ctt, tagParent)

        return ctt


def controller_tag_connect(ctt, tagParent):
    """Summary

    Args:
        ctt (TYPE): Teh control tag
        tagParent (TYPE): The object with the parent control tag
    """
    if pm.controller(tagParent, q=True):
        tpTagNode = pm.PyNode(pm.controller(tagParent, q=True)[0])
        tpTagNode.cycleWalkSibling.set(True)
        pm.connectAttr(tpTagNode.prepopulate, ctt.prepopulate, f=True)

        ni = attribute.get_next_available_index(tpTagNode.children)
        pm.disconnectAttr(ctt.parent)
        pm.connectAttr(ctt.parent, tpTagNode.attr("children[%s]" % str(ni)))
