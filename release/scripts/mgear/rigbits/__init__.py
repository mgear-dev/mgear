import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.pymaya import util as pmu


import mgear
from mgear.core import icon, applyop, node, transform, attribute
from mgear.core import primitive, meshNavigation, string


def addNPO(objs=None, *args):
    """Add a transform node as a neutral pose

    Add a transform node as a parent and in the same pose of each of the
    selected objects. This way neutralize the local transfromation
    values.
    NPO stands for "neutral position" terminology from the all mighty
    Softimage ;)

    """
    npoList = []

    if not objs:
        objs = pm.selected()
    if not isinstance(objs, list):
        objs = [objs]
    for obj in objs:
        oParent = obj.getParent()
        oTra = pm.createNode(
            "transform", n=obj.name() + "_npo", p=oParent, ss=True
        )
        oTra.setTransformation(obj.getMatrix())
        pm.parent(obj, oTra)
        npoList.append(oTra)

    return npoList


def selectDeformers(*args):
    """Select the deformers from the object skinCluster"""

    oSel = pm.selected()[0]
    oColl = pm.skinCluster(oSel, query=True, influence=True)
    pm.select(oColl)


# Icon creator
def createCTL(type="square", child=False, *args):
    """Create a control for each selected object.

    The newly create control can be parent or child of the object.

    Args:
        type (str): The shape of the control.
        child (bool): if True, the control will be created as a
            child of the object.

    """
    iconList = []
    if child:
        if len(pm.selected()) > 0:
            for x in pm.selected():
                oChilds = [
                    item
                    for item in x.listRelatives(ad=True, type="transform")
                    if item.longName().split("|")[-2] == x.name()
                ]

                o_icon = icon.create(
                    None, x.name() + "_ctl", None, [1, 0, 0], type
                )
                iconList.append(o_icon)
                o_icon.setTransformation(x.getMatrix(worldSpace=True))
                pm.parent(o_icon, x)
                for child in oChilds:

                    pm.parent(child, o_icon)
        else:

            o_icon = icon.create(
                None, type + "_ctl", datatypes.Matrix(), [1, 0, 0], type
            )
            iconList.append(o_icon)
    else:
        if len(pm.selected()) > 0:
            for x in pm.selected():
                oParent = x.getParent()
                o_icon = icon.create(
                    oParent, x.name() + "_ctl", x.getMatrix(), [1, 0, 0], type
                )
                iconList.append(o_icon)
                o_icon.setTransformation(x.getMatrix())
                pm.parent(x, o_icon)
        else:

            o_icon = icon.create(
                None, type + "_ctl", datatypes.Matrix(), [1, 0, 0], type
            )
            iconList.append(o_icon)

    for ico in iconList:
        attribute.addAttribute(ico, "isCtl", "bool", keyable=False)

    try:
        defSet = pm.PyNode("rig_controllers_grp")
        for ico in iconList:
            pm.sets(defSet, add=ico)
    except TypeError:
        print("No rig_controllers_grp found")
        pass


