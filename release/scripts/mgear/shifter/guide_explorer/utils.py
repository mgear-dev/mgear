from typing import List, Sequence, Union
import mgear.pymaya as pm


class TempSelection:
    """
    Context manager that temporarily replaces the Maya selection.

    Restores the previous selection when leaving the context.
    """
    def __init__(self, nodes: Union[pm.PyNode, Sequence[pm.PyNode]]) -> None:
        """
        :param nodes: Node or sequence of nodes to select while in context.
        """
        self._nodes = nodes if isinstance(nodes, (list, tuple)) else [nodes]
        self._prev: List[pm.PyNode] = []

    def __enter__(self) -> "TempSelection":
        """
        Store current selection and select the temporary nodes.

        :return: This context manager instance.
        """
        try:
            # -- Store current selection (PyNodes)
            self._prev = pm.ls(selection=True)
        except Exception:
            self._prev = []
        try:
            pm.select(self._nodes, replace=True)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Restore the previous selection on context exit.

        :return: None
        """
        try:
            if self._prev:
                pm.select(self._prev, replace=True)
            else:
                pm.select(clear=True)
        except Exception:
            pass