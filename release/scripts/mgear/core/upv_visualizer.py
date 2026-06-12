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
        "crossProduct_elbow": "{}_crossProduct".format(elbow.nodeName()),
        "crossProduct_wrist": "{}_crossProduct".format(wrist.nodeName()),
        "crossProduct_root": "{}_crossProduct".format(root.nodeName()),
        "sub_elbow": elbow.nodeName(),
        "sub_wrist": wrist.nodeName(),
        "sub_eff": eff.nodeName(),
    }
    nodes = {}
    for key, name in names.items():
        n = nod.createPlusMinusAverage3D([], operation=2)
        pm.rename(n, "{}_pma".format(name))
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
    # Compute the maximum of a minimum floor value and three
    # vector lengths.  The 'max' node only exists in Maya
    # 2024.2+, so we chain condition nodes instead.
    min_floor = nod.createMulNode(0.010, 1.0)
    pm.rename(min_floor, "{}_max_md".format(root.nodeName()))

    # max(floor, eff)
    cond1 = nod.createConditionNode(
        firstTerm="{}.outputX".format(min_floor.name()),
        secondTerm=length_nodes["eff"].distance,
        operator=2,  # greater than
        ifTrue="{}.outputX".format(min_floor.name()),
        ifFalse=length_nodes["eff"].distance,
    )
    pm.rename(cond1, "{}_max_cond1".format(root.nodeName()))

    # max(prev, elbow)
    cond2 = nod.createConditionNode(
        firstTerm="{}.outColorR".format(cond1.name()),
        secondTerm=length_nodes["elbow"].distance,
        operator=2,
        ifTrue="{}.outColorR".format(cond1.name()),
        ifFalse=length_nodes["elbow"].distance,
    )
    pm.rename(cond2, "{}_max_cond2".format(root.nodeName()))

    # max(prev, wrist)
    cond3 = nod.createConditionNode(
        firstTerm="{}.outColorR".format(cond2.name()),
        secondTerm=length_nodes["wrist"].distance,
        operator=2,
        ifTrue="{}.outColorR".format(cond2.name()),
        ifFalse=length_nodes["wrist"].distance,
    )
    pm.rename(cond3, "{}_max_cond3".format(root.nodeName()))

    half_one_float_node = nod.createMulNode(
        "{}.outColorR".format(cond3.name()), float_value
    )
    pm.rename(
        half_one_float_node, "{}_half_one_md".format(root.nodeName())
    )

    math_nodes = {
        "max_chain": [cond1, cond2, cond3],
        "half_multiply": half_one_float_node,
    }

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

    # Use vectorProduct nodes instead of normalize/crossProduct
    # which only exist in Maya 2024.2+.
    # vectorProduct operation: 0=none, 1=dot, 2=cross, 3=vectorMatrixProduct
    # normalizeOutput=True gives us normalized result.

    # Normalize elbow and wrist cross products
    normalize_elbow = pm.createNode(
        "vectorProduct",
        name="{}_normalize".format(elbow.nodeName()),
    )
    normalize_elbow.operation.set(0)
    normalize_elbow.normalizeOutput.set(True)
    vector_nodes["crossProduct_elbow"].output3D >> normalize_elbow.input1

    normalize_wrist = pm.createNode(
        "vectorProduct",
        name="{}_normalize".format(wrist.nodeName()),
    )
    normalize_wrist.operation.set(0)
    normalize_wrist.normalizeOutput.set(True)
    vector_nodes["crossProduct_wrist"].output3D >> normalize_wrist.input1

    # Cross product: wrist x elbow
    crossProduct_wrist_elbow = pm.createNode(
        "vectorProduct",
        name="{}_crossProduct_wrist_elbow".format(root.nodeName()),
    )
    crossProduct_wrist_elbow.operation.set(2)
    normalize_wrist.output >> crossProduct_wrist_elbow.input1
    normalize_elbow.output >> crossProduct_wrist_elbow.input2

    # Default cross product (elbow x -Z)
    crossProduct_default = pm.createNode(
        "vectorProduct",
        name="{}_crossProduct_default".format(root.nodeName()),
    )
    crossProduct_default.operation.set(2)
    crossProduct_default.input2Z.set(-1.000)
    normalize_elbow.output >> crossProduct_default.input1

    # Sum cross product components to check if zero
    cp_sum_node = nod.createPlusMinusAverage1D(
        [
            "{}.outputX".format(crossProduct_wrist_elbow),
            "{}.outputY".format(crossProduct_wrist_elbow),
            "{}.outputZ".format(crossProduct_wrist_elbow),
        ],
        operation=1,
    )
    pm.rename(
        cp_sum_node,
        "{}_crossProduct_wrist_elbow_sum".format(root.nodeName()),
    )

    condition_node = pm.createNode(
        "condition",
        name="{}_condition".format(root.nodeName()),
    )
    condition_node.secondTerm.set(0.000)

    cp_sum_node.output1D >> condition_node.firstTerm
    crossProduct_default.output >> condition_node.colorIfTrue
    crossProduct_wrist_elbow.output >> condition_node.colorIfFalse

    # Normalize condition output
    normalize_condition_node = pm.createNode(
        "vectorProduct",
        name="{}_normalize_condition".format(root.nodeName()),
    )
    normalize_condition_node.operation.set(0)
    normalize_condition_node.normalizeOutput.set(True)
    condition_node.outColor >> normalize_condition_node.input1

    # Final cross product: condition x root
    crossProduct_root = pm.createNode(
        "vectorProduct",
        name="{}_crossProduct_root".format(root.nodeName()),
    )
    crossProduct_root.operation.set(2)
    normalize_condition_node.output >> crossProduct_root.input1
    vector_nodes["crossProduct_root"].output3D >> crossProduct_root.input2

    # Normalize final result
    crossProduct_root_normalize_node = pm.createNode(
        "vectorProduct",
        name="{}_crossProduct_root_normalize".format(root.nodeName()),
    )
    crossProduct_root_normalize_node.operation.set(0)
    crossProduct_root_normalize_node.normalizeOutput.set(True)
    crossProduct_root.output >> crossProduct_root_normalize_node.input1

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
    pm.rename(upv_mul, "{}_upv_pos_multiply".format(elbow.nodeName()))

    upv_sum = nod.createPlusMinusAverage3D(
        [
            "{}.output".format(upv_mul),
            "{}.outputTranslate".format(decompose_nodes[1]),
        ],
        operation=1,
    )
    pm.rename(upv_sum, "{}_upv_pos_pma".format(elbow.nodeName()))

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