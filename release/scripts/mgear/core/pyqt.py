"""pyQt/pySide widgets and helper functions for mGear"""

#############################################
# GLOBAL
#############################################
import contextlib
import json
import logging
import os
import re
import tempfile
import traceback
from functools import partial
from html import escape
import maya.OpenMayaUI as omui
import mgear.pymaya as pm
from mgear.pymaya import versions
from maya import cmds

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCompat
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtSvg
from mgear.vendor.Qt import QtCore
PY2 = False

# Try importing PySide6, fall back to PySide2 if not available
try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QPoint
except ImportError:
    from PySide2.QtGui import QGuiApplication
    from PySide2.QtCore import QPoint

UI_EXT = "ui"

_LOGICAL_DPI_KEY = "_LOGICAL_DPI"
# QIcons of the icons folder, by file name
_ICON_CACHE = {}

#################
# Old qt importer
#################


def _qt_import(binding, shi=False, cui=False):
    QtGui = None
    QtCore = None
    QtWidgets = None
    wrapInstance = None

    if binding == "PySide2":
        from PySide2 import QtGui, QtCore, QtWidgets
        import shiboken2 as shiboken
        from shiboken2 import wrapInstance

        if versions.current() < 20220000:
            from pyside2uic import compileUi

    elif binding == "PySide6":
        from PySide6 import QtGui, QtCore, QtWidgets
        import shiboken6 as shiboken
        from shiboken6 import wrapInstance

        if versions.current() < 20220000:
            from pyside2uic import compileUi

    elif binding == "PySide":
        from PySide import QtGui, QtCore
        import PySide.QtGui as QtWidgets
        import shiboken
        from shiboken import wrapInstance
        from pysideuic import compileUi

    elif binding == "PyQt4":
        from PyQt4 import QtGui
        from PyQt4 import QtCore
        import PyQt4.QtGui as QtWidgets
        from sip import wrapinstance as wrapInstance
        from PyQt4.uic import compileUi

        print("Warning: 'shiboken' is not supported in 'PyQt4' Qt binding")
        shiboken = None

    else:
        raise Exception("Unsupported python Qt binding '%s'" % binding)

    rv = [QtGui, QtCore, QtWidgets, wrapInstance]
    if shi:
        rv.append(shiboken)
    if cui:
        rv.append(compileUi)
    return rv


def qt_import(shi=False, cui=False):
    """
    import pyside/pyQt

    Returns:
        multi: QtGui, QtCore, QtWidgets, wrapInstance

    """
    lookup = ["PySide6", "PySide2", "PySide", "PyQt4"]

    preferredBinding = os.environ.get("MGEAR_PYTHON_QT_BINDING", None)
    if preferredBinding is not None and preferredBinding in lookup:
        lookup.remove(preferredBinding)
        lookup.insert(0, preferredBinding)

    for binding in lookup:
        try:
            return _qt_import(binding, shi, cui)
        except Exception:
            pass

    raise _qt_import("ThisBindingSurelyDoesNotExist", False, False)


#############################################
# helper Maya pyQt functions
#############################################

if versions.current() < 20220000:
    compileUi = qt_import(shi=True, cui=True)[-1]

    def ui2py(filePath=None, *args):
        """Convert qtDesigner .ui files to .py"""

        if not filePath:
            startDir = pm.workspace(q=True, rootDirectory=True)
            filePath = pm.fileDialog2(
                dialogStyle=2,
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="PyQt Designer (*%s)" % UI_EXT,
                okc="Compile to .py",
            )
            if not filePath:
                return False
            filePath = filePath[0]
        if not filePath:
            return False

        if not filePath.endswith(UI_EXT):
            filePath += UI_EXT
        compiledFilePath = filePath[:-2] + "py"
        pyfile = open(compiledFilePath, "w")
        compileUi(filePath, pyfile, False, 4, False)
        pyfile.close()

        info = "PyQt Designer file compiled to .py in: "
        pm.displayInfo(info + compiledFilePath)


def maya_main_window():
    """Get Maya's main window

    Returns:
        QMainWindow: main window, or None when Maya has no main window
            (mayapy and batch mode).

    """

    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is None:
        return None
    if PY2:
        return QtCompat.wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
    return QtCompat.wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


def can_show_ui():
    """Tell if Maya can show tool windows and dialogs.

    It can't in batch mode and mayapy, where there is no main window.

    Returns:
        bool: True when Maya has a main window.
    """
    return omui.MQtUtil.mainWindow() is not None


