"""Import SDK Manager Configuration custom step template.

Template for importing Set Driven Keys from a JSON file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits import sdk_io


class CustomShifterStep(cstp.customShifterMainStep):
    """Import SDK Manager configuration.

    This custom step imports Set Driven Keys (SDK) from a JSON file
    exported by the SDK Manager tool. The SDK nodes will be recreated
    with all their driver/driven connections and keyframes.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the SDK configuration file path
        # Option 1: Hardcode the path
        # self.sdk_path = "path/to/your/sdk_config.json"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.sdk_path = os.path.join(script_dir, "sdk_config.json")

        # Option 3: Leave as None to show file dialog at runtime
        self.sdk_path = None

    def run(self):
        """Import the SDK configuration.

        If sdk_path is None, a file dialog will be shown
        to select the configuration file.

        Returns:
            None
        """
        self.log("Importing SDK configuration...")

        file_path = self.sdk_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import SDK Configuration",
                fileMode=1,
                fileFilter="SDK Files (*.json)",
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the SDK configuration
        try:
            sdk_io.importSDKs(file_path)
            self.log(
                "SDK configuration imported successfully from: {{}}".format(
                    file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import SDK configuration: {{}}".format(e),
                level="error",
            )
            raise

        return'''
