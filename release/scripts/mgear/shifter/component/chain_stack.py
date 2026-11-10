"""Shared helpers for the stackable chain components.

A master chain exposes ``fk_local_out`` and ``fk_global_out`` lists of
transforms, one per segment. A slave chain has ``fk_local_in`` and
``fk_global_in`` transforms taking those outputs, picked with the
``masterChainLocal`` and ``masterChainGlobal`` guide settings.
Some masters also have the twist, wide and depth ``_out`` setup attributes
on their root (see ``STACK_CHANNELS``).
"""

import mgear.pymaya as pm
from mgear.core import node

# twist, wide and depth channels passed from a master root to a slave root,
# with their rest value
STACK_CHANNELS = (
    ("mid_twist", 0),
    ("tip_twist", 0),
    ("mid_wide", 1),
    ("tip_wide", 1),
    ("mid_depth", 1),
    ("tip_depth", 1),
)


def chain_segments_length(chain_root):
    """Return the number of guide positions of a chain guide.

    Args:
        chain_root (dagNode): Root of a chain component guide.

    Returns:
        int: Number of positions (root and locators) of the guide.
    """
    from mgear import shifter

    module = shifter.importComponentGuide(chain_root.attr("comp_type").get())
    comp_guide = module.Guide()
    comp_guide.setFromHierarchy(chain_root)
    return len(comp_guide.pos)


def check_master_chain(self_root, master_root, compatible):
    """Check a guide root can be the master chain of a chain guide.

    Args:
        self_root (dagNode): Root of the slave chain guide.
        master_root (dagNode): Root picked as master.
        compatible (list or tuple): Component types accepted as master.

    Returns:
        tuple: The master component name (str or None) and a warning
            message (str or None). One of them is always None.
    """
    if master_root == self_root:
        return None, "Self root can not be Master. Cycle Warning"
    if not (
        isinstance(master_root, pm.nodetypes.Transform)
        and master_root.hasAttr("comp_type")
        and master_root.attr("comp_type").get() in compatible
    ):
        return None, (
            "The selected element is not a chain root or compatible chain. "
            "Compatible chain components are: {}".format(", ".join(compatible))
        )
    self_len = chain_segments_length(self_root)
    master_len = chain_segments_length(master_root)
    if master_len < self_len:
        return None, (
            "Invalid Master: {}. Current chain has: {} sections but Master "
            "chain has less sections: {}".format(master_root, self_len, master_len)
        )
    return master_root.name().replace("_root", ""), None


def master_index(index, offset, master_count):
    """Return the master output index a slave segment connects to.

    Args:
        index (int): Slave segment index.
        offset (int): Connection offset of the slave.
        master_count (int): Number of master outputs.

    Returns:
        int: ``index + offset``, or the last master output when it is past
            the end.
    """
    return min(index + offset, master_count - 1)


def connect_master(master_out, slave_in, index, offset, blend_attr):
    """Connect a master chain output to a slave chain input with a blend.

    Translate and rotate go through one pairBlend, scale through another
    one blending from a scale of 1.

    Args:
        master_out (list): Master output transforms.
        slave_in (list): Slave input transforms.
        index (int): Slave segment index.
        offset (int): Connection offset of the slave.
        blend_attr (Attribute): Blend attribute, 0 is the slave rest pose
            and 1 follows the master.
    """
    m_out = master_out[master_index(index, offset, len(master_out))]
    s_in = slave_in[index]
    pb_rt = node.createPairBlend(inputB=m_out, blender=blend_attr)
    pm.connectAttr(pb_rt.outTranslate, s_in.translate)
    pm.connectAttr(pb_rt.outRotate, s_in.rotate)
    pb_s = node.createPairBlend(blender=blend_attr)
    pm.connectAttr(m_out.scale, pb_s.inTranslate2)
    pm.setAttr(pb_s.inTranslate1, [1, 1, 1])
    pm.connectAttr(pb_s.outTranslate, s_in.scale)


def connect_stack_channels(master_root, slave_root):
    """Connect the master twist, wide and depth outputs to the slave inputs.

    Only the channels the master root has are connected, so a master
    without them (lite_chain_stack) leaves the slave inputs at their
    default values.

    Args:
        master_root (dagNode): Root of the master component rig.
        slave_root (dagNode): Root of the slave component rig.

    Returns:
        list: Names of the connected channels.
    """
    connected = []
    for channel, _default in STACK_CHANNELS:
        out_name = channel + "_out"
        in_name = channel + "_in"
        if master_root.hasAttr(out_name) and slave_root.hasAttr(in_name):
            pm.connectAttr(master_root.attr(out_name), slave_root.attr(in_name))
            connected.append(channel)
    return connected
