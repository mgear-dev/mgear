"""Built-in dag menu sections for mGear rig controls."""

from functools import partial

from maya import cmds

import mgear.pymaya as pm
from mgear.core import anim_utils
from mgear.core import transform

CONTEXT = "control"
ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")


# =============================================================================
# commands
# =============================================================================


def _short(node):
    return node.split("|")[-1]


def _with_namespace(namespace, name):
    return "{}:{}".format(namespace, name) if namespace else name


def select_host(control):
    """Select the ui host of a control.

    Args:
        control (str): Rig control.
    """
    cmds.select(anim_utils.get_host_from_node(control))


def on_controls(ctx, controls, command, *args, **kwargs):
    """Run a command on a control list of the context, resolved on click.

    The child and rig control lists are only queried when the menu item is
    clicked, not when the menu is built.

    Args:
        ctx (MenuContext): The right-click context.
        controls (str): Context control list. "child_controls" or
            "all_controls".
        command (callable): Called with the control list, args and kwargs.
        *args: Extra command arguments.
        **kwargs: Command keyword arguments.
    """
    command(getattr(ctx, controls), *args, **kwargs)


def reset_transforms(nodes, translate=True, rotate=True, scale=True):
    """Reset the transform channels of nodes.

    Args:
        nodes (list): Nodes to reset.
        translate (bool, optional): Reset translation.
        rotate (bool, optional): Reset rotation.
        scale (bool, optional): Reset scale.
    """
    for node in nodes:
        transform.resetTransform(pm.PyNode(node), t=translate, r=rotate, s=scale)


def switch_ikfk(ui_host, attr, key=False):
    """Match and switch IK/FK for the components sharing a blend attribute.

    Args:
        ui_host (str): Node with the blend attribute.
        attr (str): Blend attribute. i.e: "arm_blend" or "arm_Switch"
        key (bool, optional): Key the matched controls.
    """
    switch_control = _short(ui_host)
    namespace = anim_utils.getNamespace(switch_control)
    fk_list, ik_dict, components = anim_utils.get_ikfk_components(switch_control, attr)

    if "_Switch" in attr:
        anim_utils.ikFkMatch_with_namespace2(
            namespace=namespace,
            ikfk_attr=attr,
            ui_host=switch_control,
            fk_controls=fk_list,
            ik_controls=ik_dict,
            keyframe=key,
            ik_val=False,
            fk_val=True,
        )
        return

    blend_plug = "{}.{}".format(switch_control, attr)
    init_val = None
    for ik_controls, fk_controls in components:
        if not (ik_controls["ik_control"] and fk_controls):
            continue
        # every component is matched from the same initial blend value
        if init_val is None:
            init_val = cmds.getAttr(blend_plug)
        else:
            cmds.setAttr(blend_plug, init_val)
        anim_utils.ikFkMatch_with_namespace(
            namespace=namespace,
            ikfk_attr=attr,
            ui_host=switch_control,
            fks=fk_controls,
            ik=ik_controls["ik_control"],
            upv=ik_controls["pole_vector"],
            ik_rot=ik_controls["ik_rot"],
            key=key,
            ik_controls=ik_controls,
            ik_val=1.0,
            fk_val=0.0,
        )


def range_switch(ui_host, attr):
    """Open the IK/FK range transfer window.

    Args:
        ui_host (str): Node with the blend attribute.
        attr (str): Blend attribute.
    """
    switch_control = _short(ui_host)
    fk_list, _, components = anim_utils.get_ikfk_components(switch_control, attr)
    if not components:
        return
    ik_list = []
    upv_list = []
    ik_rot_list = []
    merged = {}
    for ik_controls, _ in components:
        found = {k: v for k, v in ik_controls.items() if v is not None}
        merged.update(found)
        if not found:
            continue
        if "ik_control" in merged:
            ik_list.append(merged["ik_control"])
        if "pole_vector" in merged:
            upv_list.append(merged["pole_vector"])
        if "ik_rot" in merged:
            ik_rot_list.append(merged["ik_rot"])

    anim_utils.IkFkTransfer.showUI(
        model=anim_utils.find_rig_root(ui_host) or "",
        ikfk_attr=attr,
        uihost=anim_utils.stripNamespace(switch_control),
        fks=fk_list,
        ik=ik_list,
        upv=upv_list,
        ikRot=ik_rot_list,
    )


