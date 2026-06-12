
# imports
import os
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.animbits.cache_manager.query import is_rig


class CacheManagerStringListModel(QtCore.QAbstractListModel):

    def __init__(self, items=[], parent=None):
        """ Custom list model for the cache manager

        Args:
            items (list): string list of rigs inside scene
            parent (QtWidget): Parent widget
        """
        super(CacheManagerStringListModel, self).__init__(parent=parent)

        self.__items = items
        self.__icons_path = self.__get_resource_path()

    @staticmethod
    def __get_resource_path():
        """ Returns the relative path to the resource folder
        """

        file_dir = os.path.dirname(__file__)

        if "\\" in file_dir:
            file_dir = file_dir.replace("\\", "/")

        return "{}/resources".format(file_dir)

    def data(self, index, role):
        """ Override QAbstractListModel method

        **data** returns the item name and icon at the given index
        """

        row = index.row()
        value = self.__items[row]

        if role == QtCore.Qt.ToolTipRole:
            return value

        if role == QtCore.Qt.DecorationRole:
            if is_rig(value):
                pixmap = QtGui.QPixmap("{}/rig.png"
                                       .format(self.__icons_path))
            else:
                pixmap = QtGui.QPixmap("{}/cache.png"
                                       .format(self.__icons_path))
            icon = QtGui.QIcon(pixmap)
            return icon

        if role == QtCore.Qt.DisplayRole:
            return value

    def rowCount(self, parent):  # @unusedVariable
        """ Override QAbstractListModel method

        **rowCount** returns the number of items in the list model
        """

        if self.__items:
            return len(self.__items)
        else:
            return 0
