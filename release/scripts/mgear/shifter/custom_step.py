import mgear.pymaya as pm
from mgear.core import attribute
from maya import cmds


class customShifterMainStep(object):
    '''
    Main Class for shifter custom steps
    '''

    def __init__(self, stored_dict):
        """Constructor
        """
        self._step_dict = stored_dict
        # init local setup root var
        # this should be a group to organize the objects of a local setup
        # we create it in a custom step
        self.setup_root = None

    @property
    def mgear_run(self):
        """Returns the resulting object of the 'mgearRun' step.
        """
        if "mgearRun" not in self._step_dict:
            raise Exception(
                "Can't access the 'mgearRun' in pre steps \
                or when running individual steps.")

        return self._step_dict.get('mgearRun')

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
                did not run yet.".format(name))

        return self._step_dict[name]

    def setup(self):
        """This function mus be re implemented for each custom step.

        Raises:
            Exception: Description
        """
        raise NotImplemented("'setup' must be implemented")

    def run(self):
        """This function mus be re implemented for each custom step.

        Raises:
            Exception: Description
        """
        raise NotImplemented("'run' must be implemented")

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