def addJnt(
    obj=False, parent=False, noReplace=False, grp=None, jntName=None, *args
):
    """Create one joint for each selected object.

    Args:
        obj (bool or dagNode, optional): The object to drive the new
            joint. If False will use the current selection.
        parent (bool or dagNode, optional): The parent for the joint.
            If False will try to parent to jnt_org. If jnt_org doesn't
            exist will parent the joint under the obj
        noReplace (bool, optional): If True will add the extension
            "_jnt" to the new joint name
        grp (pyNode or None, optional): The set to add the new joint.
            If none will use "rig_deformers_grp"
        *args: Maya's dummy

    Returns:
        pyNode: The New created joint.

    """
    if not obj:
        oSel = pm.selected()
    else:
        oSel = [obj]

    for obj in oSel:
        if not parent:
            try:
                oParent = pm.PyNode("jnt_org")
            except TypeError:
                oParent = obj
        else:
            oParent = parent
        if not jntName:
            if noReplace:
                jntName = "_".join(obj.name().split("_")) + "_jnt"
            else:
                jntName = "_".join(obj.name().split("_")[:-1]) + "_jnt"
        jnt = primitive.addJoint(oParent, jntName, transform.getTransform(obj))

        if grp:
            grp.add(jnt)
        else:
            try:
                defSet = pm.PyNode("rig_deformers_grp")
                pm.sets(defSet, add=jnt)
            except TypeError:
                pm.sets(n="rig_deformers_grp")
                defSet = pm.PyNode("rig_deformers_grp")
                pm.sets(defSet, add=jnt)

        jnt.setAttr("segmentScaleCompensate", False)
        jnt.setAttr("jointOrient", 0, 0, 0)
        try:
            cns_m = applyop.gear_matrix_cns(obj, jnt)
            # setting the joint orient compensation in order to have clean
            # rotation channels
            m = cns_m.drivenRestMatrix.get()
            tm = datatypes.TransformationMatrix(m)
            r = datatypes.degrees(tm.getRotation())
            jnt.attr("jointOrientX").set(r[0])
            jnt.attr("jointOrientY").set(r[1])
            jnt.attr("jointOrientZ").set(r[2])
        except RuntimeError:
            for axis in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                jnt.attr(axis).set(0.0)

    return jnt


def duplicateSym(*args):
    """Duplicate one dag hierarchy to/from X/-X renaming "L" to "R" """

    oSelection = pm.selected()
    if oSelection:
        oSel = oSelection[0]
        oTarget = pm.duplicate()[0]

        t = oSel.getTransformation()
        t = transform.getSymmetricalTransform(t)
        oTarget.setTransformation(t)

        # Quick rename
        pm.select(oTarget, hi=True)

        for x in pm.selected():
            x.rename(string.convertRLName(x.name().split("|")[-1]))
        oTarget.rename(string.convertRLName(oSel.name()))
    else:
        pm.displayWarning("Select something before duplicate symmetry.")


def matchWorldXform(*args):
    """Align 2 selected objects in world space"""

    if len(pm.selected()) < 2:
        mgear.log(
            "2 objects or more must be selected. Source and Targets "
            "transform",
            mgear.sev_warning,
        )
    else:
        source = pm.selected()[0]
        for target in pm.selected()[1:]:
            transform.matchWorldTransform(source, target)


def alignToPointsLoop(points=None, loc=None, name=None, *args):
    """Create space locator align to the plain define by at less 3 vertex

    Args:
        points (None or vertex list, optional): The reference vertex to align
            the ref locator
        loc (None or dagNode, optional): If none will create a new locator
        name (None or string, optional): Name of the new locator
        *args: Description

    Returns:
        TYPE: Description

    """
    if not points:
        oSel = pm.selected(fl=True)

        checkType = "<class 'mgear.pymaya.geometry.MeshVertex'>"
        if not oSel or len(oSel) < 3 or str(type(oSel[0])) != checkType:
            pm.displayWarning(
                "We need to select a points loop, with at "
                "less 3 or more points"
            )
            return
        else:
            points = oSel
    if not loc:
        if not name:
            name = "axisCenterRef"
        loc = pm.spaceLocator(n=name)

    oLen = len(points)
    wPos = [0, 0, 0]
    for x in points:
        pos = x.getPosition(space="world")
        wPos[0] += pos[0]
        wPos[1] += pos[1]
        wPos[2] += pos[2]

    centerPosition = datatypes.Vector(
        [wPos[0] / oLen, wPos[1] / oLen, wPos[2] / oLen]
    )

    lookat = datatypes.Vector(points[0].getPosition(space="world"))

    # NORMAL
    a = lookat - centerPosition
    a.normalize()

    nextV = datatypes.Vector(points[1].getPosition(space="world"))
    b = nextV - centerPosition
    b.normalize()
    normal = pmu.cross(b, a)
    normal.normalize()

    trans = transform.getTransformLookingAt(
        centerPosition, lookat, normal, axis="xy", negate=False
    )

    loc.setTransformation(trans)


