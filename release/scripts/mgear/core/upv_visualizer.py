"""UPV Visualization Module.

Creates a pole vector (UPV) visualization node network for Maya's
guide stage. Uses only nodes available in Maya 2022+ for backwards
compatibility (plusMinusAverage, multiplyDivide, etc.).
"""

import mgear.pymaya as pm
from mgear.core import node as nod


def upv_vis_decompose_nodes(root, elbow, wrist, eff):
    """Create decompose matrix nodes for guide nodes.

    Args:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        eff (PyNode): End effector guide node.

    Returns:
        list: Four decomposeMatrix nodes [root, elbow, wrist, eff].
    """
    guide_nodes = [root, elbow, wrist, eff]
    return [
        nod.createDecomposeMatrixNode(f"{guide}.worldMatrix[0]")
        for guide in guide_nodes
    ]


def create_vector_subtraction_nodes(elbow, wrist, root, eff):
    """Create vector subtraction node network.

    Uses plusMinusAverage (operation=2) instead of subtract nodes
    for Maya 2022+ compatibility.

    Args:
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        root (PyNode): Root guide node.
        eff (PyNode): End effector guide node.

    Returns:
        dict: PMA nodes keyed by role.
    """
    names = {
        "crossProduct_elbow": f"{elbow}_crossProduct",
        "crossProduct_wrist": f"{wrist}_crossProduct",
        "crossProduct_root": f"{root}_crossProduct",
        "sub_elbow": str(elbow),
        "sub_wrist": str(wrist),
        "sub_eff": str(eff),
    }
    nodes = {}
    for key, name in names.items():
        n = nod.createPlusMinusAverage3D([], operation=2)
        pm.rename(n, f"{name}_pma")
        nodes[key] = n
    return nodes


def connect_decompose_to_vector_nodes(decompose_nodes, vector_nodes):
    """Connect decompose matrix nodes to vector subtraction nodes.

    Args:
        decompose_nodes (list): DecomposeMatrix nodes
            [root, elbow, wrist, eff].
        vector_nodes (dict): PMA subtraction node dictionary.
    """
    decm = decompose_nodes
    connections = (
        # (source_for_input3D[0], source_for_input3D[1], target_key)
        (decm[2], decm[0], "crossProduct_root"),   # wrist - root
        (decm[1], decm[0], "crossProduct_elbow"),   # elbow - root
        (decm[2], decm[0], "crossProduct_wrist"),   # wrist - root
        (decm[1], decm[0], "sub_elbow"),             # elbow - root
        (decm[2], decm[0], "sub_wrist"),             # wrist - root
        (decm[3], decm[0], "sub_eff"),               # eff - root
    )
    for src_a, src_b, key in connections:
        pma = vector_nodes[key]
        pm.connectAttr(
            f"{src_a}.outputTranslate", f"{pma}.input3D[0]"
        )
        pm.connectAttr(
            f"{src_b}.outputTranslate", f"{pma}.input3D[1]"
        )


def calculate_vector_lengths(vector_nodes):
    """Calculate vector lengths from PMA subtraction outputs.

    Args:
        vector_nodes (dict): PMA subtraction node dictionary.

    Returns:
        dict: Length nodes keyed by 'eff', 'elbow', 'wrist'.
    """
    length_nodes = {}
    for joint_name in ("eff", "elbow", "wrist"):
        # Use distanceBetween with point2 at origin to
        # compute vector length. The 'length' node only
        # exists in Maya 2024.2+.
        dist_node = pm.createNode(
            "distanceBetween",
            name="{}_vectorLength".format(joint_name),
        )
        pma = vector_nodes["sub_{}".format(joint_name)]
        pma.output3D >> dist_node.point1
        # point2 defaults to (0,0,0) — distance = length
        length_nodes[joint_name] = dist_node

    return length_nodes


def setup_math_operations(root, length_nodes, float_value=0.5):
    """Set up math operation nodes for pole vector length.

    Args:
        root (PyNode): Root guide node.
        length_nodes (dict): Length nodes dictionary.
        float_value (float, optional): Multiplication coefficient.

    Returns:
        tuple: (half_one_float_node, math_nodes dict).
    """
    max_float_node = nod.createMulNode(0.010, 1.0)
    pm.rename(max_float_node, f"{root}_max_md")

    max_node = pm.createNode("max", name=f"{root.name()}_max")
    max_float_node.outputX >> max_node.input[0]

    length_nodes["eff"].distance >> max_node.input[1]
    length_nodes["elbow"].distance >> max_node.input[2]
    length_nodes["wrist"].distance >> max_node.input[3]

    half_one_float_node = nod.createMulNode(
        f"{max_node}.output", float_value
    )
    pm.rename(half_one_float_node, f"{root}_half_one_md")

    math_nodes = {"max": max_node, "half_multiply": half_one_float_node}

    return half_one_float_node, math_nodes