def switch_space(ui_host, attr, index):
    """Switch a space keeping the pose of the controls it moves.

    When the switch attribute is animated, the controls and the attribute
    are keyed on the previous and the current frame.

    Args:
        ui_host (str): Node with the space switch attribute.
        attr (str): Space switch attribute.
        index (int): Target space index.
    """
    switch_control = _short(ui_host)
    namespace = anim_utils.getNamespace(switch_control)
    targets = anim_utils.get_space_switch_targets(switch_control, attr)
    root = anim_utils.find_rig_root(ui_host)
    if not root or not targets:
        pm.displayInfo("Not root or target control list for space transfer")
        return

    plug = "{}.{}".format(switch_control, attr)
    autokey = cmds.listConnections(plug, type="animCurve")
    if autokey:
        frame = cmds.currentTime(query=True)
        for target in targets:
            cmds.setKeyframe(_with_namespace(namespace, target), plug, time=frame - 1.0)

    anim_utils.changeSpace(root, switch_control, attr, index, targets)

    if autokey:
        for target in targets:
            cmds.setKeyframe(_with_namespace(namespace, target), plug, time=frame)


def space_transfer(ui_host, attr):
    """Open the space transfer window.

    Args:
        ui_host (str): Node with the space switch attribute.
        attr (str): Space switch attribute.
    """
    switch_control = _short(ui_host)
    targets = anim_utils.get_space_switch_targets(
        switch_control, attr, fallback_role="ctl"
    )
    root = anim_utils.find_rig_root(ui_host)
    if not root or not targets:
        pm.displayInfo("Not root or target control list for space transfer")
        return
    spaces = cmds.addAttr(
        "{}.{}".format(switch_control, attr), query=True, enumName=True
    ).split(":")
    anim_utils.ParentSpaceTransfer.showUI(
        spaces,
        switch_control,
        anim_utils.stripNamespace(switch_control),
        attr,
        targets[0],
    )


# =============================================================================
# sections
# =============================================================================


def _build_select_host(builder, ctx):
    builder.item(
        "Select host",
        partial(select_host, ctx.node),
        image="hotkeySetSettings.png",
    )


def _build_ikfk_switch(builder, ctx):
    for attr, suffix in ctx.ikfk_attrs:
        state = cmds.getAttr("{}.{}".format(ctx.ui_host, attr))
        if suffix == "_blend":
            states = {0: "Fk", 1: "Ik"}
        else:
            states = {0: "IK", 1: "Fk"}
        target = states[int(not state)]
        name = attr.split(suffix)[0]
        builder.item(
            "Switch {} to {}".format(name, target),
            partial(switch_ikfk, ctx.ui_host, attr, key=False),
            image="kinReroot.png",
        )
        builder.item(
            "Switch {} to {} + Key".format(name, target),
            partial(switch_ikfk, ctx.ui_host, attr, key=True),
            image="character.svg",
        )
        builder.item("Range switch", partial(range_switch, ctx.ui_host, attr))
        builder.divider()


def _build_select_children(builder, ctx):
    builder.item(
        "Select child controls",
        partial(on_controls, ctx, "child_controls", cmds.select, add=True),
        image="dagNode.svg",
    )


def _build_reset(builder, ctx):
    builder.item(
        "Reset",
        partial(anim_utils.reset_all_keyable_attributes, ctx.selection),
        image="holder.svg",
    )
    with builder.submenu("Reset Option") as sub:
        sub.item(
            "Reset all",
            partial(
                on_controls,
                ctx,
                "all_controls",
                anim_utils.reset_all_keyable_attributes,
            ),
        )
        sub.item(
            "Reset all below",
            partial(
                on_controls,
                ctx,
                "child_controls",
                anim_utils.reset_all_keyable_attributes,
            ),
        )
        sub.item("Reset To BindPose", partial(anim_utils.bindPose, ctx.selection[0]))
        sub.divider()
        sub.item(
            "Reset All SRT",
            partial(on_controls, ctx, "all_controls", reset_transforms),
        )

        keyable = cmds.listAttr(ctx.node, keyable=True) or []
        icons = {"translate": "move_M.png"}
        for attr in ("translate", "rotate", "scale"):
            # only for the transform attributes with keyable channels
            if not [x for x in keyable if attr in x and len(x) == len(attr) + 1]:
                continue
            sub.item(
                "Reset {}".format(attr),
                partial(
                    reset_transforms,
                    ctx.selection,
                    translate=attr == "translate",
                    rotate=attr == "rotate",
                    scale=attr == "scale",
                ),
                image=icons.get(attr, "{}_M.png".format(attr)),
            )


def mirror_and_tell(command, *args, **kwargs):
    """Run a mirror or flip and say in the viewport what it keyed.

    Args:
        command (callable): ``anim_utils.mirror_controls`` or a full pose
            mirror, returning its result.
        *args: The command arguments.
        **kwargs: The command keyword arguments.
    """
    anim_utils.show_mirror_message(command(*args, **kwargs))


