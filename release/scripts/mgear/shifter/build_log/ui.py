"""Shifter Build Log - UI Module.

Qt-based build log window with color-coded severity, filtering,
right-click file opening, log export, and log comparison.
"""

import os
import platform
import subprocess

import mgear
from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from .core import BuildLogHandler
from .core import SEVERITY_MAP
from .core import FILE_PATH_PATTERN
from .core import compare_logs

# Severity filter button colors (background when active)
_FILTER_COLORS = {
    mgear.sev_fatal: "#ff4444",
    mgear.sev_error: "#cc6666",
    mgear.sev_warning: "#ddd87c",
    mgear.sev_info: "#cccccc",
    mgear.sev_verbose: "#888888",
    mgear.sev_comment: "#aaaaaa",
}

_ICON_SIZE = int(pyqt.dpi_scale(16))


class BuildLogWindow(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Dockable build log window with color-coded output and filtering.

    Singleton window — use ``show_window()`` to create or raise.
    """

    TOOL_NAME = "ShifterBuildLog"
    TOOL_TITLE = "Shifter 构建日志"

    _instance = None

    def __init__(self, parent=None):
        super(BuildLogWindow, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        # State
        self.handler = BuildLogHandler()
        self._active_severities = set(SEVERITY_MAP.keys())
        self._search_text = ""
        self._font_size = int(pyqt.dpi_scale(12))

        # Window setup
        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(400, 300)

        if cmds.about(ntOS=True):
            flags = (
                self.windowFlags()
                ^ QtCore.Qt.WindowContextHelpButtonHint
            )
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()

        self.user_settings = {}
        self.load_settings()

        self.resize(800, 500)

        # Register handler with mgear log system
        mgear.register_log_handler(self.handler.handle)

        # Intercept pm.displayInfo/Warning/Error for custom steps
        _install_display_hooks(self.handler)

        # Connect handler signal to UI update
        self.handler.signal_emitter.record_added.connect(
            self._on_record_added
        )

        # Store singleton reference
        BuildLogWindow._instance = self

        # Clean up old MEL-based log window if it exists
        _cleanup_old_log_window()

        # Print version info as first entry
        mgear.logInfos()

    # =================================================================
    # UI SETUP
    # =================================================================

    def setup_ui(self):
        """Build the UI layout."""
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        """Create all UI widgets."""
        # --- Toolbar ---
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setIconSize(QtCore.QSize(_ICON_SIZE, _ICON_SIZE))

        # Filter toggle buttons — one per severity
        self._filter_buttons = {}
        for sev in sorted(SEVERITY_MAP.keys()):
            name, color = SEVERITY_MAP[sev]
            btn = QtWidgets.QPushButton(name.capitalize())
            btn.setCheckable(True)
            btn.setChecked(True)
            self._filter_buttons[sev] = btn

        self._update_filter_button_styles()

        # Search field
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(int(pyqt.dpi_scale(200)))

        # Font size control
        self.font_size_label = QtWidgets.QLabel("字体:")
        self.font_size_label.setStyleSheet("color: #aaa;")
        self.font_size_spin = QtWidgets.QSpinBox()
        self.font_size_spin.setRange(8, 32)
        self.font_size_spin.setValue(self._font_size)
        self.font_size_spin.setSuffix("px")
        self.font_size_spin.setFixedWidth(int(pyqt.dpi_scale(70)))
        self.font_size_spin.setToolTip(
            "字体大小(Ctrl+鼠标滚轮缩放)"
        )

        # Action buttons
        btn_size = int(pyqt.dpi_scale(28))

        self.clear_btn = QtWidgets.QPushButton()
        self.clear_btn.setIcon(
            pyqt.get_icon("mgear_trash-2", _ICON_SIZE)
        )
        self.clear_btn.setFixedSize(btn_size, btn_size)
        self.clear_btn.setToolTip("清空日志")

        self.export_btn = QtWidgets.QPushButton()
        self.export_btn.setIcon(
            pyqt.get_icon("mgear_save", _ICON_SIZE)
        )
        self.export_btn.setFixedSize(btn_size, btn_size)
        self.export_btn.setToolTip("导出日志到文件")

        self.compare_btn = QtWidgets.QPushButton("比较")
        self.compare_btn.setToolTip("比较两个日志文件")

        # --- Log view ---
        self.log_view = QtWidgets.QTextBrowser()
        self.log_view.setReadOnly(True)
        self.log_view.setOpenLinks(False)
        self.log_view.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self._update_log_view_style()

        # Install event filter for Ctrl+wheel zoom on the log view
        self.log_view.viewport().installEventFilter(self)

        # --- Status bar ---
        self.status_label = QtWidgets.QLabel("就绪")
        self.status_label.setStyleSheet(
            "color: #888; font-style: italic; padding: 2px;"
        )

    def create_layout(self):
        """Arrange widgets in layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Toolbar row
        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.setSpacing(4)

        for sev in sorted(SEVERITY_MAP.keys()):
            toolbar_layout.addWidget(self._filter_buttons[sev])

        toolbar_layout.addWidget(_create_separator())
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.font_size_label)
        toolbar_layout.addWidget(self.font_size_spin)
        toolbar_layout.addWidget(_create_separator())
        toolbar_layout.addWidget(self.clear_btn)
        toolbar_layout.addWidget(self.export_btn)
        toolbar_layout.addWidget(self.compare_btn)

        main_layout.addLayout(toolbar_layout)

        # Log view
        main_layout.addWidget(self.log_view, stretch=1)

        # Status bar
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Connect signals to slots."""
        for sev, btn in self._filter_buttons.items():
            btn.toggled.connect(self._on_filter_toggled)

        self.search_input.textChanged.connect(
            self._on_search_changed
        )

        self.font_size_spin.valueChanged.connect(
            self._on_font_size_changed
        )

        self.clear_btn.clicked.connect(self._clear_log)
        self.export_btn.clicked.connect(self._export_log)
        self.compare_btn.clicked.connect(self._show_compare_dialog)

        self.log_view.customContextMenuRequested.connect(
            self._show_context_menu
        )

    # =================================================================
    # LOG DISPLAY
    # =================================================================

    def _on_record_added(self, record):
        """Append a new record to the log view.

        Args:
            record: LogRecord instance.
        """
        if record.severity not in self._active_severities:
            self._update_status()
            return

        if self._search_text and self._search_text not in record.message.lower():
            self._update_status()
            return

        self.log_view.append(
            _format_record_html(record, self._font_size)
        )
        self._update_status()

        # Flush Qt events so the log is visible during the build
        QtWidgets.QApplication.processEvents()

    def _apply_filters(self):
        """Rebuild the entire log view from stored records."""
        self.log_view.clear()
        search = self._search_text
        font_size = self._font_size

        html_parts = []
        for record in self.handler.records:
            if record.severity not in self._active_severities:
                continue
            if search and search not in record.message.lower():
                continue
            html_parts.append(
                _format_record_html(record, font_size)
            )

        if html_parts:
            self.log_view.setHtml(
                "<body style='background-color:#1e1e1e;'>"
                + "".join(html_parts)
                + "</body>"
            )

        self._update_status()

    def _update_status(self):
        """Update the status bar with record counts."""
        counts = self.handler.get_counts()
        total = len(self.handler.records)
        errors = counts.get("error", 0) + counts.get("fatal", 0)
        warnings = counts.get("warning", 0)

        self.status_label.setText(
            "总计: {} | 错误: {} | 警告: {}".format(
                total, errors, warnings
            )
        )

    # =================================================================
    # FILTER / SEARCH
    # =================================================================

    def _on_filter_toggled(self, _checked):
        """Handle any filter button toggle."""
        self._active_severities = set()
        for sev, btn in self._filter_buttons.items():
            if btn.isChecked():
                self._active_severities.add(sev)
        self._apply_filters()

    def _on_search_changed(self, text):
        """Handle search text change.

        Args:
            text (str): Current search text.
        """
        self._search_text = text.lower().strip()
        self._apply_filters()

    # =================================================================
    # FONT SIZE
    # =================================================================

    def _on_font_size_changed(self, size):
        """Handle font size spinbox change.

        Args:
            size (int): New font size in pixels.
        """
        self._font_size = size
        self._update_log_view_style()
        self._update_filter_button_styles()
        self._apply_filters()

    def _update_log_view_style(self):
        """Apply the current font size to the log view stylesheet."""
        self.log_view.setStyleSheet(
            "QTextBrowser {{"
            "    background-color: #1e1e1e;"
            "    font-family: 'Consolas', 'Courier New', monospace;"
            "    font-size: {size}px;"
            "    padding: 4px;"
            "}}".format(size=self._font_size)
        )

    def _update_filter_button_styles(self):
        """Apply the current font size to filter button stylesheets."""
        btn_font = max(10, self._font_size - 1)
        pad_v = max(2, int(btn_font * 0.3))
        pad_h = max(6, int(btn_font * 0.6))
        for sev, btn in self._filter_buttons.items():
            _name, color = SEVERITY_MAP[sev]
            btn.setStyleSheet(
                "QPushButton {{"
                "    background-color: {color};"
                "    color: #222;"
                "    border: 1px solid #555;"
                "    border-radius: 3px;"
                "    padding: {pv}px {ph}px;"
                "    font-size: {size}px;"
                "}}"
                "QPushButton:checked {{"
                "    background-color: {color};"
                "    border: 2px solid #fff;"
                "}}"
                "QPushButton:!checked {{"
                "    background-color: #444;"
                "    color: #888;"
                "    border: 1px solid #555;"
                "}}".format(
                    color=color, size=btn_font,
                    pv=pad_v, ph=pad_h,
                )
            )

    def eventFilter(self, obj, event):
        """Handle Ctrl+MouseWheel for font zoom on the log view.

        Args:
            obj: The watched object.
            event: The Qt event.

        Returns:
            bool: True if the event was handled.
        """
        if obj is self.log_view.viewport():
            if event.type() == QtCore.QEvent.Wheel:
                modifiers = event.modifiers()
                if modifiers & QtCore.Qt.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta > 0:
                        new_size = min(32, self._font_size + 1)
                    else:
                        new_size = max(8, self._font_size - 1)
                    if new_size != self._font_size:
                        self._font_size = new_size
                        self.font_size_spin.setValue(new_size)
                    return True
        return super(BuildLogWindow, self).eventFilter(obj, event)

    # =================================================================
    # CONTEXT MENU
    # =================================================================

    def _show_context_menu(self, pos):
        """Show right-click context menu on the log view.

        Args:
            pos: Mouse position in widget coordinates.
        """
        menu = QtWidgets.QMenu(self)

        # Get text of the line under cursor
        cursor = self.log_view.cursorForPosition(pos)
        cursor.select(QtGui.QTextCursor.BlockUnderCursor)
        line_text = cursor.selectedText().strip()

        # Detect file paths in the line
        if line_text:
            paths = FILE_PATH_PATTERN.findall(line_text)
            for path in paths:
                file_name = os.path.basename(path)
                action = menu.addAction(
                "打开 {}".format(file_name)
                )
                action.setData(path)
                action.triggered.connect(
                    lambda *args, p=path: _open_file_in_editor(p)
                )

            if paths:
                menu.addSeparator()

        # Standard actions
        copy_line_action = menu.addAction("复制行")
        copy_line_action.triggered.connect(
            lambda *args: _copy_to_clipboard(line_text)
        )

        copy_all_action = menu.addAction("复制全部")
        copy_all_action.triggered.connect(
            lambda *args: _copy_to_clipboard(
                self.log_view.toPlainText()
            )
        )

        menu.exec_(self.log_view.mapToGlobal(pos))

    # =================================================================
    # EXPORT / COMPARE
    # =================================================================

    def _clear_log(self):
        """Clear all log records and the display."""
        self.handler.clear()
        self.log_view.clear()
        self._update_status()

    def _export_log(self):
        """Export the log to a file."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出构建日志",
            "",
            "构建日志 (*.log)",
        )

        if not file_path:
            return

        if not file_path.endswith(".log"):
            file_path += ".log"
        success = self.handler.export_json(file_path)

        if success:
            self.status_label.setText(
                "已导出: {}".format(os.path.basename(file_path))
            )
        else:
            self.status_label.setText("导出失败")

    def _show_compare_dialog(self):
        """Open the log comparison dialog."""
        dialog = CompareLogsDialog(self._font_size, self)
        dialog.exec_()

    # =================================================================
    # WINDOW LIFECYCLE
    # =================================================================

    @classmethod
    def show_window(cls):
        """Show the build log window, creating it if needed."""
        workspace_control = cls.TOOL_NAME + "WorkspaceControl"
        if cmds.workspaceControl(workspace_control, exists=True):
            cmds.deleteUI(workspace_control)

        return pyqt.showDialog(cls, dockable=True)

    @classmethod
    def get_instance(cls):
        """Get the current window instance, or None.

        Returns:
            BuildLogWindow: The singleton instance, or None.
        """
        return cls._instance

    def close(self):
        """Clean up before closing."""
        mgear.unregister_log_handler(self.handler.handle)
        _uninstall_display_hooks()
        BuildLogWindow._instance = None
        self.save_settings()
        self.deleteLater()

    def closeEvent(self, event):
        """Handle close event."""
        self.close()

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self.close()


