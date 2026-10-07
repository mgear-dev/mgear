"""mgear.core.callbackManager test"""


def _manager():
    from mgear.core import callbackManager

    return callbackManager.CallbackManager()


def test_remove_single_managed_callback(run_with_maya_standalone, setup_path):
    from maya import cmds

    manager = _manager()
    hits = []
    manager.eventCB("a", lambda *args: hits.append("a"), "timeChanged")
    manager.eventCB("b", lambda *args: hits.append("b"), "timeChanged")

    manager.removeManagedCB("a")
    assert len(manager.MANAGER_CALLBACKS) == 1

    cmds.currentTime(cmds.currentTime(query=True) + 1, edit=True)
    assert hits == ["b"]
    manager.removeAllManagedCB()


def test_replace_by_name(run_with_maya_standalone, setup_path):
    manager = _manager()
    manager.timerCB("cam", lambda *args: None, 10.0)
    manager.timerCB("cam", lambda *args: None, 10.0)
    assert len(manager.MANAGER_CALLBACKS) == 1
    manager.removeAllManagedCB()
    assert not manager.MANAGER_CALLBACKS


def test_event_callback_fires(run_with_maya_standalone, setup_path):
    from maya import cmds

    manager = _manager()
    hits = []
    manager.eventCB(
        "time",
        lambda *args: hits.append(cmds.currentTime(query=True)),
        "timeChanged",
    )
    for frame in (3, 7):
        cmds.currentTime(frame, edit=True)
    manager.removeAllManagedCB()
    cmds.currentTime(9, edit=True)
    assert hits == [3.0, 7.0]


def test_condition_and_scene_callbacks_register(run_with_maya_standalone, setup_path):
    from maya.api import OpenMaya as om2

    manager = _manager()
    manager.conditionCB("play", lambda *args: None, "playingBack")
    manager.sceneMessageCB("new", lambda *args: None, om2.MSceneMessage.kBeforeNew)
    assert len(manager.MANAGER_CALLBACKS) == 2
    manager.removeAllManagedCB()
    assert not manager.MANAGER_CALLBACKS


def test_scene_callback_fires(run_with_maya_standalone, setup_path):
    from maya import cmds
    from maya.api import OpenMaya as om2

    manager = _manager()
    hits = []
    manager.sceneMessageCB(
        "new", lambda *args: hits.append(1), om2.MSceneMessage.kBeforeNew
    )
    cmds.file(new=True, force=True)
    manager.removeAllManagedCB()
    cmds.file(new=True, force=True)
    assert hits == [1]


def test_no_scriptjobs_created(run_with_maya_standalone, setup_path):
    from maya import cmds
    from maya.api import OpenMaya as om2

    before = set(cmds.scriptJob(listJobs=True) or [])
    manager = _manager()
    manager.timerCB("t", lambda *args: None, 10.0)
    manager.eventCB("e", lambda *args: None, "timeChanged")
    manager.conditionCB("c", lambda *args: None, "playingBack")
    manager.selectionChangedCB("s", lambda *args: None)
    manager.sceneMessageCB("n", lambda *args: None, om2.MSceneMessage.kBeforeOpen)
    after = set(cmds.scriptJob(listJobs=True) or [])
    manager.removeAllManagedCB()
    assert after == before


def test_remove_all_session_callbacks(run_with_maya_standalone, setup_path):
    from mgear.core import callbackManager as cb

    cb.eventCB("session_a", lambda *args: None, "timeChanged")
    cb.eventCB("session_b", lambda *args: None, "timeChanged")
    cb.removeAllSessionCB()
    assert "session_a" not in cb.RECORDED_CALLBACKS
    assert "session_b" not in cb.RECORDED_CALLBACKS
