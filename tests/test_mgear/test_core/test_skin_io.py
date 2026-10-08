"""mgear.core.skin IO tests: namespaces, clashing names and remapping"""

import json
import os

import pytest


def _scene():
    from maya import cmds

    cmds.file(new=True, force=True)
    return cmds


def _make_rig(cmds, ns="", parent=None, name="body", joints=("jA", "jB")):
    """Create a plane bound to a joint chain.

    Returns:
        tuple: (mesh transform full path, joint full paths)
    """
    if ns and not cmds.namespace(exists=ns):
        cmds.namespace(add=ns)
    prefix = ns + ":" if ns else ""
    mesh = cmds.polyPlane(
        name=prefix + name, subdivisionsX=4, subdivisionsY=4, constructionHistory=False
    )[0]
    if parent:
        if not cmds.objExists(parent):
            cmds.createNode("transform", name=parent)
        mesh = cmds.parent(mesh, parent)[0]
    cmds.select(clear=True)
    jnts = []
    for ii, jnt in enumerate(joints):
        jnts.append(cmds.joint(name=prefix + jnt, position=(ii - 0.5, 0, 0)))
    cmds.skinCluster(jnts, mesh, toSelectedBones=True)
    return (
        cmds.ls(mesh, long=True)[0],
        [cmds.ls(j, long=True)[0] for j in jnts],
    )


def _set_weights(cmds, mesh, joints):
    """Give the mesh a non-default, per-vertex weighting."""
    from mgear.core import skin

    skinCls = skin.getSkinCluster(mesh).name()
    count = cmds.polyEvaluate(mesh, vertex=True)
    for vtx in range(count):
        w = (vtx % 5) / 4.0
        cmds.skinPercent(
            skinCls,
            "{}.vtx[{}]".format(mesh, vtx),
            transformValue=[(joints[0], w), (joints[1], 1.0 - w)],
        )


def _weights_by_short(mesh):
    """Return {vtx: {short joint name: weight}} rounded."""
    from mgear.core import node_remap
    from mgear.core import skin

    data = skin.getCompleteWeights(mesh)
    return {
        vtx: {node_remap.short_name(k): round(v, 4) for k, v in w.items()}
        for vtx, w in data.items()
    }


def _export(cmds, tmp_path, mesh, name="skin.jSkin"):
    import mgear.pymaya as pm
    from mgear.core import skin

    path = str(tmp_path / name)
    assert skin.exportSkin(path, [pm.PyNode(mesh)])
    return path


def test_export_identity_data(run_with_maya_standalone, setup_path, tmp_path):
    cmds = _scene()
    mesh, joints = _make_rig(cmds, ns="char")
    # Pose away from bind: positions must still be bind pose.
    cmds.setAttr(joints[1] + ".tx", 5)
    path = _export(cmds, tmp_path, mesh)
    with open(path) as fp:
        data = json.load(fp)["objDDic"][0]
    assert data["objLongName"] == "|char:body"
    assert data["nameSpace"] == "char:"
    assert sorted(data["weights"]) == ["jA", "jB"]
    assert data["influencePositions"]["jB"] == pytest.approx([0.5, 0, 0])


