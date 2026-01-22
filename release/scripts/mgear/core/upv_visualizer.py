"""
UPV Visualization Module.

This module is used to create and set up a pole vector (UPV) visualization system in Maya, specifically for the guide stage.

"""

import mgear.pymaya as pm


def upv_vis_decompose_nodes(root, elbow, wrist, eff):
    """
    Create decompose matrix nodes for guide nodes.

    Creates a decomposeMatrix node for each guide node to extract world space transformation information.

    Arguments:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        eff (PyNode): End effector guide node.

    Returns:
        list: A list containing four decomposeMatrix nodes, in the order
            [root, elbow, wrist, eff].
    """
    guide_nodes = [root, elbow, wrist, eff]
    decompose_nodes = [
        pm.createNode("decomposeMatrix", name=f"{guide}_decomposeMatrix")
        for guide in guide_nodes
    ]
    for guide, decompose_node in zip(guide_nodes, decompose_nodes):
        guide.worldMatrix[0] >> decompose_node.inputMatrix

    return decompose_nodes


def create_vector_nodes(name, node_type="subtract"):
    """
    Create vector operation node groups.

    Creates a set of three nodes of the same type for processing the X, Y, Z components of a vector.

    Arguments:
        name (str): Node name prefix.
        node_type (str, optional): Node type, supports 'subtract', 'sum',
            'multiply'.

    Returns:
        list: A list containing three specified type nodes, corresponding to
            the X, Y, Z axes respectively.

    Raises:
        ValueError: When the node_type is not supported.
    """
    node_creators = {
        "subtract": ("subtract", "subtract"),
        "sum": ("sum", "sum"),
        "multiply": ("multiply", "multiply"),
    }
    if node_type not in node_creators:
        raise ValueError(f"Unsupported node type: {node_type}")
    node_class, suffix = node_creators[node_type]
    nodes = [
        pm.createNode(node_class, name=f"{name}_{axis}_{suffix}")
        for axis in ["x", "y", "z"]
    ]

    return nodes


def connect_vector_components(
    source_node, target_nodes, target_attribute="input1", axes=["X", "Y", "Z"]
):
    """
    Connect vector components to target nodes.

    Connects the output components of the source node to the specified attributes of the target nodes.

    Arguments:
        source_node (PyNode): Source node, containing outputTranslateX/Y/Z
            attributes.
        target_nodes (list): Target node list.
        target_attribute (str, optional): Target attribute name.
        axes (list, optional): List of axes to connect.

    """
    for i, component in enumerate(axes):
        source_component = getattr(source_node, f"outputTranslate{component}")
        if hasattr(target_nodes[i], target_attribute):
            target_attr = getattr(target_nodes[i], target_attribute)
            source_component >> target_attr
        elif target_attribute.startswith("input["):
            index = int(target_attribute.split("[")[1].split("]")[0])
            target_nodes[i].input[index] << source_component
        else:
            pm.displayError(
                f"Target node {target_nodes[i]} has no attribute {target_attribute}"
            )


def create_vector_subtraction_nodes(elbow, wrist, root, eff):
    """
    Create vector subtraction node network.

    Creates all necessary vector subtraction nodes for pole vector calculation.

    Arguments:
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        root (PyNode): Root guide node.
        eff (PyNode): End effector guide node.

    Returns:
        dict: A dictionary containing various vector subtraction nodes, keys
            include: 'crossProduct_elbow', 'crossProduct_wrist',
            'crossProduct_root', 'sub_elbow', 'sub_wrist', 'sub_eff'.
    """
    vector_nodes = {}
    node_type = "subtract"
    vector_nodes["crossProduct_elbow"] = create_vector_nodes(
        f"{elbow}_crossProduct", node_type
    )
    vector_nodes["crossProduct_wrist"] = create_vector_nodes(
        f"{wrist}_crossProduct", node_type
    )
    vector_nodes["crossProduct_root"] = create_vector_nodes(
        f"{root}_crossProduct", node_type
    )

    vector_nodes["sub_elbow"] = create_vector_nodes(f"{elbow}", node_type)
    vector_nodes["sub_wrist"] = create_vector_nodes(f"{wrist}", node_type)
    vector_nodes["sub_eff"] = create_vector_nodes(f"{eff}", node_type)

    return vector_nodes


