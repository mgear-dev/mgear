import mgear
import mgear.menu
from maya import cmds


def install():
    """Install Shifter submenu"""
    commands = (
        ("Guide Manager", str_show_guide_manager, "mgear_list.svg"),
        ("-----", None),
        (None, game_submenu),
        ("-----", None),
        ("Settings", str_inspect_settings, "mgear_sliders.svg"),
        ("Duplicate", str_duplicate, "mgear_copy.svg"),
        ("Duplicate Sym", str_duplicateSym, "mgear_duplicate_sym.svg"),
        ("Extract Controls", str_extract_controls, "mgear_move.svg"),
        ("-----", None),
        ("Build from Selection", str_build_from_selection, "mgear_play.svg"),
        (
            "Build From Guide Template File",
            str_build_from_file,
            "mgear_play-circle.svg",
        ),
        ("Rig Builder", str_openRigBuilder, "mgear_rigBuilder.svg"),
        ("-----", None),
        (
            "Import Guide Template",
            str_import_guide_template,
            "mgear_log-in.svg",
        ),
        (
            "Export Guide Template",
            str_export_guide_template,
            "mgear_log-out.svg",
        ),
        (
            "Extract Guide From Rig",
            str_extract_guide_from_rig,
            "mgear_download.svg",
        ),
        (
            "Extract and Match Guide From Rig",
            str_extract_match_guide_from_rig,
            "mgear_download.svg",
        ),
        ("-----", None),
        (None, guide_template_samples_submenu),
        (
            "Match Guide to Selected Joint Hierarchy",
            str_matchGuide,
            "mgear_crosshair.svg",
        ),
        ("-----", None),
        ("Auto Fit Guide", str_auto_fit_guide),
        ("-----", None),
        ("Plebes...", str_plebes),
        (None, mocap_submenu),
        ("-----", None),
        ("Update Guide", str_updateGuide, "mgear_loader.svg"),
        ("-----", None),
        ("Reload Components", str_reloadComponents, "mgear_refresh-cw.svg"),
        ("-----", None),
        (
            "Data-Centric Folders Creator",
            str_dataCentricFolders,
            "mgear_folder.svg",
        ),
        ("-----", None),
        (None, log_submenu),
    )

    mgear.menu.install("Shifter", commands, image="mgear_shifter.svg")


def get_mgear_log_window_state():
    """get the option variable from maya to check if mGear log window
    is requested

    Returns:
        int: 0 or 1, state of override
    """
    if not cmds.optionVar(exists="mgear_log_window_OV"):
        cmds.optionVar(intValue=("mgear_log_window_OV", 0))
    state = cmds.optionVar(query="mgear_log_window_OV")
    mgear.use_log_window = state
    return state


def log_window(m):
    # get state
    state = get_mgear_log_window_state()

    cmds.setParent(m, menu=True)
    cmds.menuItem(
        "mgear_logWindow_menuitem",
        label="Shifter Log Window ",
        command=toogle_log_window,
        checkBox=state,
    )


def toogle_log_window(*args, **kwargs):
    # toogle log window
    state = args[0]
    mgear.use_log_window = state
    if state:
        cmds.optionVar(intValue=("mgear_log_window_OV", 1))
    else:
        cmds.optionVar(intValue=("mgear_log_window_OV", 0))


def log_submenu(parent_menu_id):
    """Create the guide sample templates submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("Toggle Log", str_toggleLog),
        ("Toggle Debug Mode", str_toggleDebugMode),
    )

    m = mgear.menu.install(
        "Build Log",
        commands,
        parent_menu_id,
        image="mgear_printer.svg",
    )

    log_window(m)


def mocap_submenu(parent_menu_id):
    """Create the mocap submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("Human IK Mapper", str_mocap_humanIKMapper, "mgear_mocap.svg"),
        ("-----", None),
        (
            "Import Mocap Skeleton Biped (Legacy)",
            str_mocap_importSkeletonBiped,
        ),
        ("Characterize Biped (Legacy)", str_mocap_characterizeBiped),
        ("Bake Mocap Biped (Legacy)", str_mocap_bakeMocap),
    )

    mgear.menu.install("Mocap", commands, parent_menu_id)


