"""Import Skin Pack custom step template.

Template for importing skin weights from a .gSkinPack file.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.core import skin


class CustomShifterStep(cstp.customShifterMainStep):
    """Import skin weights from a skin pack file.

    This custom step imports skin weights from a .gSkinPack file.
    The skin pack contains weights for multiple meshes and can be
    exported from mGear's Skin IO tools.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the skin pack file path
        # Option 1: Hardcode the path
        # self.skin_pack_path = "path/to/your/weights.gSkinPack"

        # Option 2: Use a path relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.skin_pack_path = os.path.join(script_dir, "weights.gSkinPack")

        # Option 3: Leave as None to show file dialog at runtime
        self.skin_pack_path = None

        # Optional remap file (.gSkinMap) for renamed or namespaced
        # objects and joints. Save one from the remap dialog shown by
        # the mGear menu Import Skin Pack.
        self.skin_map_path = None

    def run(self):
        """Import the skin pack weights.

        If skin_pack_path is None, a file dialog will be shown
        to select the skin pack file.

        on_missing="error" stops the build, before any weights are
        applied, if an object or joint can't be resolved. Use "ui" to
        fix the mapping interactively instead, or "skip" to ignore them.

        Returns:
            None
        """
        self.log("Importing skin pack...")

        # importSkinPack will show file dialog if path is None
        skin.importSkinPack(
            self.skin_pack_path,
            on_missing="error",
            mapping=self.skin_map_path,
        )

        self.log("Skin pack import complete.")
        return'''
