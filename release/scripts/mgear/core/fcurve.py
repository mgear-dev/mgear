import mgear.pymaya as pm


def getFCurveValues(fcv_node, division, factor=1):
    """Get X values evenly spaced on the FCurve.

    Arguments:
        fcv_node (pyNode or str): The FCurve to evaluate.
        division (int): The number of division you want to evaluate on
            the FCurve.
        factor (float): Multiplication factor. Default = 1. (optional)

    Returns:
        list of float: The values in a list float.

    >>> self.st_value = fcu.getFCurveValues(self.settings["st_profile"],
                                            self.divisions)

    """
    incr = 1 / (division - 1.0)

    values = []
    for i in range(division):
        pm.setAttr(fcv_node + ".input", i * incr)
        values.append(pm.getAttr(fcv_node + ".output") * factor)

    return values