def center_window_on_screen(window):
    """Center the given window on the primary screen.

    Args:
        window (QWidget): The window to center.
    """
    # Get the primary screen (compatible with PySide2 and PySide6)
    screen = QGuiApplication.primaryScreen()

    # Get the screen's rectangle (geometry)
    screen_geometry = screen.geometry()

    # Get the center point of the screen
    screen_center = screen_geometry.center()

    # Get the rectangle of the window
    window_geometry = window.frameGeometry()

    # Get the center point of the window
    window_center = window_geometry.center()

    # Move the window to the center of the screen
    window.move(QPoint(screen_center - window_center))


def showDialog(dialog, dInst=True, dockable=False, *args):
    """
    Show the defined dialog window

    Attributes:
        dialog (QDialog): The window to show.

    Returns:
        QDialog: The window, or None when Maya can't show UI (batch mode).
    """
    if not can_show_ui():
        return None
    if dInst:
        try:
            for c in maya_main_window().children():
                if isinstance(c, dialog):
                    c.deleteLater()
        except Exception:
            pass

    # Create minimal dialog object

    # if versions.current() >= 20180000:
    #     windw = dialog(maya_main_window())
    # else:
    windw = dialog()

    # ensure clean workspace name
    if hasattr(windw, "toolName") and dockable:
        control = windw.toolName + "WorkspaceControl"
        if pm.workspaceControl(control, q=True, exists=True):
            pm.workspaceControl(control, e=True, close=True)
            pm.deleteUI(control, control=True)
    # desktop = QtWidgets.QApplication.desktop()
    # screen = desktop.screen()
    # screen_center = screen.rect().center()
    # windw_center = windw.rect().center()
    # windw.move(screen_center - windw_center)
    center_window_on_screen(windw)

    # Delete the UI if errors occur to avoid causing winEvent
    # and event errors (in Maya 2014)
    try:
        if dockable:
            windw.show(dockable=True)
        else:
            windw.show()
        return windw
    except Exception:
        windw.deleteLater()
        traceback.print_exc()


def deleteInstances(dialog, checkinstance):
    """Delete any instance of a given dialog

    Delete any instance of a given dialog and if the dialog is
    instance of checkinstance.

    Attributes:
        dialog (QDialog): The dialog to delete.
        checkinstance (QDialog): The instance to check the type of dialog.

    """
    if not can_show_ui():
        return
    mayaMainWindow = maya_main_window()
    for obj in mayaMainWindow.children():
        if isinstance(obj, checkinstance):
            if obj.widget().objectName() == dialog.toolName:
                print(("Deleting instance {0}".format(obj)))
                mayaMainWindow.removeDockWidget(obj)
                obj.setParent(None)
                obj.deleteLater()


def fakeTranslate(*args):
    """Fake Translation

    fake QApplication.translate. This function helps to bypass the
    incompativility for the Unicode utf8  deprecated in pyside2

    """
    return args[1]


def position_window(window):
    """set the position for the windonw

    Function borrowed from Cesar Saez QuickLauncher
    Args:
        window (QtWidget): the window to position
    """
    pos = QtGui.QCursor.pos()
    window.move(pos.x(), pos.y())


def get_main_window(widget=None):
    """Get the active window

    Function borrowed from Cesar Saez QuickLauncher
    Args:
        widget (QtWidget, optional): window

    Returns:
        QtWidget: parent of the window
    """
    widget = widget or QtWidgets.QApplication.activeWindow()
    if widget is None:
        return
    parent = widget.parent()
    if parent is None:
        return widget
    return get_main_window(parent)


def get_instance(parent, gui_class):
    """Get instace of a window from a given parent

    Function borrowed from Cesar Saez QuickLauncher
    Args:
        parent (QtWidget): parent
        gui_class (QtWidget): instance class to check

    """
    for children in parent.children():
        if isinstance(children, gui_class):
            return children
    return None


def get_top_level_widgets(class_name=None, object_name=None):
    """
    Get existing widgets for a given class name

    Args:
        class_name (str): Name of class to search top level widgets for
        object_name (str): Qt object name

    Returns:
        List of QWidgets
    """
    matches = []

    # Find top level widgets matching class name
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            # Matching class
            if class_name and widget.metaObject().className() == class_name:
                matches.append(widget)
            # Matching object name
            elif object_name and widget.objectName() == object_name:
                matches.append(widget)
        except AttributeError:
            continue
        # Print unhandled to the shell
        except Exception as e:
            print(e)

    return matches


