"""Qt/Maya-free layer model for vector (SVG) picker items.

A vector item's ``svg`` data holds its geometry. Historically that is one set
of ``subpaths`` drawn in one ``mode`` (``fill`` / ``stroke``) with one
``stroke_width``. Layers extend this: each layer is a dict::

    {
        "name": str,
        "subpaths": [...],          # normalized M / L / C / Z subpaths
        "mode": "fill" | "stroke",
        "stroke_width": float,
        "visible": bool,
        "locked": bool,
        "color": "#rrggbb" or None,  # None: use the item color
    }

listed back to front (index 0 is drawn first). A layer without its own color
uses the item color; changing the item color clears the layer colors.

Serialization stays backward compatible (see ``svg_from_layers``): a single
default layer is written with exactly the legacy keys, and anything richer
adds a ``layers`` list next to a flattened legacy fallback, so older readers
still draw an approximation.

``VectorDocument`` is the SVG editor's working copy: layers, the current
layer, the selection, and deep-copy snapshots for undo.
"""

import copy

from mgear.core.svg_import import MODE_FILL
from mgear.core.svg_import import MODE_STROKE

DEFAULT_STROKE_WIDTH = 2.0
DEFAULT_LAYER_NAME = "Layer 1"


#############################################
# LAYERS <-> SVG DATA
#############################################


def new_layer(
    name=DEFAULT_LAYER_NAME,
    subpaths=None,
    mode=MODE_FILL,
    stroke_width=DEFAULT_STROKE_WIDTH,
    visible=True,
    locked=False,
    color=None,
):
    """Return a new layer dict.

    Args:
        name (str, optional): Layer name.
        subpaths (list, optional): Normalized subpaths.
        mode (str, optional): ``MODE_FILL`` or ``MODE_STROKE``.
        stroke_width (float, optional): Line width in stroke mode.
        visible (bool, optional): Whether the layer is drawn.
        locked (bool, optional): Whether the layer is protected from editing.
        color (str, optional): ``#rrggbb`` layer color; None uses the item
            color.

    Returns:
        dict: The layer.
    """
    return {
        "name": name,
        "subpaths": [list(sub) for sub in (subpaths or [])],
        "mode": mode or MODE_FILL,
        "stroke_width": float(stroke_width),
        "visible": bool(visible),
        "locked": bool(locked),
        "color": color or None,
    }


def layers_from_svg(svg):
    """Return the layers described by an item's ``svg`` data.

    Data with a ``layers`` list is read from it; legacy data becomes one
    default layer. The result is an independent copy.

    Args:
        svg (dict): The item's ``svg`` data (may be empty).

    Returns:
        list: Layer dicts, back to front (empty when there is no data).
    """
    if not svg:
        return []
    if svg.get("layers"):
        return [
            new_layer(
                name=layer.get("name", DEFAULT_LAYER_NAME),
                subpaths=layer.get("subpaths", []),
                mode=layer.get("mode", MODE_FILL),
                stroke_width=layer.get("stroke_width", DEFAULT_STROKE_WIDTH),
                visible=layer.get("visible", True),
                locked=layer.get("locked", False),
                color=layer.get("color"),
            )
            for layer in svg["layers"]
        ]
    return [
        new_layer(
            subpaths=svg.get("subpaths", []),
            mode=svg.get("mode", MODE_FILL),
            stroke_width=svg.get("stroke_width", DEFAULT_STROKE_WIDTH),
        )
    ]


def is_default_single(layers):
    """Return True when ``layers`` is one plain layer (legacy-equivalent).

    Args:
        layers (list): Layer dicts.

    Returns:
        bool: True for a single visible, unlocked, default-named layer
            with no color of its own.
    """
    if len(layers) != 1:
        return False
    layer = layers[0]
    return (
        layer["visible"]
        and not layer["locked"]
        and not layer.get("color")
        and layer["name"] in (DEFAULT_LAYER_NAME, "")
    )


def flatten(layers, visible_only=True):
    """Return every subpath of ``layers`` as one list, back to front.

    Args:
        layers (list): Layer dicts.
        visible_only (bool, optional): Skip hidden layers.

    Returns:
        list: Subpaths.
    """
    result = []
    for layer in layers:
        if visible_only and not layer["visible"]:
            continue
        result.extend(list(sub) for sub in layer["subpaths"])
    return result


