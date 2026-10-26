"""mgear.core.dragdrop tests: file drop handler registry and handlers"""

import json
import subprocess
import sys

import pytest


@pytest.fixture
def dragdrop(setup_path):
    from maya import cmds
    from mgear.core import dragdrop

    cmds.file(new=True, force=True)
    saved = dict(dragdrop._HANDLERS)
    yield dragdrop
    dragdrop._HANDLERS.clear()
    dragdrop._HANDLERS.update(saved)


@pytest.fixture
def default_import(dragdrop, monkeypatch):
    """List of the files sent to Maya's default import."""
    calls = []
    monkeypatch.setattr(dragdrop, "_default_import", calls.append)
    return calls


def _patch_handler(dragdrop, ext):
    """Replace the function of a built-in handler, keep its label and undo."""
    calls = []
    entry = dragdrop.get_drop_handler(ext)
    dragdrop.register_drop_handler(ext, calls.append, entry.label, entry.undo)
    return calls


# Registry --------------------------------------------------------------------


def test_register_and_override(dragdrop, default_import):
    calls = []
    dragdrop.register_drop_handler(".ABC_cfg", calls.append, "ABC Config")
    assert ".abc_cfg" in dragdrop.get_drop_handlers()
    assert dragdrop.mgear_file_drop_action("C:/x/file.abc_cfg") == 1
    assert calls == ["C:/x/file.abc_cfg"]

    other = []
    dragdrop.register_drop_handler(".lat", other.append, "Studio lattice")
    dragdrop.mgear_file_drop_action("C:/x/face.lat")
    assert other == ["C:/x/face.lat"]
    assert default_import == []


def test_builtin_handlers_resolve(dragdrop):
    expected = {
        ".sgt",
        ".gskinpack",
        ".gskin",
        ".jskin",
        ".rbf",
        ".wts",
        ".gst",
        ".lat",
        ".shw",
        ".pxw",
        ".cwc",
        ".cmc",
        ".pkr",
        ".sbk",
    }
    handlers = dragdrop.get_drop_handlers()
    assert expected <= set(handlers)
    for entry in handlers.values():
        assert callable(dragdrop._resolve_handler(entry.handler))
    assert handlers[".sgt"].undo is False


def test_extension_case_insensitive(dragdrop, monkeypatch, default_import):
    calls = _patch_handler(dragdrop, ".gst")
    dragdrop.mgear_file_drop_action("C:/x/HERO.GST")
    assert calls == ["C:/x/HERO.GST"]


def test_unknown_and_false_fall_back(dragdrop, default_import):
    dragdrop.mgear_file_drop_action("C:/x/model.obj")
    dragdrop.register_drop_handler(".json", lambda path: False, "JSON")
    dragdrop.mgear_file_drop_action("C:/x/data.json")
    assert default_import == ["C:/x/model.obj", "C:/x/data.json"]


def test_error_guard(dragdrop, default_import):
    def broken(path):
        raise ValueError("corrupt file")

    dragdrop.register_drop_handler(".bad", broken, "Broken")
    assert dragdrop.mgear_file_drop_action("C:/x/file.bad") == 1
    assert default_import == []


def test_dragdrop_loads_no_tool(scripts_path):
    tools = (
        "mgear.shifter.io",
        "mgear.core.skin",
        "mgear.rigbits.rbf_io",
        "mgear.rigbits.wire_to_skinning",
        "mgear.rigbits.gimmick_tool.core",
        "mgear.rigbits.lattice_io",
        "mgear.rigbits.shrinkwrap_io",
        "mgear.rigbits.proximitywrap_io",
        "mgear.rigbits.channelWrangler",
        "mgear.animbits.channel_master_node",
        "mgear.anim_picker",
        "mgear.animbits.bookmarks",
    )
    code = (
        "import sys; sys.path.insert(0, {!r});"
        "import maya.standalone; maya.standalone.initialize();"
        "import mgear.core.dragdrop;"
        "print('LOADED:' + ','.join(m for m in {!r} if m in sys.modules))".format(
            scripts_path, tools
        )
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=600
    ).stdout
    loaded = [line for line in out.splitlines() if line.startswith("LOADED:")]
    assert loaded == ["LOADED:"]