def connectWorldTransform(source, target):
    """Connect the source world transform of one object to another object.

    Args:
        source (dagNode): Source dagNode.
        target (dagNode): target dagNode.
    """
    mulmat_node = node.createMultMatrixNode(
        source + ".worldMatrix", target + ".parentInverseMatrix"
    )
    dm_node = node.createDecomposeMatrixNode(mulmat_node + ".matrixSum")
    pm.connectAttr(dm_node + ".outputTranslate", target + ".t")
    pm.connectAttr(dm_node + ".outputRotate", target + ".r")
    pm.connectAttr(dm_node + ".outputScale", target + ".s")


def connectLocalTransform(objects=None, s=True, r=True, t=True, *args):
    """Connect scale, rotatio and translation.

    Args:
        objects (None or list of dagNode, optional): If None will use the
            current selection.
        s (bool, optional): If True will connect the local scale
        r (bool, optional): If True will connect the local rotation
        t (bool, optional): If True will connect the local translation
        *args: Maya's dummy
    """
    if objects or len(pm.selected()) >= 2:
        if objects:
            source = objects[0]
            targets = objects[1:]

        else:
            source = pm.selected()[0]
            targets = pm.selected()[1:]

        for target in targets:
            if t:
                pm.connectAttr(
                    source + ".translate", target + ".translate", force=True
                )
            if s:
                pm.connectAttr(
                    source + ".scale", target + ".scale", force=True
                )
            if r:
                pm.connectAttr(
                    source + ".rotate", target + ".rotate", force=True
                )
    else:
        pm.displayWarning("Please at less select 2 objects. Source + target/s")


def connectUserDefinedChannels(source, targets):
    """Connects the user defined channels

    Connects the user defined channels between 2 objects with the same
    channels. Usually a copy of the same object.

    Args:
        source (dagNode): The dagNode with the source user defined channels
        targets (list of dagNode): The list of dagNodes with the same user
            defined channels to be connected.

    """
    udc = source.listAttr(ud=True)
    if not isinstance(targets, list):
        targets = [targets]
    for c in udc:
        for t in targets:
            try:
                pm.connectAttr(c, t.attr(c.name().split(".")[-1]))
            except RuntimeError:
                pm.displayWarning(
                    "%s don't have contrapart channel " "on %s" % (c, t)
                )


def connectInvertSRT(source, target, srt="srt", axis="xyz"):
    """Connect the locat transformations with inverted values.

    Args:
        source (dagNode): The source driver dagNode
        target (dagNode): The target driven dagNode
        srt (string, optional): String value for the scale(s), rotate(r),
            translation(t). Default value is "srt". Posible values "s", "r",
            "t" or any combination
        axis (string, optional):  String value for the axis. Default
            value is "xyz". Posible values "x", "y", "z" or any combination
    """
    for t in srt:
        soureList = []
        invList = []
        targetList = []
        for a in axis:
            soureList.append(source.attr(t + a))
            invList.append(-1)
            targetList.append(target.attr(t + a))

        if soureList:
            node.createMulNode(soureList, invList, targetList)


def replaceShape(source=None, targets=None, *args):
    """Replace the shape of one object by another.

    Args:
        source (None, PyNode): Source object with the original shape.
        targets (None, list of pyNode): Targets object to apply the
            source shape.
        *args: Maya's dummy

    Returns:

        None: Return non if nothing is selected or the source and targets
        are none

    """
    if not source and not targets:
        oSel = pm.selected()
        if len(oSel) < 2:
            pm.displayWarning("At less 2 objects must be selected")
            return None
        else:
            source = oSel[0]
            targets = oSel[1:]

    for target in targets:
        source2 = pm.duplicate(source)[0]
        shape = target.getShapes()
        cnx = []
        if shape:
            cnx = shape[0].listConnections(plugs=True, c=True)
            cnx = [[c[1], c[0].shortName()] for c in cnx]
            # Disconnect the conexion before delete the old shape
            for s in shape:
                for c in s.listConnections(plugs=True, c=True):
                    pm.disconnectAttr(c[0])
        pm.delete(shape)
        pm.parent(source2.getShapes(), target, r=True, s=True)

        for i, sh in enumerate(target.getShapes()):
            # Restore shapes connections
            for c in cnx:
                pm.connectAttr(c[0], sh.attr(c[1]))
            pm.rename(sh, target.name() + "_%s_Shape" % str(i))

        pm.delete(source2)


