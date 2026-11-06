"""Skin IO and deformer IO with geometry from file references.

Each test saves a small asset scene, then references it under the ``ns``
namespace in a new scene.
"""

import logging

import pytest

NS = "ns"


# =============================================================================
# HELPERS
# =============================================================================


def _new_scene():
    from maya import cmds

    cmds.file(new=True, force=True)
    return cmds


def _save(path):
    """Save the current scene as a Maya ASCII file.

    Returns:
        str: The file path.
    """
    from maya import cmds

    path = str(path)
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    return path


def _reference(path):
    """Open a new scene that references a file under the ``ns`` namespace."""
    cmds = _new_scene()
    cmds.file(path, reference=True, namespace=NS)
    return cmds


def _visible_shape(transform):
    from maya import cmds

    return cmds.listRelatives(
        transform, shapes=True, noIntermediate=True, fullPath=True
    )[0]


def _points(mesh):
    from maya import cmds

    flat = cmds.xform(mesh + ".vtx[*]", query=True, worldSpace=True, translation=True)
    return [flat[i : i + 3] for i in range(0, len(flat), 3)]


def _max_delta(points_a, points_b):
    return max(abs(a - b) for pa, pb in zip(points_a, points_b) for a, b in zip(pa, pb))


def _plane(name="body"):
    """Create a 4x4 plane without construction history."""
    from maya import cmds

    return cmds.polyPlane(
        name=name, subdivisionsX=4, subdivisionsY=4, constructionHistory=False
    )[0]


def _skinned_plane(name="body", joints=("jA", "jB"), weights=True):
    """Create a plane bound to a joint chain, with per-vertex weights.

    Returns:
        tuple: (mesh, joints)
    """
    from maya import cmds

    mesh = _plane(name)
    cmds.select(clear=True)
    jnts = [
        cmds.joint(name=jnt, position=(ii - 0.5, 0, 0)) for ii, jnt in enumerate(joints)
    ]
    cmds.select(clear=True)
    skin_cls = cmds.skinCluster(jnts, mesh, toSelectedBones=True)[0]
    if weights:
        _set_weights(skin_cls, mesh, jnts, offset=0)
    return mesh, jnts