def clear_layout(layout):
    """Removes all the widgets added in the given layout.

    Args:
         layout (QtWidgets.QLayout): Qt layout to clear.
    """

    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            # hidden at once: deleteLater only runs on the next event loop
            child.widget().hide()
            child.widget().deleteLater()
        elif child.layout() is not None:
            clear_layout(child.layout())


@contextlib.contextmanager
def block_signals(widget, children=False):
    """Python context that block the signals of the widget and unblock them once wrapped code has been executed.

    Args:
        widget (QtWidgets.QWidget): Widget we want to block signals for.
        children (bool): Whether signals of given children widgets should be blocked or not.
    """

    blocked = widget.signalsBlocked()
    blocked_children = list()
    widget.blockSignals(True)
    child_widgets = (
        widget.findChildren(QtWidgets.QWidget) if children else list()
    )
    for child_widget in child_widgets:
        blocked_children.append(child_widget.signalsBlocked())
        child_widget.blockSignals(True)
    try:
        yield widget
    finally:
        widget.blockSignals(blocked)
        for i, child_widget in enumerate(child_widgets):
            child_widget.blockSignals(blocked_children[i])


def show_stacked_page(stack, page):
    """Show a stacked widget page, sizing the stack to that page only.

    By default a QStackedWidget is as large as its largest page. Hidden
    pages get an ignored size policy, so the stack follows the shown page.

    Args:
        stack (QtWidgets.QStackedWidget): The stack.
        page (QtWidgets.QWidget): The page to show.
    """
    for index in range(stack.count()):
        widget = stack.widget(index)
        policy = (
            QtWidgets.QSizePolicy.Preferred
            if widget is page
            else QtWidgets.QSizePolicy.Ignored
        )
        widget.setSizePolicy(policy, policy)
    stack.setCurrentWidget(page)
    stack.adjustSize()


def set_smooth_scroll(view, step=16, horizontal=False):
    """Scroll an item view by pixels instead of by whole items.

    The default per-item scroll jumps a full row on each wheel tick, and
    can't stop inside a row taller than the viewport (e.g. a row holding
    a large embedded widget), leaving part of it unreachable.

    Args:
        view (QtWidgets.QAbstractItemView): The view to update.
        step (int, optional): Pixels per wheel tick or arrow click, at
            96 dpi. Scaled with the screen dpi.
        horizontal (bool, optional): Also scroll horizontally by pixels.
    """
    single_step = int(round(dpi_scale(step)))
    view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
    view.verticalScrollBar().setSingleStep(single_step)
    if horizontal:
        view.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        view.horizontalScrollBar().setSingleStep(single_step)


def wildcard_to_regex(text):
    """Convert a wildcard filter text to a regular expression pattern.

    ``*`` matches any characters and ``?`` a single character. Every other
    character is matched literally.

    Args:
        text (str): Wildcard text, e.g. ``"tail*soft"``.

    Returns:
        str: The regular expression pattern (not anchored).
    """
    return re.escape(text).replace(r"\*", ".*").replace(r"\?", ".")


def set_proxy_filter(proxy, text, case_sensitive=False):
    """Apply a wildcard text filter to a sort filter proxy model.

    Works with PySide2 and PySide6: uses ``setFilterRegularExpression``
    when available and falls back to ``setFilterRegExp``. The text is
    matched anywhere in the row text.

    Args:
        proxy (QtCore.QSortFilterProxyModel): The proxy model.
        text (str): Wildcard filter text. Empty shows every row.
        case_sensitive (bool, optional): Match case.
    """
    pattern = wildcard_to_regex(text or "")
    if hasattr(proxy, "setFilterRegularExpression"):
        if not case_sensitive:
            pattern = "(?i)" + pattern
        proxy.setFilterRegularExpression(pattern)
    else:
        proxy.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitive if case_sensitive else QtCore.Qt.CaseInsensitive
        )
        proxy.setFilterRegExp(pattern)


def get_icon_path(icon_name=None):
    """Gets the directory path to the icon"""

    file_dir = os.path.dirname(__file__)

    if "\\" in file_dir:
        file_dir = file_dir.replace("\\", "/")
    file_dir = "/".join(file_dir.split("/")[:-3])
    if icon_name:
        return "{0}/icons/{1}".format(file_dir, icon_name)
    else:
        return "{}/icons".format(file_dir)