def matchPosfromBBox(*args):
    """Match the position usin bounding box of another object another.

    Match the position of one object, using the boundig box center of
    another object.

    """
    source = pm.selected()[0]
    target = pm.selected()[1]

    center = meshNavigation.bboxCenter(source, radius=False)

    target.setTranslation(center, space="world")


#######################################
# Gimmicks
#######################################


def spaceJump(ref=None, space=None, *args):
    """Space Jump gimmick

    This function create a local reference space from another space in the
    hierarchy

    Args:
        ref (None, optional): Transform reference
        space (None, optional): Space reference
        *args: Maya dummy

    Returns:
        pyNode: Transform

    """
    if not ref and not space:
        if len(pm.selected()) == 2:
            ref = pm.selected()[0]
            space = pm.selected()[1]
        else:
            pm.displayWarning(
                "Please select 2 objects. Reference Space  " "and Jump Space"
            )
            return

    refLocal = primitive.addTransform(
        ref,
        ref.name() + "_SPACE_" + space.name(),
        space.getMatrix(worldSpace=True),
    )
    spaceLocal = primitive.addTransform(
        space,
        ref.name() + "_JUMP_" + space.name(),
        space.getMatrix(worldSpace=True),
    )

    applyop.gear_mulmatrix_op(
        refLocal.attr("worldMatrix"),
        spaceLocal.attr("parentInverseMatrix[0]"),
        spaceLocal,
    )

    pm.displayInfo("Jump Space for local space: " + space.name() + "created")
    return spaceLocal


def createInterpolateTransform(objects=None, blend=0.5, *args):
    """
    Create space locator and apply gear_intmatrix_op, to interpolate the his
    pose between 2 selected objects.

    Args:
        objects (None or list of 2 dagNode, optional): The 2 dagNode to
            interpolate the transform.
        blend (float, optional): The interpolation blend factor.
        *args: Maya's dummy

    Returns:
        pyNode: The new transformation witht the interpolate matrix o_node
        applied.

    """
    if objects or len(pm.selected()) >= 2:
        if objects:
            refA = objects[0]
            refB = objects[1]

        else:
            refA = pm.selected()[0]
            refB = pm.selected()[1]

        intMatrix = applyop.gear_intmatrix_op(
            refA.attr("worldMatrix"), refB.attr("worldMatrix"), blend
        )
        intTrans = primitive.addTransform(
            refA, refA.name() + "_INTER_" + refB.name(), datatypes.Matrix()
        )

        applyop.gear_mulmatrix_op(
            intMatrix.attr("output"),
            intTrans.attr("parentInverseMatrix[0]"),
            intTrans,
        )

        pm.displayInfo(
            "Interpolated Transform: " + intTrans.name() + " created"
        )
    else:
        pm.displayWarning("Please select 2 objects. ")
        return

    return intTrans