def game_submenu(parent_menu_id):
    """Create the game tools submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("FBX Export", str_game_fbx_export),
        ("-----", None),
        ("Disconnect Joints", str_game_disconnet),
        ("Connect Joints", str_game_connect),
        ("Delete Rig + Keep Joints", str_game_delete_rig),
        ("-----", None),
        ("Game Tool Disconnect + Assembly IO", str_openGameAssemblyTool),
    )

    mgear.menu.install(
        "Game Tools",
        commands,
        parent_menu_id,
        image="mgear_game.svg",
    )


def guide_template_samples_submenu(parent_menu_id):
    """Create the guide sample templates submenu

    Args:
        parent_menu_id (str): Parent menu. i.e: "MayaWindow|mGear|menuItem355"
    """
    commands = (
        ("Biped Template, Y-up", str_biped_template),
        ("Quadruped Template, Y-up", str_quadruped_template),
        ("Game Biped Template, Y-up", str_game_biped_template),
        ("-----", None),
        ("EPIC MetaHuman Template, Z-up", str_epic_metahuman_z_template),
        ("EPIC Mannequin Template, Z-up", str_epic_mannequin_z_template),
        ("EPIC MetaHuman Template, Y-up", str_epic_metahuman_y_template),
        ("EPIC Mannequin Template, Y-up", str_epic_mannequin_y_template),
        ("-----", None),
        ("EPIC MetaHuman Snap", str_epic_metahuman_snap),
        ("-----", None),
        ("Spider", str_spider_template),
        ("Giraffe", str_giraffe_template),
        ("Mantis", str_mantis_template),
        ("T-Rex", str_trex_template),
    )

    mgear.menu.install(
        "Guide Template Samples",
        commands,
        parent_menu_id,
        image="mgear_users.svg",
    )


str_show_guide_manager = """
from mgear.shifter import guide_manager_gui
guide_manager_gui.show_guide_manager()
"""

str_inspect_settings = """
from mgear.shifter import guide_manager
guide_manager.inspect_settings(0)
"""

str_duplicate = """
from mgear.shifter import guide_manager
guide_manager.duplicate(False)
"""

str_duplicateSym = """
from mgear.shifter import guide_manager
guide_manager.duplicate(True)
"""

str_extract_controls = """
from mgear.shifter import guide_manager
guide_manager.extract_controls()
"""

str_build_from_selection = """
from mgear.shifter import guide_manager
guide_manager.build_from_selection()
"""

str_build_from_file = """
from mgear.shifter import io
io.build_from_file(None)
"""

str_import_guide_template = """
from mgear.shifter import io
io.import_guide_template(None)
"""

str_export_guide_template = """
from mgear.shifter import io
io.export_guide_template(None, None)
"""

str_plebes = """
from mgear.shifter import plebes
plebes.plebes_gui()
"""

str_auto_fit_guide = """
from mgear.shifter import afg_tools_ui
afg_tools_ui.show()
"""

str_game_disconnet = """
from mgear.shifter import game_tools_disconnect
game_tools_disconnect.disconnect_joints()
"""

str_game_connect = """
from mgear.shifter import game_tools_disconnect
game_tools_disconnect.connect_joints_from_matrixConstraint()
"""

str_game_delete_rig = """
from mgear.shifter import game_tools_disconnect
game_tools_disconnect.delete_rig_keep_joints()
"""

str_openGameAssemblyTool = """
from mgear.shifter import game_tools_disconnect
game_tools_disconnect.openGameToolsDisconnect()
"""

str_updateGuide = """
from mgear.shifter import guide_template
guide_template.updateGuide()
"""

str_reloadComponents = """
from mgear import shifter
shifter.reloadComponents()
"""

str_biped_template = """
from mgear.shifter import io
io.import_sample_template("biped.sgt")
"""

str_quadruped_template = """
from mgear.shifter import io
io.import_sample_template("quadruped.sgt")
"""

str_epic_metahuman_z_template = """
from mgear.shifter import io
io.import_sample_template("EPIC_metahuman_z_up.sgt")
io.metahuman_snap()
"""
str_epic_mannequin_z_template = """
from mgear.shifter import io
io.import_sample_template("EPIC_mannequin_z_up.sgt")
"""

str_epic_metahuman_y_template = """
from mgear.shifter import io
io.import_sample_template("EPIC_metahuman_y_up.sgt")
io.metahuman_snap()
"""

str_epic_mannequin_y_template = """
from mgear.shifter import io
io.import_sample_template("EPIC_mannequin_y_up.sgt")
"""

str_epic_metahuman_snap = """
from mgear.shifter import io
io.metahuman_snap()
"""

str_game_biped_template = """
from mgear.shifter import io
io.import_sample_template("game_biped.sgt")
"""

str_spider_template = """
from mgear.shifter import io
io.import_sample_template("spider.sgt")
"""
str_mantis_template = """
from mgear.shifter import io
io.import_sample_template("mantis.sgt")
"""
str_trex_template = """
from mgear.shifter import io
io.import_sample_template("trex.sgt")
"""
str_giraffe_template = """
from mgear.shifter import io
io.import_sample_template("giraffe.sgt")
"""

str_mocap_importSkeletonBiped = """
from mgear.shifter import mocap_tools
mocap_tools.importSkeletonBiped()
"""

str_mocap_characterizeBiped = """
from mgear.shifter import mocap_tools
mocap_tools.characterizeBiped()
"""

str_mocap_bakeMocap = """
from mgear.shifter import mocap_tools
mocap_tools.bakeMocap()
"""

str_mocap_humanIKMapper = """
from mgear.animbits import humanIkMapper
humanIkMapper.show()
"""

str_toggleLog = """
import mgear
state = mgear.toggleLog()
print("Log State: {}".format(state))
"""

str_toggleDebugMode = """
import mgear
state = mgear.toggleDebug()
print("Debug Mode State: {}".format(state))
"""

str_game_fbx_export = """
from mgear.shifter.game_tools_fbx import fbx_exporter
fbx_exporter.openFBXExporter()
"""


str_extract_guide_from_rig = """
from mgear.shifter import guide_manager
guide_manager.extract_guide_from_rig()
"""

str_extract_match_guide_from_rig = """
from mgear.shifter import guide_manager
guide_manager.extract_match_guide_from_rig()
"""

str_openRigBuilder = """
from mgear.shifter.rig_builder import ui
ui.openRigBuilderUI()
"""

str_matchGuide = """
from mgear.shifter import guide_manager
guide_manager.snap_guide_to_root_joint()
"""

str_dataCentricFolders = """
import mgear.shifter.data_centric_folder_creator as dcfc
dcfc.openFolderStructureCreator()
"""
