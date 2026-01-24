import mgear.pymaya as pm
from mgear.core import icon


def get_comp_root_by_family(guide_loc=None, comp_family="chain"):
    """Return the  component root locator name if is part of the family.


    Args:
        guide_loc (pm.PyNode or str, optional): Any locator in the
            component. If None, the current selection is used.

    Returns:
        str or None: Name of the component root locator if it is a
        chain component. None otherwise.
    """
    if not guide_loc:
        o_sel = pm.selected()
        if o_sel:
            guide_loc = o_sel[0]

    if not guide_loc:
        print("Nothing selected. Please select a guide locator.")
        return

    if not pm.attributeQuery("isGearGuide", node=guide_loc, ex=True):
        print("Selected is not a locator of a guide")
        return

    comp_type = False
    comp_root = False

    while guide_loc:
        if pm.attributeQuery("comp_type", node=guide_loc, ex=True):
            comp_type = guide_loc.attr("comp_type").get()
            if comp_family in comp_type:
                comp_root = guide_loc
                break
            else:
                print(f"Component is not of the family: {comp_family}")
                return
        elif pm.attributeQuery("ismodel", node=guide_loc, ex=True):
            print(f"Guide root selected, not a Component of family type: {comp_family}")
            return

        guide_loc = guide_loc.getParent()
        if not guide_loc:
            break
        pm.select(guide_loc)

    if not comp_root:
        return

    return comp_root.name()


def _rebuild_display_curve(base_name, centers):
    """Rebuild the chain connection curve keeping alwaysDrawOnTop input.

    Args:
        base_name (str): Base name of the chain (e.g. 'chain_C0').
        centers (list[pm.PyNode]): Ordered nodes for the curve centers.

    Returns:
        pm.PyNode or None: New curve node or None if not created.
    """
    curve_name = "{0}_crv".format(base_name)
    old_curves = pm.ls(curve_name)

    alw_on_top_attr = None
    if old_curves:
        always_attr = old_curves[0].attr("alwaysDrawOnTop")
        conns = always_attr.connections(p=True)
        if conns:
            alw_on_top_attr = conns[0]
        pm.delete(old_curves)

    if len(centers) < 2:
        # Not enough points to build a curve
        return None

    new_crv = icon.connection_display_curve(curve_name, centers)

    if alw_on_top_attr:
        pm.connectAttr(alw_on_top_attr, new_crv.attr("alwaysDrawOnTop"))

    return new_crv

#############################
# Chain tools functions
#############################


def _get_chain_index(node):
    """Return numeric chain index from a locator name.

    Expected pattern: <prefix>_<index>_loc

    Args:
        node (pm.PyNode): Locator node.

    Returns:
        int: Parsed index or -1 if not found.
    """
    name = node.name()
    parts = name.split("_")
    if len(parts) < 3:
        return -1
    try:
        return int(parts[-2])
    except ValueError:
        return -1