def get_cached_icon(file_name):
    """Return a QIcon of a file in the mGear icons folder, loaded once.

    Later calls with the same file name return the same QIcon, so views
    with many items don't load the file again for each item.

    Args:
        file_name (str): Icon file name with extension, e.g. "mgear_eye.svg".

    Returns:
        QtGui.QIcon: The icon.
    """
    icon = _ICON_CACHE.get(file_name)
    if icon is None:
        icon = QtGui.QIcon(get_icon_path(file_name))
        _ICON_CACHE[file_name] = icon
    return icon


def get_icon(icon, size=24):
    """get svg icon from icon resources folder as a pixel map"""
    img = get_icon_path("{}.svg".format(icon))
    svg_renderer = QtSvg.QSvgRenderer(img)
    image = QtGui.QImage(size, size, QtGui.QImage.Format_ARGB32)
    # Set the ARGB to 0 to prevent rendering artifacts
    image.fill(0x00000000)
    svg_renderer.render(QtGui.QPainter(image))
    pixmap = QtGui.QPixmap.fromImage(image)

    return pixmap


# dpi scale test -------------------------------------------------------------
def get_logicaldpi():
    """attempting to "cache" the query to the maya main window for speed

    Returns:
        int: dpi of the monitor
    """
    if _LOGICAL_DPI_KEY not in os.environ.keys():
        logical_dpi = _screen_logical_dpi()
        if logical_dpi is None:
            # no Qt yet: assume 96, and read it again once Qt runs
            return 96
        os.environ[_LOGICAL_DPI_KEY] = str(logical_dpi)
    return int(os.environ.get(_LOGICAL_DPI_KEY)) or 96


def _screen_logical_dpi():
    """The logical DPI of Maya's main window, else of the application's
    screen (mayapy: Qt 5 scales a high DPI screen by its DPI, Qt 6 by its
    pixel ratio); None before a QApplication exists."""
    window = maya_main_window()
    if window is not None:
        return window.logicalDpiX()
    app = QtWidgets.QApplication.instance()
    if app is None or app.primaryScreen() is None:
        return None
    return int(round(app.primaryScreen().logicalDotsPerInchX()))


def dpi_scale(value, default=96, min_=1, max_=2):
    """Scale the provided value by the scale that maya is using
    which is derived from the 'average' dpi of 96 from windows, linux, osx.

    Args:
        value (int, float): value to scale
        default (int, optional): assumed default from various platforms
        min_ (int, optional): if you do not want the value under 96 dpi
        max_ (int, optional): if you do not want a value higher than 200% scale

    Returns:
        # int, float: scaled value
    """
    return value * max(min_, min(get_logicaldpi() / float(default), max_))


#############################################
# use QSettings store/load class
#############################################


def text_width(metrics, text):
    """Return the width of a text, on Qt5 and Qt6.

    Args:
        metrics (QtGui.QFontMetrics): Font metrics.
        text (str): Text.

    Returns:
        int: Width in pixels.
    """
    if hasattr(metrics, "horizontalAdvance"):
        return metrics.horizontalAdvance(text)
    return metrics.width(text)


def square_crop_image(image, size):
    """Return a centered square crop of an image, scaled to a size.

    Args:
        image (QtGui.QImage): Source image.
        size (int): Output width and height, in pixels.

    Returns:
        QtGui.QImage: The square image, or None for a null image.
    """
    if image is None or image.isNull():
        return None
    side = min(image.width(), image.height())
    crop = image.copy(
        (image.width() - side) // 2, (image.height() - side) // 2, side, side
    )
    return crop.scaled(
        size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
    )


def capture_active_view_image(max_size=1024):
    """Capture the active 3D viewport as an image.

    Args:
        max_size (int, optional): Largest side of the returned image.

    Returns:
        QtGui.QImage: The image, or None when there is no viewport.
    """
    from mgear.core import utils

    handle, path = tempfile.mkstemp(suffix=".png")
    os.close(handle)
    try:
        if not utils.capture_active_view(path, max_size=max_size):
            return None
        image = QtGui.QImage(path)
        return None if image.isNull() else image
    finally:
        if os.path.exists(path):
            os.remove(path)


