"""Reusable Python code editor widget for mGear UIs.

A modern-looking multi-line Python editor built on ``QPlainTextEdit`` with:

- a line-number gutter,
- current-line highlight,
- Python syntax highlighting (keywords, builtins, strings, comments, numbers,
  decorators, def/class names),
- configurable monospace font family and size,
- configurable indentation (spaces or tabs) and indent width,
- smart Tab / Shift-Tab (indent / unindent, block-aware) and auto-indent on
  Enter (copies the previous line's indent, adds one level after a ``:``).

Preferences (font, indent mode/width) persist via ``QSettings`` so the editor
looks the same across sessions and across the tools that embed it.

Framework-first: this lives in ``mgear.core`` so any tool needing a Python
editor (anim picker custom scripts, shifter custom steps, ...) can reuse it
instead of dropping a bare ``QTextEdit``.
"""

import re

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets


# -- preferences -------------------------------------------------------------
_SETTINGS_ORG = "mgear"
_SETTINGS_APP = "pycodeeditor"
DEFAULT_FONT_FAMILY = "Consolas"
DEFAULT_FONT_SIZE = 10
DEFAULT_INDENT_WIDTH = 4
DEFAULT_USE_SPACES = True
DEFAULT_SHOW_WHITESPACE = False

# -- dark editor palette -----------------------------------------------------
_BG_COLOR = QtGui.QColor(30, 30, 30)
_TEXT_COLOR = QtGui.QColor(212, 212, 212)
_GUTTER_BG = QtGui.QColor(45, 45, 45)
_GUTTER_FG = QtGui.QColor(130, 130, 130)
_CURRENT_LINE = QtGui.QColor(58, 58, 70)

# Python keywords / builtins for highlighting.
_KEYWORDS = (
    "and as assert async await break class continue def del elif else except "
    "finally for from global if import in is lambda nonlocal not or pass raise "
    "return try while with yield True False None"
).split()
_BUILTINS = (
    "abs all any bin bool bytearray bytes callable chr classmethod compile "
    "complex delattr dict dir divmod enumerate eval exec filter float format "
    "frozenset getattr globals hasattr hash help hex id input int isinstance "
    "issubclass iter len list locals map max min next object oct open ord pow "
    "print property range repr reversed round set setattr slice sorted "
    "staticmethod str sum super tuple type vars zip"
).split()