def _set_weights(skin_cls, mesh, joints, offset):
    """Give a mesh a non-default per-vertex weighting."""
    from maya import cmds

    for vtx in range(cmds.polyEvaluate(mesh, vertex=True)):
        w = ((vtx + offset) % 5) / 4.0
        cmds.skinPercent(
            skin_cls,
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


def _export_skin(tmp_path, mesh, name="skin.jSkin"):
    import mgear.pymaya as pm
    from mgear.core import skin

    path = str(tmp_path / name)
    assert skin.exportSkin(path, [pm.PyNode(mesh)])
    return path


@pytest.fixture
def warnings(monkeypatch, setup_path):
    """Record the messages of ``pm.displayWarning``."""
    import mgear.pymaya as pm

    messages = []
    monkeypatch.setattr(pm, "displayWarning", messages.append)
    return messages


# =============================================================================
# CORE HELPER
# =============================================================================


def testis_referenced(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import node

    cmds = _new_scene()
    cmds.polyCube(name="body")
    path = _save(tmp_path / "asset.ma")

    cmds = _reference(path)
    local = cmds.createNode("transform", name="local")
    assert node.is_referenced(NS + ":body")
    assert not node.is_referenced(local)


# =============================================================================
# SKIN IO
# =============================================================================


def test_referenced_skin_cluster_skipped(
    run_with_maya_standalone, setup_path, tmp_path, warnings
):
    from mgear.core.node import is_referenced
    from mgear.core import skin

    cmds = _new_scene()
    _skinned_plane()
    asset = _save(tmp_path / "asset.ma")

    # Other weights for the same mesh and joints
    cmds = _new_scene()
    mesh, joints = _skinned_plane(weights=False)
    _set_weights(skin.getSkinCluster(mesh).name(), mesh, joints, offset=2)
    path = _export_skin(tmp_path, mesh)

    cmds = _reference(asset)
    body = NS + ":body"
    skin_cls = skin.getSkinCluster(body).name()
    assert is_referenced(skin_cls)
    expected = _weights_by_short(body)
    influences = cmds.skinCluster(skin_cls, query=True, influence=True)

    # Skipped with every policy, "error" included
    for policy in ("skip", "error"):
        del warnings[:]
        assert skin.importSkin(path, on_missing=policy) == []
        assert _weights_by_short(body) == expected
        assert cmds.skinCluster(skin_cls, query=True, influence=True) == influences
        assert any(body in msg and "referenced" in msg for msg in warnings)


def test_referenced_skin_cluster_influences_not_reported(
    run_with_maya_standalone, setup_path, tmp_path, warnings
):
    from mgear.core import skin

    _new_scene()
    _skinned_plane()
    asset = _save(tmp_path / "asset.ma")

    # Joints that don't exist in the referencing scene
    _new_scene()
    mesh, _ = _skinned_plane(joints=("jX", "jY"))
    path = _export_skin(tmp_path, mesh)

    _reference(asset)
    resolved, report = skin._resolve_skin_data(
        skin._load_skin_file(path), path, None, skin.load_skin_mapping()
    )
    assert resolved == []
    assert report.is_empty()
    assert report.referenced == [NS + ":body"]
    # Nothing to remap: the error policy doesn't raise
    assert skin.importSkin(path, on_missing="error") == []
    assert any(NS + ":body" in msg for msg in warnings)


def test_referenced_skin_clusters_in_pack_summary(
    run_with_maya_standalone, setup_path, tmp_path, warnings
):
    import mgear.pymaya as pm
    from mgear.core import skin

    _new_scene()
    _skinned_plane("body", ("jA", "jB"))
    _skinned_plane("hat", ("jC", "jD"))
    _skinned_plane("prop", ("jE", "jF"))
    pack = str(tmp_path / "pack.gSkinPack")
    skin.exportSkinPack(pack, [pm.PyNode(n) for n in ("body", "hat", "prop")])

    # body and hat come skinned from a reference, prop is local
    _new_scene()
    _skinned_plane("body", ("jA", "jB"))
    _skinned_plane("hat", ("jC", "jD"))
    asset = _save(tmp_path / "asset.ma")
    _reference(asset)
    _skinned_plane("prop", ("jE", "jF"), weights=False)
    del warnings[:]
    skin.importSkinPack(pack)

    summaries = [
        msg
        for msg in warnings
        if (NS + ":body") in msg and (NS + ":hat") in msg and "referenced" in msg
    ]
    assert len(summaries) == 1
    assert "prop" not in summaries[0]


def test_referenced_geometry_without_skin(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core.node import is_referenced
    from mgear.core import skin

    cmds = _new_scene()
    _plane()
    asset = _save(tmp_path / "asset.ma")

    cmds = _new_scene()
    mesh, joints = _skinned_plane()
    first = _weights_by_short(mesh)
    path_a = _export_skin(tmp_path, mesh, "a.jSkin")
    _set_weights(skin.getSkinCluster(mesh).name(), mesh, joints, offset=2)
    second = _weights_by_short(mesh)
    path_b = _export_skin(tmp_path, mesh, "b.jSkin")
    assert first != second

    cmds = _reference(asset)
    cmds.select(clear=True)
    cmds.joint(name="jA", position=(-0.5, 0, 0))
    cmds.joint(name="jB", position=(0.5, 0, 0))
    body = NS + ":body"

    skin.importSkin(path_a, on_missing="error")
    skin_cls = skin.getSkinCluster(body).name()
    assert not is_referenced(skin_cls)
    assert ":" not in skin_cls
    assert _weights_by_short(body) == first

    # The local skinCluster made by the first import is updated
    skin.importSkin(path_b, on_missing="error")
    assert skin.getSkinCluster(body).name() == skin_cls
    assert _weights_by_short(body) == second


def test_vertex_positions_from_visible_shape(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import skin

    cmds = _new_scene()
    _plane()
    asset = _save(tmp_path / "asset.ma")

    # Skinned in the referencing scene: the referenced shape is hidden
    cmds = _reference(asset)
    body = NS + ":body"
    cmds.select(clear=True)
    jnts = [cmds.joint(name="jA", position=(-0.5, 0, 0))]
    jnts.append(cmds.joint(name="jB", position=(0.5, 0, 0)))
    cmds.select(clear=True)
    skin_cls = cmds.skinCluster(jnts, body, toSelectedBones=True)[0]
    _set_weights(skin_cls, body, jnts, offset=0)
    cmds.setAttr("jB.ty", 2)
    positions, geo_type = skin.getVertexPositions(body)
    assert geo_type == "mesh"
    current = _points(body)
    assert len(positions) == len(current)
    assert _max_delta([positions[i] for i in range(len(current))], current) < 1e-4

    # The hidden referenced shape keeps the rest pose
    hidden = [
        shape
        for shape in cmds.listRelatives(body, shapes=True, fullPath=True)
        if cmds.getAttr(shape + ".intermediateObject")
    ]
    assert hidden
    rest = [
        cmds.pointPosition("{}.vtx[{}]".format(hidden[0], i), world=True)
        for i in range(len(current))
    ]
    assert _max_delta(rest, current) > 0.1


def test_skin_copy_from_referenced_mesh(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import skin

    _new_scene()
    _skinned_plane()
    asset = _save(tmp_path / "asset.ma")

    _reference(asset)
    body = NS + ":body"
    proxy = _plane("proxy")
    skin.skinCopy(body, proxy)
    assert skin.getSkinCluster(proxy)
    assert _weights_by_short(proxy) == _weights_by_short(body)


def test_skin_copy_to_referenced_mesh(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core.node import is_referenced
    from mgear.core import skin

    _new_scene()
    _plane()
    asset = _save(tmp_path / "asset.ma")

    _reference(asset)
    source, _ = _skinned_plane("body_src")
    body = NS + ":body"
    skin.skinCopy(source, body)
    skin_cls = skin.getSkinCluster(body).name()
    assert skin_cls == "body_skinCluster"
    assert not is_referenced(skin_cls)
    assert _weights_by_short(body) == _weights_by_short(source)


# =============================================================================
# DEFORMER IO: SHAPE RESOLUTION
# =============================================================================


def _plain_meshes():
    """Create a sphere, a cube and a torus in a new scene."""
    cmds = _new_scene()
    cmds.polySphere(name="cloth", radius=1.2)
    cmds.polyCube(name="bodyA", width=2, height=2, depth=2)
    cmds.polyTorus(name="belt", radius=1.3, sectionRadius=0.1)
    return cmds


def _plain_asset(tmp_path):
    """Save a scene with a sphere, a cube and a torus, no deformers."""
    _plain_meshes()
    return _save(tmp_path / "asset.ma")


def _skin_locally(cmds, mesh):
    """Bind a referenced mesh to a new local joint."""
    cmds.select(clear=True)
    joint = cmds.joint(name="j_" + mesh.split(":")[-1])
    cmds.select(clear=True)
    cmds.skinCluster(joint, mesh, toSelectedBones=True)


def test_resolve_shape_ignores_intermediate(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import deformer_io

    cmds = _reference(_plain_asset(tmp_path))
    cloth = NS + ":cloth"
    _skin_locally(cmds, cloth)
    assert cmds.getAttr(NS + ":clothShape.intermediateObject")

    shape = deformer_io.resolve_shape({"shape": "clothShape", "transform": "cloth"})
    assert shape == _visible_shape(cloth)
    assert not cmds.getAttr(shape + ".intermediateObject")


def test_resolve_stored_deformed_shape_in_local_scene(
    run_with_maya_standalone, setup_path
):
    from mgear.core import deformer_io

    cmds = _new_scene()
    cloth = cmds.polySphere(name="cloth")[0]
    shape = deformer_io.resolve_shape(
        {"shape": NS + ":clothShapeDeformed", "transform": "|" + NS + ":cloth"}
    )
    assert shape == _visible_shape(cloth)


# =============================================================================
# DEFORMER IO: PROXIMITY WRAP AND SHRINK WRAP
# =============================================================================


def _wrap_deformers(cmds, prefix):
    """Proximity wrap on cloth, shrink wrap on belt, both driven by bodyA.

    Returns:
        tuple: (proximityWrap, shrinkWrap)
    """
    from mgear.core import deformer

    pw = cmds.deformer(prefix + "cloth", type="proximityWrap", name="pw1")[0]
    deformer.add_proximity_wrap_drivers(pw, [_visible_shape(prefix + "bodyA")])
    cmds.setAttr(pw + ".falloffScale", 1.5)
    deformer.set_deformer_weights(pw, 0, {3: 0.5, 10: 0.25})

    sw = cmds.deformer(prefix + "belt", type="shrinkWrap", name="sw1")[0]
    cmds.connectAttr(
        _visible_shape(prefix + "bodyA") + ".worldMesh[0]", sw + ".targetGeom"
    )
    cmds.setAttr(sw + ".offset", 0.05)
    deformer.set_deformer_weights(sw, 0, {3: 0.5, 10: 0.25})
    cmds.setAttr(prefix + "bodyA.ty", 0.4)
    return pw, sw


def _export_wraps(tmp_path, pw, sw):
    from mgear.rigbits import proximitywrap_io
    from mgear.rigbits import shrinkwrap_io

    pxw = str(tmp_path / "wraps.pxw")
    shw = str(tmp_path / "wraps.shw")
    proximitywrap_io.export_proximitywraps([pw], pxw)
    shrinkwrap_io.export_shrinkwraps([sw], shw)
    return pxw, shw


def _import_wraps(pxw, shw):
    from mgear.rigbits import proximitywrap_io
    from mgear.rigbits import shrinkwrap_io

    created = proximitywrap_io.import_proximitywraps(pxw, check_bind_pose=False)
    created += shrinkwrap_io.import_shrinkwraps(shw)
    return created


def _check_wrap(node, mesh, weights):
    from mgear.core import deformer
    from mgear.core.node import is_referenced

    assert not is_referenced(node)
    assert ":" not in node
    geometry = deformer.get_deformer_geometry(node)
    assert [shape for _, shape in geometry] == [_visible_shape(mesh)]
    assert deformer.get_deformer_weights(node, 0) == {
        k: pytest.approx(v, abs=1e-5) for k, v in weights.items()
    }


def test_wraps_on_referenced_geometry_round_trip(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import deformer

    asset = _plain_asset(tmp_path)
    cmds = _reference(asset)
    prefix = NS + ":"
    pw, sw = _wrap_deformers(cmds, prefix)
    weights = {n: deformer.get_deformer_weights(n, 0) for n in (pw, sw)}
    cloth_points = _points(prefix + "cloth")
    belt_points = _points(prefix + "belt")
    pxw, shw = _export_wraps(tmp_path, pw, sw)

    # Same asset referenced in a new scene
    cmds = _reference(asset)
    cmds.setAttr(prefix + "bodyA.ty", 0.4)
    pw_new, sw_new = _import_wraps(pxw, shw)
    _check_wrap(pw_new, prefix + "cloth", weights[pw])
    _check_wrap(sw_new, prefix + "belt", weights[sw])
    assert cmds.getAttr(pw_new + ".falloffScale") == pytest.approx(1.5)
    assert cmds.getAttr(sw_new + ".offset") == pytest.approx(0.05)
    assert _max_delta(_points(prefix + "cloth"), cloth_points) < 1e-4
    assert _max_delta(_points(prefix + "belt"), belt_points) < 1e-4

    # Referenced to local
    cmds.file(asset, open=True, force=True)
    cmds.setAttr("bodyA.ty", 0.4)
    pw_local, sw_local = _import_wraps(pxw, shw)
    _check_wrap(pw_local, "cloth", weights[pw])
    _check_wrap(sw_local, "belt", weights[sw])


def test_referenced_wraps_kept_on_replace(
    run_with_maya_standalone, setup_path, tmp_path, caplog
):
    from mgear.core.node import is_referenced
    from mgear.core import deformer

    cmds = _plain_meshes()
    pw, sw = _wrap_deformers(cmds, "")
    asset = _save(tmp_path / "asset.ma")

    cmds = _reference(asset)
    prefix = NS + ":"
    ref_pw, ref_sw = prefix + pw, prefix + sw
    weights = {n: deformer.get_deformer_weights(n, 0) for n in (ref_pw, ref_sw)}
    pxw, shw = _export_wraps(tmp_path, ref_pw, ref_sw)

    for _ in range(2):
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="mgear"):
            pw_new, sw_new = _import_wraps(pxw, shw)
        assert ref_pw in caplog.text
        assert ref_sw in caplog.text
        assert cmds.objExists(ref_pw)
        assert cmds.objExists(ref_sw)
        _check_wrap(pw_new, prefix + "cloth", weights[ref_pw])
        _check_wrap(sw_new, prefix + "belt", weights[ref_sw])
        # The second import replaces the local nodes of the first one
        for node_type in ("proximityWrap", "shrinkWrap"):
            local = [n for n in cmds.ls(type=node_type) if not is_referenced(n)]
            assert len(local) == 1


# =============================================================================
# LATTICE IO
# =============================================================================


def _lattice(cmds, mesh):
    from mgear.core import deformer

    ffd, lattice, _ = cmds.lattice(
        mesh, divisions=(2, 3, 2), objectCentered=True, name="ffd1"
    )
    cmds.xform(lattice + ".pt[1][2][1]", objectSpace=True, translation=(0.3, 0.6, 0.2))
    deformer.set_deformer_weights(ffd, 0, {3: 0.5, 10: 0.25})
    return ffd


def test_referenced_lattice_kept_and_names_without_namespace(
    run_with_maya_standalone, setup_path, tmp_path, caplog
):
    from mgear.core import deformer
    from mgear.rigbits import lattice_io

    cmds = _new_scene()
    sphere = cmds.polySphere(name="cloth")[0]
    _lattice(cmds, sphere)
    asset = _save(tmp_path / "asset.ma")

    cmds = _reference(asset)
    ref_ffd = NS + ":ffd1"
    ref_nodes = deformer.get_lattice_nodes(ref_ffd)
    weights = deformer.get_deformer_weights(ref_ffd, 0)
    path = str(tmp_path / "lattice.lat")
    lattice_io.export_lattices([ref_ffd], path)

    with caplog.at_level(logging.WARNING, logger="mgear"):
        created = lattice_io.import_lattices(path)
    assert ref_ffd in caplog.text
    assert all(cmds.objExists(n) for n in ref_nodes if n)
    assert created == ["ffd1"]
    _check_wrap("ffd1", NS + ":cloth", weights)

    # Into a scene without those nodes: names without namespace
    cmds = _new_scene()
    cmds.polySphere(name="cloth")
    assert lattice_io.import_lattices(path) == ["ffd1"]
    lat_tfm, lat_shape, base_tfm, _ = deformer.get_lattice_nodes("ffd1")
    assert lat_tfm == "|ffd1Lattice"
    assert base_tfm == "|ffd1Base"
    assert lat_shape == "|ffd1Lattice|ffd1LatticeShape"


def test_lattice_onto_referenced_deformed_geometry(
    run_with_maya_standalone, setup_path, tmp_path
):
    from mgear.core import deformer
    from mgear.rigbits import lattice_io

    cmds = _new_scene()
    sphere = cmds.polySphere(name="cloth")[0]
    ffd = _lattice(cmds, sphere)
    weights = deformer.get_deformer_weights(ffd, 0)
    path = str(tmp_path / "lattice.lat")
    lattice_io.export_lattices([ffd], path)

    cmds = _new_scene()
    cmds.polySphere(name="cloth")
    asset = _save(tmp_path / "asset.ma")
    cmds = _reference(asset)
    cloth = NS + ":cloth"
    _skin_locally(cmds, cloth)

    assert lattice_io.import_lattices(path) == ["ffd1"]
    _check_wrap("ffd1", cloth, weights)
