"""Graphics primitives for the anim picker.

Polygon / handle / text QGraphics items, extracted from picker_widgets.py
during the Phase 2 decomposition. Qt-only, no picker/dialog dependencies.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import widget_binding
from mgear.core import svg_import


# High-DPI sizing. Scene fonts and screen-fixed affordances are multiplied by
# ``mgear.core.pyqt.dpi_scale`` so they grow on a high-DPI display to match the
# already-scaled window chrome. The factor is clamped to [1x, 2x] and cached
# for the session, so this is a no-op at 100% scaling. ``pyqt`` is imported
# lazily (it touches the Maya main window) to keep this module import-free of
# Maya at load, and the resolved factor is cached here after the first call.
_DPI_FACTOR = None

# Base scene-text point sizes (authored / 96-DPI); DPI-scaled at render. The
# backdrop title / SVG badge are NOT here: they are scene geometry, sized from
# their container height (so they never outgrow it) rather than DPI-scaled.
DEFAULT_TEXT_PT = 10.0
INDEX_PT = 8.0

# Base screen-pixel handle size (DPI-scaled; ``ItemIgnoresTransformations``).
HANDLE_PX = 8.0


def _dpi(value):
    """Return ``value`` scaled for the display DPI (no-op at 100%).

    Wraps ``mgear.core.pyqt.dpi_scale`` with a session cache; falls back to the
    unscaled value when Maya / the DPI query is unavailable.
    """
    global _DPI_FACTOR
    if _DPI_FACTOR is None:
        try:
            from mgear.core import pyqt

            _DPI_FACTOR = pyqt.dpi_scale(1.0)
        except Exception:
            _DPI_FACTOR = 1.0
    return value * _DPI_FACTOR


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

    def __init__(
        self, x=0, y=0, size=HANDLE_PX, color=None, parent=None, index=0
    ):

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
    def _draw_size(self):
        """Return the on-screen handle size, DPI-scaled (no-op at 100%).

        The handle ignores the view transform, so ``self.size`` is a screen
        size; scaling it here (not on the stored ``size``) keeps handle copies
        from compounding the DPI factor.
        """
        return _dpi(self.size)

    def shape(self):
        """Return default handle square shape based on specified size"""
        path = QtGui.QPainterPath()
        half = self._draw_size() / 2.0
        rectangle = QtCore.QRectF(
            QtCore.QPointF(-half, half),
            QtCore.QPointF(half, -half),
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
        cross_size = self._draw_size() / 2 - 2
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

    def set_size(self, value=INDEX_PT):
        """Set the index text point size (DPI-scaled)."""
        font = self.font()
        font.setPointSizeF(_dpi(value))
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


class WidgetGraphic(DefaultPolygon):
    """Interactive-widget affordance drawn over a picker item.

    Draws the checkbox / slider / 2D-slider affordance from the parent
    ``PickerItem``'s widget state, sized to the item's polygon. It is passive:
    all interaction (click / drag) is handled in ``PickerItem``'s mouse events,
    and this child accepts no mouse buttons so presses fall through to the
    item. The display values (``checked`` / ``value`` / ``value_xy``) are set
    by the item's widget refresh from the bound attribute(s).
    """

    # Modern flat palette (Fusion-like): a neutral body, a recessed groove,
    # a blue accent for progress / knob, and a light handle.
    _BODY = QtGui.QColor(58, 58, 58, 235)
    _BODY_BORDER = QtGui.QColor(96, 96, 96, 255)
    _SEL_BORDER = QtGui.QColor(240, 240, 240, 235)
    _GROOVE = QtGui.QColor(34, 34, 34, 255)
    _GROOVE_BORDER = QtGui.QColor(96, 96, 96, 255)
    _ACCENT = QtGui.QColor(90, 150, 205, 255)
    _HANDLE = QtGui.QColor(228, 228, 228, 255)
    _CHECK = QtGui.QColor(120, 200, 120, 255)

    # Fixed sizes so the knob / groove never stretch with the item. These are
    # scene units (they scale with the view zoom and render crisp on HDPI), so
    # they are deliberately NOT DPI-scaled -- doing so would enlarge them twice.
    _HANDLE_R = 6.0
    _GROOVE_T = 4.0

    def __init__(self, parent=None):
        DefaultPolygon.__init__(self, parent=parent)
        # Display state, refreshed from the bound attribute(s) by the item.
        self.checked = False
        self.value = 0.0  # 1D slider, normalized 0..1
        self.value_xy = (0.5, 0.5)  # 2D slider, normalized (x, y)
        # Passive overlay: let presses fall through to the parent PickerItem.
        self.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.setVisible(False)

    def _item_rect(self):
        """Return the parent's polygon bounding rect in local coordinates."""
        parent = self.parentItem()
        if parent is None or getattr(parent, "polygon", None) is None:
            return QtCore.QRectF(-10, -10, 20, 20)
        return parent.polygon.shape().boundingRect()

    def boundingRect(self):
        # Expand past the item rect by the knob radius (+ pen / antialias
        # margin): the fixed-size slider knob overhangs a thin track, and a
        # bounding rect that stopped at the track would leave the old knob's
        # overhang unrepainted -- a ghost of the previous drag position.
        margin = self._HANDLE_R + 2.0
        return self._item_rect().adjusted(-margin, -margin, margin, margin)

    def shape(self):
        # Hit-testing stays the item rect (the knob overhang is not clickable);
        # only boundingRect is padded, for the repaint region.
        path = QtGui.QPainterPath()
        path.addRect(self._item_rect())
        return path

    def _widget_type(self):
        parent = self.parentItem()
        return getattr(parent, "widget_type", widget_binding.WIDGET_BUTTON)

    def _is_horizontal(self):
        parent = self.parentItem()
        binding = getattr(parent, "binding", None) or {}
        orientation = binding.get(
            "orientation", widget_binding.ORIENT_HORIZONTAL
        )
        return orientation == widget_binding.ORIENT_HORIZONTAL

    def _selected(self):
        """Return True when the parent item is selected (for the border)."""
        parent = self.parentItem()
        polygon = getattr(parent, "polygon", None)
        return bool(polygon and getattr(polygon, "selected", False))

    def paint(self, painter, options, widget=None):
        """Paint the affordance for the parent item's widget type.

        A neutral rounded body is drawn first (so the widget reads as a proper
        control regardless of the underlying polygon fill), then the
        type-specific affordance on top. The rect is computed once and shared.
        """
        wtype = self._widget_type()
        if not widget_binding.is_interactive(wtype):
            return
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self._item_rect()
        self._paint_body(painter, rect)
        if wtype == widget_binding.WIDGET_CHECKBOX:
            self._paint_checkbox(painter, rect)
        elif wtype == widget_binding.WIDGET_SLIDER:
            self._paint_slider(painter, rect)
        elif wtype == widget_binding.WIDGET_SLIDER2D:
            self._paint_slider2d(painter, rect)

    def _paint_body(self, painter, rect):
        """Draw the neutral rounded widget body with selection-aware border."""
        selected = self._selected()
        pen = QtGui.QPen(self._SEL_BORDER if selected else self._BODY_BORDER)
        pen.setWidthF(1.5 if selected else 1.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self._BODY))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3.0, 3.0)

    def _paint_checkbox(self, painter, rect):
        """Draw a recessed box on the left with an upright check when on."""
        size = min(rect.height() - 6.0, 14.0)
        if size < 6.0:
            size = max(6.0, min(rect.height(), rect.width()) - 2.0)
        box = QtCore.QRectF(
            rect.left() + 4.0, rect.center().y() - size / 2.0, size, size
        )
        pen = QtGui.QPen(self._GROOVE_BORDER)
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self._GROOVE))
        painter.drawRoundedRect(box, 2.0, 2.0)
        if not self.checked:
            return
        # The view is Y-flipped, so counter-flip about the box center to draw
        # the checkmark upright (a filled glyph would otherwise be inverted).
        painter.save()
        painter.translate(box.center())
        painter.scale(1.0, -1.0)
        painter.translate(-box.center())
        pen = QtGui.QPen(self._CHECK)
        pen.setWidthF(2.0)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        check = QtGui.QPainterPath()
        check.moveTo(box.left() + size * 0.22, box.top() + size * 0.52)
        check.lineTo(box.left() + size * 0.42, box.top() + size * 0.72)
        check.lineTo(box.left() + size * 0.80, box.top() + size * 0.28)
        painter.drawPath(check)
        painter.restore()

    def _paint_slider(self, painter, rect):
        """Draw a thin groove, an accent fill, and a fixed round handle."""
        horizontal = self._is_horizontal()
        x0, x1, y0, y1 = widget_binding.track_bounds(
            rect.left(), rect.right(), rect.top(), rect.bottom()
        )
        half_t = self._GROOVE_T / 2.0
        if horizontal:
            cy = rect.center().y()
            groove = QtCore.QRectF(x0, cy - half_t, x1 - x0, self._GROOVE_T)
            hx = x0 + self.value * (x1 - x0)
            hy = cy
            fill = QtCore.QRectF(x0, cy - half_t, hx - x0, self._GROOVE_T)
        else:
            cx = rect.center().x()
            groove = QtCore.QRectF(cx - half_t, y0, self._GROOVE_T, y1 - y0)
            # Higher numeric y is higher on screen (Y-flipped view) -> value up.
            hy = y0 + self.value * (y1 - y0)
            hx = cx
            fill = QtCore.QRectF(cx - half_t, y0, self._GROOVE_T, hy - y0)
        pen = QtGui.QPen(self._GROOVE_BORDER)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self._GROOVE))
        painter.drawRoundedRect(groove, half_t, half_t)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(self._ACCENT))
        painter.drawRoundedRect(fill, half_t, half_t)
        self._draw_knob(painter, hx, hy)

    def _paint_slider2d(self, painter, rect):
        """Draw a faint crosshair pad and a fixed knob at (x, y)."""
        x0, x1, y0, y1 = widget_binding.track_bounds(
            rect.left(), rect.right(), rect.top(), rect.bottom()
        )
        pen = QtGui.QPen(self._GROOVE_BORDER)
        pen.setWidthF(0.8)
        pen.setStyle(QtCore.Qt.DotLine)
        painter.setPen(pen)
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        painter.drawLine(QtCore.QPointF(x0, cy), QtCore.QPointF(x1, cy))
        painter.drawLine(QtCore.QPointF(cx, y0), QtCore.QPointF(cx, y1))
        vx, vy = self.value_xy
        self._draw_knob(
            painter, x0 + vx * (x1 - x0), y0 + vy * (y1 - y0)
        )

    def _draw_knob(self, painter, x, y):
        """Draw a fixed-size light knob with an accent ring at ``(x, y)``."""
        pen = QtGui.QPen(self._ACCENT)
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self._HANDLE))
        painter.drawEllipse(QtCore.QPointF(x, y), self._HANDLE_R, self._HANDLE_R)


