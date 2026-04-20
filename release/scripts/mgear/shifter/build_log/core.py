"""Shifter Build Log - Core logic.

Data model, log handler, export/import, and comparison utilities
for the Shifter build log system.
"""

import datetime
import difflib
import json
import re

import mgear

from mgear.vendor.Qt import QtCore

# Regex to detect Python file paths in log messages
FILE_PATH_PATTERN = re.compile(
    r"((?:[A-Za-z]:\\|/)[^\s\"',:]+\.py)"
)

# Severity to (name, hex color) mapping
SEVERITY_MAP = {
    mgear.sev_fatal: ("致命", "#ff4444"),
    mgear.sev_error: ("错误", "#cc6666"),
    mgear.sev_warning: ("警告", "#ddd87c"),
    mgear.sev_info: ("信息", "#cccccc"),
    mgear.sev_verbose: ("详细", "#888888"),
    mgear.sev_comment: ("注释", "#aaaaaa"),
}

# Reverse lookup: name -> severity int
SEVERITY_BY_NAME = {
    name: sev for sev, (name, _) in SEVERITY_MAP.items()
}


class LogRecord:
    """A single log entry with timestamp, message, and severity.

    Args:
        message (str): The log message text.
        severity (int): mGear severity constant.
    """

    def __init__(self, message, severity=mgear.sev_comment):
        self.timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.message = message
        self.severity = severity
        name, color = SEVERITY_MAP.get(
            severity, ("comment", "#aaaaaa")
        )
        self.severity_name = name
        self.color = color

    def to_dict(self):
        """Convert to dictionary for JSON export.

        Returns:
            dict: Serializable dictionary.
        """
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "severity_name": self.severity_name,
            "message": self.message,
        }

    @staticmethod
    def from_dict(data):
        """Create a LogRecord from a dictionary.

        Args:
            data (dict): Dictionary with record data.

        Returns:
            LogRecord: Reconstructed record.
        """
        record = LogRecord(
            data.get("message", ""),
            data.get("severity", mgear.sev_comment),
        )
        record.timestamp = data.get("timestamp", record.timestamp)
        return record


class _SignalEmitter(QtCore.QObject):
    """Internal QObject for emitting Qt signals from the handler."""

    record_added = QtCore.Signal(object)


class BuildLogHandler:
    """Collects log records and notifies the UI via Qt signals.

    Connect to ``signal_emitter.record_added`` to receive new
    ``LogRecord`` instances as they arrive.
    """

    def __init__(self):
        self.records = []
        self.signal_emitter = _SignalEmitter()

    def handle(self, message, severity):
        """Handle a log message from mgear.log().

        Args:
            message (str): The log message.
            severity (int): mGear severity constant.
        """
        record = LogRecord(message, severity)
        self.records.append(record)
        self.signal_emitter.record_added.emit(record)

    def clear(self):
        """Remove all stored records."""
        self.records = []

    def get_filtered(self, severities):
        """Return records matching the given severity flags.

        Args:
            severities (set): Set of severity int values to include.

        Returns:
            list: Filtered LogRecord list.
        """
        return [r for r in self.records if r.severity in severities]

    def get_counts(self):
        """Return a dict of severity_name -> count.

        Returns:
            dict: Counts per severity name.
        """
        counts = {}
        for record in self.records:
            name = record.severity_name
            counts[name] = counts.get(name, 0) + 1
        return counts

    def export_text(self, file_path):
        """Export log as plain text.

        Args:
            file_path (str): Destination file path.

        Returns:
            bool: True if successful.
        """
        try:
            with open(file_path, "w") as f:
                for record in self.records:
                    line = "[{}] {} {}\n".format(
                        record.severity_name.upper(),
                        record.timestamp,
                        record.message,
                    )
                    f.write(line)
            return True
        except IOError:
            return False

    def export_json(self, file_path, rig_name=""):
        """Export log as structured JSON.

        Args:
            file_path (str): Destination file path.
            rig_name (str): Optional rig name for metadata.

        Returns:
            bool: True if successful.
        """
        data = {
            "version": 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "rig_name": rig_name,
            "entries": [r.to_dict() for r in self.records],
        }
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except IOError:
            return False

    @staticmethod
    def import_json(file_path):
        """Import log records from a JSON file.

        Args:
            file_path (str): Path to the JSON log file.

        Returns:
            list: List of LogRecord, or None if import failed.
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

        entries = data.get("entries", [])
        return [LogRecord.from_dict(e) for e in entries]


def compare_logs(records_a, records_b):
    """Compare two lists of LogRecord and return diff entries.

    Args:
        records_a (list): First log record list.
        records_b (list): Second log record list.

    Returns:
        list: List of tuples (tag, line) where tag is one of
            "equal", "add", "remove".
    """
    lines_a = [r.message for r in records_a]
    lines_b = [r.message for r in records_b]

    result = []
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in lines_a[i1:i2]:
                result.append(("equal", line))
        elif tag == "replace":
            for line in lines_a[i1:i2]:
                result.append(("remove", line))
            for line in lines_b[j1:j2]:
                result.append(("add", line))
        elif tag == "delete":
            for line in lines_a[i1:i2]:
                result.append(("remove", line))
        elif tag == "insert":
            for line in lines_b[j1:j2]:
                result.append(("add", line))

    return result