def svg_from_layers(layers, name=""):
    """Serialize layers to an item's ``svg`` data.

    A single default layer writes only the legacy keys (``subpaths``,
    ``mode``, ``stroke_width``). Otherwise ``layers`` is added and the legacy
    keys hold a fallback: every visible subpath, drawn in the bottom layer's
    mode and width.

    Args:
        layers (list): Layer dicts, back to front.
        name (str, optional): Source name kept on the data (e.g. the
            imported file name).

    Returns:
        dict: The ``svg`` data, or an empty dict when there are no layers.
    """
    if not layers:
        return {}
    bottom = layers[0]
    data = {
        "name": name,
        "subpaths": flatten(layers),
        "mode": bottom["mode"],
        "stroke_width": bottom["stroke_width"],
    }
    if not is_default_single(layers):
        data["layers"] = copy.deepcopy(layers)
    return data


def has_layer_colors(layers):
    """Return True when any layer has its own color.

    Args:
        layers (list): Layer dicts.

    Returns:
        bool: Whether a layer overrides the item color.
    """
    return any(layer.get("color") for layer in layers)


def clear_layer_colors(layers):
    """Return a copy of ``layers`` with every layer color removed.

    Args:
        layers (list): Layer dicts.

    Returns:
        list: New layer dicts that all use the item color.
    """
    result = copy.deepcopy(layers)
    for layer in result:
        layer["color"] = None
    return result


def map_layers(layers, fn):
    """Return a copy of ``layers`` with ``fn`` applied to each layer's subpaths.

    Args:
        layers (list): Layer dicts.
        fn (callable): Takes and returns a list of subpaths.

    Returns:
        list: New layer dicts.
    """
    result = copy.deepcopy(layers)
    for layer in result:
        layer["subpaths"] = [list(sub) for sub in fn(layer["subpaths"])]
    return result


#############################################
# EDITOR DOCUMENT
#############################################


class VectorDocument(object):
    """The SVG editor's working copy of a vector item.

    Attributes:
        layers (list): Layer dicts, back to front.
        current (int): Index of the layer new drawings go onto.
        selected_subpaths (set): ``(layer, subpath)`` pairs (Select tool).
        selected_nodes (set): ``(layer, subpath, node)`` triples (Node tool).
    """

    def __init__(self, layers=None):
        self.layers = copy.deepcopy(layers) if layers else [new_layer()]
        self.current = len(self.layers) - 1
        self.selected_subpaths = set()
        self.selected_nodes = set()

    @classmethod
    def from_svg_data(cls, svg):
        """Build a document from an item's ``svg`` data.

        Args:
            svg (dict): The item's ``svg`` data (may be empty).

        Returns:
            VectorDocument: A document with at least one layer.
        """
        return cls(layers_from_svg(svg))

    def is_empty(self):
        """Return True when no layer holds any geometry.

        Returns:
            bool: Empty state.
        """
        return not any(layer["subpaths"] for layer in self.layers)

    def editable(self, layer_index):
        """Return True when a layer is visible and unlocked.

        Args:
            layer_index (int): Layer index.

        Returns:
            bool: Whether the layer can be selected and edited.
        """
        layer = self.layers[layer_index]
        return layer["visible"] and not layer["locked"]

    def clear_selection(self):
        """Deselect everything."""
        self.selected_subpaths = set()
        self.selected_nodes = set()

    def snapshot(self):
        """Return a deep copy of the document state, for undo.

        Returns:
            dict: Layers, current layer, and selection.
        """
        return {
            "layers": copy.deepcopy(self.layers),
            "current": self.current,
            "selected_subpaths": set(self.selected_subpaths),
            "selected_nodes": set(self.selected_nodes),
        }

    def restore(self, snapshot):
        """Restore a state captured by ``snapshot``.

        Args:
            snapshot (dict): A value returned by ``snapshot``.
        """
        self.layers = copy.deepcopy(snapshot["layers"])
        self.current = min(snapshot["current"], len(self.layers) - 1)
        self.selected_subpaths = set(snapshot["selected_subpaths"])
        self.selected_nodes = set(snapshot["selected_nodes"])