class BackdropGraphic(DefaultPolygon):
    """Backdrop container fill + title, drawn as the item's body.

    A backdrop item hides its plain polygon and shows this instead: a filled
    rounded (or straight) rectangle in the item's color / alpha, a border, and
    a title strip. It is passive (no mouse); the item owns selection and the
    move-together behavior. Title / corner radius are set by the item.
    """

    _TITLE_H = 18.0

    def __init__(self, parent=None):
        DefaultPolygon.__init__(self, parent=parent)
        self.title = ""
        self.corner_radius = 8.0
        self.setAcceptHoverEvents(False)
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.setVisible(False)

    def _item_rect(self):
        """Return the parent's polygon bounding rect in local coordinates."""
        parent = self.parentItem()
        if parent is None or getattr(parent, "polygon", None) is None:
            return QtCore.QRectF(-50, -35, 100, 70)
        return parent.polygon.shape().boundingRect()

    def boundingRect(self):
        return self._item_rect()

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(self._item_rect())
        return path

    def _selected(self):
        parent = self.parentItem()
        polygon = getattr(parent, "polygon", None)
        return bool(polygon and getattr(polygon, "selected", False))

    def _fill_color(self):
        parent = self.parentItem()
        if parent is not None:
            return parent.get_color()
        return QtGui.QColor(70, 80, 110, 70)

    def paint(self, painter, options, widget=None):
        """Draw the backdrop rectangle + optional title strip."""
        rect = self._item_rect()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        color = self._fill_color()
        painter.setBrush(QtGui.QBrush(color))
        if self._selected():
            pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 230))
            pen.setWidthF(2.0)
        else:
            border = QtGui.QColor(
                color.red(),
                color.green(),
                color.blue(),
                min(255, color.alpha() + 90),
            )
            pen = QtGui.QPen(border)
            pen.setWidthF(1.5)
        painter.setPen(pen)
        radius = max(0.0, self.corner_radius)
        if radius > 0:
            painter.drawRoundedRect(rect, radius, radius)
        else:
            painter.drawRect(rect)
        if self.title:
            self._paint_title(painter, rect, color, radius)

    def _paint_title(self, painter, rect, color, radius):
        """Draw a title strip along the item's screen-top edge."""
        # Screen-top edge is the maximum numeric y under the Y-flipped view.
        strip = QtCore.QRectF(
            rect.left(),
            rect.bottom() - self._TITLE_H,
            rect.width(),
            self._TITLE_H,
        )
        strip_color = QtGui.QColor(
            color.red(),
            color.green(),
            color.blue(),
            min(255, color.alpha() + 60),
        )
        # Clip to the backdrop shape so the title bar follows the rounded top
        # corners instead of overhanging them.
        painter.save()
        clip = QtGui.QPainterPath()
        if radius > 0:
            clip.addRoundedRect(rect, radius, radius)
        else:
            clip.addRect(rect)
        painter.setClipPath(clip)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(strip_color))
        painter.drawRect(strip)
        # Counter the Y-flip so the title reads upright.
        painter.translate(strip.center())
        painter.scale(1.0, -1.0)
        painter.translate(-strip.center())
        painter.setPen(QtGui.QPen(QtGui.QColor(235, 235, 235, 255)))
        font = painter.font()
        # Size the title from the strip height (scene units) so it always fits
        # -- it scales with zoom and stays crisp on HDPI. Not DPI-scaled: the
        # strip is scene geometry, so a scaled font would outgrow it and cut.
        font.setPixelSize(max(1, int(self._TITLE_H * 0.6)))
        painter.setFont(font)
        text_rect = strip.adjusted(6.0, 0.0, -6.0, 0.0)
        title = QtGui.QFontMetricsF(font).elidedText(
            self.title, QtCore.Qt.ElideRight, text_rect.width()
        )
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            title,
        )
        painter.restore()


