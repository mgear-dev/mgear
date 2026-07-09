"""Preset color palette bar for the anim picker (bottom of the window).

Six preset swatches with explicit left / center / right side roles at two
levels (primary / secondary):

    [ sec-Left  pri-Left  sec-Center  pri-Center  pri-Right  sec-Right ]

Left-clicking a swatch applies its color to the selected item(s); a selected
item's mirror partner receives the *same level* on the *opposite side*
(primary-left mirrors to primary-right, secondary to secondary, center to
center) -- explicit L/R coloring rather than an automatic red/blue swap.
Double-click or right-click a swatch to change its color (a color-picker); that
only edits the preset and never repaints items already using the old color.
Colors persist via ``QSettings``.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets


_SETTINGS_ORG = "mgear"
_SETTINGS_APP = "anim_picker_palette"

# Left-to-right swatch order and each slot's (side, level) role.
SLOTS = (
    ("left", "secondary"),
    ("left", "primary"),
    ("center", "secondary"),
    ("center", "primary"),
    ("right", "primary"),
    ("right", "secondary"),
)

# Opposite side for mirror-partner coloring; level is preserved.
MIRROR_SIDE = {"left": "right", "right": "left", "center": "center"}

# Short label shown under each swatch.
SLOT_LABELS = {
    ("left", "secondary"): "Sec L",
    ("left", "primary"): "Pri L",
    ("center", "secondary"): "Sec C",
    ("center", "primary"): "Pri C",
    ("right", "primary"): "Pri R",
    ("right", "secondary"): "Sec R",
}

_DEFAULTS = {
    ("left", "primary"): (0, 60, 255),
    ("left", "secondary"): (90, 130, 255),
    ("center", "primary"): (255, 220, 0),
    ("center", "secondary"): (255, 235, 130),
    ("right", "primary"): (255, 40, 40),
    ("right", "secondary"): (255, 130, 130),
}


class _Swatch(QtWidgets.QFrame):
    """A single clickable preset color cell."""

    _WIDTH = 52
    _HEIGHT = 28

    def __init__(self, bar, side, level, color):
        super(_Swatch, self).__init__()
        self.bar = bar
        self.side = side
        self.level = level
        self.color = color
        self.setFixedSize(self._WIDTH, self._HEIGHT)
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        # Distinguish a single click (apply) from a double click (edit).
        self._click_timer = QtCore.QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._commit_single)
        self._refresh()

    def set_color(self, color):
        self.color = color
        self._refresh()

    def _refresh(self):
        self.setStyleSheet(
            "background-color: {}; border: 1px solid #222;".format(
                self.color.name()
            )
        )
        self.setToolTip(
            "{} {} - click to apply, double / right-click to edit".format(
                self.level.capitalize(), self.side.capitalize()
            )
        )

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._click_timer.start(
                QtWidgets.QApplication.doubleClickInterval()
            )
        super(_Swatch, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._click_timer.stop()
        self.bar.edit_swatch(self)

    def contextMenuEvent(self, event):
        self.bar.edit_swatch(self)

    def _commit_single(self):
        self.bar.apply_swatch(self)


class ColorPaletteBar(QtWidgets.QWidget):
    """Row of preset swatches that color the selection (with L/R mirroring)."""

    def __init__(self, main_window=None, parent=None):
        super(ColorPaletteBar, self).__init__(parent)
        self.main_window = main_window
        self._swatches = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)
        layout.addWidget(QtWidgets.QLabel("Palette:"))

        settings = self._settings()
        for slot in SLOTS:
            swatch = _Swatch(
                self, slot[0], slot[1], self._load_color(settings, slot)
            )
            self._swatches[slot] = swatch
            # Each swatch gets a caption below it.
            column = QtWidgets.QVBoxLayout()
            column.setSpacing(1)
            column.addWidget(swatch, 0, QtCore.Qt.AlignHCenter)
            caption = QtWidgets.QLabel(SLOT_LABELS[slot])
            caption.setAlignment(QtCore.Qt.AlignHCenter)
            column.addWidget(caption)
            layout.addLayout(column)
        layout.addStretch()

    def _settings(self):
        return QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    def _key(self, slot):
        return "{}_{}".format(slot[0], slot[1])

    def _load_color(self, settings, slot):
        value = settings.value(self._key(slot))
        if value:
            try:
                parts = [int(c) for c in str(value).split(",")]
            except ValueError:
                parts = []
            if len(parts) == 3:
                return QtGui.QColor(*parts)
        return QtGui.QColor(*_DEFAULTS[slot])

    def _save_color(self, slot, color):
        self._settings().setValue(
            self._key(slot),
            "{},{},{}".format(color.red(), color.green(), color.blue()),
        )

    def color_for(self, side, level):
        """Return the preset QColor for a (side, level), or None."""
        swatch = self._swatches.get((side, level))
        return QtGui.QColor(swatch.color) if swatch else None

    def match_color(self, color):
        """Return the (side, level) slot whose swatch RGB equals ``color``.

        Used so Duplicate & Mirror can map a palette-colored source to its
        opposite-side preset instead of a red/blue swap. Returns None when the
        color does not match any swatch (alpha is ignored).
        """
        for slot, swatch in self._swatches.items():
            if (
                swatch.color.red() == color.red()
                and swatch.color.green() == color.green()
                and swatch.color.blue() == color.blue()
            ):
                return slot
        return None

    def apply_swatch(self, swatch):
        if self.main_window is not None:
            self.main_window.apply_palette_color(swatch.side, swatch.level)

    def edit_swatch(self, swatch):
        color = QtWidgets.QColorDialog.getColor(
            initial=swatch.color, parent=self
        )
        if not color.isValid():
            return
        swatch.set_color(color)
        self._save_color((swatch.side, swatch.level), color)