# Built-in handlers -----------------------------------------------------------


def test_skin_handlers(dragdrop, monkeypatch, default_import):
    from mgear.core import skin

    calls = []
    monkeypatch.setattr(
        skin, "importSkinPack", lambda path, **kw: calls.append(("pack", path, kw))
    )
    monkeypatch.setattr(
        skin, "importSkin", lambda path, **kw: calls.append(("skin", path, kw))
    )
    dragdrop.mgear_file_drop_action("C:/x/body.gSkinPack")
    dragdrop.mgear_file_drop_action("C:/x/body.jSkin")
    dragdrop.mgear_file_drop_action("C:/x/body.gSkin")
    assert calls == [
        ("pack", "C:/x/body.gSkinPack", {"on_missing": "ui"}),
        ("skin", "C:/x/body.jSkin", {"on_missing": "ui"}),
        ("skin", "C:/x/body.gSkin", {"on_missing": "ui"}),
    ]


def test_guide_file_drop(dragdrop, monkeypatch):
    from mgear.shifter import io

    calls = []
    asked = []

    def ask(file_name, components, target_name, allow_build):
        asked.append((file_name, target_name, allow_build))
        return result[0]

    result = [(io.IMPORT_NEW, None, False)]
    monkeypatch.setattr(io, "_ask_import_choice", ask)
    monkeypatch.setattr(
        io,
        "import_guide_template",
        lambda filePath=None, conf=None: calls.append(filePath),
    )
    io.guide_file_drop("C:/x/biped.sgt")
    assert calls == ["C:/x/biped.sgt"]
    # Nothing selected: Import / Build / Cancel only
    assert asked == [("biped.sgt", None, True)]
    dragdrop.guide_file_prompt("C:/x/biped.sgt")
    assert calls == ["C:/x/biped.sgt"] * 2
    result[0] = (io.IMPORT_CANCEL, None, False)
    dragdrop.mgear_file_drop_action("C:/x/biped.sgt")
    assert calls == ["C:/x/biped.sgt"] * 2
    assert len(asked) == 3


def test_wire_to_skinning_drop(dragdrop, monkeypatch):
    from maya import cmds
    from mgear.rigbits.wire_to_skinning import core

    calls = []
    cube = cmds.polyCube(name="face")[0]
    cmds.select(cube)
    monkeypatch.setattr(cmds, "confirmDialog", lambda **kw: "Import")
    monkeypatch.setattr(
        core,
        "import_configuration",
        lambda path, target_mesh=None: calls.append((path, target_mesh)),
    )
    core.drop_file("C:/x/face.wts")
    dragdrop.wire_to_skinning_file_prompt("C:/x/face.wts")
    assert calls == [("C:/x/face.wts", "face")] * 2


