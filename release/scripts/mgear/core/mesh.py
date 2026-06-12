"""Functions to create mesh topology"""

#############################################
# GLOBAL
#############################################

import maya.api.OpenMaya as om2
import maya.cmds as cmds
import mgear.pymaya as pm


def is_selected_object_mesh(obj=None):
    """
    Check if the currently selected object's transform has a mesh shape.

    Returns:
        bool: True if the transform's shape is a mesh, False otherwise.

    Args:
        obj (str or PyNode, optional): Object to check if is mesh

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
        # Check if the shape of the selected object is a mesh
        is_mesh = isinstance(obj.getShape(), pm.nodetypes.Mesh)
        return is_mesh
    else:
        return False


def create_square_polygon(
    side_length=1.0, alignment="Y", name=None, position=(0, 0, 0)
):
    """
    Creates a square polygon face with its normal aligned along a specified
    world axis and positions it at a given 3D location.

    Args:
        side_length (float, optional): The length of each side of the square.
            Defaults to 1.0.
        alignment (str, optional): The world axis ('X', 'Y', 'Z') along which
            the square's normal will be aligned. Defaults to 'Y'.
        name (str, optional): The name of the new polygon object. If None,
            Maya will assign a default name.
        position (tuple, optional): The 3D position (x, y, z) where the square
            will be placed. Defaults to (0, 0, 0).

    Returns:
        str: The full name of the newly created polygon object.
    """
    half_length = side_length * 0.5
    points = om2.MPointArray()

    # Adjust vertex definitions based on alignment to ensure correct normal direction
    if alignment.upper() == "X":
        # Normal along X-axis
        base_points = [
            om2.MPoint(0, half_length, half_length),
            om2.MPoint(0, -half_length, half_length),
            om2.MPoint(0, -half_length, -half_length),
            om2.MPoint(0, half_length, -half_length),
        ]
    elif alignment.upper() == "Y":
        # Normal along Y-axis
        base_points = [
            om2.MPoint(-half_length, 0, half_length),
            om2.MPoint(half_length, 0, half_length),
            om2.MPoint(half_length, 0, -half_length),
            om2.MPoint(-half_length, 0, -half_length),
        ]
    else:  # Z alignment
        # Normal along Z-axis
        base_points = [
            om2.MPoint(-half_length, half_length, 0),
            om2.MPoint(half_length, half_length, 0),
            om2.MPoint(half_length, -half_length, 0),
            om2.MPoint(-half_length, -half_length, 0),
        ]

    # Apply position offset and append to MPointArray
    for pt in base_points:
        pt.x += position[0]
        pt.y += position[1]
        pt.z += position[2]
        points.append(pt)

    # Create mesh
    mesh_fn = om2.MFnMesh()
    mesh_fn.create(points, [4], [0, 1, 2, 3])

    # Get the transform node of the created mesh
    new_mesh_name = mesh_fn.fullPathName()
    transform_node = cmds.listRelatives(new_mesh_name, parent=True)[0]

    # Rename if name is provided
    if name:
        transform_node = cmds.rename(transform_node, name)

    # Apply default shader (lambert1) to the new object
    # Directly use the initialShadingGroup which is the default for lambert1
    shading_group = "initialShadingGroup"
    cmds.sets(transform_node, edit=True, forceElement=shading_group)

    transform_node = pm.PyNode(transform_node)
    return transform_node


def create_square_polygon_with_reference(
    side_length=1.0, alignment="Y", name=None, reference_matrix=None
):
    """
    Creates a square polygon face with its normal aligned and positioned
    according to the transformation matrix of a reference object and applies
    the default shader. The alignment is corrected to ensure the polygon
    aligns with the Y-axis as intended.

    Args:
        side_length (float, optional): The length of each side of the square.
            Defaults to 1.0.
        alignment (str, optional): The axis ('X', 'Y', 'Z') along which the
            square's normal will be aligned based on the reference object.
            Defaults to 'Y'.
        name (str, optional): The name of the new polygon object. If None,
            Maya will assign a default name.
        reference_matrix (matrix, optional): The matrix used for alignment and
            positioning.

    Returns:
        pm.nt.Transform: The PyNode transform of the newly created polygon object.
    """
    if reference_matrix is None:
        pm.displayWarning("Reference matrix is not specified. Aborting.")
        return None

    # # Retrieve the world matrix from the reference object
    # reference_matrix = reference_object.getMatrix(worldSpace=True)
    ref_matrix_mfn = om2.MTransformationMatrix(om2.MMatrix(reference_matrix))

    half_length = side_length / 2.0
    points = om2.MPointArray()

    # Adjust base points for square polygon to ensure proper alignment with the Y-axis
    vectors = [
        (-half_length, 0, half_length),  # Top-Left
        (half_length, 0, half_length),  # Top-Right
        (half_length, 0, -half_length),  # Bottom-Right
        (-half_length, 0, -half_length),  # Bottom-Left
    ]

    for vec in vectors:
        point = om2.MPoint(vec) * ref_matrix_mfn.asMatrix()
        points.append(point)

    # Create mesh
    mesh_fn = om2.MFnMesh()
    mesh_fn.create(points, [4], [0, 1, 2, 3])

    # Get the transform node of the created mesh and apply the default shader
    new_mesh_transform = pm.listRelatives(
        pm.PyNode(mesh_fn.fullPathName()), parent=True
    )[0]
    if name:
        new_mesh_transform = new_mesh_transform.rename(name)

    # Apply default shader (lambert1) to the new object
    pm.sets(
        "initialShadingGroup",
        edit=True,
        forceElement=new_mesh_transform.name(),
    )

    return new_mesh_transform
