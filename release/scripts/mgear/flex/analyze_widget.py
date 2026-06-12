
""" flex.analyze_widget

Contains the Flex Analyze interface

:module: flex.analyze_widget
"""


# imports
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtGui

from mgear.flex import logger
from mgear.flex.colors import YELLOW
from mgear.flex.query import get_resources_path

# flex analyze name
FLEX_ANALYZE_NAME = "flex_analyse_qdialog"


class FlexAnalyzeDialog(QtWidgets.QDialog):
    """ The Flex analyze widgets

    Flex analyze is a side by side list widget style that will allow you to
    check which shapes matches.
    """

    def __init__(self, parent=None):
        """ Creates all the user interface widgets

        :param parent: the parent widget for the Flex dialog widget
        :type parent: PySide2.QtWidgets
        """
        super(FlexAnalyzeDialog, self).__init__(parent=parent)

        logger.debug("Analyze widget initialised")

        # sets window rules
        self.setObjectName(FLEX_ANALYZE_NAME)
        self.setWindowTitle("mGear: Flex analyze shapes")
        self.setMinimumWidth(500)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # creates the icons
        self.green_icon = QtGui.QIcon()
        image = QtGui.QPixmap("{}/green.png".format(get_resources_path()))
        self.green_icon.addPixmap(image)

        self.red_icon = QtGui.QIcon()
        image = QtGui.QPixmap("{}/red.png".format(get_resources_path()))
        self.red_icon.addPixmap(image)

        self.yellow_icon = QtGui.QIcon()
        image = QtGui.QPixmap("{}/yellow.png".format(get_resources_path()))
        self.yellow_icon.addPixmap(image)

        # creates layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # setup table
        self.setLayout(layout)
        self.__create_table()

        # add widgets
        layout.addWidget(self.table_widget)

    def __create_table(self):
        """ Creates the table widget

        We could use a table view on this case as well but for now I am keeping
        if as a widget as the table is used only to represent a non changing
        state of data.
        """

        # creates the table
        self.table_widget = QtWidgets.QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setIconSize(QtCore.QSize(20, 20))

        # adds headers
        self.table_widget.setHorizontalHeaderLabels(["Source",
                                                     "Target",
                                                     "Type",
                                                     "Count",
                                                     "B-Box",
                                                     "Result"])

        # setup headers look and feel
        h_header = self.table_widget.horizontalHeader()
        h_header.setPalette(YELLOW)
        h_header.setFixedHeight(21)
        h_header.setDefaultSectionSize(40)
        h_header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        h_header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        h_header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        h_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        h_header.setSectionResizeMode(5, QtWidgets.QHeaderView.Fixed)
        h_header.setSectionsClickable(False)

        # hides vertical header
        self.table_widget.verticalHeader().setVisible(False)

    def add_item(self, source, target, match, count, bbox):
        """ Handles adding items to the table widget

        :param source: the source shape element
        :type source: string

        :param target: the target corresponding shape element matching source
        :type target: string

        :param match: whether the type matches
        :type match: bool
        """

        # source item
        source_item = QtWidgets.QTableWidgetItem()
        source_item.setTextAlignment(QtCore.Qt.AlignCenter)
        source_item.setText(source)
        source_item.setFlags(QtCore.Qt.ItemIsSelectable |
                             QtCore.Qt.ItemIsEnabled)

        # target item
        target_item = QtWidgets.QTableWidgetItem()
        target_item.setTextAlignment(QtCore.Qt.AlignCenter)
        target_item.setText(target)
        target_item.setFlags(QtCore.Qt.ItemIsSelectable |
                             QtCore.Qt.ItemIsEnabled)

        # type item
        match_item = QtWidgets.QTableWidgetItem()
        match_item.setIcon(self.green_icon)
        if source in match:
            match_item.setIcon(self.red_icon)
        match_item.setFlags(QtCore.Qt.ItemIsEnabled)

        # count item
        count_item = QtWidgets.QTableWidgetItem()
        count_item.setIcon(self.green_icon)
        if source in count:
            count_item.setIcon(self.red_icon)
        count_item.setFlags(QtCore.Qt.ItemIsEnabled)

        # bounding box item
        bbox_item = QtWidgets.QTableWidgetItem()
        bbox_item.setIcon(self.green_icon)
        if source in bbox:
            bbox_item.setIcon(self.red_icon)
        bbox_item.setFlags(QtCore.Qt.ItemIsEnabled)

        # result item
        result_item = QtWidgets.QTableWidgetItem()
        result_item.setFlags(QtCore.Qt.ItemIsEnabled)
        if source not in count and source not in bbox and source not in match:
            result_item.setIcon(self.green_icon)
        if source in count and source not in bbox:
            result_item.setIcon(self.yellow_icon)
        if source in count and source in bbox:
            result_item.setIcon(self.red_icon)
        if source in bbox and source not in count:
            result_item.setIcon(self.green_icon)
        if source in match:
            result_item.setIcon(self.red_icon)

        # insert items
        self.table_widget.insertRow(0)
        self.table_widget.setRowHeight(0, 19)
        self.table_widget.setItem(0, 0, source_item)
        self.table_widget.setItem(0, 1, target_item)
        self.table_widget.setItem(0, 2, match_item)
        self.table_widget.setItem(0, 3, count_item)
        self.table_widget.setItem(0, 4, bbox_item)
        self.table_widget.setItem(0, 5, result_item)
