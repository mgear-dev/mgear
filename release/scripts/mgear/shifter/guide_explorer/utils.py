import os
from typing import List, Optional, Sequence, Union
from pathlib import Path
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


def get_mgear_icon_search_paths() -> List[Path]:
    """
    Return all mGear-related icon search paths from XBMLANGPATH.

    These paths represent the effective icon directories Maya is using
    after module resolution.

    :return: List of icon search paths containing "mgear".
    """
    paths: List[Path] = []

    xbm_lang_path = os.environ.get("XBMLANGPATH", "")
    if not xbm_lang_path:
        return paths

    for entry in xbm_lang_path.split(os.pathsep):
        if "mgear" not in entry.lower():
            continue

        p = Path(entry)
        if p.is_dir() and p not in paths:
            paths.append(p)

    return paths


def get_mgear_icon_path(filename: str) -> Optional[Path]:
    """
    Resolve a full path to an mGear icon file using Maya's resolved icon paths.

    :param filename: Icon file name (e.g. "visibility_on.svg").
    :return: Absolute Path to the icon if found, otherwise None.
    """
    for base_path in get_mgear_icon_search_paths():
        candidate = base_path / filename
        if candidate.is_file():
            return candidate

    return None