def connect_decompose_to_vector_nodes(decompose_nodes, vector_nodes):
    """
    Connect decompose matrix nodes to vector nodes.

    Connects the outputs of decomposeMatrix nodes to the inputs of vector subtraction nodes.

    Arguments:
        decompose_nodes (list): decomposeMatrix node list.
        vector_nodes (dict): Vector subtraction node dictionary.

    Note:
        Node order convention: decompose_nodes = [root, elbow, wrist, eff].
    """
    decm = decompose_nodes
    # Connect crossProduct_root (wrist - root)
    connect_vector_components(decm[2], vector_nodes["crossProduct_root"], "input1")
    connect_vector_components(decm[0], vector_nodes["crossProduct_root"], "input2")
    # Connect crossProduct_elbow (elbow - root)
    connect_vector_components(decm[1], vector_nodes["crossProduct_elbow"], "input1")
    connect_vector_components(decm[0], vector_nodes["crossProduct_elbow"], "input2")
    # Connect crossProduct_wrist_sub (wrist - root)
    connect_vector_components(decm[2], vector_nodes["crossProduct_wrist"], "input1")
    connect_vector_components(decm[0], vector_nodes["crossProduct_wrist"], "input2")
    # elbow - root
    connect_vector_components(decm[1], vector_nodes["sub_elbow"], "input1")
    connect_vector_components(decm[0], vector_nodes["sub_elbow"], "input2")
    # wrist - root
    connect_vector_components(decm[2], vector_nodes["sub_wrist"], "input1")
    connect_vector_components(decm[0], vector_nodes["sub_wrist"], "input2")
    # eff - root
    connect_vector_components(decm[3], vector_nodes["sub_eff"], "input1")
    connect_vector_components(decm[0], vector_nodes["sub_eff"], "input2")


def calculate_vector_lengths(vector_nodes):
    """
    Calculate vector lengths.

    Creates length nodes for eff, elbow, wrist vectors to calculate their lengths.

    Arguments:
        vector_nodes (dict): Dictionary containing vector subtraction nodes.

    Returns:
        dict: Dictionary containing length nodes, keys are 'eff', 'elbow',
            'wrist'.
    """
    length_nodes = {}
    for joint_name in ["eff", "elbow", "wrist"]:
        length_node = pm.createNode("length", name=f"{joint_name}_length")
        sub_nodes = vector_nodes[f"sub_{joint_name}"]
        sub_nodes[0].output >> length_node.inputX
        sub_nodes[1].output >> length_node.inputY
        sub_nodes[2].output >> length_node.inputZ
        length_nodes[joint_name] = length_node

    return length_nodes


def setup_math_operations(root, length_nodes, float_value=0.5):
    """
    Set up mathematical operation nodes.

    Creates a chain of mathematical operation nodes for pole vector
    calculation.

    Arguments:
        root (PyNode): Root guide node.
        length_nodes (dict): Dictionary containing length nodes.
        float_value (float, optional): Multiplication coefficient,
            defaults to 0.5.

    Returns:
        tuple: A tuple containing two elements: half_one_float_node (final
            multiplication node) and math_nodes (dict containing 'max' and
            'half_multiply' nodes).
    """
    # Equivalent of floatMath (multiply)
    max_float_node = pm.createNode("multiplyDivide", name=f"{root}_max_md")
    max_float_node.input1X.set(0.010)
    max_float_node.operation.set(1)  # 1 = multiply

    max_node = pm.createNode("max", name=f"{root.name()}_max")
    max_float_node.outputX >> max_node.input[0]

    length_nodes["eff"].output >> max_node.input[1]
    length_nodes["elbow"].output >> max_node.input[2]
    length_nodes["wrist"].output >> max_node.input[3]

    # Equivalent of floatMath (multiply)
    half_one_float_node = pm.createNode("multiplyDivide", name=f"{root}_half_one_md")
    half_one_float_node.input2X.set(float_value)
    half_one_float_node.operation.set(1)  # 1 = multiply
    max_node.output >> half_one_float_node.input1X

    math_nodes = {"max": max_node, "half_multiply": half_one_float_node}

    return half_one_float_node, math_nodes


