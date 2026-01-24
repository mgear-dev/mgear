import re
from maya import cmds
from maya.api import OpenMaya
from . import base
from . import cmd
from . import exception


class EnumValue(object):
    def __init__(self, index, key):
        super(EnumValue, self).__init__()
        self.__index = index
        self.__key = key

    @property
    def key(self):
        return self.__key

    @property
    def index(self):
        return self.__index

    def __str__(self):
        """Fallback string representation."""
        return self.key if self.key else str(self.index)

    def __repr__(self):
        """Developer-friendly representation."""
        return f"EnumValue(index={self.index}, key='{self.key}')"


class Attribute(base.Attr):
    __selectionlist = OpenMaya.MSelectionList()

    @staticmethod
    def __getPlug(attrname):
        Attribute.__selectionlist.clear()
        try:
            Attribute.__selectionlist.add(attrname)
        except RuntimeError as e:
            return None

        return Attribute.__selectionlist.getPlug(0)

    def __init__(self, attrname_or_mplug):
        super(Attribute, self).__init__()
        self.__attrs = {}

        if isinstance(attrname_or_mplug, OpenMaya.MPlug):
            self.__plug = attrname_or_mplug
        else:
            self.__plug = Attribute.__getPlug(attrname_or_mplug)
            if self.__plug is None:
                raise RuntimeError(
                    "No such attribute '{}'".format(attrname_or_mplug)
                )

    def __hash__(self):
        return hash(self.name())

    def __getitem__(self, index):
        if not self.__plug.isArray:
            raise TypeError("{} is not an array plug".format(self.name()))

        return Attribute(self.__plug.elementByLogicalIndex(index))

    def __getattribute__(self, name):
        try:
            return super(Attribute, self).__getattribute__(name)
        except AttributeError:
            nfnc = super(Attribute, self).__getattribute__("name")
            if cmds.ls("{}.{}".format(nfnc(), name)):
                return super(Attribute, self).__getattribute__("attr")(name)

            raise

    def __floordiv__(self, other):
        return self.disconnect(other)

    def __rshift__(self, other):
        return self.connect(other, f=True)

    def plug(self):
        return self.__plug

    def name(self):
        this_plug = super(Attribute, self).__getattribute__("_Attribute__plug")
        obj = this_plug.node()
        nfunc = None

        if obj.hasFn(OpenMaya.MFn.kDagNode):
            nfunc = OpenMaya.MFnDagNode(
                OpenMaya.MDagPath.getAPathTo(obj)
            ).partialPathName
        else:
            nfunc = OpenMaya.MFnDependencyNode(obj).name

        return "{}.{}".format(
            nfunc(),
            this_plug.partialName(False, False, False, False, False, True),
        )

    def plugAttr(self, longName=False, fullPath=False):
        return self.__plug.partialName(
            False, False, False, False, fullPath, longName
        )

    def attrName(self, longName=False, includeNode=False):
        if includeNode:
            obj = self.__plug.node()
            nfunc = None

            if obj.hasFn(OpenMaya.MFn.kDagNode):
                nfunc = OpenMaya.MFnDagNode(
                    OpenMaya.MDagPath.getAPathTo(obj)
                ).partialPathName
            else:
                nfunc = OpenMaya.MFnDependencyNode(obj).name

            return "{}.{}".format(
                nfunc(),
                self.__plug.partialName(
                    False, False, False, False, False, longName
                ),
            )

        return self.__plug.partialName(
            False, False, False, False, False, longName
        )

    def getAlias(self):
        return OpenMaya.MFnDependencyNode(self.__plug.node()).plugsAlias(
            self.__plug
        )

    def node(self):
        from . import node

        obj = self.__plug.node()

        if obj.hasFn(OpenMaya.MFn.kDagNode):
            nfunc = OpenMaya.MFnDagNode(
                OpenMaya.MDagPath.getAPathTo(obj)
            ).partialPathName
        else:
            nfunc = OpenMaya.MFnDependencyNode(obj).name

        return node.BindNode(nfunc())

    def nodeName(self):
        return self.node().name()

    def delete(self):
        cmds.deleteAttr(self.name())

    def connect(self, other, **kwargs):
        force = kwargs.get("f", False)
        return cmds.connectAttr(
            self.name(),
            other.name() if isinstance(other, Attribute) else other,
            force=force,
        )

    def disconnect(self, *args):
        return cmd.disconnectAttr(self.name(), *args)

    def listConnections(self, **kwargs):
        return cmd.listConnections(self, **kwargs)

    # .... why ...
    def connections(self, **kwargs):
        return cmd.listConnections(self, **kwargs)

    def inputs(self, **kwargs):
        kwargs.pop("destination", None)
        kwargs.pop("d", None)
        kwargs.pop("source", None)
        kwargs.pop("s", None)
        kwargs["s"] = True
        kwargs["d"] = False
        return self.listConnections(**kwargs)

    def outputs(self, **kwargs):
        kwargs.pop("destination", None)
        kwargs.pop("d", None)
        kwargs.pop("source", None)
        kwargs.pop("s", None)
        kwargs["s"] = False
        kwargs["d"] = True
        return self.listConnections(**kwargs)

    def isConnected(self, **kwargs):
        return self.plug().isConnected

    def attr(self, name):
        attr_cache = super(Attribute, self).__getattribute__(
            "_Attribute__attrs"
        )
        if name in attr_cache:
            return attr_cache[name]

        this_plug = super(Attribute, self).__getattribute__("_Attribute__plug")
        ln = this_plug.partialName(
            False, False, False, False, False, True
        ).split(".")[-1]
        sn = this_plug.partialName(
            False, False, False, False, False, False
        ).split(".")[-1]
        res = re.match(r"{}\[([0-9]+)\]".format(re.escape(ln)), name)
        if res:
            return super(Attribute, self).__getattribute__("__getitem__")(
                int(res.group(1))
            )
        res = re.match(r"{}\[([0-9]+)\]".format(re.escape(sn)), name)
        if res:
            return super(Attribute, self).__getattribute__("__getitem__")(
                int(res.group(1))
            )

        if this_plug.isCompound:
            for ci in range(this_plug.numChildren()):
                cp = this_plug.child(ci)
                # Cache partialName calls - get both long and short forms
                long_name = cp.partialName(False, False, False, False, False, True).rsplit(".", 1)[-1]
                if name == long_name:
                    at = Attribute(cp)
                    attr_cache[name] = at
                    return at
                short_name = cp.partialName(False, False, False, False, False, False).rsplit(".", 1)[-1]
                if name == short_name:
                    at = Attribute(cp)
                    attr_cache[name] = at
                    return at

        raise exception.MayaAttributeError("No '{}' attr found".format(name))

    def lock(self):
        cmd.setAttr(self, l=True)

    def unlock(self):
        cmd.setAttr(self, l=False)

    def isLocked(self):
        return cmd.getAttr(self, l=True)

    def children(self):
        if not self.plug().isCompound:
            raise RuntimeError("{} has no children".format(self.name()))

        return [
            Attribute(self.plug().child(x))
            for x in range(self.plug().numChildren())
        ]

    def get(self, *args, **kwargs):
        return cmd.getAttr(self, *args, **kwargs)

    def set(self, *args, **kwargs):
        cmd.setAttr(self, *args, **kwargs)

    def type(self):
        return cmd.getAttr(self, type=True)

    def getEnums(self):
        attr = self.plug().attribute()
        if not attr.hasFn(OpenMaya.MFn.kEnumAttribute):
            raise Exception("{} is not an enum attribute".format(self.name()))

        fn = OpenMaya.MFnEnumAttribute(attr)
        res = {}
        splt = self.name().split(".")

        for el in cmds.attributeQuery(splt[-1], n=splt[0], le=True):
            for ev in el.split(":"):
                ev = ev.split("=")[0]
                res[ev] = fn.fieldValue(ev)

        return res

    def getMin(self):
        if cmd.attributeQuery(self.longName(), node=self.node(), mne=True):
            return cmd.attributeQuery(
                self.longName(), node=self.node(), min=True
            )[0]
        else:
            return None

    def getMax(self):
        if cmd.attributeQuery(self.longName(), node=self.node(), mxe=True):
            return cmd.attributeQuery(
                self.longName(), node=self.node(), max=True
            )[0]
        else:
            return None

    def getRange(self):
        return [self.getMin(), self.getMax()]

    def longName(self):
        return self.plug().partialName(False, False, False, False, False, True)

    def shortName(self):
        return self.plug().partialName(
            False, False, False, False, False, False
        )

    def getNumElements(self):
        """
        Get the number of elements in an array (multi) attribute.

        Returns:
            int: Number of elements in the multi-attribute.
        """
        if not self.__plug.isArray:
            raise TypeError(
                "{} is not an array (multi) plug".format(self.name())
            )

        # Get the indices of existing array elements
        indices = self.__plug.getExistingArrayAttributeIndices()
        return len(indices)

    def numConnectedElements(self):
        """
        Get the number of connected elements in a multi-attribute.

        Returns:
            int: Number of connected elements in the array attribute.
        """
        if not self.__plug.isArray:
            raise TypeError(
                "{} is not an array (multi) plug".format(self.name())
            )

        count = 0
        # Iterate over existing indices and check if the element is connected
        for index in self.__plug.getExistingArrayAttributeIndices():
            element = self.__plug.elementByLogicalIndex(index)
            if element.isConnected:
                count += 1

        return count

    def index(self):
        """Return the index of a multi-attribute element if present.

        Returns:
            int or None: The index of the attribute element if present,
                otherwise None.
        """
        attr_name = self.name()
        match = re.search(r"\[(\d+)\]$", attr_name)
        if match:
            return int(match.group(1))
        return None

    def elements(self):
        """Return the existing element names of an array attribute.

        Returns a list of attribute name strings for each existing element in a
        multi/array attribute. For sparse arrays, returns names like
        ["inputCurves[0]", "inputCurves[2]", "inputCurves[5]"].

        Returns:
            list: List of element attribute name strings.

        Raises:
            TypeError: If the attribute is not an array plug.
        """
        if not self.__plug.isArray:
            raise TypeError(
                "{} is not an array (multi) plug".format(self.name())
            )

        base_name = self.__plug.partialName(
            False, False, False, False, False, True
        )
        indices = self.__plug.getExistingArrayAttributeIndices()
        return ["{}[{}]".format(base_name, i) for i in indices]