# =====================================================================
# COMPARE LOGS DIALOG
# =====================================================================


class CompareLogsDialog(QtWidgets.QDialog):
    """Side-by-side log comparison dialog.

    Loads two .log files and displays a color-coded diff.

    Args:
        font_size (int): Font size in pixels for the diff view.
        parent: Parent widget.
    """

    def __init__(self, font_size=12, parent=None):
        super(CompareLogsDialog, self).__init__(parent)

        self.setWindowTitle("比较构建日志")
        self.setMinimumSize(800, 500)

        self._font_size = font_size
        self._records_a = None
        self._records_b = None

        self._create_ui()

    def _create_ui(self):
        """Build the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # File picker row
        file_layout = QtWidgets.QHBoxLayout()

        self.load_a_btn = QtWidgets.QPushButton("加载日志 A...")
        self.load_a_btn.clicked.connect(self._load_log_a)
        self.label_a = QtWidgets.QLabel("未加载文件")
        self.label_a.setStyleSheet("color: #888;")

        self.load_b_btn = QtWidgets.QPushButton("加载日志 B...")
        self.load_b_btn.clicked.connect(self._load_log_b)
        self.label_b = QtWidgets.QLabel("未加载文件")
        self.label_b.setStyleSheet("color: #888;")

        file_layout.addWidget(self.load_a_btn)
        file_layout.addWidget(self.label_a)
        file_layout.addStretch()
        file_layout.addWidget(self.load_b_btn)
        file_layout.addWidget(self.label_b)

        layout.addLayout(file_layout)

        # Diff view
        self.diff_view = QtWidgets.QTextBrowser()
        self.diff_view.setReadOnly(True)
        self.diff_view.setStyleSheet(
            "QTextBrowser {{"
            "    background-color: #1e1e1e;"
            "    font-family: 'Consolas', 'Courier New', monospace;"
            "    font-size: {size}px;"
            "}}".format(size=self._font_size)
        )
        layout.addWidget(self.diff_view)

        # Close button
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load_log_a(self):
        """Load the first log file."""
        path = self._pick_log_file()
        if path:
            self._records_a = BuildLogHandler.import_json(path)
            self.label_a.setText(os.path.basename(path))
            self._run_compare()

    def _load_log_b(self):
        """Load the second log file."""
        path = self._pick_log_file()
        if path:
            self._records_b = BuildLogHandler.import_json(path)
            self.label_b.setText(os.path.basename(path))
            self._run_compare()

    def _pick_log_file(self):
        """Open a file dialog for build log files.

        Returns:
            str: Selected file path, or empty string.
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "打开构建日志",
            "",
            "构建日志 (*.log)",
        )
        return path

    def _run_compare(self):
        """Run comparison if both logs are loaded."""
        if not self._records_a or not self._records_b:
            return

        diff = compare_logs(self._records_a, self._records_b)

        size = self._font_size
        html_parts = []
        for tag, line in diff:
            escaped = _escape_html(line)
            if tag == "remove":
                html_parts.append(
                    "<div style='color: #cc6666;"
                    " font-size: {s}px;'>- {m}</div>".format(
                        s=size, m=escaped
                    )
                )
            elif tag == "add":
                html_parts.append(
                    "<div style='color: #89bf72;"
                    " font-size: {s}px;'>+ {m}</div>".format(
                        s=size, m=escaped
                    )
                )
            else:
                html_parts.append(
                    "<div style='color: #888;"
                    " font-size: {s}px;'>  {m}</div>".format(
                        s=size, m=escaped
                    )
                )

        self.diff_view.setHtml(
            "<body style='background-color:#1e1e1e;'>"
            + "".join(html_parts)
            + "</body>"
        )