def test_lattice_drop_one_undo(dragdrop, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io

    sphere = cmds.polySphere(name="body")[0]
    cmds.lattice(sphere, divisions=(2, 2, 2), name="ffdA")
    cmds.lattice(sphere, divisions=(2, 2, 2), name="ffdB")
    path = str(tmp_path / "two.lat")
    lattice_io.export_lattices(["ffdA", "ffdB"], path)
    cmds.delete("ffdA", "ffdB")
    assert not cmds.ls(type="ffd")

    cmds.undoInfo(state=True, infinity=True)
    dragdrop.mgear_file_drop_action(path.upper().replace(".LAT", ".lat"))
    assert sorted(cmds.ls(type="ffd")) == ["ffdA", "ffdB"]
    cmds.undo()
    assert not cmds.ls(type="ffd")


def test_deformer_io_handlers(dragdrop):
    from mgear.rigbits.lattice_io import core as lat_core
    from mgear.rigbits.proximitywrap_io import core as pxw_core
    from mgear.rigbits.shrinkwrap_io import core as shw_core

    for ext, func in (
        (".lat", lat_core.import_lattices),
        (".shw", shw_core.import_shrinkwraps),
        (".pxw", pxw_core.import_proximitywraps),
    ):
        handler = dragdrop.get_drop_handler(ext).handler
        assert dragdrop._resolve_handler(handler) is func


def test_mel_path_escaping(dragdrop, monkeypatch):
    commands = []
    monkeypatch.setattr(dragdrop.mel, "eval", commands.append)
    dragdrop._default_import(r'C:\my "files"\model.obj')
    assert commands == [r'performFileImportAction("C:\\my \"files\"\\model.obj");']
    assert "encodeString($theFile)" in dragdrop.MEL_OVERRIDE_CMD


def _skinned_mesh():
    from maya import cmds

    cmds.select(clear=True)
    root = cmds.joint(name="j0")
    tip = cmds.joint(name="j1", position=(0, 2, 0))
    mesh = cmds.polyCylinder(name="limb", height=2, subdivisionsY=4)[0]
    cmds.move(0, 1, 0, mesh)
    cmds.skinCluster(root, tip, mesh, toSelectedBones=True)
    return mesh, root, tip


def test_proximitywrap_bind_pose_warning(dragdrop, monkeypatch):
    from maya import cmds
    from mgear.rigbits.proximitywrap_io import core as pxw_core

    mesh, root, tip = _skinned_mesh()
    imported = []
    warnings = []
    monkeypatch.setattr(pxw_core, "get_skinned_meshes", lambda path: [mesh])
    monkeypatch.setattr(
        pxw_core.FORMAT, "import_file", lambda path, *a: imported.append(path)
    )
    monkeypatch.setattr(cmds, "warning", warnings.append)

    pxw_core.import_proximitywraps("C:/x/a.pxw")
    assert warnings == []
    cmds.setAttr(root + ".rotateZ", 30)
    dragdrop.mgear_file_drop_action("C:/x/b.pxw")
    assert len(warnings) == 1 and "bind pose" in warnings[0]
    pxw_core.import_proximitywraps("C:/x/c.pxw", check_bind_pose=False)
    assert len(warnings) == 1
    assert imported == ["C:/x/a.pxw", "C:/x/b.pxw", "C:/x/c.pxw"]


def test_channel_wrangler_drop(dragdrop, tmp_path):
    from maya import cmds

    src = cmds.createNode("transform", name="src")
    dst = cmds.createNode("transform", name="dst")
    cmds.addAttr(src, longName="blink", attributeType="double", keyable=True)
    path = str(tmp_path / "rules.cwc")
    with open(path, "w") as f:
        json.dump(
            {
                "map": [["blink", src, dst, 0]],
                "movePolicy": "merge",
                "proxyPolicy": "index",
            },
            f,
        )
    dragdrop.mgear_file_drop_action(path)
    assert cmds.attributeQuery("blink", node=dst, exists=True)
    assert not cmds.attributeQuery("blink", node=src, exists=True)


def _cmc_file(tmp_path, name="face_cm", tabs=("Main",)):
    path = str(tmp_path / "{}.cmc".format(name))
    config = {
        "tabs": list(tabs),
        "tabs_data": {t: {"channels": [], "channels_data": {}} for t in tabs},
        "current_tab": 0,
    }
    with open(path, "w") as f:
        json.dump({"node_name": name, "config": config}, f)
    return path


@pytest.mark.parametrize(
    "choice, nodes, tabs",
    (
        ("Replace", ["face_cm"], ["Extra"]),
        ("Add Tabs", ["face_cm"], ["Main", "Extra"]),
        ("New Node", ["face_cm", "face_cm1"], ["Main"]),
        ("Cancel", ["face_cm"], ["Main"]),
    ),
)
def test_channel_master_drop(dragdrop, monkeypatch, tmp_path, choice, nodes, tabs):
    from maya import cmds
    from mgear.animbits import channel_master
    from mgear.animbits import channel_master_node as cmn

    shown = []
    monkeypatch.setattr(channel_master, "show_node", shown.append)
    first = cmn.drop_file(_cmc_file(tmp_path))
    assert first == "face_cm" and shown == ["face_cm"]

    monkeypatch.setattr(cmds, "confirmDialog", lambda **kw: choice)
    result = cmn.drop_file(_cmc_file(tmp_path, tabs=("Extra",)))
    assert sorted(cmn.list_channel_master_nodes()) == nodes
    assert cmn.get_node_data("face_cm")["tabs"] == tabs
    if choice == "Cancel":
        assert result is None and shown == ["face_cm"]
    else:
        assert shown[-1] == result


def test_channel_master_drop_reads_file_once(dragdrop, monkeypatch, tmp_path):
    import builtins

    from maya import cmds
    from mgear.animbits import channel_master
    from mgear.animbits import channel_master_node as cmn

    monkeypatch.setattr(channel_master, "show_node", lambda node: None)
    cmn.drop_file(_cmc_file(tmp_path))
    opened = []

    def counting_open(*args, **kwargs):
        opened.append(args[0])
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(cmn, "open", counting_open, raising=False)
    monkeypatch.setattr(cmds, "confirmDialog", lambda **kw: "Replace")
    path = _cmc_file(tmp_path, tabs=("Extra",))
    assert cmn.drop_file(path) == "face_cm"
    assert opened == [path]
    assert cmn.get_node_data("face_cm")["tabs"] == ["Extra"]


def _pkr_file(tmp_path, tabs=("Body", "Face")):
    from mgear.anim_picker.handlers import file_handlers

    path = str(tmp_path / "hero.pkr")
    data = {"tabs": [{"name": t, "data": {"items": []}} for t in tabs]}
    file_handlers.write_data_file(path, data=data, force=True)
    return path


def test_create_picker_from_file(dragdrop, tmp_path):
    from mgear.anim_picker import picker_node

    path = _pkr_file(tmp_path)
    node = picker_node.create_picker_from_file(path)
    assert node == picker_node.DataNode.__NODE__
    data_node = picker_node.DataNode(node)
    data = data_node.read_data_from_node()
    assert [t["name"] for t in data["tabs"]] == ["Body", "Face"]
    assert data["source_file_path"] == path
    assert data_node.get_file_path()


@pytest.mark.parametrize(
    "namespaces, answer, expected",
    (
        ([], None, "PICKER_DATAS"),
        (["hero"], ("hero", True), "hero:PICKER_DATAS"),
        (["hero"], ("hero", False), None),
    ),
)
def test_anim_picker_drop(
    dragdrop, monkeypatch, tmp_path, namespaces, answer, expected
):
    from maya import cmds
    import mgear.anim_picker as anim_picker
    from mgear.vendor.Qt import QtWidgets

    for ns in namespaces:
        cmds.namespace(add=ns)
    loaded = []
    monkeypatch.setattr(anim_picker, "load", lambda *a, **k: loaded.append(True))
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem", staticmethod(lambda *a, **k: answer)
    )
    monkeypatch.setattr("mgear.core.pyqt.maya_main_window", lambda: None)
    result = anim_picker.drop_file(_pkr_file(tmp_path))
    assert result == expected
    assert loaded == ([True] if expected else [])
    if expected:
        assert cmds.objExists(expected)


