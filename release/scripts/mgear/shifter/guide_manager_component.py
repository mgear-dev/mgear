import os
import sys
import traceback
from functools import partial

import pymel.core as pm

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.core import pyqt

from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

from mgear import shifter
from mgear.shifter import guide_manager
from mgear.shifter import guide_manager_component_ui as gmcUI
import importlib

PY2 = sys.version_info[0] == 2

class GuideManagerComponentUI(QtWidgets.QDialog, gmcUI.Ui_Form):

    def __init__(self, parent=None):
        super(GuideManagerComponentUI, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setupUi(self)
        self.component_listView.setAcceptDrops(False)
        self.component_listView.setDragEnabled(True)
        self.component_listView.setDropIndicatorShown(False)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(GuideManagerComponentUI, self).keyPressEvent(event)


class GuideManagerComponent(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    def __init__(self, parent=None):
        self.toolName = "shifterComponentManager"
        super(GuideManagerComponent, self).__init__(parent=parent)

        self.gmcUIInst = GuideManagerComponentUI()
        self.gmcUIInst.component_listView.setAction(self.drag_draw_component)
        self.gmcUIInst.component_listView.installEventFilter(self)

        self.start_dir = pm.workspace(q=True, rootDirectory=True)

        self.__proxyModel = QtCore.QSortFilterProxyModel(self)
        self.gmcUIInst.component_listView.setModel(self.__proxyModel)

        self.create_window()
        self.create_layout()
        self.create_connections()
        self._refreshList()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def eventFilter(self, watched, event):

        if (event.type() == QtCore.QEvent.KeyPress
                and event.matches(
                    QtGui.QKeySequence.InsertParagraphSeparator)):
            self.draw_component()

        return False

    def create_window(self):

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Shifter Guide Component")
        self.resize(280, 600)

    def create_layout(self):

        self.gmc_layout = QtWidgets.QVBoxLayout()
        self.gmc_layout.addWidget(self.gmcUIInst)
        self.gmc_layout.setContentsMargins(3, 3, 3, 3)

        self.setLayout(self.gmc_layout)

    def get_component_list(self):
        comp_list = []
        compDir = shifter.getComponentDirectories()
        trackLoadComponent = []
        for path, comps in compDir.items():
            pm.progressWindow(title='Loading Components',
                              progress=0,
                              max=len(comps))
            for comp_name in comps:
                pm.progressWindow(e=True,
                                  step=1,
                                  status='\nLoading: %s' % comp_name)
                if comp_name == "__init__.py":
                    continue
                elif comp_name in trackLoadComponent:
                    pm.displayWarning(
                        "Custom component name: %s, already in default "
                        "components. Names should be unique. This component is"
                        " not loaded" % comp_name)
                    continue
                else:
                    trackLoadComponent.append(comp_name)

                if not os.path.exists(os.path.join(path,
                                                   comp_name, "__init__.py")):
                    continue
                try:
                    module = shifter.importComponentGuide(comp_name)
                    if PY2:
                        reload(module)
                    else:
                        importlib.reload(module)
                    comp_list.append(module.Guide.compType)
                except Exception as e:
                    pm.displayWarning(
                        "{} can't be load. Error at import".format(comp_name))
                    pm.displayError(e)
                    pm.displayError(traceback.format_exc())

        pm.progressWindow(e=True, endProgress=True)
        return comp_list

    def setSourceModel(self, model):
        """Set the source model for the listview

        Args:
            model (Qt model): QtCore.QSortFilterProxyModel
        """
        self.__proxyModel.setSourceModel(model)

    def _refreshList(self):
        """Refresh listview content
        """
        model = QtGui.QStandardItemModel(self)
        for c_node in self.get_component_list():
            model.appendRow(QtGui.QStandardItem(c_node))
        self.setSourceModel(model)

    ###########################
    # "right click context menu"
    ###########################

    def _component_menu(self, QPos):
        """Create the component list rightclick menu

        Args:
            QPos (QPos): Position

        Returns:
            None: None
        """
        comp_widget = self.gmcUIInst.component_listView
        currentSelection = comp_widget.selectedIndexes()
        if currentSelection is None:
            return
        self.comp_menu = QtWidgets.QMenu()
        parentPosition = comp_widget.mapToGlobal(QtCore.QPoint(0, 0))
        menu_item_01 = self.comp_menu.addAction("Draw Component")
        self.comp_menu.addSeparator()
        menu_item_02 = self.comp_menu.addAction("Refresh List")

        menu_item_01.triggered.connect(self.draw_component)
        menu_item_02.triggered.connect(self._refreshList)

        self.comp_menu.move(parentPosition + QPos)
        self.comp_menu.show()

    def _search_menu(self, QPos):
        search_widget = self.gmcUIInst.search_lineEdit

        self.search_menu = QtWidgets.QMenu()
        parentPosition = search_widget.mapToGlobal(QtCore.QPoint(0, 0))
        menu_item_01 = self.search_menu.addAction("Clear")
        menu_item_01.triggered.connect(search_widget.clear)
        self.search_menu.move(parentPosition + QPos)
        self.search_menu.show()

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):

        # buttons
        self.gmcUIInst.settings_pushButton.clicked.connect(
            guide_manager.inspect_settings)
        self.gmcUIInst.build_pushButton.clicked.connect(
            guide_manager.build_from_selection)
        self.gmcUIInst.duplicate_pushButton.clicked.connect(
            partial(guide_manager.duplicate, False))
        self.gmcUIInst.dupSym_pushButton.clicked.connect(
            partial(guide_manager.duplicate, True))
        self.gmcUIInst.extrCtl_pushButton.clicked.connect(
            guide_manager.extract_controls)
        self.gmcUIInst.draw_pushButton.clicked.connect(
            self.draw_comp_doubleClick)

        # list view
        self.gmcUIInst.search_lineEdit.textChanged.connect(
            self.filter_changed)

        self.gmcUIInst.component_listView.clicked.connect(self.update_info)
        self.selModel = self.gmcUIInst.component_listView.selectionModel()
        self.selModel.selectionChanged.connect(self.update_info)
        self.gmcUIInst.component_listView.doubleClicked.connect(
            self.draw_comp_doubleClick)

        # connect menu
        self.gmcUIInst.component_listView.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)
        self.gmcUIInst.component_listView.customContextMenuRequested.connect(
            self._component_menu)

        self.gmcUIInst.search_lineEdit.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)
        self.gmcUIInst.search_lineEdit.customContextMenuRequested.connect(
            self._search_menu)

    #############
    # SLOTS
    #############

    def update_info(self):
        try:
            item = self.gmcUIInst.component_listView.selectedIndexes()[0]
            comp_name = item.data()
            module = shifter.importComponentGuide(comp_name)
            if PY2:
                reload(module)
            else:
                importlib.reload(module)
            guide = module.Guide
            info_text = (
                "{}\n".format(guide.description)
                + "\n-------------------------------\n\n"
                + "Author: {}\n".format(guide.author)
                + "Url: {}\n".format(guide.url)
                + "Version: {}\n".format(str(guide.version))
                + "Type: {}\n".format(guide.compType)
                + "Name: {}\n".format(guide.compName)
            )
        except IndexError:
            info_text = ""

        self.gmcUIInst.info_plainTextEdit.setPlainText(info_text)

    def draw_comp_doubleClick(self, *args):
        self.draw_component()

    def drag_draw_component(self, pGuide):
        if pGuide:
            if pGuide and isinstance(pGuide, list):
                pGuide = pGuide[0]
            parent = pm.PyNode(pGuide)
            self.draw_component(parent)
        else:
            pm.displayWarning("Nothing catch under cursor. Not Component Draw")

    def draw_component(self, parent=None):
        showUI = self.gmcUIInst.showUI_checkBox.checkState()
        for x in self.gmcUIInst.component_listView.selectedIndexes():
            guide_manager.draw_comp(x.data(), parent, showUI)

    def filter_changed(self, filter):
        """Filter out the elements in the list view

        """
        regExp = QtCore.QRegExp(filter,
                                QtCore.Qt.CaseSensitive,
                                QtCore.QRegExp.Wildcard
                                )
        self.__proxyModel.setFilterRegExp(regExp)
        self.gmcUIInst.info_plainTextEdit.setPlainText("")


def show_guide_component_manager(*args):
    pyqt.showDialog(GuideManagerComponent, dockable=True)


if __name__ == "__main__":

    show_guide_component_manager()