def build_vector_path(subpaths):
    """Build a ``QPainterPath`` from ``svg_import`` M / L / C / Z subpaths.

    Curves are real (``cubicTo``) and overlapping subpaths cut holes (even-odd
    fill). Shared by the vector item body and the shape-library icon preview so
    both render identical geometry.

    Args:
        subpaths (list): normalized subpaths, each a list of command tuples
            (``("M", x, y)`` / ``("L", x, y)`` / ``("C", ...)`` / ``("Z",)``).

    Returns:
        QtGui.QPainterPath: the compound path.
    """
    path = QtGui.QPainterPath()
    # Even-odd so overlapping subpaths cut holes (typical icon glyphs).
    path.setFillRule(QtCore.Qt.OddEvenFill)
    for sub in subpaths or []:
        for segment in sub:
            command = segment[0]
            if command == "M":
                path.moveTo(segment[1], segment[2])
            elif command == "L":
                path.lineTo(segment[1], segment[2])
            elif command == "C":
                path.cubicTo(
                    segment[1],
                    segment[2],
                    segment[3],
                    segment[4],
                    segment[5],
                    segment[6],
                )
            elif command == "Z":
                path.closeSubpath()
    return path


class VectorGraphic(DefaultPolygon):
    """Vector (curved) shape drawn as the item's body, from imported SVG.

    A vector item hides its plain polygon and shows this instead: a compound
    ``QPainterPath`` (with curves and holes) built from the item's normalized
    subpaths, drawn either **filled** in the item's color or **stroked** as
    lines of a given width (so line-art icons read correctly). Clicks fall
    through to the parent item, but it accepts hover so a hovered vector item
    shows an "SVG" badge (a distinct hover cue, not a border lighten).
    ``shape()`` delegates hit-testing to the path. Subpaths / mode / width are
    set by the item from its ``svg`` data.
    """

    __DEFAULT_SELECT_COLOR__ = QtGui.QColor(230, 230, 230, 240)
    _BADGE = QtCore.QRectF(0.0, 0.0, 34.0, 18.0)

    def __init__(self, parent=None):
        DefaultPolygon.__init__(self, parent=parent)
        self.subpaths = []
        self._path = QtGui.QPainterPath()
        self.selected = False
        self.mode = svg_import.MODE_FILL
        self.stroke_width = 2.0
        # Accept hover (for the SVG badge) but no mouse buttons, so a click
        # falls through to the parent PickerItem for selection.
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.setVisible(False)

    def set_subpaths(self, subpaths):
        """Set the normalized subpaths and rebuild the cached path."""
        self.prepareGeometryChange()
        self.subpaths = [list(sub) for sub in (subpaths or [])]
        self._path = self._build_path(self.subpaths)
        self.update()

    def set_mode(self, mode):
        """Set the render mode (``MODE_FILL`` / ``MODE_STROKE``)."""
        self.prepareGeometryChange()
        self.mode = mode or svg_import.MODE_FILL
        self.update()

    def set_stroke_width(self, width):
        """Set the stroke width (used in ``MODE_STROKE``)."""
        self.prepareGeometryChange()
        self.stroke_width = max(0.1, float(width))
        self.update()

    @staticmethod
    def _build_path(subpaths):
        """Build a ``QPainterPath`` from M / L / C / Z segments."""
        return build_vector_path(subpaths)

    def boundingRect(self):
        # Pad for the selection border / stroke width / antialias so a moving
        # selection or a thick stroke never leaves a paint ghost.
        margin = max(2.0, self.stroke_width)
        return self._path.boundingRect().adjusted(
            -margin, -margin, margin, margin
        )

    def shape(self):
        return self._path

    def set_selected_state(self, state):
        if state == self.selected:
            return
        self.selected = state
        self.update()

    def _fill_color(self):
        parent = self.parentItem()
        if parent is not None:
            return parent.get_color()
        return QtGui.QColor(self.color)

    def paint(self, painter, options, widget=None):
        """Draw the path filled or stroked, plus selection / hover cues."""
        if self._path.isEmpty():
            return
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        color = QtGui.QColor(self._fill_color())
        if self.mode == svg_import.MODE_STROKE:
            pen = QtGui.QPen(color)
            pen.setWidthF(self.stroke_width)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawPath(self._path)
        else:
            painter.fillPath(self._path, QtGui.QBrush(color))
            if self.selected:
                painter.fillPath(
                    self._path, QtGui.QBrush(QtGui.QColor(255, 255, 255, 50))
                )
        if self.selected:
            border = QtGui.QPen(self.__DEFAULT_SELECT_COLOR__)
            border.setWidthF(2.0)
            painter.setPen(border)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawPath(self._path)
        if self._hovered:
            self._paint_svg_badge(painter)

    def _paint_svg_badge(self, painter):
        """Draw a small upright "SVG" badge over the shape center on hover."""
        text = "SVG"
        # Font sized from the reference badge height (scene units) so it scales
        # with zoom and stays crisp on HDPI; not DPI-scaled (scene geometry).
        font = QtGui.QFont(painter.font())
        font.setBold(True)
        font.setPixelSize(max(1, int(self._BADGE.height() * 0.55)))
        # Size the pill to the text so it never clips (grows past the reference
        # width for a wider font / label).
        metrics = QtGui.QFontMetricsF(font)
        try:
            text_w = metrics.horizontalAdvance(text)
        except AttributeError:
            text_w = metrics.width(text)
        width = max(self._BADGE.width(), text_w + 12.0)
        badge = QtCore.QRectF(0.0, 0.0, width, self._BADGE.height())
        badge.moveCenter(self._path.boundingRect().center())
        painter.save()
        # Counter the view's Y-flip so the label reads upright.
        center = badge.center()
        painter.translate(center)
        painter.scale(1.0, -1.0)
        painter.translate(-center)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(20, 20, 20, 175)))
        painter.drawRoundedRect(badge, 4.0, 4.0)
        painter.setPen(QtGui.QPen(QtGui.QColor(235, 235, 235, 255)))
        painter.setFont(font)
        painter.drawText(badge, QtCore.Qt.AlignCenter, text)
        painter.restore()


