import mgear.pymaya as pm
from mgear.core import attribute
from maya import cmds
import sys
import importlib
import os


class customShifterMainStep(object):
    """
    Main Class for shifter custom steps
    """

    def __init__(self, stored_dict):
        """Constructor"""
        self._step_dict = stored_dict
        # init local setup root var
        # this should be a group to organize the objects of a local setup
        # we create it in a custom step
        self.setup_root = None

    @property
    def mgear_run(self):
        """Returns the resulting object of the 'mgearRun' step."""
        if "mgearRun" not in self._step_dict:
            raise Exception(
                "Can't access the 'mgearRun' in pre steps \
                or when running individual steps."
            )

        return self._step_dict.get("mgearRun")

    @property
    def rig(self):
        """Alias for mgear_run for more intuitive access.

        Returns:
            mgearRun: The shifter rig object

        Example:
            global_ctl = self.rig.global_ctl
        """
        return self.mgear_run

    @property
    def guide(self):
        """Access to the guide if available.

        Returns:
            Guide: The guide object from the rig build
        """
        if hasattr(self.mgear_run, "guide"):
            return self.mgear_run.guide
        return None

    def component(self, name):
        """Access to components from the current build process.

        Args:
            name (str): The name of the component

        Returns:
            Component: The matching Component object
        """
        if name not in self.mgear_run.components:
            raise KeyError("Could not find the '{}' component.".format(name))
        return self.mgear_run.components[name]

    def components_by_type(self, comp_type):
        """Get all components of a specific type.

        Args:
            comp_type (str): The component type (e.g., "control_01", "arm_2jnt_01")

        Returns:
            list: List of matching components

        Example:
            all_controls = self.components_by_type("control_01")
            for ctrl in all_controls:
                print(ctrl.fullName)
        """
        matching = []
        for comp_name, comp in self.mgear_run.components.items():
            if comp.type == comp_type:
                matching.append(comp)
        return matching

    def has_component(self, name):
        """Check if a component exists without raising an error.

        Args:
            name (str): The name of the component

        Returns:
            bool: True if component exists, False otherwise

        Example:
            if self.has_component("arm_L0"):
                arm = self.component("arm_L0")
        """
        return name in self.mgear_run.components

    def custom_step(self, name):
        """Allows access to custom steps that have already ran in the past.

        Args:
            name (str): The name of the custom step

        Returns:
            customShifterMainStep: The matching customShifterMainStep object
        """
        if name not in self._step_dict:
            raise KeyError(
                "The custom step '{}' does not exist, or \
                did not run yet.".format(
                    name
                )
            )

        return self._step_dict[name]

    def has_custom_step(self, name):
        """Check if a custom step exists without raising an error.

        Args:
            name (str): The name of the custom step

        Returns:
            bool: True if custom step exists, False otherwise

        Example:
            if self.has_custom_step("proxy_setup"):
                proxy = self.custom_step("proxy_setup")
        """
        return name in self._step_dict

    def run_sub_step(self, module_name, step_path=None):
        """Load and run a sub custom step from an external module.

        This method allows you to dynamically load and execute another custom step
        from a separate Python file. The sub-step will have access to the same
        step dictionary, components, and mgear_run context as the parent step.

        The method will automatically:
        - Check for MGEAR_SHIFTER_CUSTOMSTEP_PATH environment variable if no step_path is provided
        - Add the step_path to sys.path if provided and not already present
        - Import and reload the module to get the latest changes
        - Find the class that inherits from customShifterMainStep
        - Instantiate it with the same step dictionary
        - Run its setup() and run() methods
        - Register it in the step dictionary for later access

        Args:
            module_name (str): The name of the Python module/file without the .py extension.
                              Example: "my_other_step" for file "my_other_step.py"
            step_path (str, optional): The absolute directory path where the module is located.
                                      If None, will check MGEAR_SHIFTER_CUSTOMSTEP_PATH environment variable.
                                      If neither is provided, assumes the module is already in Python's path.
                                      Example: "w:/my_steps" or "C:/pipeline/custom_steps"

        Returns:
            customShifterMainStep: The instantiated and executed sub-step object.
                                  You can use this to access attributes from the sub-step
                                  immediately after execution.

        Raises:
            ImportError: If the module cannot be found or imported
            AttributeError: If the module does not contain a class that inherits
                           from customShifterMainStep

        Examples:
            # Run a sub-step from a specific path
            self.run_sub_step("apply_colors", "w:/my_steps")

            # Run a sub-step using MGEAR_SHIFTER_CUSTOMSTEP_PATH env var
            self.run_sub_step("apply_colors")

            # Run a sub-step that's already in the Python path
            self.run_sub_step("mirror_controls")

            # Access the sub-step immediately after running
            color_step = self.run_sub_step("apply_colors", "w:/my_steps")
            print(color_step.colors_applied)

            # Access the sub-step later using custom_step()
            self.run_sub_step("apply_colors", "w:/my_steps")
            # ... other code ...
            colors = self.custom_step("apply_colors").colors_applied

        Note:
            - The module must contain exactly one class that inherits from
              customShifterMainStep (excluding the base class itself)
            - The sub-step's name (set in its setup() method) determines how
              it can be accessed later via self.custom_step("name")
            - The module is reloaded each time to ensure you get the latest version
              during development
            - If step_path is not provided, the method will check for the
              MGEAR_SHIFTER_CUSTOMSTEP_PATH environment variable
        """
        self.log("Running sub-step: '{}'".format(module_name))

        # If no step_path provided, check for environment variable
        if step_path is None:
            step_path = os.environ.get("MGEAR_SHIFTER_CUSTOMSTEP_PATH")

        # Add path if provided and not already in sys.path
        if step_path and step_path not in sys.path:
            sys.path.insert(0, step_path)

        # Import the module
        try:
            module = importlib.import_module(module_name)
            # Reload to ensure we get the latest version
            importlib.reload(module)
        except ImportError as e:
            raise ImportError(
                "Could not import module '{}': {}".format(module_name, e)
            )

        # Find the CustomShifterStep class in the module
        step_class = None
        for item_name in dir(module):
            item = getattr(module, item_name)
            # Check if it's a class and a subclass of customShifterMainStep
            # but not customShifterMainStep itself
            if (
                isinstance(item, type)
                and issubclass(item, customShifterMainStep)
                and item is not customShifterMainStep
            ):
                step_class = item
                break

        if not step_class:
            raise AttributeError(
                "Module '{}' has no class that inherits from customShifterMainStep".format(
                    module_name
                )
            )

        # Instantiate with the same step dictionary
        other_step = step_class(self._step_dict)

        # Run setup
        other_step.setup()

        # Register it in the step dictionary
        if other_step.name:
            self._step_dict[other_step.name] = other_step

        # Run the step
        other_step.run()

        self.log("Sub-step '{}' completed successfully".format(module_name))

        return other_step

    def get_or_create_setup_root(self, name=None):
        """Get or create the setup root group for organizing custom step objects.

        Args:
            name (str, optional): Custom name for the setup root.
                                 If None, uses "{self.name}_setup_grp"

        Returns:
            PyNode: The setup root group

        Example:
            setup_grp = self.get_or_create_setup_root()
            pm.parent(my_object, setup_grp)
        """
        if not self.setup_root or not pm.objExists(self.setup_root):
            grp_name = name or "{}_setup_root".format(self.name)
            self.setup_root = pm.group(empty=True, name=grp_name)

            # Try to parent under rig setup group if it exists
            if pm.objExists(
                self.mgear_run.setupWS
            ):
                pm.parent(self.setup_root, self.mgear_run.setupWS)

        return self.setup_root

    def log(self, message, level="info"):
        """Log a message with the step name prefix.

        Args:
            message (str): The message to log
            level (str): Log level - "info", "warning", or "error"

        Example:
            self.log("Processing controls")
            self.log("Missing component", level="warning")
        """
        prefix = "[{}]".format(self.name) if hasattr(self, "name") else "[CustomStep]"
        full_message = "{} {}".format(prefix, message)

        if level == "warning":
            pm.warning(full_message)
        elif level == "error":
            pm.error(full_message)
        else:
            print(full_message)

    def setup(self):
        """This function must be re implemented for each custom step.

        Raises:
            NotImplementedError: If not implemented in subclass
        """
        raise NotImplementedError("'setup' must be implemented")

    def run(self):
        """This function must be re implemented for each custom step.

        Raises:
            NotImplementedError: If not implemented in subclass
        """
        raise NotImplementedError("'run' must be implemented")

    def dup(self, source, name=None):
        """Duplicate the source object and rename it

        Args:
            source (PyNode): The Source object to duplicate
            name (None, string): The name for the new object. If the value
                is None the name will be set by using the custom step name

        Returns:
            PyNode: The new duplicated object.
        """
        dup = pm.duplicate(source)[0]
        dup.visibility.set(True)
        attribute.unlockAttribute(dup)
        if name:
            pm.rename(dup, name)
        else:
            pm.rename(dup, "_".join([source.name(), self.name, "setup"]))

        if self.setup_root:
            cmds.parent(dup.longName(), self.setup_root.longName())
        return dup