def test_namespace_to_root_round_trip(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    mesh, joints = _make_rig(cmds, ns="char")
    _set_weights(cmds, mesh, joints)
    expected = _weights_by_short(mesh)
    path = _export(cmds, tmp_path, mesh)

    cmds = _scene()
    mesh, joints = _make_rig(cmds)
    skin.importSkin(path, on_missing="error")
    assert _weights_by_short(mesh) == expected


def test_root_to_namespace_without_skin(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    mesh, joints = _make_rig(cmds)
    _set_weights(cmds, mesh, joints)
    expected = _weights_by_short(mesh)
    path = _export(cmds, tmp_path, mesh)

    cmds = _scene()
    mesh, joints = _make_rig(cmds, ns="rig")
    cmds.delete(skin.getSkinCluster(mesh).name())
    skin.importSkin(path, on_missing="error")
    assert skin.getSkinCluster(mesh)
    assert _weights_by_short(mesh) == expected


def test_pack_namespace_and_clash_file_names(
    run_with_maya_standalone, setup_path, tmp_path
):
    import mgear.pymaya as pm
    from mgear.core import skin

    cmds = _scene()
    meshA, _ = _make_rig(cmds, ns="nsA", joints=("aA", "aB"))
    meshB, _ = _make_rig(cmds, ns="nsB", joints=("bA", "bB"))
    meshC, _ = _make_rig(cmds, parent="grpA", joints=("cA", "cB"))
    meshD, _ = _make_rig(cmds, parent="grpB", joints=("dA", "dB"))
    pack = str(tmp_path / "test.gSkinPack")
    skin.exportSkinPack(
        pack, [pm.PyNode(m) for m in (meshA, meshB, meshC, meshD)], use_json=True
    )
    with open(pack) as fp:
        files = json.load(fp)["packFiles"]
    assert sorted(files) == sorted(
        ["nsA.body.jSkin", "nsB.body.jSkin", "grpA-body.jSkin", "grpB-body.jSkin"]
    )
    for f in files:
        assert os.path.exists(os.path.join(str(tmp_path), f))

    # Clashing objects import back to the right one.
    expected = _weights_by_short(meshD)
    cmds.skinPercent(
        skin.getSkinCluster(meshD).name(), meshD, transformValue=[("dA", 1.0)]
    )
    skin.importSkinPack(pack, on_missing="error")
    assert _weights_by_short(meshD) == expected


def test_file_name_collision_suffix(setup_path):
    from mgear.core import skin

    used = set()
    assert skin._skin_file_name("|grp|body", used) == "grp-body"
    assert skin._skin_file_name("grp|Body", used) == "grp-Body_1"
    assert skin._skin_file_name("ns:body", used) == "ns.body"


def test_clashing_joint_short_names(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    mesh = cmds.polyPlane(name="body", constructionHistory=False)[0]
    for side, x in (("armA", -1), ("armB", 1)):
        cmds.select(clear=True)
        cmds.joint(name=side, position=(x, 0, 0))
        cmds.joint(name="end_jnt", position=(x * 0.5, 0, 0))
    endA, endB = "|armA|end_jnt", "|armB|end_jnt"
    skinCls = cmds.skinCluster([endA, endB], mesh, toSelectedBones=True)[0]
    cmds.skinPercent(skinCls, mesh + ".vtx[0]", transformValue=[(endA, 1.0)])
    cmds.skinPercent(skinCls, mesh + ".vtx[1]", transformValue=[(endB, 1.0)])
    path = _export(cmds, tmp_path, "|body")

    cmds.skinPercent(skinCls, mesh, transformValue=[(endA, 0.5), (endB, 0.5)])
    skin.importSkin(path, on_missing="error")
    assert cmds.skinPercent(
        skinCls, mesh + ".vtx[0]", query=True, transform=endA
    ) == pytest.approx(1.0)
    assert cmds.skinPercent(
        skinCls, mesh + ".vtx[1]", query=True, transform=endB
    ) == pytest.approx(1.0)


def _renamed_target(cmds, tmp_path):
    """Export from jA/jB and rebuild the scene with renamed joints."""
    mesh, joints = _make_rig(cmds)
    _set_weights(cmds, mesh, joints)
    expected = {
        vtx: {k.replace("j", "new_j"): v for k, v in w.items()}
        for vtx, w in _weights_by_short(mesh).items()
    }
    path = _export(cmds, tmp_path, mesh)
    cmds = _scene()
    mesh, _ = _make_rig(cmds, joints=("new_jA", "new_jB"))
    return path, mesh, expected


def test_on_missing_error(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    path, mesh, _ = _renamed_target(cmds, tmp_path)
    before = _weights_by_short(mesh)
    with pytest.raises(skin.SkinRemapError) as err:
        skin.importSkin(path, on_missing="error")
    report = err.value.reports[0]
    assert sorted(report.influences) == ["jA", "jB"]
    assert report.influences["jA"]["position"] == pytest.approx([-0.5, 0, 0])
    assert _weights_by_short(mesh) == before


def test_on_missing_callable_and_position_match(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import node_remap
    from mgear.core import skin

    cmds = _scene()
    path, mesh, expected = _renamed_target(cmds, tmp_path)
    calls = []

    def policy(report):
        calls.append(report)
        sources = {k: v["position"] for k, v in report.influences.items()}
        targets = skin.get_bind_world_positions(
            skin._skin_influence_paths(skin.getSkinCluster(mesh))
        )
        return {"influences": node_remap.match_by_position(sources, targets, 0.01)}

    skin.importSkin(path, on_missing=policy)
    assert len(calls) == 1
    assert _weights_by_short(mesh) == expected


def test_on_missing_skip_warns(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    path, mesh, _ = _renamed_target(cmds, tmp_path)
    # No influence resolves: the object is skipped, nothing raises.
    assert skin.importSkin(path) == []


def test_pack_policy_per_file_and_carry_forward(
    run_with_maya_standalone, setup_path, tmp_path
):
    import mgear.pymaya as pm
    from mgear.core import skin

    cmds = _scene()
    meshes = [
        (
            _make_rig(cmds, name=n, joints=("jA", "jB"))[0]
            if n == "m1"
            else cmds.polyPlane(name=n, constructionHistory=False)[0]
        )
        for n in ("m1", "m2", "m3")
    ]
    for m in meshes[1:]:
        cmds.skinCluster(["jA", "jB"], m, toSelectedBones=True)
    pack = str(tmp_path / "p.gSkinPack")
    skin.exportSkinPack(pack, [pm.PyNode(m) for m in meshes], use_json=True)

    cmds.rename("jA", "new_jA")
    cmds.rename("jB", "new_jB")
    calls = []

    def policy(report):
        calls.append(report)
        return {"influences": {"jA": "new_jA", "jB": "new_jB"}}

    skin.importSkinPack(pack, on_missing=policy)
    # Asked once; files 2 and 3 reuse the mapping.
    assert len(calls) == 1


def test_pack_error_is_atomic(run_with_maya_standalone, setup_path, tmp_path):
    import mgear.pymaya as pm
    from mgear.core import skin

    cmds = _scene()
    m1, j1 = _make_rig(cmds, name="m1", joints=("jA", "jB"))
    m2, j2 = _make_rig(cmds, name="m2", joints=("kA", "kB"))
    pack = str(tmp_path / "p.gSkinPack")
    skin.exportSkinPack(pack, [pm.PyNode(m1), pm.PyNode(m2)], use_json=True)

    skinCls = skin.getSkinCluster(m1).name()
    cmds.skinPercent(skinCls, m1, transformValue=[(j1[0], 1.0)])
    before = _weights_by_short(m1)
    cmds.rename(j2[1], "renamed")
    with pytest.raises(skin.SkinRemapError) as err:
        skin.importSkinPack(pack, on_missing="error")
    assert len(err.value.reports) == 1
    assert _weights_by_short(m1) == before


def test_pack_cancel_stops_remaining(run_with_maya_standalone, setup_path, tmp_path):
    import mgear.pymaya as pm
    from mgear.core import skin

    cmds = _scene()
    m1, j1 = _make_rig(cmds, name="m1", joints=("jA", "jB"))
    m2, j2 = _make_rig(cmds, name="m2", joints=("kA", "kB"))
    m3, j3 = _make_rig(cmds, name="m3", joints=("lA", "lB"))
    pack = str(tmp_path / "p.gSkinPack")
    skin.exportSkinPack(pack, [pm.PyNode(m) for m in (m1, m2, m3)], use_json=True)
    for m, j in ((m1, j1), (m3, j3)):
        cmds.skinPercent(skin.getSkinCluster(m).name(), m, transformValue=[(j[0], 1.0)])
    m3_before = _weights_by_short(m3)
    cmds.rename(j2[1], "renamed")

    skin.importSkinPack(pack, on_missing=lambda report: None)
    # File 1 applied (weights restored), file 3 never reached.
    assert _weights_by_short(m1) != {v: {"jA": 1.0} for v in _weights_by_short(m1)}
    assert _weights_by_short(m3) == m3_before


def test_mapping_file_reuse(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    path, mesh, expected = _renamed_target(cmds, tmp_path)
    map_path = skin.save_skin_mapping(
        {"influences": {"jA": "new_jA", "jB": "new_jB"}},
        str(tmp_path / ("remap" + skin.MAP_EXT)),
    )
    with open(map_path) as fp:
        assert json.load(fp)["version"] == 1
    skin.importSkin(path, on_missing="error", mapping=map_path)
    assert _weights_by_short(mesh) == expected


def test_old_file_without_new_keys(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    cmds = _scene()
    mesh, joints = _make_rig(cmds)
    _set_weights(cmds, mesh, joints)
    expected = _weights_by_short(mesh)
    path = _export(cmds, tmp_path, mesh)
    with open(path) as fp:
        pack = json.load(fp)
    for data in pack["objDDic"]:
        data.pop("objLongName")
        data.pop("influencePositions")
    with open(path, "w") as fp:
        json.dump(pack, fp)

    cmds.skinPercent(
        skin.getSkinCluster(mesh).name(), mesh, transformValue=[(joints[0], 1.0)]
    )
    skin.importSkin(path, on_missing="error")
    assert _weights_by_short(mesh) == expected


def test_vertex_mismatch_volume_regression(
    run_with_maya_standalone, setup_path, tmp_path
):
    import mgear.pymaya as pm
    from mgear.core import skin

    cmds = _scene()
    mesh, joints = _make_rig(cmds)
    path = str(tmp_path / "pos.jSkin")
    skin.exportSkin(path, [pm.PyNode(mesh)], storePositions=True)

    cmds = _scene()
    mesh = cmds.polyPlane(
        name="body", subdivisionsX=6, subdivisionsY=6, constructionHistory=False
    )[0]
    cmds.select(clear=True)
    cmds.joint(name="jA", position=(-0.5, 0, 0))
    cmds.joint(name="jB", position=(0.5, 0, 0))
    volume = skin.importSkin(path, on_missing="error")
    assert volume == ["body"]
    assert skin.getSkinCluster(mesh)


def test_policy_asked_again_for_picked_geometry(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import skin

    cmds = _scene()
    path, mesh, expected = _renamed_target(cmds, tmp_path)
    mesh = cmds.rename(mesh, "body_renamed")
    calls = []

    def policy(report):
        calls.append(report)
        if report.geometry:
            # The joints of the missing object aren't known yet.
            assert not report.influences
            return {"geometry": {"body": "|body_renamed"}}
        return {"influences": {"jA": "new_jA", "jB": "new_jB"}}

    skin.importSkin(path, on_missing=policy)
    assert len(calls) == 2
    assert sorted(calls[1].influences) == ["jA", "jB"]
    assert _weights_by_short("body_renamed") == expected


def test_report_subset_keys_by_kind(setup_path):
    from mgear.core import skin

    report = skin.SkinRemapReport("f.jSkin")
    report.geometry.append({"name": "body", "long_name": None, "candidates": []})
    report.influences = {"body": {"position": None, "users": [], "candidates": []}}
    report.influence_pool = ["|a"]
    # A mesh and a joint with the same name are different items.
    assert report.item_keys() == {("geometry", "body"), ("influence", "body")}
    sub = report.subset({("influence", "body")})
    assert not sub.geometry
    assert list(sub.influences) == ["body"]
    assert sub.influence_pool == ["|a"]
