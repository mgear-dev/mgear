"""Custom Step Template Registry.

This module provides a registry of custom step templates that users can
choose from when creating a new custom step file.
"""

# Template metadata structure
TEMPLATES = {
    "blank": {
        "name": "Blank",
        "description": "Empty custom step with setup() and run() methods",
        "module": "blank",
    },
    "import_skin_pack": {
        "name": "Import Skin Pack",
        "description": "Import skin weights from a .gSkinPack file",
        "module": "import_skin_pack",
    },
    "import_guide_visualizer_config": {
        "name": "Import Guide Visualizer Configuration",
        "description": "Import guide visualizer settings from a JSON file",
        "module": "import_guide_visualizer_config",
    },
    "import_rbf_config": {
        "name": "Import RBF Configuration",
        "description": "Import RBF Manager setups from a JSON file",
        "module": "import_rbf_config",
    },
    "import_sdk_config": {
        "name": "Import SDK Configuration",
        "description": "Import Set Driven Keys from a JSON file",
        "module": "import_sdk_config",
    },
    "import_eye_rigger_config": {
        "name": "Import Eye Rigger Configuration",
        "description": "Build eye rigs from Eye Rigger 2.1 JSON configs (L/R)",
        "module": "import_eye_rigger_config",
    },
    "import_channel_master_config": {
        "name": "Import Channel Master Configuration",
        "description": "Import Channel Master node configuration from .cmc file",
        "module": "import_channel_master_config",
    },
    "import_anim_picker": {
        "name": "Import Anim Picker Template",
        "description": "Import Anim Picker from .pkr file with optional rig parenting",
        "module": "import_anim_picker",
    },
}


def get_template_names():
    """Return list of template keys and display names for UI.

    Returns:
        list: List of (key, display_name) tuples
    """
    return [(key, data["name"]) for key, data in TEMPLATES.items()]


def get_template_content(template_key, step_name):
    """Get the template content with the step name substituted.

    Args:
        template_key (str): Key identifying the template
        step_name (str): Name for the custom step

    Returns:
        str: Template content with {stepName} replaced
    """
    if template_key not in TEMPLATES:
        template_key = "blank"

    template_module_name = TEMPLATES[template_key]["module"]

    # Dynamic import of template module
    from importlib import import_module

    template_module = import_module(
        ".{}".format(template_module_name),
        package="mgear.shifter.custom_step_templates",
    )

    return template_module.TEMPLATE.format(stepName=step_name)