def setup_cross_product_chain(root, elbow, wrist, vector_nodes, float_value):
    """Set up cross product calculation chain.

    Args:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        vector_nodes (dict): PMA vector node dictionary.
        float_value (float): Length calculation coefficient.

    Returns:
        tuple: (normalize_node, half_multiply_node, math_nodes).
    """
    length_nodes = calculate_vector_lengths(vector_nodes)
    half_multiply_node, math_nodes = setup_math_operations(
        root, length_nodes, float_value
    )

    normalize_elbow = pm.createNode(
        "normalize", name=f"{elbow}_normalize"
    )
    normalize_wrist = pm.createNode(
        "normalize", name=f"{wrist}_normalize"
    )

    vector_nodes["crossProduct_elbow"].output3D >> normalize_elbow.input
    vector_nodes["crossProduct_wrist"].output3D >> normalize_wrist.input

    crossProduct_wrist_elbow = pm.createNode(
        "crossProduct", name=f"{root}_crossProduct_wrist_elbow"
    )
    crossProduct_default = pm.createNode(
        "crossProduct", name=f"{root}_crossProduct_default"
    )
    crossProduct_default.input2Z.set(-1.000)

    normalize_wrist.output >> crossProduct_wrist_elbow.input1
    normalize_elbow.output >> crossProduct_wrist_elbow.input2
    normalize_elbow.output >> crossProduct_default.input1

    # Sum cross product components to check if zero
    cp_sum_node = nod.createPlusMinusAverage1D(
        [
            f"{crossProduct_wrist_elbow}.outputX",
            f"{crossProduct_wrist_elbow}.outputY",
            f"{crossProduct_wrist_elbow}.outputZ",
        ],
        operation=1,
    )
    pm.rename(cp_sum_node, f"{root}_crossProduct_wrist_elbow_sum")

    condition_node = pm.createNode(
        "condition", name=f"{root}_condition"
    )
    condition_node.secondTerm.set(0.000)

    cp_sum_node.output1D >> condition_node.firstTerm
    crossProduct_default.output >> condition_node.colorIfTrue
    crossProduct_wrist_elbow.output >> condition_node.colorIfFalse

    normalize_condition_node = pm.createNode(
        "normalize", name=f"{root}_normalize_condition"
    )
    condition_node.outColor >> normalize_condition_node.input

    crossProduct_root = pm.createNode(
        "crossProduct", name=f"{root}_crossProduct_root"
    )
    normalize_condition_node.output >> crossProduct_root.input1
    vector_nodes["crossProduct_root"].output3D >> crossProduct_root.input2

    crossProduct_root_normalize_node = pm.createNode(
        "normalize", name=f"{root}_crossProduct_root_normalize"
    )
    crossProduct_root.output >> crossProduct_root_normalize_node.input

    return crossProduct_root_normalize_node, half_multiply_node, math_nodes


def setup_upv_position_calculation(
    elbow, upv, normalize_node, half_multiply_node, decompose_nodes
):
    """Calculate the final UPV position.

    Args:
        elbow (PyNode): Elbow guide node.
        upv (PyNode): Pole vector guide node.
        normalize_node (PyNode): Normalized cross product node.
        half_multiply_node (PyNode): Length multiplication node.
        decompose_nodes (list): DecomposeMatrix node list.
    """
    upv_mul = nod.createMulNode(
        [
            f"{normalize_node}.outputX",
            f"{normalize_node}.outputY",
            f"{normalize_node}.outputZ",
        ],
        [
            f"{half_multiply_node}.outputX",
            f"{half_multiply_node}.outputX",
            f"{half_multiply_node}.outputX",
        ],
    )
    pm.rename(upv_mul, f"{elbow}_upv_pos_multiply")

    upv_sum = nod.createPlusMinusAverage3D(
        [
            f"{upv_mul}.output",
            f"{decompose_nodes[1]}.outputTranslate",
        ],
        operation=1,
    )
    pm.rename(upv_sum, f"{elbow}_upv_pos_pma")

    upv_sum.output3Dx >> upv.translateX
    upv_sum.output3Dy >> upv.translateY
    upv_sum.output3Dz >> upv.translateZ


def setup_visibility_and_matrix(root, root_decompose, upv, upvcrv):
    """Set up visibility and matrix connections.

    Args:
        root (PyNode): Root guide node.
        root_decompose (PyNode): Decompose matrix node from root.
        upv (PyNode): Pole vector guide node.
        upvcrv (PyNode): Pole vector display curve.
    """
    root_decompose.outputScale >> upv.scale
    root.worldInverseMatrix[0] >> upv.offsetParentMatrix
    root.worldInverseMatrix[0] >> upvcrv.offsetParentMatrix


def create_upv_system(root, elbow, wrist, eff, upvcrv, upv, float_value=0.5):
    """Create a complete UPV visualization system.

    Args:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        eff (PyNode): End effector guide node.
        upvcrv (PyNode): Pole vector display curve node.
        upv (PyNode): Pole vector guide node.
        float_value (float, optional): Pole vector length coefficient.
    """
    decompose_nodes = upv_vis_decompose_nodes(root, elbow, wrist, eff)
    if not decompose_nodes:
        return

    vector_nodes = create_vector_subtraction_nodes(elbow, wrist, root, eff)
    connect_decompose_to_vector_nodes(decompose_nodes, vector_nodes)

    normalize_node, half_multiply_node, math_nodes = (
        setup_cross_product_chain(
            root, elbow, wrist, vector_nodes, float_value
        )
    )

    setup_upv_position_calculation(
        elbow, upv, normalize_node, half_multiply_node, decompose_nodes
    )

    setup_visibility_and_matrix(root, decompose_nodes[0], upv, upvcrv)