def addBlendedJoint(
    oSel=None, compScale=True, blend=0.5, name=None, select=True, *args
):
    """Create and gimmick blended joint

    Create a joint that rotate 50% of the selected joint. This operation is
    done using a pairBlend node.

    Args:
        oSel (None or joint, optional): If None will use the selected joints.
        compScale (bool, optional): Set the compScale option of the blended
            joint. Default is True.
        blend (float, optional): blend rotation value
        name (None, optional): Name for the blended o_node
        *args: Maya's dummy

    Returns:
        list: blended joints list

    """
    if not oSel:
        oSel = pm.selected()
    elif not isinstance(oSel, list):
        oSel = [oSel]
    jnt_list = []
    for x in oSel:
        if isinstance(x, pm.nodetypes.Joint):
            parent = x.getParent()
            if name:
                bname = "blend_" + name
            else:
                bname = "blend_" + x.name()

            jnt = pm.createNode("joint", n=bname, p=x)
            jnt_list.append(jnt)
            jnt.attr("radius").set(1.5)
            pm.parent(jnt, parent)
            o_node = pm.createNode("pairBlend")
            o_node.attr("rotInterpolation").set(1)
            pm.setAttr(o_node + ".weight", blend)
            pm.connectAttr(x + ".translate", o_node + ".inTranslate1")
            pm.connectAttr(x + ".translate", o_node + ".inTranslate2")
            pm.connectAttr(x + ".rotate", o_node + ".inRotate1")

            pm.connectAttr(o_node + ".outRotateX", jnt + ".rotateX")
            pm.connectAttr(o_node + ".outRotateY", jnt + ".rotateY")
            pm.connectAttr(o_node + ".outRotateZ", jnt + ".rotateZ")

            pm.connectAttr(o_node + ".outTranslateX", jnt + ".translateX")
            pm.connectAttr(o_node + ".outTranslateY", jnt + ".translateY")
            pm.connectAttr(o_node + ".outTranslateZ", jnt + ".translateZ")

            pm.connectAttr(x + ".scale", jnt + ".scale")

            jnt.attr("overrideEnabled").set(1)
            jnt.attr("overrideColor").set(17)

            jnt.attr("segmentScaleCompensate").set(compScale)

            try:
                defSet = pm.PyNode("rig_deformers_grp")

            except TypeError:
                pm.sets(n="rig_deformers_grp")
                defSet = pm.PyNode("rig_deformers_grp")

            pm.sets(defSet, add=jnt)
        else:
            pm.displayWarning(
                "Blended Joint can't be added to: %s. Because "
                "is not ot type Joint" % x.name()
            )

    if jnt_list and select:
        pm.select(jnt_list)

    return jnt_list


def addSupportJoint(oSel=None, select=True, *args):
    """Add an extra joint to the blended joint.

    This is meant to be use with SDK for game style deformation.

    Args:
        oSel (None or blended joint, optional): If None will use the current
            selection.
        *args: Mays's dummy

    Returns:
        list: blended joints list

    """
    if not oSel:
        oSel = pm.selected()
    elif not isinstance(oSel, list):
        oSel = [oSel]

    jnt_list = []
    for x in oSel:
        if x.name().split("_")[0] == "blend":
            children = [
                item
                for item in pm.selected()[0].listRelatives(
                    ad=True, type="joint"
                )
            ]
            i = len(children)
            name = x.name().replace("blend", "blendSupport_%s" % str(i))
            jnt = pm.createNode("joint", n=name, p=x)
            jnt_list.append(jnt)
            jnt.attr("radius").set(1.5)
            jnt.attr("overrideEnabled").set(1)
            jnt.attr("overrideColor").set(17)
            try:
                defSet = pm.PyNode("rig_deformers_grp")

            except pm.MayaNodeError:
                pm.sets(n="rig_deformers_grp")
                defSet = pm.PyNode("rig_deformers_grp")

            pm.sets(defSet, add=jnt)

        else:
            pm.displayWarning(
                "Support Joint can't be added to: %s. Because "
                "is not blend joint" % x.name()
            )

    if jnt_list and select:
        pm.select(jnt_list)

    return jnt_list


def connect_scale_from_world_matrix(driver, driven):
    """
    Set up node connections to make the driven object scale based on the
    driver object's world scale matrix. Accepts either str or PyNode.

    Args:
        driver (str or pm.nodetypes.Transform): Name or PyNode of the
                                                driver object.
        driven (str or pm.nodetypes.Transform): Name or PyNode of the
                                                driven object.

    Example:
        >>> connect_scale_from_world_matrix('driver_cube', 'driven_cube')
        >>> connect_scale_from_world_matrix(pm.PyNode('driver_cube'),
        ...                                 pm.PyNode('driven_cube'))
    """

    # Convert to PyNode if input is str
    if isinstance(driver, str):
        driver = pm.PyNode(driver)
    if isinstance(driven, str):
        driven = pm.PyNode(driven)

    # Create a decomposeMatrix node
    dec_matrix = pm.createNode("decomposeMatrix", name="decomposeMatrix1")

    # Connect the driver's worldMatrix to the decomposeMatrix node
    pm.connectAttr(
        driver.attr("worldMatrix[0]"), dec_matrix.attr("inputMatrix")
    )

    # Connect the decomposeMatrix's outputScale to the driven's scale
    axes = ["X", "Y", "Z"]
    for axis in axes:
        pm.connectAttr(
            dec_matrix.attr("outputScale" + axis), driven.attr("scale" + axis)
        )

