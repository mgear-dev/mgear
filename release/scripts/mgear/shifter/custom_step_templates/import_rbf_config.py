"""Import RBF Manager Configuration custom step template.

Template for importing RBF (Radial Basis Function) setups from a JSON file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits import rbf_io


class CustomShifterStep(cstp.customShifterMainStep):
    """Import RBF Manager configuration.

    This custom step imports RBF setups from a JSON file exported by the
    RBF Manager tool. The RBF nodes will be recreated with all their
    poses and driver/driven connections.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the RBF configuration file path
        # Option 1: Hardcode the path
        # self.rbf_path = "path/to/your/rbf_config.json"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.rbf_path = os.path.join(script_dir, "rbf_config.json")

        # Option 3: Leave as None to show file dialog at runtime
        self.rbf_path = None

    def run(self):
        """Import the RBF configuration.

        If rbf_path is None, a file dialog will be shown
        to select the configuration file.

        Returns:
            None
        """
        self.log("Importing RBF configuration...")

        file_path = self.rbf_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import RBF Configuration",
                fileMode=1,
                fileFilter="RBF Files (*.json)",
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the RBF configuration
        try:
            rbf_io.importRBFs(file_path)
            self.log(
                "RBF configuration imported successfully from: {{}}".format(
                    file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import RBF configuration: {{}}".format(e),
                level="error",
            )
            raise

        return'''
