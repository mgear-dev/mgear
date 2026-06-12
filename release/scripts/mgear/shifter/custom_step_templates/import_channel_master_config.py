"""Import Channel Master Configuration custom step template.

Template for importing Channel Master node configurations from a .cmc file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.animbits import channel_master_node


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Channel Master configuration.

    This custom step imports Channel Master node configuration from a
    .cmc file exported by the Channel Master tool. A new Channel Master
    node will be created with the imported tab configuration.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the Channel Master configuration file path
        # Option 1: Hardcode the path
        # self.config_path = "path/to/your/channel_master.cmc"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.config_path = os.path.join(script_dir, "channel_master.cmc")

        # Option 3: Leave as None to show file dialog at runtime
        self.config_path = None

        # Optional: Specify an existing node to add data to
        # If None, a new Channel Master node will be created
        self.target_node = None

        # If True and target_node is set, data will be added to existing tabs
        # If False, existing data will be replaced
        self.add_data = False

    def run(self):
        """Import the Channel Master configuration.

        If config_path is None, a file dialog will be shown
        to select the configuration file.

        Returns:
            None
        """
        self.log("Importing Channel Master configuration...")

        file_path = self.config_path

        # Show file dialog if no path is configured
        if not file_path:
            import mgear.pymaya as pm

            file_path = pm.fileDialog2(
                caption="Import Channel Master Configuration",
                fileMode=1,
                fileFilter="Channel Master Configuration .cmc (*.cmc)",
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            if not isinstance(file_path, str):
                file_path = file_path[0]

        # Import the configuration
        try:
            node = channel_master_node.import_data(
                filePath=file_path,
                node=self.target_node,
                add_data=self.add_data,
            )
            if node:
                self.log(
                    "Channel Master configuration imported to node: {{}}".format(
                        node
                    )
                )
            else:
                self.log(
                    "Channel Master import completed from: {{}}".format(
                        file_path
                    )
                )
        except Exception as e:
            self.log(
                "Failed to import Channel Master configuration: {{}}".format(e),
                level="error",
            )
            raise

        return'''
