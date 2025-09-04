import importlib
import mgear.pymaya as pm
from mgear.vendor.Qt import QtCore, QtWidgets
import mgear.compatible.compatible_comp_ui as rcUI

importlib.reload(rcUI)


class RelatedComponents(QtWidgets.QDialog, rcUI.Ui_Dialog):
    def __init__(self, related_components, parent=None):
        self.toolName = "RelatedComponents"
        super(RelatedComponents, self).__init__(parent)
        self.setupUi(self)
        self.result_components = None
        self.update_flag = False
        self.components_comboBox.addItems(related_components)
        self.create_connections()
        self.setWindowTitle("Related Components")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def create_connections(self):
        self.buttonBox.accepted.connect(self.ok)
        self.update_checkBox.stateChanged.connect(self.on_update_changed)

    def on_update_changed(self, state):
        self.update_flag = state == QtCore.Qt.Checked

    def ok(self):
        self.result_components = str(self.components_comboBox.currentText())
        self.update_flag = self.update_checkBox.isChecked()

    def cancel(self):
        pm.displayWarning("User cancels update.")


def exec_window(related_components, *args):
    windw = RelatedComponents(related_components)
    if windw.exec_():
        return windw


if __name__ == "__main__":
    sample_components = ["Arm", "Leg", "Spine"]
    w = exec_window(sample_components)
    if w:
        print(f"Selected: {w.result_components}")
        print(f"Update enabled: {w.update_flag}")
