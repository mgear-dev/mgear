"""Import Anim Picker Template custom step template.

Template for importing Anim Picker data from a .pkr file with optional
reparenting under the rig root.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.anim_picker import picker_node
from mgear.anim_picker.handlers import file_handlers
from maya import cmds


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Anim Picker template.

    This custom step imports Anim Picker data from a .pkr file and
    creates a picker data node in the scene. Optionally, the picker
    node can be reparented under the rig root for organization.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the Anim Picker template file path
        # Option 1: Hardcode the path
        # self.picker_path = "path/to/your/picker_template.pkr"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.picker_path = os.path.join(script_dir, "picker.pkr")

        # Option 3: Leave as None to show file dialog at runtime
        self.picker_path = None

        # Set to True to reparent the picker node under the rig root
        self.reparent_to_rig = True

        # Optional: Custom name for the picker node (None = use default)
        self.picker_node_name = None

    def run(self):
        """Import the Anim Picker template.

        If picker_path is None, a file dialog will be shown
        to select the picker file.

        Returns:
            None
        """
        self.log("Importing Anim Picker template...")

        file_path = self.picker_path

        # Show file dialog if no path is configured
        if not file_path:
            file_path = cmds.fileDialog2(
                caption="Import Anim Picker Template",
                fileMode=1,
                fileFilter="Anim Picker Files (*.pkr)",
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Read the picker data from file
        try:
            picker_data = file_handlers.read_data_file(file_path)
        except Exception as e:
            self.log(
                "Failed to read picker file: {{}}".format(e), level="error"
            )
            raise

        # Create the picker data node
        try:
            node_name = self.picker_node_name or picker_node.DataNode.__NODE__
            data_node = picker_node.DataNode(node_name)

            # Create the node if it doesn't exist
            if not data_node.exists():
                data_node.create()

            # Write the data to the node
            data_node.set_data(picker_data)
            data_node.write_data(to_node=True, to_file=False)

            # Store the file path reference
            if hasattr(data_node, "_set_str_attr"):
                data_node._set_str_attr(
                    data_node.__FILE_ATTR__,
                    file_handlers.replace_path_with_token(file_path),
                )

            self.log(
                "Anim Picker node '{{}}' created from: {{}}".format(
                    data_node.name, file_path
                )
            )

            # Reparent to rig root if requested
            if self.reparent_to_rig:
                self._reparent_to_rig(data_node.name)

        except Exception as e:
            self.log(
                "Failed to create picker node: {{}}".format(e), level="error"
            )
            raise

        return

    def _reparent_to_rig(self, node_name):
        """Reparent the picker node under the rig root.

        Args:
            node_name (str): Name of the picker node to reparent
        """
        try:
            # Get the rig root from the build
            rig_root = None
            if hasattr(self, "mgear_run") and self.mgear_run:
                if hasattr(self.mgear_run, "model"):
                    rig_root = self.mgear_run.model.name()

            if rig_root and cmds.objExists(rig_root):
                cmds.parent(node_name, rig_root)
                self.log(
                    "Picker node reparented under: {{}}".format(rig_root)
                )
            else:
                self.log(
                    "Rig root not found, picker node not reparented.",
                    level="warning",
                )
        except Exception as e:
            self.log(
                "Failed to reparent picker node: {{}}".format(e),
                level="warning",
            )'''
