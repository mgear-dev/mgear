import mgear.pymaya as pm

from mgear.vendor.Qt import QtCore, QtWidgets


import mgear.shifter.component.chain_guide_initializer_ui as cgiUI


class ChainGuideInitializer(QtWidgets.QDialog,
                            cgiUI.Ui_Dialog):

    """Modal dialog to set positions for the chain guides

    Attributes:
        dir_axis (int): Direction for the chain [X, Y, Z, -X, -Y, -Z]
        sections_number (int): Number of sections in the guide
        spacing (float): Space between sections
        toolName (str): Name of the tool
    """

    def __init__(self, parent=None):
        self.toolName = "ChainGuideInitializer"
        super(ChainGuideInitializer, self).__init__(parent)
        self.setupUi(self)

        self.sections_number = None
        self.dir_axis = None
        self.spacing = None

        self.create_connections()
        self.setWindowTitle("Chain Initializer")

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def create_connections(self):
        self.buttonBox.accepted.connect(self.ok)
        self.buttonBox.rejected.connect(self.cancel)

    def ok(self):
        self.sections_number = self.sections_spinBox.value()
        self.dir_axis = self.direction_comboBox.currentIndex()
        self.spacing = self.spacing_doubleSpinBox.value()

    def cancel(self):
        pm.displayWarning("Guide Chain Drawing Cancelled")


def exec_window(*args):

    windw = ChainGuideInitializer()
    if windw.exec_():
        return windw


if __name__ == "__main__":

    w = exec_window()
    if w:
        print(w.sections_number)
        print(w.dir_axis)
        print(w.spacing)