def _char_format(color, bold=False, italic=False):
    """Return a QTextCharFormat for the given color/style."""
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(color)
    if bold:
        fmt.setFontWeight(QtGui.QFont.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    """Lightweight Python syntax highlighter (regex + triple-string states)."""

    def __init__(self, document):
        super(PythonHighlighter, self).__init__(document)

        keyword_fmt = _char_format(QtGui.QColor(86, 156, 214), bold=True)
        builtin_fmt = _char_format(QtGui.QColor(78, 201, 176))
        self_fmt = _char_format(QtGui.QColor(156, 220, 254), italic=True)
        number_fmt = _char_format(QtGui.QColor(181, 206, 168))
        decorator_fmt = _char_format(QtGui.QColor(220, 220, 170))
        defname_fmt = _char_format(QtGui.QColor(220, 220, 170))
        self._string_fmt = _char_format(QtGui.QColor(206, 145, 120))
        self._comment_fmt = _char_format(QtGui.QColor(106, 153, 85), italic=True)

        # (compiled regex, capture group, format). Applied in order; later
        # matches override earlier ones for overlapping ranges.
        self._rules = []
        keyword_re = r"\b(?:{})\b".format("|".join(_KEYWORDS))
        builtin_re = r"\b(?:{})\b".format("|".join(_BUILTINS))
        self._rules.append((re.compile(keyword_re), 0, keyword_fmt))
        self._rules.append((re.compile(builtin_re), 0, builtin_fmt))
        self._rules.append((re.compile(r"\bself\b"), 0, self_fmt))
        self._rules.append(
            (re.compile(r"\b[0-9]+\.?[0-9]*\b"), 0, number_fmt)
        )
        self._rules.append((re.compile(r"@\w+"), 0, decorator_fmt))
        self._rules.append(
            (re.compile(r"\b(?:def|class)\s+(\w+)"), 1, defname_fmt)
        )
        # Single-line strings.
        self._rules.append(
            (re.compile(r"'[^'\\\n]*(?:\\.[^'\\\n]*)*'"), 0, self._string_fmt)
        )
        self._rules.append(
            (re.compile(r'"[^"\\\n]*(?:\\.[^"\\\n]*)*"'), 0, self._string_fmt)
        )
        # Comments last so they win over code (a "#" inside a string is a known
        # limitation of a simple line highlighter and is acceptable here).
        self._rules.append((re.compile(r"#[^\n]*"), 0, self._comment_fmt))

        self._tri_single = re.compile(r"'''")
        self._tri_double = re.compile(r'"""')

    def highlightBlock(self, text):
        for pattern, group, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start(group)
                end = match.end(group)
                self.setFormat(start, end - start, fmt)

        # Triple-quoted (possibly multi-line) strings via block state.
        self.setCurrentBlockState(0)
        if not self._match_multiline(text, self._tri_single, 1):
            self._match_multiline(text, self._tri_double, 2)

    def _match_multiline(self, text, delimiter, state):
        """Highlight a triple-quoted string that may span blocks."""
        start = 0
        if self.previousBlockState() == state:
            start = 0
            add = 0
        else:
            match = delimiter.search(text)
            if not match:
                return False
            start = match.start()
            add = match.end() - match.start()

        while start >= 0:
            end_match = delimiter.search(text, start + add)
            if end_match:
                length = end_match.end() - start
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(state)
                length = len(text) - start
            self.setFormat(start, length, self._string_fmt)
            if not end_match:
                break
            next_match = delimiter.search(text, start + length)
            start = next_match.start() if next_match else -1
            add = 3
        return self.currentBlockState() == state


class _LineNumberArea(QtWidgets.QWidget):
    """Gutter widget painted by the editor to show line numbers."""

    def __init__(self, editor):
        super(_LineNumberArea, self).__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QtCore.QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class PythonCodeEditor(QtWidgets.QPlainTextEdit):
    """A ``QPlainTextEdit`` with line numbers, highlighting and smart indent."""

    def __init__(self, parent=None):
        super(PythonCodeEditor, self).__init__(parent)

        self._line_number_area = _LineNumberArea(self)
        self._highlighter = PythonHighlighter(self.document())

        # Indentation / display state (loaded from settings in _load_prefs).
        self._use_spaces = DEFAULT_USE_SPACES
        self._indent_width = DEFAULT_INDENT_WIDTH
        self._show_whitespace = DEFAULT_SHOW_WHITESPACE

        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Base, _BG_COLOR)
        palette.setColor(QtGui.QPalette.Text, _TEXT_COLOR)
        self.setPalette(palette)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._load_prefs()
        self._update_line_number_area_width(0)
        self._highlight_current_line()

    # -- preferences ----------------------------------------------------
    def _settings(self):
        return QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    def _load_prefs(self):
        settings = self._settings()
        family = settings.value("font_family", DEFAULT_FONT_FAMILY)
        size = int(settings.value("font_size", DEFAULT_FONT_SIZE))
        self._use_spaces = (
            str(settings.value("use_spaces", DEFAULT_USE_SPACES)).lower()
            in ("true", "1")
        )
        self._indent_width = int(
            settings.value("indent_width", DEFAULT_INDENT_WIDTH)
        )
        self._show_whitespace = (
            str(
                settings.value("show_whitespace", DEFAULT_SHOW_WHITESPACE)
            ).lower()
            in ("true", "1")
        )
        self.set_editor_font(family, size)
        self.set_show_whitespace(self._show_whitespace)

    def _save_prefs(self):
        settings = self._settings()
        settings.setValue("font_family", self.font().family())
        settings.setValue("font_size", self.font().pointSize())
        settings.setValue("use_spaces", self._use_spaces)
        settings.setValue("indent_width", self._indent_width)
        settings.setValue("show_whitespace", self._show_whitespace)

    # -- public configuration -------------------------------------------
    def set_editor_font(self, family, size):
        """Set a fixed-pitch editor font and refresh dependent metrics."""
        font = QtGui.QFont(family)
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(int(size))
        self.setFont(font)
        self._line_number_area.setFont(font)
        self._apply_tab_stop()
        self._update_line_number_area_width(0)
        self._save_prefs()

    def set_indent_width(self, width):
        """Set the number of columns one indent level occupies."""
        self._indent_width = max(1, int(width))
        self._apply_tab_stop()
        self._save_prefs()

    def set_use_spaces(self, use_spaces):
        """Choose spaces (True) or a tab character (False) for indentation."""
        self._use_spaces = bool(use_spaces)
        self._save_prefs()

    def use_spaces(self):
        return self._use_spaces

    def indent_width(self):
        return self._indent_width

    def set_show_whitespace(self, show):
        """Toggle rendering of spaces/tabs (visualize indentation)."""
        self._show_whitespace = bool(show)
        option = self.document().defaultTextOption()
        flags = option.flags()
        if self._show_whitespace:
            flags |= QtGui.QTextOption.ShowTabsAndSpaces
        else:
            flags &= ~QtGui.QTextOption.ShowTabsAndSpaces
        option.setFlags(flags)
        self.document().setDefaultTextOption(option)
        self.viewport().update()
        self._save_prefs()

    def show_whitespace(self):
        return self._show_whitespace

    def convert_indentation_to_spaces(self):
        """Replace every tab with ``indent_width`` spaces and switch to spaces.

        Preserves the cursor position (clamped) and groups as one undo step.
        """
        spaces = " " * self._indent_width
        cursor = self.textCursor()
        position = cursor.position()
        new_text = self.toPlainText().replace("\t", spaces)
        cursor.beginEditBlock()
        cursor.select(QtGui.QTextCursor.Document)
        cursor.insertText(new_text)
        cursor.endEditBlock()
        restore = self.textCursor()
        restore.setPosition(min(position, len(new_text)))
        self.setTextCursor(restore)
        self.set_use_spaces(True)

    def _apply_tab_stop(self):
        advance = self.fontMetrics().horizontalAdvance(" ")
        self.setTabStopDistance(self._indent_width * advance)

    def _indent_text(self):
        return " " * self._indent_width if self._use_spaces else "\t"

    # -- line number area ----------------------------------------------
    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _count):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super(PythonCodeEditor, self).resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QtCore.QRect(
                cr.left(), cr.top(), self.line_number_area_width(), cr.height()
            )
        )

    def line_number_area_paint_event(self, event):
        painter = QtGui.QPainter(self._line_number_area)
        painter.fillRect(event.rect(), _GUTTER_BG)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = int(self.blockBoundingGeometry(block).translated(offset).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        width = self._line_number_area.width() - 5
        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(_GUTTER_FG)
                painter.drawText(
                    0,
                    top,
                    width,
                    height,
                    QtCore.Qt.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()
            selection.format.setBackground(_CURRENT_LINE)
            selection.format.setProperty(
                QtGui.QTextFormat.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.setExtraSelections(selections)

    # -- indentation / key handling ------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Tab:
            self._indent(True)
            return
        if key == QtCore.Qt.Key_Backtab:
            self._indent(False)
            return
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self._newline(event)
            return
        super(PythonCodeEditor, self).keyPressEvent(event)

    def _indent(self, forward):
        cursor = self.textCursor()
        # Tab with no selection just inserts one indent level at the cursor.
        if forward and not cursor.hasSelection():
            cursor.insertText(self._indent_text())
            return
        doc = self.document()
        if cursor.hasSelection():
            first = doc.findBlock(cursor.selectionStart()).blockNumber()
            last = doc.findBlock(cursor.selectionEnd()).blockNumber()
        else:
            first = last = cursor.blockNumber()
        self._shift_lines(first, last, forward)

    def _shift_lines(self, first, last, forward):
        """Indent or unindent the block-number range [first, last]."""
        doc = self.document()
        indent_text = self._indent_text()
        group = self.textCursor()
        group.beginEditBlock()
        for number in range(first, last + 1):
            block = doc.findBlockByNumber(number)
            line_cursor = QtGui.QTextCursor(block)
            line_cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
            if forward:
                line_cursor.insertText(indent_text)
            else:
                line = block.text()
                if line.startswith("\t"):
                    remove = 1
                else:
                    leading = len(line) - len(line.lstrip(" "))
                    remove = min(leading, self._indent_width)
                if remove:
                    line_cursor.movePosition(
                        QtGui.QTextCursor.NextCharacter,
                        QtGui.QTextCursor.KeepAnchor,
                        remove,
                    )
                    line_cursor.removeSelectedText()
        group.endEditBlock()

    def _newline(self, event):
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = re.match(r"[ \t]*", line).group(0)
        extra = self._indent_text() if line.strip().endswith(":") else ""
        super(PythonCodeEditor, self).keyPressEvent(event)
        self.insertPlainText(indent + extra)
