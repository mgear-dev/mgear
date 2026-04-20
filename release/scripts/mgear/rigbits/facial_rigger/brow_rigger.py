# Original design Krzysztof Marcinowski
import json
from functools import partial
string_types = str


import mgear.core.pyqt as gqt
import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.pymaya import datatypes

from mgear import rigbits
from mgear.core import meshNavigation, curve, applyop, primitive, icon
from mgear.core import transform, attribute, skin, pickWalk, vector
from mgear.core import node

from mgear.rigbits.facial_rigger import lib
from mgear.rigbits.facial_rigger import helpers
from mgear.rigbits.facial_rigger import constraints


def rig(edge_loop,
        name_prefix,
        thickness,
        main_div,
        sec_div,
        do_skin,
        secondary_ctl_check,
        symmetry_mode,
        side,
        rigid_loops,
        falloff_loops,
        brow_jnt_C=None,
        brow_jnt_L=None,
        brow_jnt_R=None,
        ctl_parent_C=None,
        ctl_parent_L=None,
        ctl_parent_R=None,
        parent_node=None,
        ctl_name="ctl"):

    ######
    # Var
    ######
    FRONT_OFFSET = .02
    NB_ROPE = 10
    midDivisions = 3

    ####################
    # Validate Data
    # ##################
    edge_loops = {}  # collect edge loops and it's sides in DICT
    controls_collect = []  # collect parent controls
    joints_collect = []  # collect parent joints

    # divisions
    main_div = int(main_div)
    sec_div = int(sec_div)
    # Edges

    if edge_loop:
        try:
            edge_loop = [pm.PyNode(e) for e in edge_loop.split(",")]
        except RuntimeError:
            pm.displayWarning(
                "Some of the edges listed in edge loop can not be found")
            return
    # Geo
        geo = pm.listRelatives(edge_loop[0], parent=True)[0]
        geoTransform = pm.listRelatives(geo, fullPath=False, parent=True)[0]

    else:
        pm.displayWarning("Please set the edge loop first")
        return

    # symmetry mode
    # 0 => ON  1 = > OFF
    if symmetry_mode == 0:
        # symmetry is on, collect required data
        # mirror edge loop
        mLoop = []
        for edge in edge_loop:
            mEdge = meshNavigation.find_mirror_edge(geoTransform,
                                                    edge.indices()[0])
            mLoop.append(mEdge)

        if len(mLoop) != len(edge_loop):
            pm.displayWarning(
                "Mesh is not symmetrical, please fix it or create temp GEO")
            return

        # set side
        if edge_loop[0].getPoint(0, space='world')[0] > 0:
            # left
            side = "L"
            l_Loop = edge_loop
            r_Loop = mLoop
        else:
            # right
            side = "R"
            l_Loop = mLoop
            r_Loop = edge_loop

        # get edges for center module
        p1 = l_Loop[0].getPoint(0, space='world')
        p2 = l_Loop[-1].getPoint(0, space='world')
        if p1[0] < p2[0]:
            l_inner = l_Loop[0]
        else:
            l_inner = l_Loop[-1]
        p1 = r_Loop[0].getPoint(0, space='world')
        p2 = r_Loop[-1].getPoint(0, space='world')

        if p1[0] > p2[0]:
            r_inner = r_Loop[0]
        else:
            r_inner = r_Loop[-1]

        # center segment
        # TODO: this does not always work depending geometry
        mid_loop = pm.polySelect(
            geoTransform,
            edgeLoopPath=(l_inner.indices()[0],
                          r_inner.indices()[0]),
            ass=True,
            ns=True)
        if not mid_loop:
            pm.displayError(
                "Mid loop can't be traced. Probably the topology"
                " have a vertex with 5 edges or more in the loop")
            return
        mid_loop_len = len(mid_loop)
        c_Loop = [pm.PyNode(e) for e in mid_loop
                  if pm.PyNode(e) not in l_Loop and pm.PyNode(e) not in r_Loop]
        edge_loops = dict(zip(["L", "R", "C"], [l_Loop, r_Loop, c_Loop]))

    else:
        # symmetry is off
        sideOptions = {0: "C",
                       1: "L",
                       2: "R"}
        if side:
            side = sideOptions[side]
        else:
            side = "C"
        # set
        c_Loop = edge_loop
        edge_loops = dict(zip([side], [c_Loop]))
    positions = meshNavigation.getExtremeVertexFromLoop(edge_loop)
    p1 = positions[2].getPosition(space='world')
    p2 = positions[3].getPosition(space='world')
    self_size = vector.getDistance(p1, p2) / sec_div

    # parent node
    if parent_node:
        try:
            parent_node = pm.PyNode(parent_node)
        except RuntimeError:
            pm.displayWarning(
                "Static rig parent: %s can not be found" % parent_node)
            return

    if brow_jnt_C:
        try:
            brow_jnt_C = pm.PyNode(brow_jnt_C)
            joints_collect.append(brow_jnt_C)
        except RuntimeError:
            pm.displayWarning(
                "Mid parent joint: %s can not be found" % brow_jnt_C)
            return
    else:
        pm.displayWarning("Main parent joints is required. It would be used"
                          " as main parent if side parents are not set.")
        return

    if symmetry_mode == 0:
        if brow_jnt_L:
            try:
                brow_jnt_L = pm.PyNode(brow_jnt_L)
                joints_collect.append(brow_jnt_L)
            except RuntimeError:
                pm.displayWarning(
                    "Left parent joint: %s can not be found" % brow_jnt_L)
                return
        else:
            pm.displayWarning(
                "With symmetry mode you need to set the left parent joint.")
            return

        if brow_jnt_R:
            try:
                brow_jnt_R = pm.PyNode(brow_jnt_R)
                joints_collect.append(brow_jnt_R)
            except RuntimeError:
                pm.displayWarning(
                    "Right parent joint: %s can not be found." % brow_jnt_R)
                return
        else:
            try:
                brow_jnt_R = pickWalk.getMirror(brow_jnt_L)[0]
                joints_collect.append(brow_jnt_R)
            except RuntimeError:
                pm.displayWarning(
                    "Right parent joint: "
                    "%s can't be found. Please set it manually." % brow_jnt_R)
                return

    ##################
    # Helper functions
    # ##################

    def setName(name, side="C", idx=None):
        namesList = [name_prefix, side, name]
        if idx is not None:
            namesList[1] = side + str(idx)
        name = "_".join(namesList)
        return name

    def getSide(name):
        # name = name.strip(name_prefix)

        if name_prefix + "_L_" in name.name():
            side = "L"
        elif name_prefix + "_R_" in name.name():
            side = "R"
        else:
            side = "C"
        return side

    # check if the rig already exist in the current scene
    if pm.ls(setName("root", side)):
        pm.displayWarning("The object %s already exist in the scene. Please "
                          "choose another name prefix" % setName("root"))
        return

    ###################
    # Root creation
    ###################
    if symmetry_mode == 0:
        rootSide = "C"
    else:
        rootSide = side
    brows_root = primitive.addTransform(None,
                                        setName("root", rootSide))
    browsCrv_root = primitive.addTransform(brows_root,
                                           setName("crvs", "main"))
    browsHooks_root = primitive.addTransform(brows_root,
                                             setName("hooks", rootSide))
    browsRope_root = primitive.addTransform(brows_root,
                                            setName("rope", rootSide))
    browsControl_root = primitive.addTransform(brows_root,
                                               setName("controls", rootSide))

    # parent controls
    if ctl_parent_L:
        try:
            ctl_parent_L = pm.PyNode(ctl_parent_L)
            controls_collect.append(ctl_parent_L)
            parent_tag_L = ctl_parent_L
        except RuntimeError:
            pm.displayWarning(
                "Right (Left) ctl: %s can not be found" % ctl_parent_L)
            return
    else:
        # ctl_parent_L = brow_jnt_L
        ctl_parent_L = brows_root
        parent_tag_L = None

    if ctl_parent_R:
        try:
            ctl_parent_R = pm.PyNode(ctl_parent_R)
            controls_collect.append(ctl_parent_R)
            parent_tag_R = ctl_parent_R
        except RuntimeError:
            pm.displayWarning(
                "Right ctl: %s can not be found" % ctl_parent_R)
            return
    else:
        # ctl_parent_R = brow_jnt_R
        ctl_parent_R = brows_root
        parent_tag_R = None

    if ctl_parent_C:
        try:
            ctl_parent_C = pm.PyNode(ctl_parent_C)
            controls_collect.append(ctl_parent_C)
            parent_tag_C = ctl_parent_C
        except RuntimeError:
            pm.displayWarning(
                "Main ctl: %s can not be found" % ctl_parent_R)
            return
    else:
        # ctl_parent_R = brow_jnt_R
        ctl_parent_C = brows_root
        parent_tag_C = None

    if symmetry_mode == 0:
        if ctl_parent_R:
            try:
                ctl_parent_R = pm.PyNode(ctl_parent_R)
                controls_collect.append(ctl_parent_R)
                parent_tag_R = ctl_parent_R
            except RuntimeError:
                pm.displayWarning(
                    "Right ctl: %s can not be found" % ctl_parent_R)
                return
        else:
            # ctl_parent_R = brow_jnt_R
            ctl_parent_R = brows_root
            parent_tag_R = None

    #####################
    # Groups
    #####################
    # TODO: the set name should not be hardcoded to "rig" name
    try:
        ctlSet = pm.PyNode("rig_controllers_grp")
    except RuntimeError:
        pm.sets(n="rig_controllers_grp", em=True)
        ctlSet = pm.PyNode("rig_controllers_grp")
    try:
        defset = pm.PyNode("rig_deformers_grp")
    except RuntimeError:
        pm.sets(n="rig_deformers_grp", em=True)
        defset = pm.PyNode("rig_deformers_grp")

    # ###################
    # Collect data
    #####################
    # store the closest vertex by curv cv index. To be use fo the auto skining
    # browsMainCrv_closestVtxList = []

    # temp parent memory
    # parentsMemory = []
    l_hookMem = []
    r_hookMem = []
    c_hookMem = []

    # collect curves
    rigCurves = []
    mainCtlCurves = []
    mainCtlUpvs = []
    secondaryCurves = []
    mainRopes = []
    mainRopeUpvs = []
    mainCurveUpvs = []
    mainCurves = []

    # collect objects
    mainControls = []
    mainUpvs = []
    secondaryControls = []
    secondaryUpvs = []
    allJoints = []
    closestVtxsList = []

    # ###############################
    # Create curves and controls
    #################################
    for side, loop in edge_loops.items():

        browsCrv_side_root = primitive.addTransform(browsCrv_root,
                                                    setName("crvs", side))

        # create poly based curve for each part
        mainCurve = curve.createCuveFromEdges(loop,
                                              setName("main_crv", side),
                                              parent=browsCrv_side_root)
        # collect main poly based curve
        mainCurves.append(mainCurve)
        rigCurves.append(mainCurve)

        # offset main brow curve
        # NOTE Miquel: we dont need to offset here. The offset was for the lips
        # because have thickness. Here  is not needed
        cvs = mainCurve.getCVs(space='world')
        for i, cv in enumerate(cvs):
            closestVtx = meshNavigation.getClosestVertexFromTransform(geo, cv)
            closestVtxsList.append(closestVtx)

        # ###################
        # Get control positions
        #####################
        if symmetry_mode == 0:  # 0 means ON
            if side == "C":  # middle segment should be divided into 3 points.
                mainCtrlPos = helpers.divideSegment(mainCurve, midDivisions)
                # since the central part is process first we usen the main list
                # to slice repeted vertex
                closestVtxsList = closestVtxsList[1:mid_loop_len - 1]
            else:
                mainCtrlPos = helpers.divideSegment(mainCurve, main_div)
            if secondary_ctl_check and side != "C":
                # get secondary controls position
                secCtrlPos = helpers.divideSegment(mainCurve, sec_div)

        else:

            mainCtrlPos = helpers.divideSegment(mainCurve, main_div)
            if secondary_ctl_check:
                # get secondary controls position

                secCtrlPos = helpers.divideSegment(mainCurve, sec_div)
        # ###################
        # Set control options
        #####################
        # points are sorted from X+, based on this set required options
        mainCtrlOptions = []
        secCtrlOptions = []

        # main control options
        for i, ctlPos in enumerate(mainCtrlPos):
            controlType = "square"

            if i == 0:
                if side == "L":
                    posPrefix = "in"
                if side == "R":
                    posPrefix = "out"
                if side == "C":
                    posPrefix = "out_R"
                    if symmetry_mode == 0:
                        controlType = "npo"

            elif i == (len(mainCtrlPos) - 1):
                if side == "L":
                    posPrefix = "out"
                if side == "R":
                    posPrefix = "in"
                if side == "C":
                    posPrefix = "out_L"
                    if symmetry_mode == 0:
                        controlType = "npo"
            else:
                posPrefix = "mid_0" + str(i)
                if side == "R":
                    posPrefix = "mid_0" + str(len(mainCtrlPos) - (i + 1))
            set_options = False  # when mirror is set we need to avoid the
            # tanget controls on the central part

            if posPrefix == "in" or posPrefix == "out_R":
                if side == "L":
                    tPrefix = [posPrefix + "_tangent", posPrefix]
                    tControlType = ["sphere", controlType]
                    tControlSize = [0.8, 1.0]
                    set_options = True
                if side == "C" and symmetry_mode:
                    tPrefix = ["out_R_tangent", posPrefix]
                    tControlType = ["sphere", controlType]
                    tControlSize = [0.8, 1.0]
                    set_options = True
                if side == "R":
                    tPrefix = [posPrefix, posPrefix + "_tangent"]
                    tControlType = [controlType, "sphere"]
                    tControlSize = [1.0, 0.8]
                    set_options = True
                if set_options:
                    options = [tPrefix[1],
                               side,
                               tControlType[1],
                               6,
                               tControlSize[1],
                               [],
                               ctlPos]
                    mainCtrlOptions.append(options)

                    options = [tPrefix[0],
                               side,
                               tControlType[0],
                               6,
                               tControlSize[0],
                               [],
                               ctlPos]
                    mainCtrlOptions.append(options)

            elif posPrefix == "out" or posPrefix == "out_L":
                if side == "L":
                    tPrefix = [posPrefix + "_tangent", posPrefix]
                    tControlType = ["sphere", controlType]
                    tControlSize = [0.8, 1.0]
                    set_options = True
                if side == "C" and symmetry_mode:
                    tPrefix = ["out_L_tangent", posPrefix]
                    tControlType = ["sphere", controlType]
                    tControlSize = [0.8, 1.0]
                    set_options = True
                if side == "R":
                    tPrefix = [posPrefix, posPrefix + "_tangent"]
                    tControlType = [controlType, "sphere"]
                    tControlSize = [1.0, 0.8]
                    set_options = True
                if set_options:
                    options = [tPrefix[0],
                               side,
                               tControlType[0],
                               6,
                               tControlSize[0],
                               [],
                               ctlPos]
                    mainCtrlOptions.append(options)
                    options = [tPrefix[1],
                               side,
                               tControlType[1],
                               6,
                               tControlSize[1],
                               [],
                               ctlPos]
                    mainCtrlOptions.append(options)

            else:
                options = [posPrefix,
                           side,
                           controlType,
                           6,
                           1.0,
                           [],
                           ctlPos]
                mainCtrlOptions.append(options)

            if controlType == "npo":
                options = [posPrefix,
                           side,
                           controlType,
                           6,
                           1.0,
                           [],
                           ctlPos]
                mainCtrlOptions.append(options)

        # secondary control options
        if secondary_ctl_check:
            if symmetry_mode == 0:  # 0 means ON
                secSideRange = "LR"
            else:
                secSideRange = "CLR"

            if side in secSideRange:
                sec_number_index = len(secCtrlPos) - 1
                controlType = "circle"
                for i, ctlPos in enumerate(secCtrlPos):
                    # invert the index naming only.
                    # if the full list is inver we generate another issues
                    if side == "R":
                        i_name = sec_number_index - i
                    else:
                        i_name = i
                    posPrefix = "sec_" + str(i_name).zfill(2)
                    options = [posPrefix,
                               side,
                               controlType,
                               13,
                               0.55,
                               [],
                               ctlPos]
                    secCtrlOptions.append(options)

        params = ["tx", "ty", "tz"]
        # TODO: Is this a constant? Magic number ??
        distSize = 1
        if secondary_ctl_check:
            controlOptionList = [mainCtrlOptions, secCtrlOptions]
        else:
            controlOptionList = [mainCtrlOptions]

        # ###################
        # Create controls from option lists.
        #####################
        localCtlList = []
        localSecCtlList = []
        # TODO: why is using test name for parent controls?
        for j, ctlOptions in enumerate(controlOptionList):
            # set status for main controllers
            if j == 0:
                testName = setName("mainControls")
                controlStatus = 0  # main controls
                try:
                    controlParentGrp = pm.PyNode(testName)
                except:
                    controlParentGrp = primitive.addTransform(
                        browsControl_root, setName("mainControls"))
            # set status for secondary controllers
            else:
                testName = setName("secondaryControls")
                controlStatus = 1  # secondary controls
                try:
                    controlParentGrp = pm.PyNode(testName)
                except:
                    controlParentGrp = primitive.addTransform(
                        browsControl_root, setName("secondaryControls"))

            # Create controls for each point position.
            for i, point in enumerate(ctlOptions):
                pm.progressWindow(e=True,
                                  step=1,
                                  status='\nCreating control for%s' % point)
                oName = ctlOptions[i][0]
                oSide = ctlOptions[i][1]
                o_icon = ctlOptions[i][2]
                color = ctlOptions[i][3]
                wd = ctlOptions[i][4]
                oPar = ctlOptions[i][5]
                point = ctlOptions[i][6]

                position = transform.getTransformFromPos(point)
                npo = primitive.addTransform(controlParentGrp,
                                             setName("%s_npo" % oName, oSide),
                                             position)

                npoBuffer = primitive.addTransform(
                    npo,
                    setName("%s_bufferNpo" % oName, oSide),
                    position)
                # Create casual control
                if o_icon != "npo":
                    if o_icon == "sphere":
                        rot_offset = None
                    else:
                        rot_offset = datatypes.Vector(1.57079633, 0, 0)

                    ctl = icon.create(
                        npoBuffer,
                        setName("%s_%s" % (oName, ctl_name), oSide),
                        position,
                        icon=o_icon,
                        w=wd * self_size,
                        d=wd * self_size,
                        ro=rot_offset,
                        po=datatypes.Vector(0, 0, .07 * distSize),
                        color=color)
                    attribute.addAttribute(ctl, "isCtl", "bool", keyable=False)
                # Create buffer node instead
                else:
                    ctl = primitive.addTransform(
                        npoBuffer,
                        setName("%s_HookNpo" % oName, oSide),
                        position)

                cname_split = ctl_name.split("_")
                if len(cname_split) == 2 and cname_split[-1] == "ghost":
                    pass
                else:
                    pm.sets(ctlSet, add=ctl)
                attribute.setKeyableAttributes(ctl, params + oPar)

                # Create up vectors for each control
                upv = primitive.addTransform(ctl,
                                             setName("%s_upv" % oName, oSide),
                                             position)
                upv.attr("tz").set(FRONT_OFFSET)

                # Collect local (per curve) and global controllers list
                if controlStatus == 0:
                    mainControls.append(ctl)
                    mainUpvs.append(upv)
                    localCtlList.append(ctl)

                if controlStatus == 1:
                    secondaryControls.append(ctl)
                    secondaryUpvs.append(upv)
                    localSecCtlList.append(ctl)

                if oSide == "R":
                    npo.attr("sx").set(-1)

                # collect hook npos'
                if side == "L" and "in" in oName:
                    l_hookMem.append(ctl)
                if side == "R" and "in" in oName:
                    r_hookMem.append(ctl)
                if side == "C":
                    c_hookMem.append(ctl)

            pm.progressWindow(e=True, endProgress=True)

            #####################
            # Curves creation
            #####################
            crv_degree = 2

            if controlStatus == 0:  # main controls
                mainCtlCurve = helpers.addCnsCurve(
                    browsCrv_side_root,
                    setName("mainCtl_crv", side),
                    localCtlList,
                    crv_degree)
                rigCurves.append(mainCtlCurve[0])
                mainCtlCurves.append(mainCtlCurve[0])

                # create upvector curve to drive secondary control
                if secondary_ctl_check:
                    if side in secSideRange:
                        mainCtlUpv = helpers.addCurve(
                            browsCrv_side_root,
                            setName("mainCtl_upv", side),
                            localCtlList,
                            crv_degree)
                        # connect upv curve to mainCrv_ctl driver node.
                        pm.connectAttr(
                            mainCtlCurve[1].attr("outputGeometry[0]"),
                            mainCtlUpv.getShape().attr("create"))

                        # offset upv curve
                        cvs = mainCtlUpv.getCVs(space="world")
                        for i, cv in enumerate(cvs):
                            offset = [cv[0], cv[1], cv[2] + FRONT_OFFSET]
                            mainCtlUpv.setCV(i, offset, space='world')
                        # collect mainCrv upv
                        rigCurves.append(mainCtlUpv)
                        mainCtlUpvs.append(mainCtlUpv)

            # create secondary control curve.
            if controlStatus == 1:
                if side in secSideRange:
                    secondaryCtlCurve = helpers.addCnsCurve(
                        browsCrv_side_root,
                        setName("secCtl_crv", side),
                        localSecCtlList,
                        crv_degree)
                    secondaryCurves.append(secondaryCtlCurve[0])
                    rigCurves.append(secondaryCtlCurve[0])

        # Constrain curves roots
        ctl_parent = None
        if side == "C":
            ctl_parent = ctl_parent_C
        elif side == "L":
            ctl_parent = ctl_parent_L
        elif side == "R":
            ctl_parent = ctl_parent_R

        if ctl_parent:
            constraints.matrixConstraint(ctl_parent,
                                         browsCrv_side_root,
                                         'srt',
                                         True)

        # create upvector / rope curves
        mainRope = curve.createCurveFromCurve(
            mainCurve,
            setName("mainRope", side),
            nbPoints=NB_ROPE,
            parent=browsCrv_side_root)

        rigCurves.append(mainRope)
        mainRopes.append(mainRope)
        ###
        mainRope_upv = curve.createCurveFromCurve(
            mainCurve,
            setName("mainRope_upv", side),
            nbPoints=NB_ROPE,
            parent=browsCrv_side_root)

        rigCurves.append(mainRope_upv)
        mainRopeUpvs.append(mainRope_upv)
        ###
        mainCrv_upv = curve.createCurveFromCurve(
            mainCurve,
            setName("mainCrv_upv", side),
            nbPoints=7,
            parent=browsCrv_side_root)

        rigCurves.append(mainCrv_upv)
        mainCurveUpvs.append(mainCrv_upv)

    # offset upv curves
        for crv in [mainRope_upv, mainCrv_upv]:
            cvs = crv.getCVs(space="world")
            for i, cv in enumerate(cvs):
                # we populate the closest vertext list here to skipt the first
                # and latest point
                offset = [cv[0], cv[1], cv[2] + FRONT_OFFSET]
                crv.setCV(i, offset, space='world')

    # hide curves
    for crv in rigCurves:
        crv.attr("visibility").set(False)

    ###########################################
    # Connecting controls
    ###########################################
    if parent_node:
        try:
            if isinstance(parent_node, string_types):
                parent_node = pm.PyNode(parent_node)
            parent_node.addChild(brows_root)
        except RuntimeError:
            pm.displayWarning("The brow rig can not be parent to: %s. Maybe "
                              "this object doesn't exist." % parent_node)

    # Reparent controls
    # TODO: this can be more simple an easy to read
    for ctl in mainControls:
        tag_parent = None
        ctl_side = getSide(ctl)

        if ctl_side == "L":
            if "in_tangent_ctl" in ctl.name():
                t_inL = ctl
            if "in_ctl" in ctl.name():
                c_inL = ctl
            if "out_tangent" in ctl.name():
                t_outL = ctl
            if "out_ctl" in ctl.name():
                c_outL = ctl
            tag_parent = parent_tag_L

        if ctl_side == "R":
            if "in_tangent_ctl" in ctl.name():
                t_inR = ctl
            if "in_ctl" in ctl.name():
                c_inR = ctl
            if "out_tangent" in ctl.name():
                t_outR = ctl
            if "out_ctl" in ctl.name():
                c_outR = ctl
            tag_parent = parent_tag_R

        if symmetry_mode == 0:  # 0 means ON
            if ctl_side == "C":
                if "R_HookNpo" in ctl.name():
                    h_outR = ctl
                if "L_HookNpo" in ctl.name():
                    h_outL = ctl
                if "mid_" in ctl.name():
                    c_mid = ctl
                tag_parent = parent_tag_L
        else:
            if ctl_side == "C":
                if "out_R_ctl" in ctl.name():
                    c_outR = ctl
                if "out_L_ctl" in ctl.name():
                    c_outL = ctl

                if "out_R_tangent" in ctl.name():
                    t_outR = ctl
                if "out_L_tangent" in ctl.name():
                    t_outL = ctl

                tag_parent = parent_tag_L
        # controls tags
        node.add_controller_tag(ctl, tagParent=tag_parent)

    # parent controls
    if symmetry_mode == 0:
        # inside parents
        pm.parent(t_inL.getParent(2), c_inL)
        pm.parent(t_inR.getParent(2), c_inR)

        pm.parent(t_outL.getParent(2), c_outL)
        pm.parent(t_outR.getParent(2), c_outR)
        constraints.matrixBlendConstraint([c_inR, c_inL],
                                          c_mid.getParent(2),
                                          [0.5, 0.5],
                                          't',
                                          True,
                                          c_mid)

        constraints.matrixConstraint(c_inR,
                                     h_outR.getParent(2),
                                     'srt',
                                     True)
        constraints.matrixConstraint(c_inL,
                                     h_outL.getParent(2),
                                     'srt',
                                     True)
        constraints.matrixConstraint(ctl_parent_C,
                                     c_mid.getParent(2),
                                     'rs',
                                     True)
        # TODO: we don't need matrix constrains in Main controls. This should
        # be replace by simple parenting to the eyebrow main control
        for ctl in mainControls:
            ctl_side = getSide(ctl)

            if ctl_side == "L" and "_tangent" not in ctl.name():
                pm.parent(ctl.getParent(2), ctl_parent_L)

            if ctl_side == "R" and "_tangent" not in ctl.name():
                pm.parent(ctl.getParent(2), ctl_parent_R)

    else:
        ctl_side = getSide(mainControls[0])

        if ctl_side == "L":
            pm.parent(t_inL.getParent(2), c_inL)
            pm.parent(t_outL.getParent(2), c_outL)
            ctl_parent = ctl_parent_L
        if ctl_side == "R":
            pm.parent(t_inR.getParent(2), c_inR)
            pm.parent(t_outR.getParent(2), c_outR)
            ctl_parent = ctl_parent_R
        if ctl_side == "C":
            pm.parent(t_outR.getParent(2), c_outR)
            pm.parent(t_outL.getParent(2), c_outL)
            ctl_parent = ctl_parent_C
        for ctl in mainControls:
            if "_tangent" not in ctl.name():
                pm.parent(ctl.getParent(2), ctl_parent)

    # Attach secondary controls to main curve
    if secondary_ctl_check:
        secControlsMerged = []
        if symmetry_mode == 0:  # 0 means ON
            tempMainCtlCurves = [crv for crv in mainCtlCurves
                                 if getSide(crv) in "LR"]
            tempMainUpvCurves = [crv for crv in mainCtlUpvs
                                 if getSide(crv) in "LR"]
            leftSec = []
            rightSec = []
            for secCtl in secondaryControls:
                # tag_parent = None
                if getSide(secCtl) == "L":
                    # connect secondary controla rotate/scale to ctl_parent_L.
                    constraints.matrixConstraint(ctl_parent_L,
                                                 secCtl.getParent(2),
                                                 'rs',
                                                 True)
                    leftSec.append(secCtl)
                    tag_parent = parent_tag_L

                if getSide(secCtl) == "R":
                    # connect secondary controla rotate/scale to ctl_parent_L.
                    constraints.matrixConstraint(ctl_parent_R,
                                                 secCtl.getParent(2),
                                                 'rs',
                                                 True)
                    rightSec.append(secCtl)
                    tag_parent = parent_tag_R

                # controls tags
                node.add_controller_tag(secCtl, tagParent=tag_parent)

            secControlsMerged.append(rightSec)
            secControlsMerged.append(leftSec)

        else:
            tempMainCtlCurves = mainCtlCurves
            tempMainUpvCurves = mainCtlUpvs
            secControlsMerged.append(secondaryControls)

            for secCtl in secondaryControls:
                constraints.matrixConstraint(ctl_parent,
                                             secCtl.getParent(2),
                                             'rs',
                                             True)

                # controls tags
                node.add_controller_tag(secCtl, tagParent=parent_tag_L)

        # create hooks on the main ctl curve
        for j, crv in enumerate(secondaryCurves):
            side = getSide(crv)

            lvlType = 'transform'
            cvs = crv.getCVs(space="world")

            for i, cv in enumerate(cvs):

                oTransUpV = pm.PyNode(pm.createNode(
                    lvlType,
                    n=setName("secNpoUpv", side, idx=str(i).zfill(3)),
                    p=browsHooks_root,
                    ss=True))

                oTrans = pm.PyNode(pm.createNode(
                    lvlType,
                    n=setName("secNpo", side, idx=str(i).zfill(3)),
                    p=browsHooks_root, ss=True))

                oParam, oLength = curve.getCurveParamAtPosition(crv, cv)
                uLength = curve.findLenghtFromParam(crv, oParam)
                u = uLength / oLength

                # create motion paths transforms on main ctl curves
                applyop.pathCns(oTransUpV,
                                tempMainUpvCurves[j],
                                cnsType=False,
                                u=u,
                                tangent=False)
                cns = applyop.pathCns(oTrans,
                                      tempMainCtlCurves[j],
                                      cnsType=False,
                                      u=u,
                                      tangent=False)

                cns.setAttr("worldUpType", 1)
                cns.setAttr("frontAxis", 0)
                cns.setAttr("upAxis", 1)

                pm.connectAttr(oTransUpV.attr("worldMatrix[0]"),
                               cns.attr("worldUpMatrix"))

                # connect scaling
                ctl_parent = None
                if side == "C":
                    ctl_parent = ctl_parent_C
                elif side == "L":
                    ctl_parent = ctl_parent_L
                elif side == "R":
                    ctl_parent = ctl_parent_R

                if ctl_parent:
                    constraints.matrixConstraint(ctl_parent,
                                                 oTrans,
                                                 's',
                                                 True)

                # connect secondary control to oTrans hook.
                constraints.matrixConstraint(
                    oTrans,
                    secControlsMerged[j][i].getParent(2),
                    't',
                    True)

    ##################
    # Wires and connections
    ##################

    # set drivers
    crvDrivers = []
    if secondary_ctl_check:
        if symmetry_mode == 0:
            crv = [crv for crv in mainCtlCurves if getSide(crv) == "C"]
            crvDrivers.append(crv[0])

            crvDrivers = crvDrivers + secondaryCurves
        else:
            crvDrivers = secondaryCurves

    else:
        crvDrivers = mainCtlCurves

    for i, drv in enumerate(crvDrivers):
        pm.wire(mainCurves[i], w=drv, dropoffDistance=[0, 1000])
        pm.wire(mainCurveUpvs[i], w=drv, dropoffDistance=[0, 1000])
        pm.wire(mainRopes[i], w=drv, dropoffDistance=[0, 1000])
        pm.wire(mainRopeUpvs[i], w=drv, dropoffDistance=[0, 1000])
    # ###########################################
    # Joints
    ###########################################
    lvlType = "transform"

    for j, crv in enumerate(mainCurves):
        cvs = crv.getCVs(space="world")
        side = getSide(crv)

        if symmetry_mode == 0:  # 0 means ON
            if side == "L":
                browJoint = brow_jnt_L
            if side == "R":
                browJoint = brow_jnt_R
            if side == "C":
                browJoint = brow_jnt_C
        else:
            browJoint = brow_jnt_C

        for i, cv in enumerate(cvs):
            if symmetry_mode == 0 and side == "C":

                if i == 0 or i >= mid_loop_len - 1:
                    continue

            oTransUpV = pm.PyNode(pm.createNode(
                lvlType,
                n=setName("browRopeUpv", idx=str(i).zfill(3)),
                p=browsRope_root,
                ss=True))

            oTrans = pm.PyNode(
                pm.createNode(lvlType,
                              n=setName("browRope", side, idx=str(i).zfill(3)),
                              p=browsRope_root, ss=True))

            oParam, oLength = curve.getCurveParamAtPosition(mainRopeUpvs[j],
                                                            cv)
            uLength = curve.findLenghtFromParam(mainRopes[j], oParam)
            u = uLength / oLength

            applyop.pathCns(
                oTransUpV, mainRopeUpvs[j], cnsType=False, u=u, tangent=False)

            cns = applyop.pathCns(
                oTrans, mainRopes[j], cnsType=False, u=u, tangent=False)

            cns.setAttr("worldUpType", 1)
            cns.setAttr("frontAxis", 0)
            cns.setAttr("upAxis", 1)

            pm.connectAttr(oTransUpV.attr("worldMatrix[0]"),
                           cns.attr("worldUpMatrix"))
            jnt = rigbits.addJnt(oTrans, noReplace=True, parent=browJoint)
            jnt.segmentScaleCompensate.set(0)
            allJoints.append(jnt)
            pm.sets(defset, add=jnt)

            # connect scaling
            ctl_parent = None
            if side == "C":
                ctl_parent = ctl_parent_C
            elif side == "L":
                ctl_parent = ctl_parent_L
            elif side == "R":
                ctl_parent = ctl_parent_R

            if ctl_parent:
                constraints.matrixConstraint(ctl_parent,
                                             oTrans,
                                             's',
                                             True)

    for crv in mainCurves:
        pm.delete(crv)

    ###########################################
    # Auto Skinning
    ###########################################
    if do_skin:
        # base skin
        if brow_jnt_C:
            try:
                brow_jnt_C = pm.PyNode(brow_jnt_C)
            except RuntimeError:
                pm.displayWarning(
                    "Auto skin aborted can not find %s " % brow_jnt_C)
                return

        # Check if the object has a skinCluster
        objName = pm.listRelatives(geo, parent=True)[0]

        skinCluster = skin.getSkinCluster(objName)

        if not skinCluster:
            skinCluster = pm.skinCluster(joints_collect,
                                         geo,
                                         tsb=True,
                                         nw=2,
                                         n='skinCluster_{}'.format(geo.name()))

        # totalLoops = rigid_loops + falloff_loops

        # we set the first value 100% for the first initial loop
        skinPercList = [1.0]
        # we expect to have a regular grid topology
        for r in range(rigid_loops):
            for rr in range(2):
                skinPercList.append(1.0)
        increment = 1.0 / float(falloff_loops)
        # we invert to smooth out from 100 to 0
        inv = 1.0 - increment
        for r in range(falloff_loops):
            for rr in range(2):
                if inv < 0.0:
                    inv = 0.0
                skinPercList.append(inv)
            inv -= increment

        # this loop add an extra 0.0 indices to avoid errors
        for r in range(10):
            for rr in range(2):
                skinPercList.append(0.0)

        pm.progressWindow(title='Auto skinning process',
                          progress=0,
                          max=len(allJoints))

        vertexRowsList = []

        totalLoops = rigid_loops + falloff_loops
        vertexLoopList = meshNavigation.getConcentricVertexLoop(
            closestVtxsList,
            totalLoops)
        vertexRowsList = meshNavigation.getVertexRowsFromLoops(vertexLoopList)

        for i, jnt in enumerate(allJoints):

            pm.progressWindow(e=True, step=1, status='\nSkinning %s' % jnt)
            skinCluster.addInfluence(jnt, weight=0)
            v = closestVtxsList[i]
            for row in vertexRowsList:
                if v in row:
                    for i, rv in enumerate(row):
                        # find the deformer with max value for each vertex
                        w = pm.skinPercent(skinCluster,
                                           rv,
                                           query=True,
                                           value=True)
                        transJoint = pm.skinPercent(skinCluster,
                                                    rv,
                                                    query=True,
                                                    t=None)
                        max_value = max(w)
                        max_index = w.index(max_value)

                        perc = skinPercList[i]
                        t_value = [(jnt, perc),
                                   (transJoint[max_index], 1.0 - perc)]
                        pm.skinPercent(skinCluster,
                                       rv,
                                       transformValue=t_value)
        pm.progressWindow(e=True, endProgress=True)

