"""Pytest conftest module

In this file you will find all **fixtures** that you are used while running
mgear tests.

Github Actions workflow will run Pytest but because their clusters will not have
Autodesk Maya install / neither PyMel, most of the tests will be skip.

In order to ensure all tests are correctly executed you must run them locally
with both Maya and PyMel installed.
"""

# Stdlib imports
import sys
import os

# Pytest imports
import pytest


@pytest.fixture(scope='session')
def mock_maya_module():
    """Mocks Maya python module
    """

    def maya_module():
        return

    maya = type(sys)('maya')
    maya.cmds = maya_module
    maya.standalone = maya_module
    sys.modules['maya'] = maya


@pytest.fixture(scope='session')
def setup_path():
    """ Adds python dependencies to sys.path

    Note:
        Add here python path packages if needed.
    """

    # adds anim_scene_builder to python path
    sys.path.insert(0, os.path.abspath("./python"))
    sys.path.insert(0, os.path.abspath("./mgear4/python"))


@pytest.fixture(scope='session')
def run_with_maya_standalone():
    from maya import standalone
    standalone.initialize(name="python")
    yield
    standalone.uninitialize()


@pytest.fixture(scope='session')
def run_with_maya_pymel():
    import pymel.core
    yield


def pytest_configure(config):
    """Create the GUI QApplication before Maya starts.

    Widget tests need a GUI QApplication, and maya.standalone.initialize()
    creates a non-GUI one if none exists yet. This hook runs before test
    collection, so before the run_with_maya_standalone fixture. Skipped when
    no PySide binding is installed (e.g. CI without Maya).
    """
    try:
        from PySide6 import QtWidgets
    except ImportError:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            return
    config._mgear_qt_app = QtWidgets.QApplication.instance() or (
        QtWidgets.QApplication([])
    )


@pytest.fixture
def qt_app(run_with_maya_standalone, setup_path):
    """GUI QApplication running alongside maya.standalone.

    Skips the test when only a non-GUI application is available.
    """
    from mgear.vendor.Qt import QtWidgets

    app = QtWidgets.QApplication.instance()
    if not isinstance(app, QtWidgets.QApplication):
        pytest.skip("No GUI QApplication available")
    yield app


@pytest.fixture
def clean_settings(qt_app):
    """mGear user settings, restored to their prior state after the test.

    Yields the shared settings object (mgear.core.pyqt.get_user_settings).
    """
    from mgear.core import pyqt

    settings = pyqt.get_user_settings()
    saved = {key: settings.value(key) for key in settings.allKeys()}
    yield settings
    for key in settings.allKeys():
        if key not in saved:
            settings.remove(key)
    for key, value in saved.items():
        settings.setValue(key, value)
    settings.sync()
