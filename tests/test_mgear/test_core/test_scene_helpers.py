"""mgear.core undo chunk, progress bar, plug, point count and log helpers test"""

import logging

import pytest


def test_undo_chunk_single_undo(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    with utils.undo_chunk("test"):
        for i in range(3):
            cmds.createNode("transform", name="chunk_{}".format(i))
    cmds.undo()
    assert not cmds.ls("chunk_*")


def test_undo_chunk_closes_on_error(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    with pytest.raises(ValueError):
        with utils.undo_chunk():
            cmds.createNode("transform", name="chunk_err")
            raise ValueError("boom")

    # The chunk is closed: a new edit is a separate undo step.
    cmds.createNode("transform", name="after_chunk")
    cmds.undo()
    assert not cmds.objExists("after_chunk")
    assert cmds.objExists("chunk_err")


def test_one_undo_uses_chunk(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    @utils.one_undo
    def build():
        cmds.createNode("transform", name="dec_a")
        cmds.createNode("transform", name="dec_b")
        return "done"

    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    assert build() == "done"
    cmds.undo()
    assert not cmds.ls("dec_*")


def test_main_progress_bar_batch(run_with_maya_standalone, setup_path):
    from mgear.core import utils

    with utils.main_progress_bar("Testing", 3) as step:
        for _ in range(3):
            step("x")
        step()

    with pytest.raises(ValueError):
        with utils.main_progress_bar("Testing", 1):
            raise ValueError("boom")


def test_get_plug(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere()[0]
    ffd = cmds.lattice(sphere)[0]
    plug = utils.get_plug(ffd, "weightList")
    assert plug.isArray
    assert utils.get_plug(sphere, "tx").partialName() == "tx"
    with pytest.raises(RuntimeError):
        utils.get_plug("does_not_exist", "tx")


def test_get_point_count(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import utils

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere()[0]
    assert utils.get_point_count(sphere) == 382

    curve = cmds.curve(point=[(0, 0, 0), (1, 0, 0), (2, 1, 0), (3, 0, 0)])
    assert utils.get_point_count(curve) == 4

    surface = cmds.nurbsPlane(patchesU=1, patchesV=1, degree=3)[0]
    assert utils.get_point_count(surface) == 16

    lattice = cmds.lattice(sphere, divisions=(2, 3, 4))[1]
    assert utils.get_point_count(lattice) == 24


def test_qt_log_handler(qt_app):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtWidgets

    widget = QtWidgets.QPlainTextEdit()
    handler = pyqt.QtLogHandler(widget)
    logger = logging.getLogger("mgear.test.qt_log_handler")
    logger.addHandler(handler)
    try:
        logger.warning("hello")
    finally:
        logger.removeHandler(handler)
    qt_app.processEvents()
    assert widget.toPlainText().endswith("WARNING: hello")

    custom = pyqt.QtLogHandler(widget, fmt="%(message)s!")
    logger.addHandler(custom)
    try:
        logger.warning("bye")
    finally:
        logger.removeHandler(custom)
    assert widget.toPlainText().endswith("bye!")


def test_qt_log_handler_attach(qt_app):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtWidgets

    widget = QtWidgets.QPlainTextEdit()
    logger = logging.getLogger("mgear.test.qt_log_attach")
    logger.setLevel(logging.NOTSET)
    handler = pyqt.QtLogHandler(widget)

    handler.attach(logger)
    assert handler in logger.handlers
    assert logger.level == logging.INFO
    logger.info("shown")
    assert widget.toPlainText().endswith("INFO: shown")

    handler.detach()
    handler.detach()  # safe to call twice
    assert handler not in logger.handlers
    assert logger.level == logging.NOTSET

    # A level set by the user is kept
    logger.setLevel(logging.WARNING)
    handler.attach(logger)
    assert logger.level == logging.WARNING
    handler.detach()
    assert logger.level == logging.WARNING
    logger.setLevel(logging.NOTSET)