##########################################################
# Brows Rig UI
##########################################################


class ui(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ui, self).__init__(parent)

        self.filter = "Brows Rigger Configuration .brows (*.brows)"

        self.create()

    def create(self):

        self.setWindowTitle("Brows Rigger")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)

        self.create_controls()
        self.create_layout()
        self.create_connections()

    def create_controls(self):

        # Geometry input controls
        self.geometryInput_group = QtWidgets.QGroupBox("Geometry Input")
        self.edge_loop_label = QtWidgets.QLabel("Brow Edge Loop:")
        self.edge_loop = QtWidgets.QLineEdit()
        self.edge_loop_button = QtWidgets.QPushButton("<<")
        # Name prefix
        self.prefix_group = QtWidgets.QGroupBox("Name Prefix")
        self.name_prefix = QtWidgets.QLineEdit()
        self.name_prefix.setText("brow")

        # control extension
        self.control_group = QtWidgets.QGroupBox("Control Name Extension")
        self.ctl_name = QtWidgets.QLineEdit()
        self.ctl_name.setText("ctl")

        # Topological Autoskin
        self.topoSkin_group = QtWidgets.QGroupBox("蒙皮")
        self.rigid_loops_label = QtWidgets.QLabel("Rigid Loops:")
        self.rigid_loops = QtWidgets.QSpinBox()
        self.rigid_loops.setRange(0, 30)
        self.rigid_loops.setSingleStep(1)
        self.rigid_loops.setValue(1)
        self.falloff_loops_label = QtWidgets.QLabel("Falloff Loops:")
        self.falloff_loops = QtWidgets.QSpinBox()
        self.falloff_loops.setRange(0, 30)
        self.falloff_loops.setSingleStep(1)
        self.falloff_loops.setValue(2)

        self.do_skin = QtWidgets.QCheckBox(
            'Compute Topological Autoskin')
        self.do_skin.setChecked(False)

        # Side
        self.mode_group = QtWidgets.QGroupBox("Symmetry:")
        self.mode_label = QtWidgets.QLabel("Mode:")
        self.symmetry_mode = QtWidgets.QComboBox()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.symmetry_mode.sizePolicy().hasHeightForWidth())
        self.symmetry_mode.setSizePolicy(sizePolicy)
        self.symmetry_mode.addItem("On")
        self.symmetry_mode.addItem("Off")

        # Options
        self.options_group = QtWidgets.QGroupBox("选项")

        # default options
        self.thickness_label = QtWidgets.QLabel("Brow Thickness:")
        self.thickness = QtWidgets.QDoubleSpinBox()
        self.thickness.setRange(0, 10)
        self.thickness.setSingleStep(.01)
        self.thickness.setValue(.03)

        # Side if single
        self.side_label = QtWidgets.QLabel("Side:")
        self.side = QtWidgets.QComboBox()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.side.sizePolicy().hasHeightForWidth())
        self.side.setSizePolicy(sizePolicy)
        self.side.addItem("C")
        self.side.addItem("L")
        self.side.addItem("R")

        self.side.setHidden(True)
        self.side_label.setHidden(True)

        # main divisions
        self.main_div_label = QtWidgets.QLabel("Main Controls:")
        self.main_div = QtWidgets.QDoubleSpinBox()
        self.main_div.setRange(0, 10)
        self.main_div.setSingleStep(1)
        self.main_div.setValue(3)
        self.main_div.setDecimals(0)
        self.main_div.setMinimum(3)

        # secondary divisions
        self.sec_div_label = QtWidgets.QLabel("Secondary Controls:")
        self.sec_div = QtWidgets.QDoubleSpinBox()
        self.sec_div.setRange(0, 10)
        self.sec_div.setSingleStep(1)
        self.sec_div.setValue(5)
        self.sec_div.setDecimals(0)
        self.sec_div.setMinimum(3)

        # secondary controls ?
        self.secondary_ctl_check = QtWidgets.QCheckBox('Secondary controls')
        self.secondary_ctl_check.setChecked(True)

        # Parents
        self.joints_group = QtWidgets.QGroupBox("Parent / Joints")
        self.controls_group = QtWidgets.QGroupBox("Controls")

        # central/main parent
        self.brow_jnt_C_label = QtWidgets.QLabel("Main/central brow joint:")
        self.brow_jnt_C = QtWidgets.QLineEdit()
        self.brow_jnt_C_button = QtWidgets.QPushButton("<<")

        # side joints
        self.brow_jnt_L_label = QtWidgets.QLabel("Left brow joint:")
        self.brow_jnt_L = QtWidgets.QLineEdit()
        self.brow_jnt_L_button = QtWidgets.QPushButton("<<")

        self.brow_jnt_R_label = QtWidgets.QLabel("Right brow joint:")
        self.brow_jnt_R = QtWidgets.QLineEdit()
        self.brow_jnt_R_button = QtWidgets.QPushButton("<<")

        # ctl parents
        self.ctl_parent_C_label = QtWidgets.QLabel("Head/Central control:")
        self.ctl_parent_C = QtWidgets.QLineEdit()
        self.ctl_parent_C_button = QtWidgets.QPushButton("<<")

        self.ctl_parent_L_label = QtWidgets.QLabel("Left control:")
        self.ctl_parent_L = QtWidgets.QLineEdit()
        self.ctl_parent_L_button = QtWidgets.QPushButton("<<")

        self.ctl_parent_R_label = QtWidgets.QLabel("Right control:")
        self.ctl_parent_R = QtWidgets.QLineEdit()
        self.ctl_parent_R_button = QtWidgets.QPushButton("<<")

        # static parent
        self.parent_label = QtWidgets.QLabel("Static Rig Parent:")
        self.parent_node = QtWidgets.QLineEdit()
        self.parent_button = QtWidgets.QPushButton("<<")

        # Build button
        self.build_button = QtWidgets.QPushButton("Build Brows Rig")
        self.import_button = QtWidgets.QPushButton("Import Config from json")
        self.export_button = QtWidgets.QPushButton("Export Config to json")

    def create_layout(self):

        # Edge Loop Layout
        edge_loop_layout = QtWidgets.QHBoxLayout()
        edge_loop_layout.setContentsMargins(1, 1, 1, 1)
        edge_loop_layout.addWidget(self.edge_loop_label)
        edge_loop_layout.addWidget(self.edge_loop)
        edge_loop_layout.addWidget(self.edge_loop_button)

        # Geometry Input Layout
        geometryInput_layout = QtWidgets.QVBoxLayout()
        geometryInput_layout.setContentsMargins(6, 1, 6, 2)
        geometryInput_layout.addLayout(edge_loop_layout)
        self.geometryInput_group.setLayout(geometryInput_layout)

        # Symmetry mode Layout
        sym_layout = QtWidgets.QHBoxLayout()
        sym_layout.setContentsMargins(1, 1, 1, 1)
        sym_layout.addWidget(self.mode_label)
        sym_layout.addWidget(self.symmetry_mode)

        # Side if single
        side_layout = QtWidgets.QHBoxLayout()
        side_layout.setContentsMargins(1, 1, 1, 1)
        side_layout.addWidget(self.side_label)
        side_layout.addWidget(self.side)

        mode_layout = QtWidgets.QVBoxLayout()
        mode_layout.setContentsMargins(6, 4, 6, 4)
        mode_layout.addLayout(sym_layout)
        mode_layout.addLayout(side_layout)
        self.mode_group.setLayout(mode_layout)

        # parents Layout
        # joints
        brow_jnt_L_layout = QtWidgets.QHBoxLayout()
        brow_jnt_L_layout.addWidget(self.brow_jnt_L_label)
        brow_jnt_L_layout.addWidget(self.brow_jnt_L)
        brow_jnt_L_layout.addWidget(self.brow_jnt_L_button)

        brow_jnt_R_layout = QtWidgets.QHBoxLayout()
        brow_jnt_R_layout.addWidget(self.brow_jnt_R_label)
        brow_jnt_R_layout.addWidget(self.brow_jnt_R)
        brow_jnt_R_layout.addWidget(self.brow_jnt_R_button)

        brow_jnt_C_layout = QtWidgets.QHBoxLayout()
        brow_jnt_C_layout.addWidget(self.brow_jnt_C_label)
        brow_jnt_C_layout.addWidget(self.brow_jnt_C)
        brow_jnt_C_layout.addWidget(self.brow_jnt_C_button)

        # controls
        ctl_parent_C_layout = QtWidgets.QHBoxLayout()
        ctl_parent_C_layout.addWidget(self.ctl_parent_C_label)
        ctl_parent_C_layout.addWidget(self.ctl_parent_C)
        ctl_parent_C_layout.addWidget(self.ctl_parent_C_button)

        ctl_parent_L_layout = QtWidgets.QHBoxLayout()
        ctl_parent_L_layout.addWidget(self.ctl_parent_L_label)
        ctl_parent_L_layout.addWidget(self.ctl_parent_L)
        ctl_parent_L_layout.addWidget(self.ctl_parent_L_button)

        ctl_parent_R_layout = QtWidgets.QHBoxLayout()
        ctl_parent_R_layout.addWidget(self.ctl_parent_R_label)
        ctl_parent_R_layout.addWidget(self.ctl_parent_R)
        ctl_parent_R_layout.addWidget(self.ctl_parent_R_button)

        # static parent
        staticParent_layout = QtWidgets.QHBoxLayout()
        staticParent_layout.addWidget(self.parent_label)
        staticParent_layout.addWidget(self.parent_node)
        staticParent_layout.addWidget(self.parent_button)

        # joing layout
        parents_layout = QtWidgets.QVBoxLayout()
        parents_layout.setContentsMargins(6, 4, 6, 4)
        parents_layout.addLayout(staticParent_layout)
        parents_layout.addLayout(brow_jnt_L_layout)
        parents_layout.addLayout(brow_jnt_R_layout)
        parents_layout.addLayout(brow_jnt_C_layout)
        self.joints_group.setLayout(parents_layout)

        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.setContentsMargins(6, 4, 6, 4)
        controls_layout.addLayout(ctl_parent_C_layout)
        controls_layout.addLayout(ctl_parent_L_layout)
        controls_layout.addLayout(ctl_parent_R_layout)
        self.controls_group.setLayout(controls_layout)

        # Options Layout
        thickness_layout = QtWidgets.QHBoxLayout()
        thickness_layout.addWidget(self.thickness_label)
        thickness_layout.addWidget(self.thickness)

        secondary_ctl_check_layout = QtWidgets.QVBoxLayout()
        secondary_ctl_check_layout.setContentsMargins(6, 4, 6, 4)
        secondary_ctl_check_layout.addWidget(
            self.secondary_ctl_check, alignment=QtCore.Qt.Alignment())

        main_div_layout = QtWidgets.QHBoxLayout()
        main_div_layout.addWidget(self.main_div_label)
        main_div_layout.addWidget(self.main_div)

        sec_div_layout = QtWidgets.QHBoxLayout()
        sec_div_layout.addWidget(self.sec_div_label)
        sec_div_layout.addWidget(self.sec_div)

        options_layout = QtWidgets.QVBoxLayout()
        options_layout.setContentsMargins(6, 1, 6, 2)
        options_layout.addLayout(secondary_ctl_check_layout)
        options_layout.addLayout(thickness_layout)
        options_layout.addLayout(main_div_layout)
        options_layout.addLayout(sec_div_layout)
        self.options_group.setLayout(options_layout)

        # Name prefix
        name_prefix_layout = QtWidgets.QHBoxLayout()
        name_prefix_layout.setContentsMargins(1, 1, 1, 1)
        name_prefix_layout.addWidget(self.name_prefix)
        self.prefix_group.setLayout(name_prefix_layout)

        # Control Name Extension
        controlExtension_layout = QtWidgets.QHBoxLayout()
        controlExtension_layout.setContentsMargins(1, 1, 1, 1)
        controlExtension_layout.addWidget(self.ctl_name)
        self.control_group.setLayout(controlExtension_layout)

        # topological autoskin Layout
        skinLoops_layout = QtWidgets.QGridLayout()
        skinLoops_layout.addWidget(self.rigid_loops_label, 0, 0)
        skinLoops_layout.addWidget(self.falloff_loops_label, 0, 1)
        skinLoops_layout.addWidget(self.rigid_loops, 1, 0)
        skinLoops_layout.addWidget(self.falloff_loops, 1, 1)

        topoSkin_layout = QtWidgets.QVBoxLayout()
        topoSkin_layout.setContentsMargins(6, 4, 6, 4)
        topoSkin_layout.addWidget(self.do_skin,
                                  alignment=QtCore.Qt.Alignment())
        topoSkin_layout.addLayout(skinLoops_layout)
        topoSkin_layout.addLayout(parents_layout)
        self.topoSkin_group.setLayout(topoSkin_layout)

        # Main Layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.addWidget(self.prefix_group)
        main_layout.addWidget(self.control_group)
        main_layout.addWidget(self.geometryInput_group)
        main_layout.addWidget(self.mode_group)
        main_layout.addWidget(self.options_group)
        main_layout.addWidget(self.joints_group)
        main_layout.addWidget(self.controls_group)
        main_layout.addWidget(self.topoSkin_group)
        main_layout.addWidget(self.build_button)
        main_layout.addWidget(self.import_button)
        main_layout.addWidget(self.export_button)

        self.setLayout(main_layout)

    def create_connections(self):
        self.symmetry_mode.currentTextChanged.connect(self.setSymmetryLayout)
        self.side.currentIndexChanged.connect(self.setSideControls)
        self.secondary_ctl_check.stateChanged.connect(
            self.setSecondaryControls)

        self.edge_loop_button.clicked.connect(partial(self.populate_edge_loop,
                                                      self.edge_loop))

        self.parent_button.clicked.connect(partial(self.populate_element,
                                                   self.parent_node))

        self.brow_jnt_L_button.clicked.connect(partial(self.populate_element,
                                                       self.brow_jnt_L,
                                                       "joint"))

        self.brow_jnt_R_button.clicked.connect(partial(self.populate_element,
                                                       self.brow_jnt_R,
                                                       "joint"))

        self.brow_jnt_C_button.clicked.connect(partial(self.populate_element,
                                                       self.brow_jnt_C,
                                                       "joint"))

        self.ctl_parent_C_button.clicked.connect(partial(self.populate_element,
                                                         self.ctl_parent_C))
        self.ctl_parent_L_button.clicked.connect(partial(self.populate_element,
                                                         self.ctl_parent_L))

        self.ctl_parent_R_button.clicked.connect(partial(self.populate_element,
                                                         self.ctl_parent_R))

        self.build_button.clicked.connect(self.build_rig)
        self.import_button.clicked.connect(self.import_settings)
        self.export_button.clicked.connect(self.export_settings)

    def setSymmetryLayout(self, value):
        self.setSideControls(value)
        if value == "Off":
            self.side.setHidden(False)
            self.side_label.setHidden(False)

            self.brow_jnt_L_label.setHidden(True)
            self.brow_jnt_L.setHidden(True)
            self.brow_jnt_L_button.setHidden(True)

            self.brow_jnt_R_label.setHidden(True)
            self.brow_jnt_R.setHidden(True)
            self.brow_jnt_R_button.setHidden(True)

            self.ctl_parent_R_label.setHidden(True)
            self.ctl_parent_R.setHidden(True)
            self.ctl_parent_R_button.setHidden(True)
        else:
            self.side.setHidden(True)
            self.side_label.setHidden(True)

            self.brow_jnt_L_label.setHidden(False)
            self.brow_jnt_L.setHidden(False)
            self.brow_jnt_L_button.setHidden(False)

            self.brow_jnt_R_label.setHidden(False)
            self.brow_jnt_R.setHidden(False)
            self.brow_jnt_R_button.setHidden(False)

            self.ctl_parent_R_label.setHidden(False)
            self.ctl_parent_R.setHidden(False)
            self.ctl_parent_R_button.setHidden(False)

    def setSideControls(self, value):

        if value == "On":
            self.ctl_parent_R_label.setHidden(False)
            self.ctl_parent_R.setHidden(False)
            self.ctl_parent_R_button.setHidden(False)
            self.ctl_parent_L_label.setHidden(False)
            self.ctl_parent_L.setHidden(False)
            self.ctl_parent_L_button.setHidden(False)
            self.ctl_parent_C_label.setHidden(False)
            self.ctl_parent_C.setHidden(False)
            self.ctl_parent_C_button.setHidden(False)

        elif self.side.currentText() == "R":
            self.ctl_parent_R_label.setHidden(False)
            self.ctl_parent_R.setHidden(False)
            self.ctl_parent_R_button.setHidden(False)
            self.ctl_parent_L_label.setHidden(True)
            self.ctl_parent_L.setHidden(True)
            self.ctl_parent_L_button.setHidden(True)
            self.ctl_parent_C_label.setHidden(True)
            self.ctl_parent_C.setHidden(True)
            self.ctl_parent_C_button.setHidden(True)

        elif self.side.currentText() == "L":
            self.ctl_parent_R_label.setHidden(True)
            self.ctl_parent_R.setHidden(True)
            self.ctl_parent_R_button.setHidden(True)
            self.ctl_parent_L_label.setHidden(False)
            self.ctl_parent_L.setHidden(False)
            self.ctl_parent_L_button.setHidden(False)
            self.ctl_parent_C_label.setHidden(True)
            self.ctl_parent_C.setHidden(True)
            self.ctl_parent_C_button.setHidden(True)

        elif self.side.currentText() == "C":
            self.ctl_parent_R_label.setHidden(True)
            self.ctl_parent_R.setHidden(True)
            self.ctl_parent_R_button.setHidden(True)
            self.ctl_parent_L_label.setHidden(True)
            self.ctl_parent_L.setHidden(True)
            self.ctl_parent_L_button.setHidden(True)
            self.ctl_parent_C_label.setHidden(False)
            self.ctl_parent_C.setHidden(False)
            self.ctl_parent_C_button.setHidden(False)

    def setSecondaryControls(self, value):
        if value == 0:
            self.sec_div_label.setHidden(True)
            self.sec_div.setHidden(True)
        else:
            self.sec_div_label.setHidden(False)
            self.sec_div.setHidden(False)
    #SLOTS ##########################################################

    def populate_element(self, lEdit, oType="transform"):
        if oType == "joint":
            oTypeInst = pm.nodetypes.Joint
        elif oType == "vertex":
            oTypeInst = pm.MeshVertex
        else:
            oTypeInst = pm.nodetypes.Transform

        oSel = pm.selected()
        if oSel:
            if isinstance(oSel[0], oTypeInst):
                lEdit.setText(oSel[0].name())
            else:
                pm.displayWarning(
                    "The selected element is not a valid %s" % oType)
        else:
            pm.displayWarning("Please select first one %s." % oType)

    def populate_edge_loop(self, lineEdit):
        lineEdit.setText(lib.get_edge_loop_from_selection())

    def build_rig(self):
        rig(**lib.get_settings_from_widget(self))

    def export_settings(self):
        data_string = json.dumps(
            lib.get_settings_from_widget(self), indent=4, sort_keys=True
        )

        file_path = lib.get_file_path(self.filter, "save")
        if not file_path:
            return

        with open(file_path, "w") as f:
            f.write(data_string)

    def import_settings(self):
        file_path = lib.get_file_path(self.filter, "open")
        if not file_path:
            return

        lib.import_settings_from_file(file_path, self)


# Build from json file.
def rig_from_file(path):
    rig(**json.load(open(path)))


def show(*args):
    gqt.showDialog(ui)


if __name__ == "__main__":
    show()