def test_import_anim_picker_template(dragdrop, tmp_path):
    from maya import cmds
    from mgear.shifter import custom_step_templates

    code = custom_step_templates.get_template_content(
        "import_anim_picker", "picker_step"
    )
    namespace = {}
    exec(compile(code, "picker_step.py", "exec"), namespace)
    step = namespace["CustomShifterStep"]({})
    step.setup()
    step.picker_path = _pkr_file(tmp_path)
    step.reparent_to_rig = False
    step.run()
    assert cmds.objExists("PICKER_DATAS")


@pytest.mark.parametrize("answer, count", (("No", 3), ("Yes", 1)))
def test_bookmarks_load_file(dragdrop, qt_app, monkeypatch, tmp_path, answer, count):
    from mgear.animbits import bookmarks
    from mgear.core import selection_bookmarks as core
    from mgear.vendor.Qt import QtWidgets

    path = str(tmp_path / "one.sbk")
    core.export_bookmarks(
        path,
        [
            {
                "name": "New",
                "items": ["pCube1"],
                "color": [1, 0, 0],
                "type": core.BOOKMARK_SELECTION,
            }
        ],
    )
    # dockable windows can't show in standalone: use an undocked window
    window = bookmarks.BookmarksUI()
    monkeypatch.setattr(bookmarks, "show", lambda *a: window)
    monkeypatch.setattr(bookmarks, "_window", window)
    try:
        window._bookmarks = []
        for name in ("A", "B"):
            window._add_chip(
                {
                    "name": name,
                    "items": [],
                    "color": [0, 1, 0],
                    "type": core.BOOKMARK_SELECTION,
                }
            )
        button = getattr(QtWidgets.QMessageBox, answer)
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "question", staticmethod(lambda *a, **k: button)
        )
        assert bookmarks.drop_file(path) is window
        assert len(window._bookmarks) == count
        assert window._bookmarks[-1]["name"] == "New"
        assert len(core.load_from_scene()["bookmarks"]) == count
    finally:
        window.close()