# Hide and lock functions


def lock_hide_ctl(ctlList, ctl_ext="_ctl", lock_ext="_lock"):
    """Hide shapes, lock attrs, rename, and remove from object sets.

    Args:
        ctl_list (list): Iterable of controls (MObjects or names).
        ctl_ext (str, optional): Suffix to replace. Defaults to "_ctl".
        lock_ext (str, optional): Replacement suffix. Defaults to "_lock".
    """

    for ctl in ctlList:
        try:
            if isinstance(ctl, str):
                ctl = pm.PyNode(ctl)
            # Hide shapes
            for shape in ctl.getShapes():
                shape.visibility.set(False)
            # lock ctl attr
            attribute.lockAttribute(ctl)
            pm.rename(ctl, ctl.name().replace(ctl_ext, lock_ext))

            # remove from grp
            grps = ctl.listConnections(t="objectSet")
            for grp in grps:
                grp.remove(ctl)
        except:
            print("{}: not found".format(ctl))


def show_hide_toggle(ctl, at_name, groupA, groupB, keyable=False):
    """Create boolean attr on ctl to toggle visibility of two groups.

    Args:
        ctl (pm.DagNode|str): Control node or its name.
        attr_name (str): Name of the toggle attribute to create.
        group_a (list): Nodes visible when attr is True.
        group_b (list): Nodes visible when attr is False.
    """

    # create attr
    ctl = pm.PyNode(ctl)
    at = attribute.addAttribute(ctl, at_name, "bool", value=True, keyable=keyable)

    # connect visibility group A
    for x in groupA:
        pm.connectAttr(at, x + ".visibility")

    # reverse note
    rever = node.createReverseNode(at)

    # connect visibility group B
    for x in groupB:
        pm.connectAttr(rever.outputX, x + ".visibility")


def hide_shape(obj_list, attr_name, attr_host, val=True, keyable=False):
    """Hide shapes of given nodes using a host boolean attribute.

    Args:
        obj_list (list): Nodes (or names) whose shapes will be hidden.
        attr_name (str): Attribute name to create/use on the host.
        attr_host (pm.DependNode|str): Node holding the attribute.
        val (bool, optional): Initial value. Defaults to True.
    """

    if not attr_host.hasAttr(attr_name):
        attrHide = attribute.addAttribute(
            attr_host, attr_name, "bool", val, keyable=keyable
        )
    else:
        attrHide = attr_host.attr(attr_name)

    for ctl in obj_list:
        if isinstance(ctl, str):
            ctl = pm.PyNode(ctl)
        for shape in ctl.getShapes():
            if not shape.visibility.isConnected():
                pm.connectAttr(attrHide, shape.visibility)


def hide_transform(transform_list, attr_name, attr_host, val=True, keyable=False):
    """Hide transform nodes using a host boolean attribute.

    Args:
        transform_list (list): Transform nodes (or names) to hide.
        attr_name (str): Attribute name to create/use on the host.
        attr_host (pm.DependNode|str): Node holding the attribute.
        val (bool, optional): Initial value. Defaults to True.
    """

    if not attr_host.hasAttr(attr_name):
        attrHide = attribute.addAttribute(
            attr_host, attr_name, "bool", val, keyable=keyable
        )
    else:
        attrHide = attr_host.attr(attr_name)

    for part in transform_list:
        if isinstance(part, str):
            part = pm.PyNode(part)
        if not part.visibility.isConnected():
            pm.connectAttr(attrHide, part.visibility)
