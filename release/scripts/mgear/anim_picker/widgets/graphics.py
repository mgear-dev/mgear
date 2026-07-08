"""Graphics primitives for the anim picker.

Polygon / handle / text QGraphics items, extracted from picker_widgets.py
during the Phase 2 decomposition. Qt-only, no picker/dialog dependencies.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets


class DefaultPolygon(QtWidgets.QGraphicsObject):
    """Default polygon class, with move and hover support"""

    __DEFAULT_COLOR__ = QtGui.QColor(0, 0, 0, 255)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsObject.__init__(self, parent=parent)

        if parent:
            self.setParent(parent)

        # Hover feedback
        self.setAcceptHoverEvents(True)
        self._hovered = False

        # Init default
        self.color = self.__DEFAULT_COLOR__

    def hoverEnterEvent(self, event=None):
        """Lightens background color on mose over"""
        QtWidgets.QGraphicsObject.hoverEnterEvent(self, event)
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event=None):
        """Resets mouse over background color"""
        QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)
        self._hovered = False
        self.update()

    def boundingRect(self):
        """
        Needed override:
        Returns the bounding rectangle for the graphic item
        """
        return self.shape().boundingRect()

    def itemChange(self, change, value):
        """itemChange update behavior"""
        # Catch position update
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            # Force scene update to prevent "ghosts"
            # (ghost happen when the previous polygon is out of
            # the new bounding rect when updating)
            if self.scene():
                self.scene().update()

        # Run default action
        return QtWidgets.QGraphicsObject.itemChange(self, change, value)

    def get_color(self):
        """Get polygon color"""
        return QtGui.QColor(self.color)

    def set_color(self, color=None):
        """Set polygon color"""
        if not color:
            color = QtGui.QColor(0, 0, 0, 255)
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        msg = "input color '{}' is invalid".format(color)
        assert isinstance(color, QtGui.QColor), msg

        self.color = color
        self.update()

        return color


class PointHandle(DefaultPolygon):
    """Handle polygon object to move picker polygon cvs"""

    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 200)

    def __init__(self, x=0, y=0, size=8, color=None, parent=None, index=0):

        DefaultPolygon.__init__(self, parent)

        # Make movable
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Set values
        self.setPos(x, y)
        self.index = index
        self.size = size
        self.set_color()
        self.draw_index = False

        # Hide by default
        self.setVisible(False)

        # Add index element
        self.index = PointHandleIndex(parent=self, index=index)

    # =========================================================================
    # Default python methods
    # =========================================================================
    def _new_pos_handle_copy(self, pos):
        """Return a new PointHandle isntance with same attributes
        but different position
        """
        new_handle = PointHandle(
            x=pos.x(),
            y=pos.y(),
            size=self.size,
            color=self.color,
            parent=self.parentObject(),
        )
        return new_handle

    def _get_pos_for_input(self, other):
        if isinstance(other, PointHandle):
            return other.pos()
        return other

    def __add__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() + other
        return self._new_pos_handle_copy(new_pos)

    def __sub__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() - other
        return self._new_pos_handle_copy(new_pos)

    def __div__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    def __mul__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    # =========================================================================
    # QT OVERRIDES
    # =========================================================================
    def setX(self, value=0):
        """Override to support keyword argument for spin_box callback"""
        DefaultPolygon.setX(self, value)

    def setY(self, value=0):
        """Override to support keyword argument for spin_box callback"""
        DefaultPolygon.setY(self, value)

    # =========================================================================
    # Graphic item methods
    # =========================================================================
    def shape(self):
        """Return default handle square shape based on specified size"""
        path = QtGui.QPainterPath()
        rectangle = QtCore.QRectF(
            QtCore.QPointF(-self.size / 2.0, self.size / 2.0),
            QtCore.QPointF(self.size / 2.0, -self.size / 2.0),
        )
        # path.addRect(rectangle)
        path.addEllipse(rectangle)
        return path

    def paint(self, painter, options, widget=None):
        """Paint graphic item"""
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Set node background color
        brush = QtGui.QBrush(self.color)
        if self._hovered:
            brush = QtGui.QBrush(self.color.lighter(500))

        # Paint background
        painter.fillPath(path, brush)

        border_pen = QtGui.QPen(QtGui.QColor(200, 200, 200, 255))
        painter.setPen(border_pen)

        # Paint Borders
        painter.drawPath(path)

        # if not edit_mode: return
        # Paint center cross
        cross_size = self.size / 2 - 2
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-cross_size, 0, cross_size, 0)
        painter.drawLine(0, cross_size, 0, -cross_size)

    def mirror_x_position(self):
        """will mirror local x position value"""
        self.setX(-1 * self.x())

    def scale_pos(self, x=1.0, y=1.0):
        """Scale handle local position"""
        self.setPos(self.pos().x() * x, self.pos().y() * y)
        self.update()

    def enable_index_draw(self, status=False):
        self.index.setVisible(status)

    def set_index(self, index):
        self.index.setText(index)

    def get_index(self):
        return int(self.index.text())


class Polygon(DefaultPolygon):
    """
    Picker controls visual graphic object
    (inherits from QtWidgets.QGraphicsObject rather
    than QtWidgets.QGraphicsItem for signal support)
    """

    __DEFAULT_COLOR__ = QtGui.QColor(200, 200, 200, 180)
    __DEFAULT_SELECT_COLOR__ = QtGui.QColor(230, 230, 230, 240)

    def __init__(self, parent=None, points=[], color=None):

        DefaultPolygon.__init__(self, parent=parent)
        self.points = points
        self.set_color(Polygon.__DEFAULT_COLOR__)

        self._edit_status = False
        self.selected = False

    def set_edit_status(self, status=False):
        self._edit_status = status
        self.update()

    def shape(self):
        """Override function to return proper "hit box",
        and compute shape only once.
        """
        path = QtGui.QPainterPath()

        # Polygon case
        if len(self.points) > 2:
            # Define polygon points for closed loop
            shp_points = []
            for handle in self.points:
                shp_points.append(handle.pos())
            shp_points.append(self.points[0].pos())

            # Draw polygon
            polygon = QtGui.QPolygonF(shp_points)

            # Update path
            path.addPolygon(polygon)

        # Circle case
        else:
            center = self.points[0].pos()
            radius = QtGui.QVector2D(
                self.points[0].pos() - self.points[1].pos()
            ).length()

            # Update path
            path.addEllipse(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            )

        return path

    def paint(self, painter, options, widget=None):
        """Paint graphic item"""
        # Set render quality
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Background color
        color = QtGui.QColor(self.color)
        if self._hovered:
            color = color.lighter(130)
        brush = QtGui.QBrush(color)

        painter.fillPath(path, brush)

        # Add white layer color overlay on selected state
        if self.selected:
            color = QtGui.QColor(255, 255, 255, 50)
            brush = QtGui.QBrush(color)
            painter.fillPath(path, brush)

        # Border status feedback
        border_pen = QtGui.QPen(self.__DEFAULT_SELECT_COLOR__)
        border_pen.setWidthF(2)

        if self.selected:
            painter.setPen(border_pen)
            painter.drawPath(path)

        elif self._hovered:
            border_pen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(border_pen)
            painter.drawPath(path)

        # Stop her if not in edit mode
        if not self._edit_status:
            return

        # Paint center cross
        painter.setRenderHints(QtGui.QPainter.Antialiasing, False)
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(0, 5, 0, -5)

    def set_selected_state(self, state):
        """Will set border color feedback based on selection state"""
        # Do nothing on same state
        if state == self.selected:
            return

        # Change state, and update
        self.selected = state
        self.update()

    def set_color(self, color):
        # Run default method
        color = DefaultPolygon.set_color(self, color)

        # Store new color as default
        Polygon.__DEFAULT_COLOR__ = color


class PointHandleIndex(QtWidgets.QGraphicsSimpleTextItem):
    """Point handle index text element"""

    __DEFAULT_COLOR__ = QtGui.QColor(130, 50, 50, 255)

    def __init__(self, parent=None, scene=None, index=0):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Init defaults
        self.set_size()
        self.set_color(PointHandleIndex.__DEFAULT_COLOR__)
        self.setPos(QtCore.QPointF(-9, -14))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Hide by default
        self.setVisible(False)

        self.setText(index)

    def set_size(self, value=8.0):
        """Set pointSizeF for text"""
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)

    def set_color(self, color=None):
        """Set text color"""
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

    def setText(self, text):
        """Override default setText method to force unicode on int index input"""
        return QtWidgets.QGraphicsSimpleTextItem.setText(self, str(text))


class GraphicText(QtWidgets.QGraphicsSimpleTextItem):
    """Picker item text element"""

    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 255)

    def __init__(self, parent=None, scene=None):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Counter view scale
        self.scale_transform = QtGui.QTransform().scale(1, -1)
        self.setTransform(self.scale_transform)

        # Init default size
        self.set_size()
        self.set_color(GraphicText.__DEFAULT_COLOR__)

    def set_text(self, text):
        """
        Set current text
        (Will center text on parent too)
        """
        self.setText(text)
        self.center_on_parent()

    def get_text(self):
        """Return element text"""
        return str(self.text())

    def set_size(self, value=10.0):
        """Set pointSizeF for text"""
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)
        self.center_on_parent()

    def get_size(self):
        """Return text pointSizeF"""
        return self.font().pointSizeF()

    def get_color(self):
        """Return text color"""
        return self.brush().color()

    def set_color(self, color=None):
        """Set text color"""
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

        # Store new color as default color
        GraphicText.__DEFAULT_COLOR__ = color

    def center_on_parent(self):
        """
        Center text on parent item
        (Since by default the text start on the bottom left corner)
        """
        center_pos = self.boundingRect().center()
        # self.setPos(-center_pos * self.scale_transform)
        scale_xy = QtCore.QPointF(center_pos.x(), center_pos.y() * -1)
        self.setPos(-scale_xy)


