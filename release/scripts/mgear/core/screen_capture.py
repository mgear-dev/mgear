"""Interactive screen region capture.

Freeze-then-select: when a capture starts, every screen is grabbed and shown
in a frameless full-screen overlay (one per screen). The user drags a
rectangle on that frozen snapshot and the result is cropped from it, so the
selected pixels are exactly the captured pixels and the overlay itself never
appears in the image.

The module never writes files: ``capture_screen_region`` returns a
``QImage`` and the caller decides whether and where to save it.

Example:
    from mgear.core import screen_capture

    image = screen_capture.capture_screen_region(hide_widgets=[my_window])
    if image is not None:
        image.save("C:/temp/region.png")
"""

from mgear.vendor.Qt import QtCompat
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

# Smallest selection, in logical pixels, accepted as a capture. Anything
# smaller is treated as an accidental click and the overlay stays open.
MIN_SELECTION_SIZE = 4

# Default delay, in milliseconds, between hiding the caller's widgets and
# grabbing the screens, so the compositor has removed them.
DEFAULT_HIDE_DELAY = 150

_DIM_COLOR = QtGui.QColor(0, 0, 0, 120)
_OUTLINE_COLOR = QtGui.QColor(255, 170, 0)
_LABEL_BG_COLOR = QtGui.QColor(30, 30, 30, 200)
_LABEL_TEXT_COLOR = QtGui.QColor(230, 230, 230)


#############################################
# GEOMETRY HELPERS
#############################################


def normalize_rect(start, end):
    """Return the rectangle spanned by two drag points, in any direction.

    Args:
        start (tuple): (x, y) point where the drag started.
        end (tuple): (x, y) point where the drag currently is.

    Returns:
        tuple: (x, y, width, height) with a non-negative width and height.
    """
    x0, y0 = start
    x1, y1 = end
    return (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))


def logical_to_device_rect(rect, device_pixel_ratio):
    """Map a logical rectangle to the physical pixels of a screen grab.

    Args:
        rect (tuple): (x, y, width, height) in logical (widget) pixels.
        device_pixel_ratio (float): Physical pixels per logical pixel.

    Returns:
        tuple: (x, y, width, height) in physical pixels, rounded to int.
    """
    x, y, width, height = rect
    ratio = device_pixel_ratio
    return (
        int(round(x * ratio)),
        int(round(y * ratio)),
        int(round(width * ratio)),
        int(round(height * ratio)),
    )


#############################################
# CAPTURE
#############################################


class _CaptureSession(object):
    """Shared state between the overlays of one capture."""

    def __init__(self):
        self.image = None
        self.overlays = []
        self.loop = QtCore.QEventLoop()
        self._finished = False

    def finish(self, image=None):
        """End the capture with an image, or None when cancelled.

        Only the first call has an effect, so closing the remaining
        overlays afterwards cannot overwrite the result.

        Args:
            image (QImage, optional): The captured region.
        """
        if self._finished:
            return
        self._finished = True
        self.image = image
        self.loop.quit()


