import pyblish.api
import mgear.pymaya as pm


@pyblish.api.log
class CollectShifterRig(pyblish.api.Collector):
    """Inject all Shifter rig parts from the scene into the context"""

    optional = True
    label = "Collector - Shifter Rig"

    def process(self, context):

        sets = pm.ls(sets=True)

        for obj in sets:

            patterns = ["sets_grp"]
            if any(ext in obj.name().lower() for ext in patterns):

                for cnx in obj.listConnections():
                    if cnx.hasAttr("is_rig"):
                        name = item = cnx.name()
                        instance = context.create_instance(name, family="rig")
                        instance.data["families"] = ["rig"]
                        instance.data["item"] = item
                        # instance.add(cnx)

                        self.log.info("Successfully collected %s" % cnx.name())
