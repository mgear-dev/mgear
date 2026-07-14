"""Maya attribute binding for interactive picker widgets.

A widget item (checkbox / slider) can drive a Maya attribute. This module is
the single place that reads and writes those attributes safely: a missing,
locked, or incoming-connected attribute is skipped with a warning rather than
raising, so an interaction on a rig that has changed never throws. Slider drags
are wrapped in one undo chunk via :func:`undo_chunk` so a whole drag is a
single undo step.

The pure value <-> range mapping lives in the Qt-free
``widgets.widget_binding`` module; this module only touches ``maya.cmds``.
"""

from contextlib import contextmanager

from maya import cmds

import mgear


def resolve_attr(attr, namespace=None):
    """Return ``attr`` with the item's namespace applied to its node token.

    Bindings store the attribute as ``node.attr`` without a namespace (like
    control names), so the namespace is prefixed at runtime when the item has
    one and the node is not already namespaced.

    Args:
        attr (str): a ``node.attr`` string, or None / empty.
        namespace (str, optional): namespace to prefix onto the node.

    Returns:
        str: the resolved ``node.attr`` (unchanged when there is nothing to
        do), or an empty string for an empty input.
    """
    if not attr:
        return ""
    if not namespace or ":" in attr:
        return attr
    if "." not in attr:
        return "{}:{}".format(namespace, attr)
    node, _, plug = attr.partition(".")
    return "{}:{}.{}".format(namespace, node, plug)


def is_settable(attr):
    """Return True when ``attr`` exists and can be written.

    Guards the three cases that would make a widget write fail: the attribute
    does not exist, it is locked, or it has an incoming connection (a driven /
    constrained attribute). Any of these logs a warning and returns False.

    Args:
        attr (str): a resolved ``node.attr`` string.

    Returns:
        bool: True when a ``setAttr`` would succeed.
    """
    if not attr or not cmds.objExists(attr):
        mgear.log(
            "anim_picker: widget attribute '{}' not found".format(attr),
            mgear.sev_warning,
        )
        return False
    if cmds.getAttr(attr, lock=True):
        mgear.log(
            "anim_picker: widget attribute '{}' is locked".format(attr),
            mgear.sev_warning,
        )
        return False
    if cmds.connectionInfo(attr, isDestination=True):
        mgear.log(
            "anim_picker: widget attribute '{}' is connected "
            "(read-only)".format(attr),
            mgear.sev_warning,
        )
        return False
    return True


def read_attr(attr):
    """Return the value of ``attr``, or None when it cannot be read.

    A missing attribute returns None silently (the caller falls back to a
    default); it is not an error to read a widget whose target is absent.

    Args:
        attr (str): a resolved ``node.attr`` string.

    Returns:
        The attribute value, or None.
    """
    if not attr or not cmds.objExists(attr):
        return None
    try:
        return cmds.getAttr(attr)
    except Exception:
        return None


def write_attr(attr, value):
    """Set ``attr`` to ``value`` when it is settable; never raise.

    Args:
        attr (str): a resolved ``node.attr`` string.
        value: the value to set.

    Returns:
        bool: True when the attribute was written.
    """
    if not is_settable(attr):
        return False
    try:
        cmds.setAttr(attr, value)
        return True
    except Exception as exc:
        mgear.log(
            "anim_picker: failed to set '{}' -> {} ({})".format(
                attr, value, exc
            ),
            mgear.sev_warning,
        )
        return False


def toggle_attr(attr):
    """Flip a boolean ``attr`` and return the new state, or None on failure.

    Args:
        attr (str): a resolved ``node.attr`` string.

    Returns:
        bool: the new state, or None when the attribute could not be toggled.
    """
    current = read_attr(attr)
    if current is None:
        return None
    new_state = not bool(current)
    if write_attr(attr, new_state):
        return new_state
    return None


@contextmanager
def undo_chunk():
    """Group the wrapped Maya edits into a single undo step."""
    cmds.undoInfo(openChunk=True)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)
