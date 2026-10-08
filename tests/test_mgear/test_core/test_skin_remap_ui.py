"""mgear.core.skin_remap_ui dialog tests"""


def _report_scene():
    """Scene with renamed joints and a report for the old names."""
    from maya import cmds
    from mgear.core import skin

    cmds.file(new=True, force=True)
    mesh = cmds.polyPlane(name="body", constructionHistory=False)[0]
    cmds.select(clear=True)
    left = cmds.joint(name="arm_R0_jnt", position=(-1, 0, 0))
    cmds.select(clear=True)
    spine = cmds.joint(name="new_spine", position=(0, 1, 0))
    cmds.skinCluster([left, spine], mesh, toSelectedBones=True)

    report = skin.SkinRemapReport("C:/tmp/body.jSkin")
    report.geometry.append(
        {"name": "body1", "long_name": None, "candidates": ["|a|body1", "|b|body1"]}
    )
    report.influences = {
        "arm_L0_jnt": {"position": None, "users": ["body"], "candidates": []},
        "spine": {"position": [0, 1, 0], "users": ["body"], "candidates": []},
    }
    report.influence_pool = ["|arm_R0_jnt", "|new_spine"]
    return report


def test_dialog_title_and_rows(qt_app, clean_settings):
    from mgear.core import skin_remap_ui

    dialog = skin_remap_ui.SkinRemapDialog(_report_scene(), index=2, total=5)
    try:
        assert "body.jSkin" in dialog.windowTitle()
        assert "2/5" in dialog.windowTitle()
        assert dialog.inf_table.rowCount() == 2
        assert dialog.geo_table.rowCount() == 1
        # Ambiguous geometry defaults to Skip.
        assert dialog.get_mapping()["geometry"] == {}
        assert not dialog.apply_btn.isEnabled()
    finally:
        dialog.deleteLater()


def test_dialog_batch_tools(qt_app, clean_settings):
    from mgear.core import skin_remap_ui

    dialog = skin_remap_ui.SkinRemapDialog(_report_scene())
    try:
        dialog.match_side()
        assert dialog.targets["arm_L0_jnt"] == "|arm_R0_jnt"
        assert dialog.methods["arm_L0_jnt"] == "side swap"
        assert dialog.position_btn.isEnabled()
        dialog.match_position()
        assert dialog.targets["spine"] == "|new_spine"
        assert dialog.apply_btn.isEnabled()

        # Manual change is recorded as such.
        combo = dialog.target_combos["spine"]
        combo.setCurrentIndex(dialog.pool.index("|arm_R0_jnt") + 1)
        assert dialog.methods["spine"] == "manual"
        assert dialog.get_mapping()["influences"] == {
            "arm_L0_jnt": "|arm_R0_jnt",
            "spine": "|arm_R0_jnt",
        }
    finally:
        dialog.deleteLater()


def test_dialog_position_disabled_without_data(qt_app, clean_settings):
    from mgear.core import skin_remap_ui

    report = _report_scene()
    report.influences["spine"]["position"] = None
    dialog = skin_remap_ui.SkinRemapDialog(report)
    try:
        assert not dialog.position_btn.isEnabled()
        assert "no influence positions" in dialog.position_btn.toolTip()
    finally:
        dialog.deleteLater()


def test_geometry_suggestions_and_picker(qt_app, clean_settings):
    from maya import cmds
    from mgear.core import skin
    from mgear.core import skin_remap_ui

    cmds.file(new=True, force=True)
    cmds.polyPlane(name="geo_body_01_MMM", constructionHistory=False)
    cmds.polyCube(name="geo_body_02_MMM", constructionHistory=False)
    report = skin.SkinRemapReport("body.jSkin")
    report.geometry.append(
        {
            "name": "geo_root|geo_body_00_MMM",
            "long_name": "|geo_root|geo_body_00_MMM",
            "point_count": 8,
            "candidates": [],
        }
    )
    dialog = skin_remap_ui.SkinRemapDialog(report)
    try:
        combo = dialog.geo_combos["geo_root|geo_body_00_MMM"]
        labels = [combo.itemText(i) for i in range(combo.count())]
        # Skip, then the cube (same point count) before the plane.
        assert labels == [
            skin_remap_ui.SKIP_LABEL,
            "geo_body_02_MMM  (8 pts) " + skin_remap_ui.SAME_COUNT_MARK,
            "geo_body_01_MMM  (121 pts)",
        ]
        assert dialog.get_mapping()["geometry"] == {}

        scene = dialog.session.get_scene_geometry()
        assert scene == {"|geo_body_01_MMM": 121, "|geo_body_02_MMM": 8}
        picker = skin_remap_ui.GeometryPickerDialog(scene, "geo_body_00_MMM", 8, dialog)
        assert picker.visible_count() == 2
        picker.filter_line.setText("01")
        assert picker.visible_count() == 1
        picker.filter_line.clear()
        picker.same_count_chk.setChecked(True)
        assert picker.visible_count() == 1
        visible = [i for i, _, _ in picker.items if not i.isHidden()]
        picker.tree.setCurrentItem(visible[0])
        assert picker.selected_path() == "|geo_body_02_MMM"
        picker.deleteLater()

        # A picked object is added to the row and selected.
        dialog.select_geometry("geo_root|geo_body_00_MMM", "|geo_body_02_MMM")
        assert dialog.get_mapping()["geometry"] == {
            "geo_root|geo_body_00_MMM": "|geo_body_02_MMM"
        }
    finally:
        dialog.deleteLater()


