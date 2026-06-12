import mgear.menu


def install():
    """Install Skinning submenu"""
    commands = (
        ("Channel Master", str_openChannelMaster, "mgear_channel_master.svg"),
        ("-----", None),
        ("Soft Tweaks", str_openSoftTweakManager, "mgear_soft_tweaks.svg"),
        ("Cache Manager", str_run_cache_mamanger, "mgear_cache_manager.svg"),
        ("-----", None),
        ("Human IK Mapper", str_mocap_humanIKMapper, "mgear_mocap.svg"),
        ("Space Recorder", str_space_recorder, "mgear_key.svg"),
        ("-----", None),
        ("Smart Reset Attribute/SRT", str_smart_reset, "mgear_smart_reset.svg"),
        ("-----", None),
        ("Spring Manager", str_openSpringManager, "mgear_spring.svg"),
        ("Bake Spring nodes (Shifter Component)", str_bakeSprings, "mgear_bake_spring.svg"),
        ("Clear Baked Spring nodes (Shifter Component)", str_clearSprings, "mgear_clear_spring.svg"),
    )

    mgear.menu.install("Animbits", commands, image="mgear_animbits.svg")


str_openChannelMaster = """
from mgear.animbits import channel_master
channel_master.openChannelMaster()
"""

str_openSoftTweakManager = """
from mgear.animbits import softTweaks
softTweaks.openSoftTweakManager()
"""

str_run_cache_mamanger = """
from mgear.animbits.cache_manager.dialog import run_cache_mamanger
run_cache_mamanger()
"""

str_smart_reset = """
from mgear.core import attribute
attribute.smart_reset()
"""

str_space_recorder = """
from mgear.animbits import space_recorder
space_recorder.open()
"""

str_bakeSprings = """
from mgear.core.anim_utils import bakeSprings
bakeSprings()
"""

str_clearSprings = """
from mgear.core.anim_utils import clearSprings
clearSprings()
"""

str_openSpringManager = """
from mgear.animbits.spring_manager import ui
ui.openSpringManagerManager()
"""

str_mocap_humanIKMapper = """
from mgear.animbits import humanIkMapper
humanIkMapper.show()
"""
