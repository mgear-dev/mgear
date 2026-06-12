"""Functions to help navigate the NURBS surface"""

#############################################
# GLOBAL
#############################################
import maya.api.OpenMaya as om
import mgear.pymaya as pm


def is_selected_object_nurbs(obj=None):
    """
    Check if the currently selected object's transform has a NURBS shape.

    Returns:
        bool: True if the transform's shape is a NURBS, False otherwise.

    Args:
        obj (str or PyNode, optional): Object to check if is NURBS

    """
    if not obj:
        # Get the current selection
        selection = pm.selected()

        if not selection:
            raise ValueError("No object is selected.")

        # Get the first item in the selection
        obj = selection[0]
    else:
        if isinstance(obj, str):
            obj = pm.PyNode(obj)

    # Check if the selected object is a transform and has a shape
    if obj.nodeType() == "transform" and obj.getShape():
        # Check if the shape of the selected object is a NURBS
        is_nurbs = isinstance(obj.getShape(), pm.nodetypes.NurbsSurface)
        return is_nurbs
    else:
        return False


def get_closest_uv_coord(surface_name, position):
    """
    Get the closest UV coordinates on a NURBS surface from a given position.

    Args:
        surface_name (str): The name of the NURBS surface.
        position (list): The position in world space [x, y, z].

    Returns:
        tuple: The closest UV coordinates (u, v).
    """
    # Get the MObject for the NURBS surface
    selection_list = om.MSelectionList()
    selection_list.add(surface_name)
    surface_dag_path = selection_list.getDagPath(0)

    # Create MFnNurbsSurface function set
    surface_fn = om.MFnNurbsSurface(surface_dag_path)

    # Create MPoint from position
    point = om.MPoint(position[0], position[1], position[2])

    # Initialize closest distance and UV coordinates
    closest_distance = float("inf")
    closest_uv = (0.0, 0.0)
    # Sample the surface at regular intervals to find the closest UV
    num_samples = 100
    u_range = surface_fn.knotDomainInU
    v_range = surface_fn.knotDomainInV

    for i in range(num_samples + 1):
        for j in range(num_samples + 1):
            u = u_range[0] + (u_range[1] - u_range[0]) * (i / num_samples)
            v = v_range[0] + (v_range[1] - v_range[0]) * (j / num_samples)
            sample_point = surface_fn.getPointAtParam(u, v, om.MSpace.kWorld)
            distance = (sample_point - point).length()
            if distance < closest_distance:
                closest_distance = distance
                closest_uv = (u, v)

    # Normalize the UV coordinates
    u_normalized = (closest_uv[0] - u_range[0]) / (u_range[1] - u_range[0])
    v_normalized = (closest_uv[1] - v_range[0]) / (v_range[1] - v_range[0])

    return u_normalized, v_normalized
