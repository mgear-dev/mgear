"""循环调整模块

此模块包含用于装配具有良性循环的调整的工具和程序
"""
import mgear.pymaya as pm
import mgear.pymaya.datatypes as datatypes

from mgear.core import icon, skin, node
from mgear import rigbits
from mgear.rigbits import rivet, blendShapes


def inverseTranslateParent(obj):
    """反转父级变换

    参数：
        obj (dagNode): 要反转父级变换的源 dagNode。
    """
    if not isinstance(obj, list):
        obj = [obj]
    for x in obj:
        node.createMulNode([x.attr("tx"), x.attr("ty"), x.attr("tz")],
                           [-1, -1, -1],
                           [x.getParent().attr("tx"),
                            x.getParent().attr("ty"),
                            x.getParent().attr("tz")])


def initCycleTweakBase(outMesh, baseMesh, rotMesh, transMesh, staticJnt=None):
    """初始化循环调整设置结构

    参数：
        outMesh (Mesh): 调整变形后的输出网格。
        baseMesh (Mesh): 循环调整的基础网格。
        rotMesh (Mesh): 将支持旋转变换的网格。
        transMesh (Mesh): 将支持平移和缩放变换的网格。
        staticJnt (None 或 joint, 可选): 静态顶点的静态关节。
    """
    blendShapes.connectWithBlendshape(rotMesh, baseMesh)
    blendShapes.connectWithBlendshape(transMesh, rotMesh)
    blendShapes.connectWithBlendshape(outMesh, transMesh)

    # Init skinClusters
    pm.skinCluster(staticJnt,
                   rotMesh,
                   tsb=True,
                   nw=2,
                   n='%s_skinCluster' % rotMesh.name())
    pm.skinCluster(staticJnt,
                   transMesh,
                   tsb=True,
                   nw=2,
                   n='%s_skinCluster' % transMesh.name())


def cycleTweak(name,
               edgePair,
               mirrorAxis,
               baseMesh,
               rotMesh,
               transMesh,
               setupParent,
               ctlParent,
               jntOrg=None,
               grp=None,
               iconType="square",
               size=.025,
               color=13,
               ro=datatypes.Vector(1.5708, 0, 1.5708 / 2)):
    """创建循环调整的命令。

    循环调整是一种调整，它循环到父级位置，但不会
    创建依赖关系循环。这种类型的调整对于创建面部调整器非常有用。

    参数：
        name (string): 循环调整的名称。
        edgePair (list): 要附加循环调整的边对列表。
        mirrorAxis (bool): 如果为 true，将镜像 x 轴行为。
        baseMesh (Mesh): 循环调整的基础网格。
        rotMesh (Mesh): 将支持旋转变换的网格。
        transMesh (Mesh): 将支持平移和缩放变换的网格。
        setupParent (dagNode): 设置对象的父级。
        ctlParent (dagNode): 控制对象的父级。
        jntOrg (None 或 dagNode, 可选): 关节的父级。
        grp (None 或 set, 可选): 要添加控件的集合。
        iconType (str, 可选): 控件形状。
        size (float, 可选): 控件大小。
        color (int, 可选): 控件颜色。
        ro (TYPE, 可选): 控件形状旋转偏移。

    返回：
        multi: 调整控件和相关关节列表。
    """
    # rotation sctructure
    rRivet = rivet.rivet()
    rBase = rRivet.create(
        baseMesh, edgePair[0], edgePair[1], setupParent, name + "_rRivet_loc")

    pos = rBase.getTranslation(space="world")

    # translation structure
    tRivetParent = pm.createNode("transform",
                                 n=name + "_tRivetBase",
                                 p=ctlParent)
    tRivetParent.setMatrix(datatypes.Matrix(), worldSpace=True)
    tRivet = rivet.rivet()
    tBase = tRivet.create(transMesh,
                          edgePair[0],
                          edgePair[1],
                          tRivetParent,
                          name + "_tRivet_loc")

    # create the control
    tweakBase = pm.createNode("transform", n=name + "_tweakBase", p=ctlParent)
    tweakBase.setMatrix(datatypes.Matrix(), worldSpace=True)
    tweakNpo = pm.createNode("transform", n=name + "_tweakNpo", p=tweakBase)
    tweakBase.setTranslation(pos, space="world")
    tweakCtl = icon.create(tweakNpo,
                           name + "_ctl",
                           tweakNpo.getMatrix(worldSpace=True),
                           color,
                           iconType,
                           w=size,
                           d=size,
                           ro=ro)
    inverseTranslateParent(tweakCtl)
    pm.pointConstraint(tBase, tweakBase)

    # rot
    rotBase = pm.createNode("transform", n=name + "_rotBase", p=setupParent)
    rotBase.setMatrix(datatypes.Matrix(), worldSpace=True)
    rotNPO = pm.createNode("transform", n=name + "_rot_npo", p=rotBase)
    rotJointDriver = pm.createNode("transform",
                                   n=name + "_rotJointDriver",
                                   p=rotNPO)
    rotBase.setTranslation(pos, space="world")

    node.createMulNode([rotNPO.attr("tx"),
                        rotNPO.attr("ty"),
                        rotNPO.attr("tz")],
                       [-1, -1, -1],
                       [rotJointDriver.attr("tx"),
                        rotJointDriver.attr("ty"),
                        rotJointDriver.attr("tz")])

    pm.pointConstraint(rBase, rotNPO)
    pm.connectAttr(tweakCtl.r, rotNPO.r)
    pm.connectAttr(tweakCtl.s, rotNPO.s)

    # transform
    posNPO = pm.createNode("transform", n=name + "_pos_npo", p=setupParent)
    posJointDriver = pm.createNode("transform",
                                   n=name + "_posJointDriver",
                                   p=posNPO)
    posNPO.setTranslation(pos, space="world")
    pm.connectAttr(tweakCtl.t, posJointDriver.t)

    # mirror behaviour
    if mirrorAxis:
        tweakBase.attr("ry").set(tweakBase.attr("ry").get() + 180)
        rotBase.attr("ry").set(rotBase.attr("ry").get() + 180)
        posNPO.attr("ry").set(posNPO.attr("ry").get() + 180)
        tweakBase.attr("sz").set(-1)
        rotBase.attr("sz").set(-1)
        posNPO.attr("sz").set(-1)

    # create joints
    rJoint = rigbits.addJnt(rotJointDriver, jntOrg, True, grp)
    tJoint = rigbits.addJnt(posJointDriver, jntOrg, True, grp)

    # add to rotation skin
    # TODO: add checker to see if joint is in the skincluster.
    rSK = skin.getSkinCluster(rotMesh)
    pm.skinCluster(rSK, e=True, ai=rJoint, lw=True, wt=0)

    # add to transform skin
    # TODO: add checker to see if joint is in the skincluster.
    tSK = skin.getSkinCluster(transMesh)
    pm.skinCluster(tSK, e=True, ai=tJoint, lw=True, wt=0)

    return tweakCtl, [rJoint, tJoint]