def setup_cross_product_chain(root, elbow, wrist, vector_nodes, float_value):
    """
    Set up cross product calculation chain.

    Creates a complete cross product calculation node network to determine the pole vector direction.

    Arguments:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        vector_nodes (dict): Vector node dictionary.
        float_value (float): Coefficient used for length calculation.

    Returns:
        tuple: A tuple containing three elements:
            crossProduct_root_normalize_node, half_multiply_node, math_nodes.
    """
    length_nodes = calculate_vector_lengths(vector_nodes)
    half_multiply_node, math_nodes = setup_math_operations(
        root, length_nodes, float_value
    )

    normalize_elbow = pm.createNode("normalize", name=f"{elbow}_normalize")
    normalize_wrist = pm.createNode("normalize", name=f"{wrist}_normalize")

    for i, axis in enumerate(["X", "Y", "Z"]):
        getattr(vector_nodes["crossProduct_elbow"][i], "output") >> getattr(
            normalize_elbow, f"input{axis}"
        )
        getattr(vector_nodes["crossProduct_wrist"][i], "output") >> getattr(
            normalize_wrist, f"input{axis}"
        )

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

    crossProduct_wrist_elbow_sum_node = pm.createNode(
        "sum", name=f"{root}_crossProduct_wrist_elbow_sum"
    )

    crossProduct_wrist_elbow.outputX >> crossProduct_wrist_elbow_sum_node.input[0]
    crossProduct_wrist_elbow.outputY >> crossProduct_wrist_elbow_sum_node.input[1]
    crossProduct_wrist_elbow.outputZ >> crossProduct_wrist_elbow_sum_node.input[2]

    condition_node = pm.createNode("condition", name=f"{root}_condition")
    condition_node.secondTerm.set(0.000)

    crossProduct_wrist_elbow_sum_node.output >> condition_node.firstTerm
    crossProduct_default.output >> condition_node.colorIfTrue
    crossProduct_wrist_elbow.output >> condition_node.colorIfFalse

    normalize_condition_node = pm.createNode(
        "normalize", name=f"{root}_normalize_condition"
    )
    condition_node.outColor >> normalize_condition_node.input

    crossProduct_root = pm.createNode("crossProduct", name=f"{root}_crossProduct_root")
    normalize_condition_node.output >> crossProduct_root.input1

    for i, axis in enumerate(["X", "Y", "Z"]):
        getattr(vector_nodes["crossProduct_root"][i], "output") >> getattr(
            crossProduct_root, f"input2{axis}"
        )

    crossProduct_root_normalize_node = pm.createNode(
        "normalize", name=f"{root}_crossProduct_root_normalize"
    )
    crossProduct_root.output >> crossProduct_root_normalize_node.input

    return crossProduct_root_normalize_node, half_multiply_node, math_nodes


def setup_upv_position_calculation(
    elbow, upv, normalize_node, half_multiply_node, decompose_nodes
):
    """
    Calculate the final position of the UPV node.

    Determines the final position of the pole vector guide node based on cross product direction and length calculation.

    Arguments:
        elbow (PyNode): Elbow guide node.
        upv (PyNode): Pole vector guide node.
        normalize_node (PyNode): Normalized cross product direction node.
        half_multiply_node (PyNode): Length multiplication node.
        decompose_nodes (list): decomposeMatrix node list.
    """
    upv_pos_mul = create_vector_nodes(f"{elbow}_upv_pos", "multiply")
    upv_pos_sum = create_vector_nodes(f"{elbow}_upv_pos", "sum")
    if upv_pos_mul and upv_pos_sum:
        for i, axis in enumerate(["X", "Y", "Z"]):
            getattr(normalize_node, f"output{axis}") >> upv_pos_mul[i].input[0]
            half_multiply_node.outputX >> upv_pos_mul[i].input[1]

            upv_pos_mul[i].output >> upv_pos_sum[i].input[0]
            (
                getattr(decompose_nodes[1], f"outputTranslate{axis}")
                >> upv_pos_sum[i].input[1]
            )

            upv_pos_sum[i].output >> getattr(upv, f"translate{axis}")


def setup_visibility_and_matrix(root, root_decompose, upv, upvcrv):
    """
    Set up visibility and matrix connections.

    Ensures the UPV node and curve correctly inherit the root node's transformation.

    Arguments:
        root (PyNode): Root guide node.
        root_decompose (PyNode): Decompose matrix node from root.
        upv (PyNode): Pole vector guide node.
        upvcrv (PyNode): Pole vector display curve.
    """
    root_decompose.outputScale >> upv.scale
    root.worldInverseMatrix[0] >> upv.offsetParentMatrix
    root.worldInverseMatrix[0] >> upvcrv.offsetParentMatrix


def create_upv_system(root, elbow, wrist, eff, upvcrv, upv, float_value=0.5):
    """
    Create a complete UPV visualization system.

    Main function that coordinates all sub-functions to create a complete pole vector visualization system.

    Arguments:
        root (PyNode): Root guide node.
        elbow (PyNode): Elbow guide node.
        wrist (PyNode): Wrist guide node.
        eff (PyNode): End effector guide node.
        upvcrv (PyNode): Pole vector display curve node.
        upv (PyNode): Pole vector guide node.
        float_value (float, optional): Pole vector length coefficient,
            defaults to 0.5.

    Example:
        >>> create_upv_system('root_guide', 'elbow_guide', 'wrist_guide',
        ...                   'eff_guide', upv_curve, upv_node, 0.5)
    """
    decompose_nodes = upv_vis_decompose_nodes(root, elbow, wrist, eff)
    if decompose_nodes:
        vector_nodes = create_vector_subtraction_nodes(elbow, wrist, root, eff)
        connect_decompose_to_vector_nodes(decompose_nodes, vector_nodes)

        normalize_node, half_multiply_node, math_nodes = setup_cross_product_chain(
            root, elbow, wrist, vector_nodes, float_value
        )

        setup_upv_position_calculation(
            elbow, upv, normalize_node, half_multiply_node, decompose_nodes
        )

        setup_visibility_and_matrix(root, decompose_nodes[0], upv, upvcrv)