def text_badge(text, size, color, text_color=None):
    """Return a rounded square icon with a short text, e.g. an initial.

    Args:
        text (str): Text drawn in the middle, one or two characters.
        size (int): Icon size, in pixels.
        color (QtGui.QColor): Background color.
        text_color (QtGui.QColor, optional): Text color, white by default.

    Returns:
        QtGui.QPixmap: The badge.
    """
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QtCore.Qt.NoPen)
    margin = size * 0.08
    painter.drawRoundedRect(
        QtCore.QRectF(margin, margin, size - 2 * margin, size - 2 * margin),
        size * 0.15,
        size * 0.15,
    )
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(int(size * 0.45))
    painter.setFont(font)
    painter.setPen(text_color or QtGui.QColor(255, 255, 255))
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, text)
    painter.end()
    return pixmap


def text_color_for_background(color):
    """Return a readable text color for a background color.

    Uses relative luminance: 0.299*R + 0.587*G + 0.114*B.

    Args:
        color (tuple): RGB 0-1 tuple.

    Returns:
        tuple: (1, 1, 1) for white or (0.1, 0.1, 0.1) for dark.
    """
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    if luminance > 0.5:
        return (0.1, 0.1, 0.1)
    return (1.0, 1.0, 1.0)


def tint_pixmap(pixmap, color):
    """Return a copy of a pixmap drawn in one color, its alpha kept.

    Args:
        pixmap (QtGui.QPixmap): The pixmap, e.g. from :func:`get_icon`.
        color (QtGui.QColor): The color.

    Returns:
        QtGui.QPixmap: The tinted copy.
    """
    image = pixmap.toImage()
    painter = QtGui.QPainter(image)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(image.rect(), color)
    painter.end()
    return QtGui.QPixmap.fromImage(image)


TOOLTIP_COLOR = "#4a90d9"


def rich_tooltip(title, text, bullets=None, color=None):
    """Return an HTML tooltip with a colored title, a text and bullets.

    Use the result with ``setToolTip``. The title, text and bullets are
    HTML-escaped.

    Args:
        title (str): Tool name, bold, in ``color``.
        text (str): What the tool does.
        bullets (list, optional): Short usage notes, one per line.
        color (str, optional): Title color, e.g. ``"#e8b030"``. Defaults to
            ``TOOLTIP_COLOR``.

    Returns:
        str: The tooltip HTML.

    Example:
        >>> button.setToolTip(rich_tooltip(
        ...     "Nudge Keys",
        ...     "Move the selected keys in time.",
        ...     ["Left arrow nudges backward.", "Right arrow nudges forward."],
        ... ))
    """
    html = [
        '<p style="margin:0; font-size:13pt; font-weight:bold; color:{};">'
        "{}</p>".format(color or TOOLTIP_COLOR, escape(title)),
        '<hr style="margin:2px 0;"/>',
        '<p style="margin:2px 0 4px 0; font-size:10pt;">{}</p>'.format(escape(text)),
    ]
    for bullet in bullets or []:
        html.append(
            '<p style="margin:0; color:#a0a0a0;">&bull; {}</p>'.format(escape(bullet))
        )
    return "<div>{}</div>".format("".join(html))


class CoalescedCall(object):
    """Callable that runs a function once on the next event loop pass.

    However often it is called before then, the function runs once. Use it
    to turn bursts of Maya callbacks (selection, undo, scene messages) into
    one UI refresh.

    Example:
        >>> refresh = CoalescedCall(window.refresh)
        >>> callbacks.selectionChangedCB("selection", refresh)
    """

    def __init__(self, func):
        """Initialize the call.

        Args:
            func (callable): Function called without arguments.
        """
        self.func = func
        self.pending = False

    def __call__(self, *args):
        if self.pending:
            return
        self.pending = True
        QtCore.QTimer.singleShot(0, self._run)

    def _run(self):
        self.pending = False
        self.func()


def get_user_settings():
    """Return the shared mGear user settings object.

    Settings are stored in ``mGear_user_settings.ini`` in the Maya user
    prefs folder.

    Returns:
        QtCore.QSettings: The settings object (INI format).
    """
    prefs_folder = cmds.internalVar(userPrefDir=True)
    settings_file_path = os.path.join(prefs_folder, "mGear_user_settings.ini")
    return QtCore.QSettings(settings_file_path, QtCore.QSettings.IniFormat)