# =====================================================================
# MODULE-LEVEL HELPERS
# =====================================================================


def _format_record_html(record, font_size=12):
    """Format a LogRecord as an HTML div with color.

    Args:
        record: LogRecord instance.
        font_size (int): Font size in pixels.

    Returns:
        str: HTML string.
    """
    escaped = _escape_html(record.message)
    return (
        "<div style='color: {color}; margin: 0; padding: 0;"
        " font-size: {size}px;'>"
        "<span style='color: #666;'>[{time}]</span> {msg}"
        "</div>"
    ).format(
        color=record.color,
        size=font_size,
        time=record.timestamp,
        msg=escaped,
    )


def _escape_html(text):
    """Escape HTML special characters.

    Args:
        text (str): Raw text.

    Returns:
        str: HTML-safe text.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace(" ", "&nbsp;")
    )


def _create_separator():
    """Create a vertical line separator widget.

    Returns:
        QFrame: Separator widget.
    """
    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.VLine)
    sep.setFrameShadow(QtWidgets.QFrame.Sunken)
    return sep


def _copy_to_clipboard(text):
    """Copy text to the system clipboard.

    Args:
        text (str): Text to copy.
    """
    clipboard = QtWidgets.QApplication.clipboard()
    if clipboard:
        clipboard.setText(text)


def _open_file_in_editor(file_path):
    """Open a file in the OS default editor.

    Args:
        file_path (str): Path to the file.
    """
    if not os.path.isfile(file_path):
        cmds.warning(
            "文件未找到: {}".format(file_path)
        )
        return

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(file_path)
        elif system == "Darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        cmds.warning(
            "Could not open file: {}".format(str(e))
        )


def _cleanup_old_log_window():
    """Delete the old MEL-based log window if it exists."""
    old_window = "mgear_shifter_build_log_window"
    try:
        if cmds.window(old_window, exists=True):
            cmds.deleteUI(old_window, window=True)
    except Exception:
        pass


# =====================================================================
# pm.display* HOOKS
# =====================================================================

# Saved originals for uninstall
_original_display_info = None
_original_display_warning = None
_original_display_error = None


def _install_display_hooks(handler):
    """Wrap pm.displayInfo/Warning/Error to forward to the log handler.

    This captures messages from custom steps and other code that
    uses pm.display* instead of mgear.log().

    Args:
        handler (BuildLogHandler): The handler to forward to.
    """
    global _original_display_info
    global _original_display_warning
    global _original_display_error

    # Guard against double-install: if already hooked, the globals hold
    # the real originals — capturing again would store the hooked
    # versions, causing infinite recursion when they call themselves.
    if _original_display_info is not None:
        return

    import mgear.pymaya as pm
    from mgear.pymaya import cmd as pm_cmd

    _original_display_info = pm_cmd.displayInfo
    _original_display_warning = pm_cmd.displayWarning
    _original_display_error = pm_cmd.displayError

    def hooked_info(msg):
        _original_display_info(msg)
        handler.handle(str(msg), mgear.sev_info)

    def hooked_warning(msg):
        _original_display_warning(msg)
        handler.handle(str(msg), mgear.sev_warning)

    def hooked_error(msg):
        _original_display_error(msg)
        handler.handle(str(msg), mgear.sev_error)

    pm_cmd.displayInfo = hooked_info
    pm_cmd.displayWarning = hooked_warning
    pm_cmd.displayError = hooked_error

    # Also patch the pm namespace so callers using pm.displayInfo work
    pm.displayInfo = hooked_info
    pm.displayWarning = hooked_warning
    pm.displayError = hooked_error


def _uninstall_display_hooks():
    """Restore original pm.displayInfo/Warning/Error functions."""
    global _original_display_info
    global _original_display_warning
    global _original_display_error

    if _original_display_info is None:
        return

    import mgear.pymaya as pm
    from mgear.pymaya import cmd as pm_cmd

    pm_cmd.displayInfo = _original_display_info
    pm_cmd.displayWarning = _original_display_warning
    pm_cmd.displayError = _original_display_error

    pm.displayInfo = _original_display_info
    pm.displayWarning = _original_display_warning
    pm.displayError = _original_display_error

    _original_display_info = None
    _original_display_warning = None
    _original_display_error = None
