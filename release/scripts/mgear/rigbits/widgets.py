"""Rigbits  widgets"""

from mgear.core import widgets
from mgear.vendor.Qt import QtWidgets


################################################
# CUSTOM WIDGETS
################################################

class TableWidgetDragRowsChannelWrangler(widgets.TableWidgetDragRows):
    """TableWidgetDragRows subclass for channelWrangler"""

    def __init__(self, *args, **kwargs):
        super(TableWidgetDragRowsChannelWrangler, self).__init__(*args,
                                                                 **kwargs)

    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))

            rows_to_move = [[QtWidgets.QTableWidgetItem(
                self.item(row_index, column_index))
                for column_index in range(self.columnCount())]
                for row_index in rows]

            rows_widgets_to_move = [self.cellWidget(row_index, 4)
                                    for row_index in rows]

            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):

                inRow = row_index + drop_row
                self.insertRow(inRow)
                for column_index, column_data in enumerate(data):
                    if column_index != 4:
                        self.setItem(inRow, column_index, column_data)
                # self.setCellWidget(inRow, 4, rows_widgets_to_move[row_index])
                # moving the combo box crash core. Current workaround is
                # create a new one and destroy the old
                # someone knows better way?  Thanks :)
                operation_comboBox = QtWidgets.QComboBox()
                operation_comboBox.setObjectName("operation")
                operation_comboBox.addItem("移动通道")
                operation_comboBox.addItem("代理通道")
                size_polizy = QtWidgets.QComboBox.AdjustToContentsOnFirstShow
                operation_comboBox.SizeAdjustPolicy(size_polizy)
                oComboOld = rows_widgets_to_move[row_index]
                self.setCellWidget(inRow, 4, operation_comboBox)
                operation_comboBox.setCurrentIndex(oComboOld.currentIndex())
                oComboOld.deleteLater()

            event.accept()
            for row_index in range(len(rows_to_move)):
                self.item(drop_row + row_index, 0).setSelected(True)
                self.item(drop_row + row_index, 1).setSelected(True)
                self.item(drop_row + row_index, 2).setSelected(True)
                self.item(drop_row + row_index, 3).setSelected(True)
