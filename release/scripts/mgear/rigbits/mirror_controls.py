import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import mgear

from mgear.vendor.Qt import QtCore, QtWidgets


class MirrorController:
    def __init__(self):
        pass

    @staticmethod
    def get_opposite_control(node):
        try:
            side_l = node.attr("L_custom_side_label").get()
            side_r = node.attr("R_custom_side_label").get()
            side = node.attr("side_label").get()

            target_name = None
            if side == "L":
                target_name = node.name().replace(side_l, side_r)
            elif side == "R":
                target_name = node.name().replace(side_r, side_l)

            if target_name and pm.objExists(target_name):
                return pm.PyNode(target_name)
            return None
        except pm.MayaAttributeError:
            # try to get the opposite control using the old logic
            target_name = mgear.core.string.convertRLName(node.name())
            target = None
            if pm.objExists(target_name):
                target = pm.PyNode(target_name)
            return target

    @staticmethod
    def get_specific_side_controls(side="L"):
        # Find controllers set
        rig_models = [item for item in pm.ls(transforms=True) if item.hasAttr("is_rig")]
        controllers_set = None
        for node in rig_models[0].rigGroups.inputs():
            if node.name().endswith("controllers_grp"):
                controllers_set = node
                break

        # Collect all transforms from set and subsets.
        nodes = []
        for node in controllers_set.members():
            if node.nodeType() == "objectSet":
                nodes.extend(node.members())
            else:
                nodes.append(node)

        side_name = None
        side_ctl = [node for node in nodes if node.hasAttr("{}_custom_side_label".format(side))]
        if side_ctl:
            side_name = side_ctl[0].attr("{}_custom_side_label".format(side)).get()

        # Find all nodes without exclusion_string
        nodes = [x for x in nodes if side_name in x.name()]
        return nodes

    @staticmethod
    def copy_and_prepare_source(source):
        source_copy = pm.duplicate(source)[0]
        mgear.core.attribute.setKeyableAttributes(
            source_copy,
            ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]
        )

        for child in source_copy.getChildren():
            if child.nodeType() != "nurbsCurve":
                pm.delete(child)
        return source_copy

    def mirror_pairs(self, pairs):
        # Modify control shapes
        for source, target in pairs:
            source_copy = self.copy_and_prepare_source(source)

            pm.select(clear=True)

            # Mirror a source copy under a group node
            grp = pm.group(em=True, world=True)
            pm.parent(source_copy, grp)
            grp.scaleX.set(-1)

            # Re-parent, freeze transforms and match color
            pm.parent(source_copy, target)
            pm.makeIdentity(source_copy, apply=True, t=1, r=1, s=1, n=0)
            pm.parent(source_copy, target.getParent())

            target_color = mgear.core.curve.get_color(target)
            if target_color:
                mgear.core.curve.set_color(source_copy, target_color)

            # Replace shape
            mgear.rigbits.replaceShape(source_copy, [target])

            # Clean up
            pm.delete(grp)
            pm.delete(source_copy)

    def mirror_selection(self):
        pairs = []
        for source in pm.selected():
            target = self.get_opposite_control(source)
            if not target:
                continue
            pairs.append([source, target])

        self.mirror_pairs(pairs)

    def mirror_left_to_right(self):
        pairs = []
        for source in self.get_specific_side_controls(side="L"):
            target = self.get_opposite_control(source)
            if target:
                pairs.append([source, target])

        self.mirror_pairs(pairs)

    def mirror_right_to_left(self):
        pairs = []
        for source in self.get_specific_side_controls(side="R"):
            target = self.get_opposite_control(source)
            if target:
                pairs.append([source, target])

        self.mirror_pairs(pairs)


class MirrorControlsUi(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(MirrorControlsUi, self).__init__(parent)

        self.func = MirrorController()

        self.setWindowTitle("Mirror Controls")
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)
        self.setMinimumSize(QtCore.QSize(350, 0))

        layout = QtWidgets.QVBoxLayout(self)
        self.selection_button = QtWidgets.QRadioButton("Selection")
        self.selection_button.setChecked(True)
        layout.addWidget(self.selection_button)

        self.left_to_right_button = QtWidgets.QRadioButton("Left to Right")
        layout.addWidget(self.left_to_right_button)

        self.right_to_left_button = QtWidgets.QRadioButton("Right to Left")
        layout.addWidget(self.right_to_left_button)

        self.mirror_button = QtWidgets.QPushButton("Mirror Controls")
        layout.addWidget(self.mirror_button)

        self.mirror_button.clicked.connect(self.mirror_button_pressed)

    def mirror_button_pressed(self):
        pm.undoInfo(openChunk=True)

        # Store selection
        selection = pm.selected()

        if self.selection_button.isChecked():
            self.func.mirror_selection()
        if self.left_to_right_button.isChecked():
            self.func.mirror_left_to_right()
        if self.right_to_left_button.isChecked():
            self.func.mirror_right_to_left()

        # Restore selection
        pm.select(selection)

        pm.undoInfo(closeChunk=True)


def show(*args):
    mgear.core.pyqt.showDialog(MirrorControlsUi)


if __name__ == "__main__":
    show()