class SettingsMixin(object):
    """Save and restore widget values in the mGear user settings.

    Fill ``self.user_settings`` with ``{key: (widget, default)}`` and call
    :meth:`load_settings`; values are then saved on every change. The file
    is written once the values stop changing (``SETTINGS_SYNC_DELAY``);
    call :meth:`save_settings` to write everything at once.

    Supported widgets: check boxes, actions and checkable buttons, combo
    boxes, line edits, spin boxes and sliders, plus any widget that
    implements the settings protocol: ``settings_value()``,
    ``set_settings_value(value)`` and ``settings_signal()`` returning the
    signal emitted on change (for example ``widgets.ColorSwatchButton`` and
    ``widgets.NodeListWidget``).
    """

    # Delay before writing changed widget values to disk, in milliseconds
    SETTINGS_SYNC_DELAY = 500

    def __init__(self, parent=None):
        self.settings = self.create_qsettings_object()
        self.user_settings = {}
        self._settings_sync_timer = None

    def create_qsettings_object(self):
        return get_user_settings()

    def load_settings(self):
        for key, (widget, default_value) in self.user_settings.items():
            value = self.settings.value(key, defaultValue=default_value)
            self.set_widget_value(widget, value, default_value)
            self._connect_widget_signal(widget, key)

    def load_json_setting(self, key, default):
        """Return a JSON value stored in the settings.

        Args:
            key (str): Settings key.
            default (object): Returned when the value is missing, invalid
                or not of the same type.

        Returns:
            object: The value.
        """
        try:
            value = json.loads(self.settings.value(key) or "null")
        except (TypeError, ValueError):
            return default
        return value if isinstance(value, type(default)) else default

    def save_json_setting(self, key, value):
        """Store a JSON serializable value in the settings.

        Args:
            key (str): Settings key.
            value (object): Value.
        """
        self.settings.setValue(key, json.dumps(value))

    def save_settings(self):
        for key, (widget, _) in self.user_settings.items():
            self.settings.setValue(key, self.get_widget_value(widget))
        self.settings.sync()

    def get_widget_value(self, widget):
        """Return a widget's value in a settings / JSON friendly form.

        Args:
            widget (QtWidgets.QWidget): A supported widget.

        Returns:
            object: The value (bool, int, float, str or list).
        """
        if _has_settings_protocol(widget):
            return widget.settings_value()
        if _is_toggle_widget(widget):
            return widget.isChecked()
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentIndex()
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        if isinstance(widget, _VALUE_WIDGETS):
            return widget.value()
        return None

    def set_widget_value(self, widget, value, default=None):
        """Set a widget from a stored value, converting its type.

        Values read back from QSettings are often strings; they are
        converted to the widget's type, falling back to ``default``.

        Args:
            widget (QtWidgets.QWidget): A supported widget.
            value (object): Stored value.
            default (object, optional): Fallback when ``value`` is unusable.
        """
        if _has_settings_protocol(widget):
            widget.set_settings_value(default if value is None else value)
        elif _is_toggle_widget(widget):
            if value in ("true", "True", True):
                widget.setChecked(True)
            elif value in ("false", "False", False):
                widget.setChecked(False)
            else:
                widget.setChecked(bool(default))
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentIndex(_to_number(value, default, int))
        elif isinstance(widget, QtWidgets.QLineEdit):
            if value is None:
                value = default or ""
            widget.setText(str(value))
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(_to_number(value, default, float))
        elif isinstance(widget, _VALUE_WIDGETS):
            widget.setValue(_to_number(value, default, int))

    def _save_widget_setting(self, key, widget, *args):
        """Store one widget's value and schedule the write to disk.

        The value is in the settings object at once, so other settings
        objects of the process see it. Writing the file waits until the
        values stop changing, so a slider drag writes it once.

        Args:
            key (str): Settings key.
            widget (QtWidgets.QWidget): The changed widget.
            *args: Signal arguments, ignored.
        """
        self.settings.setValue(key, self.get_widget_value(widget))
        # getattr: subclasses may set self.settings without calling __init__
        timer = getattr(self, "_settings_sync_timer", None)
        if timer is None:
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.setInterval(self.SETTINGS_SYNC_DELAY)
            timer.timeout.connect(self._sync_settings)
            self._settings_sync_timer = timer
        timer.start()

    def _sync_settings(self):
        self.settings.sync()

    def _connect_widget_signal(self, widget, key=None):
        save = self.save_settings
        if key is not None:
            save = partial(self._save_widget_setting, key, widget)
        if _has_settings_protocol(widget):
            widget.settings_signal().connect(save)
        elif _is_toggle_widget(widget):
            widget.toggled.connect(save)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(save)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(save)
        elif isinstance(widget, _VALUE_WIDGETS):
            widget.valueChanged.connect(save)


