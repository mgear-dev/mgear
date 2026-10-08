"""Import Proximity Wrap Configuration custom step template.

Template for rebuilding proximityWrap deformers from a Proximity Wrap IO
.pxw file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits import proximitywrap_io


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Proximity Wrap IO configuration.

    This custom step rebuilds proximityWrap deformers from a .pxw file
    exported by the Proximity Wrap IO tool (mGear > Rigbits > Proximity
    Wrap IO): settings and ramps, drivers with their settings, driven
    connections, affected geometry, weights and deformer order. The driver
    meshes must exist in the rig, at bind pose (drivers are bound again
    at their current shape).
    """

    def setup(self):
        """Set up the custom step name and import options."""
        self.name = "{stepName}"

        # Configure the proximity wrap configuration file path
        # Option 1: Hardcode the path
        # self.proximitywrap_path = "path/to/your/proximitywraps.pxw"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.proximitywrap_path = os.path.join(script_dir, "proximitywraps.pxw")

        # Option 3: Leave as None to show file dialog at runtime
        self.proximitywrap_path = None

        # proximityWrap names to import. None imports all of them
        self.proximitywrap_names = None

        # Delete proximityWraps with the same names before rebuilding them
        self.replace = True

        # Deformer order. None uses the mode stored in the file for each
        # proximity wrap. Override with:
        #   "current": the position it had when exported (last if not found)
        #   "front": before all the existing deformers
        #   "last": after all the existing deformers
        self.order = None

    def run(self):
        """Import the proximity wrap configuration.

        If proximitywrap_path is None, a file dialog will be shown
        to select the configuration file.
        """
        self.log("Importing proximity wrap configuration...")

        file_path = self.proximitywrap_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import Proximity Wrap Configuration",
                fileMode=1,
                fileFilter="mGear Proximity Wrap Config (*{{}})".format(
                    proximitywrap_io.PROXIMITYWRAP_FILE_EXT
                ),
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the proximity wrap configuration
        try:
            created = proximitywrap_io.import_proximitywraps(
                file_path,
                names=self.proximitywrap_names,
                replace=self.replace,
                order=self.order,
            )
            self.log(
                "Imported {{}} proximity wrap(s) from: {{}}".format(
                    len(created), file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import proximity wrap configuration: {{}}".format(e),
                level="error",
            )
            raise'''
