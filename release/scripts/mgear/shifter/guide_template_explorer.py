import mgear.pymaya as pm


import mgear.shifter.guide_template_explorer_ui as gteUI
import mgear.shifter.guide_diff_ui as gdUI
from mgear.shifter import io, guide_template
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.core import pyqt
from mgear.vendor.Qt import QtCore, QtWidgets
from mgear.vendor.qjsonmodel import QJsonModel


class GuideTemplateExplorerUI(QtWidgets.QMainWindow, gteUI.Ui_MainWindow):
    def __init__(self, parent=None):
        super(GuideTemplateExplorerUI, self).__init__(parent)
        self.setupUi(self)


class GuideTemplateExplorer(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        self.toolName = "shifterGuideTemplateExplorer"
        super(GuideTemplateExplorer, self).__init__(parent=parent)
        self.gteUIInst = GuideTemplateExplorerUI()
        self.__model = QJsonModel()
        self.gteUIInst.explorer_treeView.setModel(self.__model)

        self.start_dir = pm.workspace(q=True, rootDirectory=True)

        self.create_window()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(GuideTemplateExplorer, self).keyPressEvent(event)

    def create_window(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Guide Template Explorer")
        self.resize(300, 330)

    def create_layout(self):

        self.gte_layout = QtWidgets.QVBoxLayout()
        self.gte_layout.addWidget(self.gteUIInst)

        self.setLayout(self.gte_layout)

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):
        self.gteUIInst.actionOpen.triggered.connect(self.open_template)
        self.gteUIInst.actionLoad_Selected_Guide.triggered.connect(
            self.load_selected_guide
        )
        self.gteUIInst.actionSave_As.triggered.connect(self.save_as_template)
        self.gteUIInst.actionClear.triggered.connect(self.clear_template)

        self.gteUIInst.actionBuild.triggered.connect(self.build_template)
        self.gteUIInst.actionImport.triggered.connect(self.import_template)
        self.gteUIInst.actionImport_Partial.triggered.connect(
            self.import_partial_template
        )
        self.gteUIInst.actionDiff_Tool.triggered.connect(self.diff_tool)

    #############
    # SLOTS
    #############
    def load_selected_guide(self):
        template = io.get_template_from_selection(None)
        if template:
            self.__model.load(template)
        else:
            pm.displayWarning("Not guide root slected")

    def open_template(self):
        template = io._import_guide_template()
        if template:
            self.__model.load(template)
        else:
            pm.displayWarning("Not guide template load")

    def save_as_template(self):
        template = self.__model.json()
        if template:
            io.export_guide_template(conf=template)
        else:
            pm.displayWarning("Not guide template load")

    def clear_template(self):
        self.__model.load({})

    def diff_tool(self):
        open_guide_template_diff(self.__model.json())

    def build_template(self):
        template = self.__model.json()
        if template:
            io.build_from_file(conf=template)
        else:
            pm.displayWarning("Not guide template load")

    def import_template(self):
        template = self.__model.json()
        if template:
            io.import_partial_guide(conf=template)
        else:
            pm.displayWarning("Not guide template load")

    def import_partial_template(self):
        template = self.__model.json()
        if template:
            indx = self.gteUIInst.explorer_treeView.selectedIndexes()[0]
            try:
                if indx.parent().internalPointer().key == "components_list":
                    part = indx.internalPointer().value
                    oSel = pm.selected()
                    if oSel and oSel[0].getParent(-1).hasAttr("ismodel"):
                        initParent = oSel[0]
                    else:
                        initParent = None
                    io.import_partial_guide(
                        partial=part, initParent=initParent, conf=template
                    )
                else:
                    pm.displayWarning(
                        "Please select a component guide to "
                        "import from components_list"
                    )
            except AttributeError:
                pm.displayWarning(
                    "Please select a component guide to import"
                    " from components_list"
                )
        else:
            pm.displayWarning("Not guide template load")


def open_guide_template_explorer(*args):

    pyqt.showDialog(GuideTemplateExplorer, dockable=True)


# Guide difference tool


class GuideDiffUI(QtWidgets.QDialog, gdUI.Ui_Form):
    def __init__(self, parent=None):
        super(GuideDiffUI, self).__init__(parent)
        self.setupUi(self)


class GuideDiffTool(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        self.toolName = "GuideDiffTool"
        super(GuideDiffTool, self).__init__(parent=parent)
        self.gdUIInst = GuideDiffUI()
        self.guide = None

        self.create_window()
        self.create_layout()
        self.create_connections()

    def create_window(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Shifter Guide Template Diff Tool")
        self.resize(250, 275)

    def create_layout(self):

        self.gd_layout = QtWidgets.QVBoxLayout()
        self.gd_layout.addWidget(self.gdUIInst)
        self.gd_layout.setContentsMargins(3, 3, 3, 3)

        self.setLayout(self.gd_layout)

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):

        # buttons
        self.gdUIInst.load_pushButton.clicked.connect(
            self.load_master_template
        )
        self.gdUIInst.runTest_pushButton.clicked.connect(self.run_test)

    #############
    # SLOTS
    #############

    def load_master_template(self):
        self.path = io._get_file()
        self.gdUIInst.path_lineEdit.setText(self.path)

    def run_test(self):
        master_guide = io._import_guide_template(self.path)
        miss = self.gdUIInst.missingGuide_checkBox.isChecked()
        extra = self.gdUIInst.extraGuide_checkBox.isChecked()
        guide_tra = self.gdUIInst.transform_checkBox.isChecked()
        root_sett = self.gdUIInst.rootSettings_checkBox.isChecked()
        comp_sett = self.gdUIInst.compSettings_checkBox.isChecked()
        custom_step = self.gdUIInst.customStep_checkBox.isChecked()
        guide_diff = guide_template.guide_diff(
            self.guide,
            master_guide,
            check_missing_guide_component_diff=miss,
            check_extra_guide_component_diff=extra,
            check_guide_transform_diff=guide_tra,
            check_guide_root_settings_diff=root_sett,
            check_component_settings_diff=comp_sett,
            check_guide_custom_step_diff=custom_step,
        )
        guide_template.print_guide_diff(guide_diff)


def open_guide_template_diff(guide=None, *args):

    if guide:
        windw = pyqt.showDialog(GuideDiffTool, dockable=True)
        windw.guide = guide
    else:
        pm.displayWarning("Initial guide not provided.")


if __name__ == "__main__":

    pyqt.showDialog(GuideTemplateExplorer, dockable=True)