def test_channel_master_show_node(dragdrop, qt_app, monkeypatch):
    from mgear.animbits import channel_master
    from mgear.animbits import channel_master_node as cmn

    cmn.create_channel_master_node("a_cm")
    cmn.create_channel_master_node("b_cm")
    # dockable windows can't show in standalone: use an undocked window
    monkeypatch.setattr(
        channel_master, "openChannelMaster", lambda: channel_master.ChannelMaster()
    )
    window = channel_master.show_node("b_cm")
    try:
        assert window.node_list_combobox.currentText() == "b_cm"
    finally:
        window.close()


# Bind pose -------------------------------------------------------------------


def test_bind_pose_check(dragdrop):
    from maya import cmds
    from mgear.core import skin

    mesh, root, tip = _skinned_mesh()
    assert skin.is_at_bind_pose([mesh])
    assert skin.get_off_bind_pose_influences([mesh]) == []
    cmds.setAttr(root + ".rotateZ", 30)
    assert not skin.is_at_bind_pose([mesh])
    assert set(skin.get_off_bind_pose_influences([mesh])) == {root, tip}
    cmds.setAttr(root + ".rotateZ", 0)
    cmds.setAttr(tip + ".rotateX", 30)
    assert skin.get_off_bind_pose_influences([mesh]) == [tip]


def test_bind_pose_no_skin(dragdrop):
    from maya import cmds
    from mgear.core import skin

    cube = cmds.polyCube()[0]
    assert skin.is_at_bind_pose([cube, "missing_node"])


def test_scene_namespaces_moved_to_core(dragdrop):
    from maya import cmds
    from mgear.core import node_remap

    assert node_remap.scene_namespaces() == []
    cmds.namespace(add="hero")
    cmds.namespace(add="prop", parent="hero")
    assert node_remap.scene_namespaces() == ["hero", "hero:prop"]


def test_blendshape_imports_before_deformer(scripts_path):
    """core.blendshape loads on its own: deformer re-exports its names
    lazily, without a circular import."""
    code = (
        "import sys; sys.path.insert(0, {!r});"
        "import maya.standalone; maya.standalone.initialize();"
        "import mgear.core.blendshape;"
        "from mgear.core import deformer;"
        "from mgear.core.deformer import BS_TARGET_ITEM_ATTR;"
        "print('OK:' + str(deformer.bs_target_weight is "
        "mgear.core.blendshape.bs_target_weight))".format(scripts_path)
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=600
    )
    assert "OK:True" in result.stdout, result.stderr[-2000:]
