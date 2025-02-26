"""Rigbits Ghost module

Helper tools to create layered controls rigs
"""
import mgear.pymaya as pm

from mgear.core import node, primitive
from mgear import rigbits
from .six import string_types


def connect_matching_attrs(
    driver, driven, attr_list=["compRoot", "uiHost_cnx"]
):
    """
    Connect matching attributes from driven to driver node if they exist and have inputs.

    Args:
        driver (pm.PyNode): The driver PyNode transform.
        driven (pm.PyNode): The driven PyNode transform.
        attr_list (list): List of attribute names to check and connect. Default is ["compRoot", "uiHost_cnx"].

    Returns:
        None
    """
    for attr_name in attr_list:
        # Check if the driven node has the attribute
        if pm.hasAttr(driven, attr_name):
            # Check if the driver node has the attribute
            if pm.hasAttr(driver, attr_name):
                # Check if the attribute on the driven node has any inputs
                inputs = pm.listConnections(
                    driven.attr(attr_name), s=True, p=True
                )
                if inputs:
                    # Connect the same inputs to the driver node
                    for inp in inputs:
                        pm.connectAttr(inp, driver.attr(attr_name))


def createGhostCtl(ctl, parent=None, connect=True):
    """Create a duplicated Ghost control

    Create a duplicate of the control and rename the original with _ghost.
    Later connect the local transforms and the Channels.
    This is useful to connect local rig controls with the final rig control.

    Args:
        ctl (dagNode): Original Control to duplicate
        parent (dagNode): Parent for the new created control

    Returns:
       pyNode: The new created control

    """
    if isinstance(ctl, string_types):
        ctl = pm.PyNode(ctl)
    if parent:
        if isinstance(parent, string_types):
            parent = pm.PyNode(parent)
    grps = ctl.listConnections(t="objectSet")
    for grp in grps:
        grp.remove(ctl)
    oName = ctl.name()
    pm.rename(ctl, oName + "_ghost")
    newCtl = pm.duplicate(ctl, po=True)[0]
    pm.rename(newCtl, oName)
    source2 = pm.duplicate(ctl)[0]
    for shape in source2.getShapes():
        pm.parent(shape, newCtl, r=True, s=True)
        pm.rename(shape, newCtl.name() + "Shape")
    pm.delete(source2)
    if parent:
        pm.parent(newCtl, parent)
        oTra = pm.createNode(
            "transform", n=newCtl.name() + "_npo", p=parent, ss=True
        )
        oTra.setMatrix(
            ctl.getParent().getMatrix(worldSpace=True), worldSpace=True
        )
        pm.parent(newCtl, oTra)
    if connect:
        rigbits.connectLocalTransform([newCtl, ctl])
        rigbits.connectUserDefinedChannels(newCtl, ctl)
        connect_matching_attrs(newCtl, ctl)
    for grp in grps:
        grp.add(newCtl)

    # add control tag
    node.add_controller_tag(newCtl, parent)

    return newCtl


def createDoritoGhostCtl(ctl, parent=None):
    """Create a duplicated Ghost control for doritos
    Create a duplicate of the dorito/tweak and rename the original with _ghost.
    Later connect the local transforms and the Channels.
    This is useful to connect local rig controls with the final rig control.

    Args:
        ctl (dagNode): Original Control to duplicate
        parent (dagNode): Parent for the new created control

    """
    if isinstance(ctl, string_types):
        ctl = pm.PyNode(ctl)
    if parent:
        if isinstance(parent, string_types):
            parent = pm.PyNode(parent)
    doritoCtl = createGhostCtl(ctl, parent)
    doritoParent = doritoCtl.getParent()
    ghostBaseParent = ctl.getParent(2)
    oTra = pm.createNode(
        "transform",
        n=ghostBaseParent.name() + "_npo",
        p=ghostBaseParent.getParent(),
        ss=True,
    )

    oTra.setTransformation(ghostBaseParent.getMatrix())
    pm.parent(ghostBaseParent, oTra)
    oTra = pm.createNode(
        "transform",
        n=doritoParent.name() + "_npo",
        p=doritoParent.getParent(),
        ss=True,
    )
    oTra.setTransformation(doritoParent.getMatrix())
    pm.parent(doritoParent, oTra)

    rigbits.connectLocalTransform(ghostBaseParent, doritoParent)
    rigbits.connectUseDefinedChannels(ghostBaseParent, doritoParent)


def ghostSlider(ghostControls, surface, sliderParent):
    """Modify the ghost control behaviour to slide on top of a surface

    Args:
        ghostControls (dagNode): The ghost control
        surface (Surface): The NURBS surface
        sliderParent (dagNode): The parent for the slider.
    """
    if not isinstance(ghostControls, list):
        ghostControls = [ghostControls]

    # Seleccionamos los controles Ghost que queremos mover sobre el surface

    surfaceShape = surface.getShape()

    for ctlGhost in ghostControls:
        ctl = pm.listConnections(ctlGhost, t="transform")[-1]
        t = ctl.getMatrix(worldSpace=True)

        gDriver = primitive.addTransform(
            ctlGhost.getParent(), ctl.name() + "_slideDriver", t
        )

        try:
            pm.connectAttr(ctl + ".translate", gDriver + ".translate")
            pm.disconnectAttr(ctl + ".translate", ctlGhost + ".translate")
        except RuntimeError:
            pass

        try:
            pm.connectAttr(ctl + ".scale", gDriver + ".scale")
            pm.disconnectAttr(ctl + ".scale", ctlGhost + ".scale")
        except RuntimeError:
            pass

        try:
            pm.connectAttr(ctl + ".rotate", gDriver + ".rotate")
            pm.disconnectAttr(ctl + ".rotate", ctlGhost + ".rotate")
        except RuntimeError:
            pass

        oParent = ctlGhost.getParent()
        npoName = "_".join(ctlGhost.name().split("_")[:-1]) + "_npo"
        oTra = pm.PyNode(
            pm.createNode("transform", n=npoName, p=oParent, ss=True)
        )
        oTra.setTransformation(ctlGhost.getMatrix())
        pm.parent(ctlGhost, oTra)

        slider = primitive.addTransform(
            sliderParent, ctl.name() + "_slideDriven", t
        )

        # connexion

        dm_node = node.createDecomposeMatrixNode(
            gDriver.attr("worldMatrix[0]")
        )
        cps_node = pm.createNode("closestPointOnSurface")
        dm_node.attr("outputTranslate") >> cps_node.attr("inPosition")
        surfaceShape.attr("worldSpace[0]") >> cps_node.attr("inputSurface")
        cps_node.attr("position") >> slider.attr("translate")

        pm.normalConstraint(
            surfaceShape,
            slider,
            aimVector=[0, 0, 1],
            upVector=[0, 1, 0],
            worldUpType="objectrotation",
            worldUpVector=[0, 1, 0],
            worldUpObject=gDriver,
        )

        pm.parent(ctlGhost.getParent(), slider)
