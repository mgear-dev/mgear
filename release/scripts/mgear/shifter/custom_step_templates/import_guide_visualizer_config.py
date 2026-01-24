"""Import Guide Visualizer Configuration custom step template.

Template for importing guide visualizer settings from a JSON file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.shifter.guide_tools.guide_visualizer import (
    import_full_configuration,
)


class CustomShifterStep(cstp.customShifterMainStep):
    """Import guide visualizer configuration.

    This custom step imports guide visualizer settings including:
    - Display curves configuration
    - Guide colors
    - Guide curves (lineWidth, CV scale)
    - Labels

    The configuration is imported from a JSON file exported by the
    Guide Visualizer tool.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the configuration file path
        # Option 1: Hardcode the path
        # self.config_path = "path/to/your/guide_visualizer_config.json"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.config_path = os.path.join(script_dir, "guide_vis_config.json")

        # Option 3: Leave as None to show file dialog at runtime
        self.config_path = None

    def run(self):
        """Import the guide visualizer configuration.

        If config_path is None, a file dialog will be shown
        to select the configuration file.

        Returns:
            None
        """
        self.log("Importing guide visualizer configuration...")

        file_path = self.config_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import Guide Visualizer Configuration",
                fileMode=1,
                fileFilter="JSON Files (*.json)",
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the configuration
        try:
            import_full_configuration(file_path)
            self.log(
                "Configuration imported successfully from: {{}}".format(
                    file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import configuration: {{}}".format(e), level="error"
            )
            raise

        return'''
