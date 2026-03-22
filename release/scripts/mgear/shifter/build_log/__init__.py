"""Shifter Build Log.

Qt-based build log window with color-coded severity, filtering,
right-click file opening, log export, and log comparison.

Replaces the old MEL-based cmdScrollFieldReporter log window.
"""

import mgear

from .ui import BuildLogWindow


def log_window():
    """Show the build log window if logging is enabled.

    Drop-in replacement for the old MEL-based log window.
    Called by ``shifter.log_window()`` at build start.
    """
    if mgear.logMode and mgear.use_log_window:
        show_build_log()


def show_build_log():
    """Show the Qt build log window, creating it if needed.

    Returns:
        BuildLogWindow: The window instance.
    """
    return BuildLogWindow.show_window()


def get_instance():
    """Get the current build log window instance.

    Returns:
        BuildLogWindow: The singleton instance, or None.
    """
    return BuildLogWindow.get_instance()
