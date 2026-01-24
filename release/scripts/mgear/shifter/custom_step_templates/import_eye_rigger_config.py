"""Import Eye Rigger 2.1 Configuration custom step template.

Template for building eye rigs from JSON configuration files.
Supports importing both left and right eye configurations.
"""

TEMPLATE = r'''import mgear.shifter.custom_step as cstp
from mgear.rigbits.facial_rigger2 import eye_rigger


class CustomShifterStep(cstp.customShifterMainStep):
    """Import Eye Rigger 2.1 configuration.

    This custom step builds eye rigs from JSON configuration files
    exported by the Eye Rigger 2.1 tool. Supports building both
    left and right eyes from separate configuration files.
    """

    def setup(self):
        """Set up the custom step name."""
        self.name = "{stepName}"

        # Configure the eye rigger configuration file paths
        # You can set paths for left eye, right eye, or both

        # Option 1: Hardcode the paths
        # self.left_eye_path = "path/to/your/left_eye_config.json"
        # self.right_eye_path = "path/to/your/right_eye_config.json"

        # Option 2: Use paths relative to this script
        # import os
        # script_dir = os.path.dirname(__file__)
        # self.left_eye_path = os.path.join(script_dir, "left_eye.json")
        # self.right_eye_path = os.path.join(script_dir, "right_eye.json")

        # Option 3: Leave as None to show file dialog at runtime
        self.left_eye_path = None
        self.right_eye_path = None

        # Set to True to prompt for file selection if path is None
        self.prompt_for_left = True
        self.prompt_for_right = True

    def run(self):
        """Build the eye rigs from configuration files.

        Returns:
            None
        """
        from maya import cmds

        # Build left eye
        if self.left_eye_path or self.prompt_for_left:
            left_path = self.left_eye_path
            if not left_path:
                left_path = cmds.fileDialog2(
                    caption="Select Left Eye Configuration",
                    fileMode=1,
                    fileFilter="Eye Rigger Config (*.json)",
                )
                if left_path:
                    left_path = left_path[0]

            if left_path:
                self.log("Building left eye rig...")
                try:
                    eye_rigger.rig_from_file(left_path)
                    self.log(
                        "Left eye rig built from: {{}}".format(left_path)
                    )
                except Exception as e:
                    self.log(
                        "Failed to build left eye: {{}}".format(e),
                        level="error",
                    )
                    raise

        # Build right eye
        if self.right_eye_path or self.prompt_for_right:
            right_path = self.right_eye_path
            if not right_path:
                right_path = cmds.fileDialog2(
                    caption="Select Right Eye Configuration",
                    fileMode=1,
                    fileFilter="Eye Rigger Config (*.json)",
                )
                if right_path:
                    right_path = right_path[0]

            if right_path:
                self.log("Building right eye rig...")
                try:
                    eye_rigger.rig_from_file(right_path)
                    self.log(
                        "Right eye rig built from: {{}}".format(right_path)
                    )
                except Exception as e:
                    self.log(
                        "Failed to build right eye: {{}}".format(e),
                        level="error",
                    )
                    raise

        self.log("Eye rigger import complete.")
        return'''