def _build_mirror_flip(builder, ctx):
    mirror = partial(mirror_and_tell, anim_utils.mirror_controls)
    builder.item(
        "Mirror",
        partial(mirror, ctx.selection, flip=False),
        image="redrawPaintEffects.png",
    )
    builder.item(
        "Mirror all below",
        partial(on_controls, ctx, "child_controls", mirror, flip=False),
    )
    builder.item("Flip", partial(mirror, ctx.selection, flip=True), image="redo.png")
    builder.item(
        "Flip all below",
        partial(on_controls, ctx, "child_controls", mirror, flip=True),
    )
    with builder.submenu("Full Pose") as sub:
        _add_full_pose_items(sub, ctx.selection)
        sub.divider()
        for control_set in anim_utils.get_rig_control_sets(ctx.selection):
            with sub.submenu(control_set) as set_menu:
                _add_full_pose_items(set_menu, ctx.selection, control_set)


def _add_full_pose_items(builder, selection, control_set=None):
    """Add the Mirror L to R, Mirror R to L and Flip full pose items."""
    for source, target in (("L", "R"), ("R", "L")):
        builder.item(
            "Mirror {} → {}".format(source, target),
            partial(
                mirror_and_tell,
                anim_utils.mirror_full_pose,
                selection,
                source,
                control_set=control_set,
            ),
        )
    builder.item(
        "Flip",
        partial(
            mirror_and_tell,
            anim_utils.flip_full_pose,
            selection,
            control_set=control_set,
        ),
    )


def _poll_rotate_order(ctx):
    plug = "{}.rotateOrder".format(ctx.node)
    return cmds.getAttr(plug, channelBox=True) or (
        cmds.getAttr(plug, keyable=True) and not cmds.getAttr(plug, lock=True)
    )


def _build_rotate_order(builder, ctx):
    current = cmds.getAttr("{}.rotateOrder".format(ctx.node))
    with builder.submenu("Rotate Order switch", radio=True) as sub:
        for idx, order in enumerate(ROTATE_ORDERS):
            sub.item(
                order,
                partial(anim_utils.change_rotate_order, ctx.node, order),
                radioButton=idx == current,
            )


def _build_spaces(builder, ctx):
    for ui_host, attr in ctx.space_attrs:
        part = attr.split("_")[0]
        _, ctl = anim_utils.parse_space_attr(attr)
        plug = "{}.{}".format(ui_host, attr)
        spaces = cmds.addAttr(plug, query=True, enumName=True).split(":")
        current = cmds.getAttr(plug)
        with builder.submenu(
            "Parent {} {}".format(part, ctl),
            image="dynamicConstraint.svg",
            radio=True,
        ) as sub:
            for idx, space in enumerate(spaces):
                sub.item(
                    space,
                    partial(switch_space, ui_host, attr, idx),
                    radioButton=idx == current,
                )
            sub.item("++ Space Transfer ++", partial(space_transfer, ui_host, attr))


def _build_select_all_keyframe(builder, ctx):
    builder.item(
        "Select all controls",
        partial(on_controls, ctx, "all_controls", cmds.select, add=True),
    )
    builder.item(
        "Keyframe child controls",
        partial(on_controls, ctx, "child_controls", cmds.setKeyframe),
        image="setKeyframe.png",
    )


def _build_xray(builder, ctx):
    builder.item(
        "X-Ray CTL Toggle",
        partial(anim_utils.toggle_ctl_xray, ctx.node),
        image="mgear_x.svg",
    )


def register(registry):
    """Register the built-in control sections.

    Args:
        registry (Registry): Dag menu registry.
    """
    registry.register_section(
        CONTEXT,
        "select_host",
        100,
        _build_select_host,
        poll=lambda ctx: cmds.attributeQuery("uiHost", node=ctx.node, exists=True),
    )
    registry.register_section(
        CONTEXT,
        "ikfk_switch",
        200,
        _build_ikfk_switch,
        poll=lambda ctx: bool(ctx.ikfk_attrs),
    )
    registry.register_section(CONTEXT, "select_children", 300, _build_select_children)
    registry.register_section(CONTEXT, "reset", 400, _build_reset)
    registry.register_section(CONTEXT, "mirror_flip", 500, _build_mirror_flip)
    registry.register_section(
        CONTEXT,
        "rotate_order",
        600,
        _build_rotate_order,
        poll=_poll_rotate_order,
    )
    registry.register_section(
        CONTEXT,
        "spaces",
        700,
        _build_spaces,
        poll=lambda ctx: bool(ctx.space_attrs),
    )
    registry.register_section(
        CONTEXT, "select_all_keyframe", 800, _build_select_all_keyframe
    )
    registry.register_section(CONTEXT, "xray", 900, _build_xray)
