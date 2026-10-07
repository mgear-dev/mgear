"""Blocking Ghosts - see your key poses side by side while blocking.

Creates static, semi-transparent ghosts of the character at the keyframes
of a set of watched controls. Ghosts are colored as previous / post
relative to the playhead, can be spread along the camera's right axis, and
clicking a ghost jumps to its frame.

Example:
    from mgear.animbits import blocking_ghosts
    blocking_ghosts.show()
"""

__version__ = "1.0.0"


def show(*args):
    """Show the Blocking Ghosts window.

    Returns:
        BlockingGhostsUI: The window instance.
    """
    from . import ui

    return ui.show()
