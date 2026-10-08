"""Import Lattice Configuration custom step template.

Template for rebuilding ffd lattice setups from a Lattice IO .lat file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits import lattice_io


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Lattice IO configuration.

    This custom step rebuilds ffd lattice setups from a .lat file exported
    by the Lattice IO tool (mGear > Rigbits > Lattice IO): lattice shape
    and placement, affected geometry, weights and deformer order.
    """

    def setup(self):
        """Set up the custom step name and import options."""
        self.name = "{stepName}"

        # Configure the lattice configuration file path
        # Option 1: Hardcode the path
        # self.lattice_path = "path/to/your/lattices.lat"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.lattice_path = os.path.join(script_dir, "lattices.lat")

        # Option 3: Leave as None to show file dialog at runtime
        self.lattice_path = None

        # ffd names to import. None imports all the lattices in the file
        self.lattice_names = None

        # Delete lattices with the same names before rebuilding them
        self.replace = True

        # Deformer order. None uses the mode stored in the file for each
        # lattice. Override with:
        #   "current": the position it had when exported (last if not found)
        #   "front": before all the existing deformers
        #   "last": after all the existing deformers
        self.order = None

    def run(self):
        """Import the lattice configuration.

        If lattice_path is None, a file dialog will be shown
        to select the configuration file.
        """
        self.log("Importing lattice configuration...")

        file_path = self.lattice_path

        # Show file dialog if no path is configured
        if not file_path:
            from maya import cmds

            file_path = cmds.fileDialog2(
                caption="Import Lattice Configuration",
                fileMode=1,
                fileFilter="mGear Lattice Config (*{{}})".format(
                    lattice_io.LATTICE_FILE_EXT
                ),
            )
            if not file_path:
                self.log("Import cancelled.", level="warning")
                return
            file_path = file_path[0]

        # Import the lattice configuration
        try:
            created = lattice_io.import_lattices(
                file_path,
                names=self.lattice_names,
                replace=self.replace,
                order=self.order,
            )
            self.log(
                "Imported {{}} lattice(s) from: {{}}".format(
                    len(created), file_path
                )
            )
        except Exception as e:
            self.log(
                "Failed to import lattice configuration: {{}}".format(e),
                level="error",
            )
            raise'''
