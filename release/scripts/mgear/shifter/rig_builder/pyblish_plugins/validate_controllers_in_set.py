import pyblish.api
import mgear.pymaya as pm

# from pyblish_shifter.actions import RepairAction
# from pyblish_shifter.actions import SelectInvalidAction


class RenameAsNoCtl(pyblish.api.Action):
    """Rename the controllers with wrong suffix"""

    label = "Rename objects with _NoCtl suffix"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "wrench"  # Icon from Awesome Icon

    def process(self, context, plugin):
        """add _ctl to controllers grp"""
        for x in plugin.notInControllersSet:
            pm.rename(x, x.name().replace("_ctl", "_NoCtl"))


class validateControllersInSet(pyblish.api.Validator):
    """Validate if all the objects with name ended with '*_ctl'
    are members of the controllers_grp set"""

    families = ["rig"]
    # actions = [RepairAction, SelectInvalidAction, RenameAsNoCtl]
    actions = [RenameAsNoCtl]
    optional = True
    label = "Validator - Controllers in Set"

    @classmethod
    def get_invalid(self, instance, repair=False):
        # controls listed from scene
        ctlsByName = pm.ls("*_ctl", et="transform")

        self.notInControllersSet = []

        # get controllers grp
        oSet = self.getControllersGrp(instance)
        oMemb = oSet.members(flatten=True)
        self.notInControllersSet = list(set(ctlsByName) - set(oMemb))

        if repair:
            for x in self.notInControllersSet:
                oSet.add(x)

        return self.notInControllersSet

    @classmethod
    def getControllersGrp(self, instance):
        """return the controllers grp"""
        node = pm.PyNode(instance)
        sets = node.listConnections(type="objectSet")

        controllersGrp = False
        for oSet in sets:
            if "controllers_grp" in oSet.name().lower():
                controllersGrp = oSet

        return controllersGrp

    def process(self, instance):
        """Process all the nodes in the instance"""
        check = True
        notInControllersSet = self.get_invalid(instance)
        if notInControllersSet:
            check = False

        assert check, "{} are not in controllers_grp".format(
            str(notInControllersSet)
        )

    @classmethod
    def repair(self, instance):
        """add _ctl to controllers grp"""
        self.get_invalid(instance, True)