def test_tools_override_manual_rows_and_typed_text(qt_app, clean_settings):
    from mgear.core import skin_remap_ui

    dialog = skin_remap_ui.SkinRemapDialog(_report_scene())
    try:
        # Manual (wrong) choice, then a tool with nothing selected.
        combo = dialog.target_combos["spine"]
        combo.setCurrentIndex(dialog.pool_rows["|arm_R0_jnt"])
        assert dialog.methods["spine"] == "manual"
        dialog.match_position()
        assert dialog.targets["spine"] == "|new_spine"
        assert dialog.methods["spine"] == "position"
        # Rows without a match keep their target.
        dialog.set_target("arm_L0_jnt", "|arm_R0_jnt", "manual")
        dialog.match_position()
        assert dialog.targets["arm_L0_jnt"] == "|arm_R0_jnt"

        # Typed text matching a candidate selects it, otherwise reverts.
        combo.setEditText("ARM_R0_JNT")
        dialog.on_target_edited("spine")
        assert dialog.targets["spine"] == "|arm_R0_jnt"
        combo.setEditText("nope")
        dialog.on_target_edited("spine")
        assert combo.currentText() == "arm_R0_jnt"
        assert dialog.targets["spine"] == "|arm_R0_jnt"
    finally:
        dialog.deleteLater()


def test_mapping_saved_for_whole_import(qt_app, clean_settings, tmp_path, monkeypatch):
    import json

    from mgear.core import skin
    from mgear.core import skin_remap_ui
    from mgear.vendor.Qt import QtWidgets

    map_path = str(tmp_path / ("biped" + skin.MAP_EXT))
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **k: (map_path, "")),
    )
    # Choices from an earlier file of the same import.
    session = skin.SkinRemapSession({"influences": {"head_jnt": "|new_spine"}})

    dialog = skin_remap_ui.SkinRemapDialog(_report_scene(), 1, 2, session=session)
    try:
        dialog.match_side()
        dialog.save_mapping()
        assert session.save_path == map_path
        assert "biped" in dialog.save_label.text()
        with open(map_path) as fp:
            saved = json.load(fp)
        assert saved["influences"] == {
            "head_jnt": "|new_spine",
            "arm_L0_jnt": "|arm_R0_jnt",
        }
    finally:
        dialog.deleteLater()

    # The import merges the dialog choices; the next dialog updates the
    # same file on Apply, without asking again.
    session.add({"influences": {"arm_L0_jnt": "|arm_R0_jnt"}})
    dialog = skin_remap_ui.SkinRemapDialog(_report_scene(), 2, 2, session=session)
    try:
        dialog.set_target("spine", "|new_spine", "manual")
        dialog.accept_apply()
        # What the import does with an applied dialog.
        session.add(dialog.get_mapping())
        with open(map_path) as fp:
            saved = json.load(fp)
        assert saved["influences"]["spine"] == "|new_spine"
        assert saved["influences"]["head_jnt"] == "|new_spine"
    finally:
        dialog.deleteLater()

    # Skip this file doesn't save its rows.
    dialog = skin_remap_ui.SkinRemapDialog(_report_scene(), 2, 2, session=session)
    try:
        dialog.set_target("spine", "|arm_R0_jnt", "manual")
        dialog.accept_skip_file()
        with open(map_path) as fp:
            assert json.load(fp)["influences"]["spine"] == "|new_spine"
    finally:
        dialog.deleteLater()


def test_loaded_mapping_added_to_session(qt_app, clean_settings, tmp_path, monkeypatch):
    from mgear.core import skin
    from mgear.core import skin_remap_ui
    from mgear.vendor.Qt import QtWidgets

    map_path = skin.save_skin_mapping(
        {"influences": {"spine": "|new_spine", "other_jnt": "|arm_R0_jnt"}},
        str(tmp_path / ("in" + skin.MAP_EXT)),
    )
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        staticmethod(lambda *a, **k: (map_path, "")),
    )
    session = skin.SkinRemapSession()
    dialog = skin_remap_ui.SkinRemapDialog(_report_scene(), session=session)
    try:
        dialog.load_mapping()
        assert dialog.targets["spine"] == "|new_spine"
        assert dialog.methods["spine"] == "file"
        # Entries for other files are kept for the rest of the import.
        assert session.mapping["influences"]["other_jnt"] == "|arm_R0_jnt"
    finally:
        dialog.deleteLater()