def add_chain_locator(guide_loc=None):
    """Extend an mGear chain component by adding a new locator.

    Args:
        guide_loc (pm.PyNode or str, optional): Any locator belonging
            to the chain guide. If None, the current selection is used.

    Returns:
        pm.PyNode or None: The new locator, or None on failure.
    """
    # Get component root and ensure it is a CHAIN component
    comp_root_name = get_comp_root_by_family(guide_loc)
    if not comp_root_name:
        return

    comp_root = pm.PyNode(comp_root_name)

    # Base name from root: "chain_C0_root" -> "chain_C0"
    root_name = comp_root.name()
    if not root_name.endswith("_root"):
        print(
            "Component root name does not end with '_root': {0}".format(
                root_name
            )
        )
        return

    base_name = root_name[:-5]  # strip "_root"

    # Collect chain locators: "base_index_loc"
    loc_pattern = "{0}_*_loc".format(base_name)
    all_locs = pm.ls(loc_pattern, type="transform") or []

    # Filter only those with a valid numeric index and sort by index
    chain_locs = [n for n in all_locs if _get_chain_index(n) >= 0]
    if not chain_locs:
        print(
            "No chain locators found for base '{0}'".format(base_name)
        )
        return

    chain_locs = sorted(chain_locs, key=_get_chain_index)

    # Build ordered list from root to last locator
    ordered_nodes = [comp_root] + chain_locs

    if len(ordered_nodes) <= 2:
        print("Not enough nodes to extend the chain.")
        return

    last_loc = ordered_nodes[-1]
    prev_loc = ordered_nodes[-2]

    # Compute vector from prev -> last in world space
    prev_pos = prev_loc.getTranslation(space="world")
    last_pos = last_loc.getTranslation(space="world")
    delta = last_pos - prev_pos
    new_pos = last_pos + delta

    # Determine new index and name
    last_index = _get_chain_index(last_loc)
    if last_index < 0:
        new_index = len(chain_locs)
    else:
        new_index = last_index + 1

    new_name = "{0}_{1}_loc".format(base_name, new_index)

    # Duplicate last locator, parent under last, move to extrapolated pos
    new_loc = pm.duplicate(last_loc, n=new_name)[0]
    pm.parent(new_loc, last_loc)
    new_loc.setTranslation(new_pos, space="world")

    # Rebuild the connection curve: <base>_crv
    centers = ordered_nodes + [new_loc]
    _rebuild_display_curve(base_name, centers)

    pm.select(new_loc)
    print("Added new chain locator: {0}".format(new_loc.name()))

    return new_loc


def delete_chain_locator(guide_loc=None):
    """Remove the last locator of an mGear chain component.

    Args:
        guide_loc (pm.PyNode or str, optional): Any locator belonging
            to the chain guide. If None, the current selection is used.

    Returns:
        pm.PyNode or None: The new last locator after deletion, or
        None on failure.
    """
    # Get component root and ensure it is a CHAIN component
    comp_root_name = get_comp_root_by_family(guide_loc)
    if not comp_root_name:
        return

    comp_root = pm.PyNode(comp_root_name)

    # Base name from root: "chain_C0_root" -> "chain_C0"
    root_name = comp_root.name()
    if not root_name.endswith("_root"):
        print(
            "Component root name does not end with '_root': {0}".format(
                root_name
            )
        )
        return

    base_name = root_name[:-5]  # strip "_root"

    # Collect chain locators: "base_index_loc"
    loc_pattern = "{0}_*_loc".format(base_name)
    all_locs = pm.ls(loc_pattern, type="transform") or []

    # Filter only those with a valid numeric index and sort by index
    chain_locs = [n for n in all_locs if _get_chain_index(n) >= 0]
    if not chain_locs:
        print(
            "No chain locators found for base '{0}'".format(base_name)
        )
        return

    chain_locs = sorted(chain_locs, key=_get_chain_index)

    # Build ordered list from root to last locator
    ordered_nodes = [comp_root] + chain_locs

    if len(ordered_nodes) < 2:
        print("Not enough nodes in the chain to delete.")
        return

    # Last node must be a locator, not the root
    last_loc = ordered_nodes[-1]
    prev_loc = ordered_nodes[-2]

    if last_loc == comp_root:
        print("Last element is the component root. Nothing to delete.")
        return

    # Delete the last locator
    pm.delete(last_loc)

    # Remaining centers for the curve (from root to new last element)
    remaining_chain_locs = chain_locs[:-1]
    centers = [comp_root] + remaining_chain_locs

    # Rebuild the connection curve: <base>_crv
    _rebuild_display_curve(base_name, centers)

    # If there are remaining locators, select the new last one
    if remaining_chain_locs:
        new_last = remaining_chain_locs[-1]
        pm.select(new_last)
        print(
            "Deleted last chain locator. New last locator: {0}".format(
                new_last.name()
            )
        )
        return new_last

    # Only the root remains
    pm.select(comp_root)
    print(
        "Deleted last chain locator. Only component root remains: {0}"
        .format(comp_root.name())
    )
    return comp_root


# Snippets:
# add_chain_locator()
# delete_chain_locator()