# Text placement relative to the item, plus an inward/outward gap. "center"
# keeps the legacy origin-centered behavior; the edge alignments place the text
# just outside that edge of the item so it does not overlap the button.
TEXT_ALIGN_CENTER = "center"
TEXT_ALIGNS = ("center", "top", "bottom", "left", "right")


class GraphicText(QtWidgets.QGraphicsSimpleTextItem):
    """Picker item text element"""

    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 255)

    def __init__(self, parent=None, scene=None):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Counter view scale
        self.scale_transform = QtGui.QTransform().scale(1, -1)
        self.setTransform(self.scale_transform)

        # Placement relative to the item + a gap in pixels.
        self.align = TEXT_ALIGN_CENTER
        self.offset = 0.0

        # Authored (DPI-independent) point size; the font is set to the
        # DPI-scaled size, but this is what is stored / shown.
        self.point_size = DEFAULT_TEXT_PT

        # Init default size
        self.set_size()
        self.set_color(GraphicText.__DEFAULT_COLOR__)

    def set_text(self, text):
        """
        Set current text
        (Will reposition text on parent too)
        """
        self.setText(text)
        self._reposition()

    def get_text(self):
        """Return element text"""
        return str(self.text())

    def set_size(self, value=DEFAULT_TEXT_PT):
        """Set the text size from an authored (DPI-independent) point size.

        The authored value is stored; the font is set to the DPI-scaled size so
        the label grows on a high-DPI display (a no-op at 100%).
        """
        self.point_size = value
        font = self.font()
        font.setPointSizeF(_dpi(value))
        self.setFont(font)
        self._reposition()

    def set_alignment(self, align=None, offset=0.0):
        """Set the text placement (``TEXT_ALIGNS``) + gap and reposition."""
        self.align = align if align in TEXT_ALIGNS else TEXT_ALIGN_CENTER
        self.offset = offset or 0.0
        self._reposition()

    def _reposition(self):
        """Reposition the text from the current alignment + offset."""
        if self.align == TEXT_ALIGN_CENTER:
            self.center_on_parent()
        else:
            self.align_on_parent(self.align, self.offset)

    def get_size(self):
        """Return the authored (DPI-independent) text point size."""
        return self.point_size

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

    def align_on_parent(self, align, offset=0.0):
        """Place the text just outside the item's ``align`` edge.

        Positions the text's visual center against the parent polygon's
        bounding box: left / right beside it, top / bottom above / below it,
        each pushed out by ``offset`` pixels so the text clears the button. The
        Y-flipped view is accounted for (higher numeric y is higher on screen).

        Args:
            align (str): one of ``TEXT_ALIGNS`` (non-center).
            offset (float): gap in pixels between the text and the item edge.
        """
        parent = self.parentItem()
        if parent is None or getattr(parent, "polygon", None) is None:
            self.center_on_parent()
            return
        rect = parent.polygon.shape().boundingRect()
        text_center = self.boundingRect().center()
        half_tw = self.boundingRect().width() / 2.0
        half_th = self.boundingRect().height() / 2.0
        cx = rect.center().x()
        cy = rect.center().y()
        if align == "left":
            cx = rect.center().x() - rect.width() / 2.0 - half_tw - offset
        elif align == "right":
            cx = rect.center().x() + rect.width() / 2.0 + half_tw + offset
        elif align == "top":
            cy = rect.center().y() + rect.height() / 2.0 + half_th + offset
        elif align == "bottom":
            cy = rect.center().y() - rect.height() / 2.0 - half_th - offset
        # Place the text's visual center at (cx, cy). The item's own scale(1,-1)
        # maps its local center (tx, ty) to (tx, -ty), so pos = center - (tx,-ty).
        self.setPos(cx - text_center.x(), cy + text_center.y())


