"""Qt/Maya-free data model for picker tab background layers.

A picker tab background is an ordered list of image *layers* drawn back-to-front
(index 0 is the backmost layer). ``BackgroundLayer`` mirrors the per-layer
dictionary schema stored in ``.pkr`` files and the ``PICKER_DATAS`` node, and is
the serialization authority for the view's backgrounds (``get_data`` / ``set_data``
delegate to ``layers_to_data`` / ``layers_from_view_data``). It has no Qt or Maya
dependency, so layers can be constructed and round-tripped for import/export
without a running DCC.

Fields map 1:1 to the schema keys:
    path       image file path (absolute or relative)
    position   [cx, cy] layer center in the view's centered, Y-flipped scene space
    size       [w, h] draw size in scene units ([0, 0] means "use natural size")
"""


class BackgroundLayer(object):
    """Serializable data model for a single background image layer."""

    def __init__(self):
        self.path = None
        self.position = [0, 0]
        self.size = [0, 0]

    @classmethod
    def from_dict(cls, data):
        """Build a layer from a background-layer dictionary.

        Args:
            data (dict): background layer data.

        Returns:
            BackgroundLayer: populated model.
        """
        layer = cls()
        data = data or {}

        if "path" in data:
            layer.path = data["path"]
        if "position" in data:
            layer.position = list(data.get("position", [0, 0]))
        if "size" in data:
            layer.size = list(data.get("size", [0, 0]))

        return layer

    def to_dict(self):
        """Serialize the layer back to the background-layer dictionary schema.

        Returns:
            dict: background layer data with ``path``, ``position``, ``size``.
        """
        return {
            "path": self.path,
            "position": list(self.position),
            "size": list(self.size),
        }


def layers_from_view_data(data):
    """Build a list of ``BackgroundLayer`` from a tab's view data.

    Accepts the new ``backgrounds`` list, or the legacy single ``background`` /
    ``background_size`` keys (mapped to one centered layer), or neither.

    Args:
        data (dict): tab view data (may be partial).

    Returns:
        list: list of ``BackgroundLayer`` (empty when there is no background).
    """
    data = data or {}

    if "backgrounds" in data:
        return [BackgroundLayer.from_dict(entry) for entry in data["backgrounds"]]

    # Legacy single-image compatibility: map to one centered layer so bundled
    # templates and older user exports keep loading.
    background = data.get("background", None)
    if background:
        layer = BackgroundLayer()
        layer.path = background
        layer.position = [0, 0]
        size = data.get("background_size", None)
        if size:
            layer.size = list(size)
        return [layer]

    return []


def layers_to_data(layers):
    """Serialize a list of ``BackgroundLayer`` to the ``backgrounds`` list form.

    Args:
        layers (list): list of ``BackgroundLayer``.

    Returns:
        list: list of background-layer dictionaries.
    """
    return [layer.to_dict() for layer in layers]
