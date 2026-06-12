from mgear.vendor.Qt import QtCore, QtWidgets, QtGui


class VisibilityDelegate(QtWidgets.QStyledItemDelegate):
    """
    Item delegate responsible for custom rendering of the visibility column.

    The delegate suppresses the default icon and text drawing performed by
    ``QStyledItemDelegate`` for the designated visibility column (logical index 2),
    and instead draws a single centered icon at a fixed size.

    :param icon_size: The size at which the visibility icon should be painted.
    :type icon_size: QtCore.QSize
    :param parent: Optional parent widget.
    :type parent: QtWidgets.QWidget or None
    :return: None
    """
    def __init__(self, icon_size: QtCore.QSize, parent=None) -> None:
        super(VisibilityDelegate, self).__init__(parent)
        self._icon_size = icon_size

    def paint(self,
              painter: QtGui.QPainter,
              option: QtWidgets.QStyleOptionViewItem,
              index: QtCore.QModelIndex) -> None:
        """
       Paint the visibility icon for the corresponding cell.

       For all non-visibility columns, the base delegate paints normally.
       For the visibility column, the default text and icon drawing is skipped
       and replaced with a manually rendered icon that is visually centered
       and scaled to the configured icon size.

       :param painter: Painter used for drawing the item.
       :param option: Style options describing the cell.
       :param index: Model index of the cell being rendered.
       :return: None
       """
        # -- Only customize the visibility column (logical index 2)
        if index.column() != 2:
            super(VisibilityDelegate, self).paint(painter, option, index)
            return

        # -- Prepare a style option but clear the icon & text
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        # -- Prevent default icon draw
        opt.icon = QtGui.QIcon()
        # -- No text in the visibility column
        opt.text = ""

        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter)

        # -- Now draw our scaled icon once (Was getting duplicates)
        icon = index.data(QtCore.Qt.DecorationRole)
        if not isinstance(icon, QtGui.QIcon):
            return

        size = self._icon_size
        rect = opt.rect
        x = rect.x() + (rect.width() - size.width()) // 2
        y = rect.y() + (rect.height() - size.height()) // 2
        target_rect = QtCore.QRect(x, y, size.width(), size.height())

        icon.paint(painter, target_rect)
