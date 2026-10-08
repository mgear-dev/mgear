"""Pytest conftest module

Shared fixtures for the mGear tests.

Importing ``mgear`` needs Maya, so run the tests with ``mayapy``::

    mayapy -m pytest -v

Without Maya (for example on the GitHub Actions runners) every test that
uses the ``setup_path`` or ``run_with_maya_standalone`` fixtures is skipped.
"""

# Stdlib imports
import os
import sys

# Pytest imports
import pytest

_SCRIPTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "release", "scripts")
)


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


@pytest.fixture(scope="session")
def run_with_maya_standalone():
    """Initialize maya.standalone for the test session.

    Skips the test when Maya is not available.
    """
    standalone = pytest.importorskip("maya.standalone")
    standalone.initialize(name="python")
    yield
    standalone.uninitialize()


@pytest.fixture(scope="session")
def setup_path(run_with_maya_standalone):
    """Make ``mgear`` importable from this repository.

    Adds ``release/scripts`` to ``sys.path``. Importing ``mgear`` needs
    Maya, so this also starts maya.standalone.
    """
    if _SCRIPTS not in sys.path:
        sys.path.insert(0, _SCRIPTS)


@pytest.fixture
def qt_app(setup_path):
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