class _RegionOverlay(QtWidgets.QWidget):
    """Full-screen overlay showing one screen's snapshot for selection.

    Args:
        screen (QScreen): The screen this overlay covers.
        snapshot (QPixmap): The grab of that screen.
        session (_CaptureSession): The capture this overlay belongs to.
    """

    def __init__(self, screen, snapshot, session):
        super(_RegionOverlay, self).__init__(
            None,
            QtCore.Qt.Window
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint,
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        geometry = screen.geometry()
        # Derive the ratio from the grab itself: the reported screen ratio
        # and the grab's own ratio do not always agree across Qt versions.
        self._ratio = float(snapshot.width()) / max(geometry.width(), 1)
        snapshot.setDevicePixelRatio(self._ratio)
        self._snapshot = snapshot
        # Dim once up front, so each drag frame is a single copy instead of
        # a full-screen alpha blend.
        self._dimmed = QtGui.QPixmap(snapshot)
        painter = QtGui.QPainter(self._dimmed)
        painter.fillRect(self._dimmed.rect(), _DIM_COLOR)
        painter.end()
        self._session = session
        self._start = None
        self._end = None

        # Bind the native window to its screen before sizing, so the
        # geometry is interpreted on the right monitor.
        self.winId()
        handle = self.windowHandle()
        if handle is not None:
            handle.setScreen(screen)
        self.setGeometry(geometry)

    def _selection(self):
        """Return the current selection as (x, y, w, h), or None.

        Returns:
            tuple: Logical selection rectangle clamped to the overlay.
        """
        if self._start is None or self._end is None:
            return None
        x, y, width, height = normalize_rect(self._start, self._end)
        right = min(x + width, self.width())
        bottom = min(y + height, self.height())
        x = max(x, 0)
        y = max(y, 0)
        return (x, y, max(right - x, 0), max(bottom - y, 0))

    def _source_rect(self, selection):
        """Return the snapshot pixels covered by a logical selection.

        Args:
            selection (tuple): (x, y, w, h) in logical pixels.

        Returns:
            QRect: The selection in the snapshot's physical pixels.
        """
        return QtCore.QRect(*logical_to_device_rect(selection, self._ratio))

    def paintEvent(self, event):
        """Draw the dimmed snapshot, the selection, and its size."""
        painter = QtGui.QPainter(self)
        painter.drawPixmap(self.rect(), self._dimmed)

        selection = self._selection()
        if selection and selection[2] and selection[3]:
            target = QtCore.QRect(*selection)
            source = self._source_rect(selection)
            painter.drawPixmap(target, self._snapshot, source)

            painter.setPen(_OUTLINE_COLOR)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(target.adjusted(0, 0, -1, -1))

            self._draw_size_label(painter, target, source)
        painter.end()

    def _draw_size_label(self, painter, target, source):
        """Draw the selection size in pixels next to the selection.

        Args:
            painter (QPainter): Active painter.
            target (QRect): Selection in logical pixels.
            source (QRect): Selection in physical pixels.
        """
        text = "{} x {}".format(source.width(), source.height())
        metrics = painter.fontMetrics()
        label = metrics.boundingRect(text).adjusted(-4, -2, 4, 2)
        label.moveTopLeft(target.topLeft() - QtCore.QPoint(0, label.height() + 2))
        if label.top() < 0:
            label.moveTopLeft(target.topLeft() + QtCore.QPoint(2, 2))
        painter.fillRect(label, _LABEL_BG_COLOR)
        painter.setPen(_LABEL_TEXT_COLOR)
        painter.drawText(label, QtCore.Qt.AlignCenter, text)

    def mousePressEvent(self, event):
        """Start a selection on left-click; cancel on right-click."""
        if event.button() == QtCore.Qt.RightButton:
            self._session.finish(None)
            return
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            self._start = (pos.x(), pos.y())
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event):
        """Grow the selection while dragging."""
        if self._start is None:
            return
        pos = event.pos()
        self._end = (pos.x(), pos.y())
        self.update()

    def mouseReleaseEvent(self, event):
        """Accept the selection, or keep the overlay open if it is tiny."""
        if event.button() != QtCore.Qt.LeftButton or self._start is None:
            return
        selection = self._selection()
        self._start = None
        self._end = None
        if (
            selection is None
            or selection[2] < MIN_SELECTION_SIZE
            or selection[3] < MIN_SELECTION_SIZE
        ):
            self.update()
            return
        source = self._source_rect(selection)
        self._session.finish(self._snapshot.copy(source).toImage())

    def keyPressEvent(self, event):
        """Cancel the capture on Esc."""
        if event.key() == QtCore.Qt.Key_Escape:
            self._session.finish(None)
            return
        super(_RegionOverlay, self).keyPressEvent(event)

    def closeEvent(self, event):
        """Treat closing an overlay (e.g. Alt+F4) as a cancel."""
        self._session.finish(None)
        super(_RegionOverlay, self).closeEvent(event)


def _wait(delay_ms):
    """Process Qt events for ``delay_ms`` milliseconds without blocking UI.

    Args:
        delay_ms (int): Milliseconds to wait.
    """
    if delay_ms <= 0:
        return
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(int(delay_ms), loop.quit)
    loop.exec_()


def _activate_overlay_under_cursor(overlays):
    """Give keyboard focus to the overlay under the mouse, so Esc works.

    Args:
        overlays (list): _RegionOverlay instances.
    """
    pos = QtGui.QCursor.pos()
    target = next((o for o in overlays if o.geometry().contains(pos)), overlays[0])
    target.raise_()
    target.activateWindow()
    target.setFocus()


def _restore_active_window(window):
    """Raise and activate the window that was active before the capture.

    Args:
        window (QWidget): The previously active window, or None.
    """
    if window is None or not QtCompat.isValid(window) or not window.isVisible():
        return
    window.raise_()
    window.activateWindow()


def capture_screen_region(hide_widgets=None, delay_ms=DEFAULT_HIDE_DELAY):
    """Let the user drag a rectangle on the screen and return it as an image.

    Hides ``hide_widgets``, waits ``delay_ms`` for the desktop to repaint,
    grabs every screen, and shows one selection overlay per screen. Blocks
    until the user drags a region (left mouse) or cancels (Esc or right
    mouse). The hidden widgets are always restored, including on cancel or
    error. Nothing is written to disk.

    Args:
        hide_widgets (list, optional): Widgets to hide during the capture,
            so the area behind them can be captured.
        delay_ms (int, optional): Milliseconds to wait after hiding the
            widgets before grabbing the screens.

    Returns:
        QImage: The captured region at physical pixel resolution, or None
            if the user cancelled.
    """
    hidden = [w for w in (hide_widgets or []) if w is not None and w.isVisible()]
    # Hiding the active window lets the OS hand focus to another application,
    # so remember it and re-activate it once the capture ends.
    active_window = QtWidgets.QApplication.activeWindow()
    session = _CaptureSession()
    try:
        # setVisible bypasses show() overrides such as Maya's dockable
        # mixin, which would otherwise re-dock or re-float the widget.
        for widget in hidden:
            widget.setVisible(False)
        _wait(delay_ms)

        for screen in QtWidgets.QApplication.screens():
            snapshot = screen.grabWindow(0)
            if snapshot.isNull():
                continue
            overlay = _RegionOverlay(screen, snapshot, session)
            session.overlays.append(overlay)
            overlay.show()

        if session.overlays:
            _activate_overlay_under_cursor(session.overlays)
            session.loop.exec_()
    finally:
        for widget in hidden:
            widget.setVisible(True)
        # Re-activate while an overlay still holds the foreground: the OS
        # allows focus to move between this process's own windows then.
        _restore_active_window(active_window)
        for overlay in session.overlays:
            overlay.close()

    return session.image
