"""pyQt/pySide widgets and helper functions for mGear"""

#############################################
# GLOBAL
#############################################
import os
import traceback
import contextlib
import maya.OpenMayaUI as omui
import mgear.pymaya as pm
from mgear.pymaya import versions
from maya import cmds

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCompat
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtSvg
from mgear.vendor.Qt import QtCore
from .six import PY2

# Try importing PySide6, fall back to PySide2 if not available
try:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QPoint
except ImportError:
    from PySide2.QtGui import QGuiApplication
    from PySide2.QtCore import QPoint

UI_EXT = "ui"

_LOGICAL_DPI_KEY = "_LOGICAL_DPI"

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
        QMainWindow: main window.

    """

    main_window_ptr = omui.MQtUtil.mainWindow()
    if PY2:
        return QtCompat.wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
    return QtCompat.wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


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

    """
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
        try:
            logical_dpi = maya_main_window().logicalDpiX()
        except Exception:
            logical_dpi = 96
        finally:
            os.environ[_LOGICAL_DPI_KEY] = str(logical_dpi)
    return int(os.environ.get(_LOGICAL_DPI_KEY)) or 96


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


class SettingsMixin(object):
    def __init__(self, parent=None):
        self.settings = self.create_qsettings_object()
        self.user_settings = {}

    def create_qsettings_object(self):
        prefs_folder = cmds.internalVar(userPrefDir=True)
        settings_file_path = os.path.join(
            prefs_folder, "mGear_user_settings.ini"
        )
        return QtCore.QSettings(settings_file_path, QtCore.QSettings.IniFormat)

    def load_settings(self):
        for key, (widget, default_value) in self.user_settings.items():
            value = self.settings.value(key, defaultValue=default_value)
            # Convert string values to appropriate types based on widget
            if isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QAction)):
                # For checkboxes/actions, convert string to bool
                if value in ["true", "True", True]:
                    value = True
                elif value in ["false", "False", False]:
                    value = False
                else:
                    value = bool(default_value)
            elif isinstance(widget, QtWidgets.QComboBox):
                # For combo boxes, ensure integer
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = int(default_value) if default_value else 0
            elif isinstance(widget, QtWidgets.QLineEdit):
                # For line edits, ensure string
                if value is None:
                    value = str(default_value) if default_value else ""
                else:
                    value = str(value)
            self._set_widget_value(widget, value)
            self._connect_widget_signal(widget)

    def save_settings(self):
        for key, (widget, _) in self.user_settings.items():
            value = self._get_widget_value(widget)
            self.settings.setValue(key, value)
        self.settings.sync()

    def _get_widget_value(self, widget):
        if isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QAction)):
            return widget.isChecked()
        elif isinstance(widget, QtWidgets.QComboBox):
            return widget.currentIndex()
        elif isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        # Add support for other widget types as needed.
        # ...

    def _set_widget_value(self, widget, value):
        if isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QAction)):
            widget.setChecked(value)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.setCurrentIndex(int(value))
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(value)
        # Add support for other widget types as needed.
        # ...

    def _connect_widget_signal(self, widget):
        if isinstance(widget, (QtWidgets.QCheckBox, QtWidgets.QAction)):
            widget.toggled.connect(self.save_settings)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(self.save_settings)
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(self.save_settings)
        # Add support for other widget types as needed.
        # ...