_VALUE_WIDGETS = (
    QtWidgets.QSpinBox,
    QtWidgets.QDoubleSpinBox,
    QtWidgets.QAbstractSlider,
)


def _has_settings_protocol(widget):
    """Return True for widgets that save and restore their own value.

    Args:
        widget (QtWidgets.QWidget): Widget to test.

    Returns:
        bool: True when the widget implements ``settings_value``,
        ``set_settings_value`` and ``settings_signal``.
    """
    return all(
        hasattr(widget, name)
        for name in ("settings_value", "set_settings_value", "settings_signal")
    )


def _is_toggle_widget(widget):
    """Return True for widgets holding a checked state.

    Check boxes, actions and any checkable button (e.g. a toggle
    QPushButton).

    Args:
        widget (QtWidgets.QWidget): Widget to test.

    Returns:
        bool: True when the widget's value is its checked state.
    """
    if isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QAction)):
        return True
    return isinstance(widget, QtWidgets.QAbstractButton) and widget.isCheckable()


def _to_number(value, default, cast):
    """Convert a stored settings value to a number.

    Args:
        value (object): Value read from QSettings, often a string.
        default (object): Fallback when the value can not be converted.
        cast (type): ``int`` or ``float``.

    Returns:
        int or float: The converted value.
    """
    try:
        return cast(float(value))
    except (TypeError, ValueError):
        return cast(default or 0)


#############################################
# Logging
#############################################


class _LogEmitter(QtCore.QObject):
    """Carry log messages to the GUI thread through a Qt signal."""

    message = QtCore.Signal(str)


class QtLogHandler(logging.Handler):
    """Logging handler that appends records to a text widget.

    Records are sent through a Qt signal, so messages logged from worker
    threads are delivered safely in the GUI thread. Use :meth:`attach` and
    :meth:`detach` to connect it to a logger: the logger level is lowered
    while attached so INFO messages reach the widget, then restored. The
    handler detaches itself when the widget is destroyed.

    Example:
        >>> self.log_handler = QtLogHandler(self.log_output)
        >>> self.log_handler.attach(logging.getLogger("mgear.rigbits.my_tool"))
        >>> ...
        >>> self.log_handler.detach()  # e.g. in closeEvent
    """

    def __init__(self, widget, fmt=None):
        """Initialize the handler.

        Args:
            widget (QtWidgets.QPlainTextEdit): Output widget. Any widget
                with an ``appendPlainText(str)`` method works.
            fmt (str, optional): Log format. Defaults to
                ``"%(levelname)s: %(message)s"``.
        """
        super(QtLogHandler, self).__init__()
        self.setFormatter(logging.Formatter(fmt or "%(levelname)s: %(message)s"))
        self.emitter = _LogEmitter()
        self.emitter.message.connect(widget.appendPlainText)
        # [(logger, level before attach)]
        self.attached = []
        widget.destroyed.connect(self.detach)

    def attach(self, *loggers, **kwargs):
        """Add the handler to one or more loggers.

        Args:
            *loggers (logging.Logger): Loggers to show in the widget, e.g.
                the tool logger and the core module loggers it uses.
            **kwargs: ``level`` (int, optional): level set on each logger
                while attached, only if the logger has no level of its own.
                Defaults to ``logging.INFO``.
        """
        level = kwargs.get("level", logging.INFO)
        self.detach()
        for logger in loggers:
            self.attached.append((logger, logger.level))
            logger.addHandler(self)
            if logger.level == logging.NOTSET:
                logger.setLevel(level)

    def detach(self, *args):
        """Remove the handler from its loggers and restore their levels."""
        for logger, previous_level in self.attached:
            logger.removeHandler(self)
            logger.setLevel(previous_level)
        self.attached = []

    def emit(self, record):
        """Send a formatted record to the widget.

        Args:
            record (logging.LogRecord): Log record.
        """
        try:
            self.emitter.message.emit(self.format(record))
        except RuntimeError:
            # The widget or emitter was deleted
            pass
