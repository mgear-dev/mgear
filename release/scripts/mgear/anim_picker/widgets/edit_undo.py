"""Bounded undo/redo stack for the anim picker editor.

A tiny, Qt- and Maya-free stack of opaque records. The editor pushes one
record per committed edit; a record is whatever the caller stores. The picker
view stores a ``{"before": snapshot, "after": snapshot}`` pair of item-state
snapshots (the item serialization plus z-order), so restoring an edit is just
re-applying one side of the pair.

The stack only manages ordering: pushing a new record truncates any redo tail
(the records that were undone), and the oldest records are evicted once the
bound is exceeded. Kept free of Qt / Maya so the ordering logic is testable in
isolation, matching the ``alignment`` / ``overlay`` / ``visibility`` modules.
"""

# Default cap on the number of retained edits. Snapshots are small dicts, but a
# fixed bound keeps memory predictable on a long editing session.
DEFAULT_MAX_STEPS = 50


class UndoStack(object):
    """A bounded linear undo/redo stack of opaque records."""

    def __init__(self, max_steps=DEFAULT_MAX_STEPS):
        self._records = []
        # Index of the last-applied record; -1 means nothing left to undo.
        self._index = -1
        self._max_steps = max(1, int(max_steps))

    def clear(self):
        """Drop every record (e.g. on load or when entering edit mode)."""
        self._records = []
        self._index = -1

    def can_undo(self):
        """Return True when there is a record to undo."""
        return self._index >= 0

    def can_redo(self):
        """Return True when there is an undone record to redo."""
        return self._index < len(self._records) - 1

    def push(self, record):
        """Append a record, truncating any redo tail and bounding the size.

        Args:
            record (object): the opaque payload the caller restores on
                undo / redo.
        """
        # Discard the redo tail (undone records) before the new branch.
        del self._records[self._index + 1:]
        self._records.append(record)
        # Evict the oldest records past the bound, keeping the newest.
        overflow = len(self._records) - self._max_steps
        if overflow > 0:
            del self._records[:overflow]
        self._index = len(self._records) - 1

    def undo(self):
        """Return the record to reverse and step back, or None."""
        if not self.can_undo():
            return None
        record = self._records[self._index]
        self._index -= 1
        return record

    def redo(self):
        """Step forward and return the record to re-apply, or None."""
        if not self.can_redo():
            return None
        self._index += 1
        return self._records[self._index]
