import mgear.pymaya as pm
from mgear.core import meshNavigation, curve, applyop, primitive, icon
from mgear.core import transform, attribute, skin, vector, pickWalk, utils
from mgear.pymaya import datatypes
string_types = str


##################
# Helper functions
# ##################

# sort vertices from X+ to X-
def sortVerts(points):
    length = len(points)
    for i in range(length):
        for j in range((i + 1), length):
            pos_i = points[i].getPosition(space='world')[0]
            pos_j = points[j].getPosition(space='world')[0]

            if (pos_i < pos_j):
                temp1 = points[i]
                points[i] = points[j]
                points[j] = temp1
    return points

# get control positions from each segment
# generate new curve/rebuild and get cv positions.


def divideSegment(crv, count, name="Temp"):
    if isinstance(crv, str) or isinstance(crv, string_types):
        crv = pm.PyNode(crv)

    curveFromCurve = curve.createCurveFromCurve(crv, name, count)
    cvs = curveFromCurve.getCVs(space='world')

    dividedPositions = []
    for cv in cvs:
        dividedPositions.append(cv)

    pm.delete(curveFromCurve)

    return dividedPositions


def excludeInbetweens(controls, divisions):
    # returns inbetween controls

    if len(controls) > 4:
        midRange = divisions / 2
        if ((divisions % 2) == 0):
            right_inbetweens = controls[midRange + 1:-1]
            left_inbetweens = controls[1:midRange - 1]
        else:
            right_inbetweens = controls[midRange + 1:-1]
            left_inbetweens = controls[1:midRange]
    else:
        left_inbetweens = None
        right_inbetweens = None

    return left_inbetweens, right_inbetweens


def excludeParents(controls, divisions):
    # returns parent controls
    # helper for contraint distribution
    midRange = divisions / 2

    if len(controls) > 3:
        parents = []
        parents.append(controls[0])
        parents.append(controls[midRange])
        parents.append(controls[-1])
        if ((divisions % 2) == 0):
            parents.append(controls[midRange - 1])
    else:
        parents = controls
    return parents


def parentInbetweenControls(controls, divisions):
    # get all parent npos, and then get all inbetweens.
    # then distribute parent constraints between parents and inbetweens
    # there is no sense for parenting anything if there is less than 5 controls
    if len(controls) > 4:
        parents = excludeParents(controls, divisions)
        left_inbetweens, right_inbetweens = excludeInbetweens(controls,
                                                              divisions)
        parentSides = [left_inbetweens, right_inbetweens]

        value = (100.0 / (len(left_inbetweens) + 1)) / 100

        index = 0
        if ((divisions % 2) == 0):
            indx_array = [0, 3, 1, 2]
            for side in parentSides:
                counter = value
                for pObj in reversed(side):
                    cns_nodeA = pm.parentConstraint(parents[indx_array[index]],
                                                    pObj.getParent(2),
                                                    mo=True)

                    cns_nodeA.attr(
                        parents[indx_array[index]].name() + "W0").set(counter)
                    counter = counter + value
                counter = value
                index = index + 1
                for pObj in side:
                    cns_nodeB = pm.parentConstraint(parents[indx_array[index]],
                                                    pObj.getParent(2),
                                                    mo=True)
                    cns_nodeB.attr(
                        parents[indx_array[index]].name() + "W1").set(counter)
                    counter = counter + value
                index = index + 1

        else:
            for side in parentSides:
                counter = value
                for pObj in reversed(side):
                    cns_nodeA = pm.parentConstraint(parents[index],
                                                    pObj.getParent(2),
                                                    mo=True)
                    cns_nodeA.attr(parents[index].name() + "W0").set(counter)
                    counter = counter + value
                counter = value
                for pObj in side:
                    cns_nodeB = pm.parentConstraint(parents[index + 1],
                                                    pObj.getParent(2),
                                                    mo=True)
                    cns_nodeB.attr(
                        parents[index + 1].name() + "W1").set(counter)
                    counter = counter + value
                index = index + 1


def addCnsCurve(parent, name, centers, degree=1):
    """Create a curve attached to given centers. One point per center
    Return gear curvecns node.

    Arguments:
        parent (dagNode): Parent object.
        name (str): Name
        centers (list of dagNode): Object that will drive the curve.
        degree (int): 1 for linear curve, 3 for Cubic.

    Returns:
        dagNode: The newly created curve.
    """
    # rebuild list to avoid input list modification
    centers = centers[:]
    if degree == 3:
        if len(centers) == 2:
            centers.insert(0, centers[0])
            centers.append(centers[-1])
        elif len(centers) == 3:
            centers.append(centers[-1])

    points = [datatypes.Vector() for center in centers]

    node = curve.addCurve(parent, name, points, False, degree)

    gearNode = applyop.gear_curvecns_op(node, centers)

    return node, gearNode


def addCurve(parent, name, centers, degree=1):
    """Create a curve based on given centers. One point per center
    """
    # rebuild list to avoid input list modification
    centers = centers[:]
    if degree == 3:
        if len(centers) == 2:
            centers.insert(0, centers[0])
            centers.append(centers[-1])
        elif len(centers) == 3:
            centers.append(centers[-1])

    # points = [datatypes.Vector() for center in centers]
    points = []
    for center in centers:
        points.append(center.getTranslation(space="world"))

    node = curve.addCurve(parent, name, points, False, degree)

    return node
