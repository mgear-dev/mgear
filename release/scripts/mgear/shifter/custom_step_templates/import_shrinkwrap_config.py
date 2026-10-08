"""Import Shrink Wrap Configuration custom step template.

Template for rebuilding shrinkWrap deformers from a Shrink Wrap IO .shw
file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits import shrinkwrap_io


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Shrink Wrap IO configuration.

    This custom step rebuilds shrinkWrap deformers from a .shw file
    exported by the Shrink Wrap IO tool (mGear > Rigbits > Shrink Wrap IO):
    settings, target and driven connections, affected geometry, weights
    and deformer order. The target meshes must exist in the rig.
    """

    def setup(self):
        """Set up the custom step name and import options."""
        self.name = "{stepName}"

        # Configure the shrink wrap configuration file path
        # Option 1: Hardcode the path
        # self.shrinkwrap_path = "path/to/your/shrinkwraps.shw"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.shrinkwrap_path = os.path.join(script_dir, "shrinkwraps.shw")

        # Option 3: Leave as None to show file dialog at runtime
        self.shrinkwrap_path = None

        # shrinkWrap names to import. None imports all of them
        self.shrinkwrap_names = None

        # Delete shrinkWraps with the same names before rebuilding them
        self.replace = True

        # Deformer order. None uses the mode stored in the file for each
        # shrink wrap. Override with:
        #   "current": the position it had when exported (last if not found)
        #   "front": before all the existing deformers
        #   "last": after all the existing deformers
        self.order = None

    def run(self):
        """Import the shrink wrap configuration.

        If shrinkwrap_path is None, a file dialog will be shown
        to select the configuration file.
        """
        self.log("Importing shrink wrap configuration...")

        file_path = self.shrinkwrap_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import Shrink Wrap Configuration",
                fileMode=1,
                fileFilter="mGear Shrink Wrap Config (*{{}})".format(
                    shrinkwrap_io.SHRINKWRAP_FILE_EXT
                ),
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the shrink wrap configuration
        try:
            created = shrinkwrap_io.import_shrinkwraps(
                file_path,
                names=self.shrinkwrap_names,
                replace=self.replace,
                order=self.order,
            )
            self.log(
                "Imported {{}} shrink wrap(s) from: {{}}".format(
                    len(created), file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import shrink wrap configuration: {{}}".format(e),
                level="error",
            )
            raise'''
