"""Qt/Maya-free data model for a picker item.

`PickerItemData` mirrors the picker-item dictionary schema used by ``.pkr``
files and the ``PICKER_DATAS`` node, and is the serialization authority for a
``PickerItem`` (``get_data`` / ``set_data`` delegate to ``to_dict`` /
``from_dict``). It has no Qt or Maya dependency, so it can be constructed and
round-tripped for import/export without a running DCC.

Fields map 1:1 to the schema keys:
    color        RGBA tuple
    position     [x, y]
    rotation     float
    handles      list of [x, y]
    action_mode  bool (custom action script mode)
    action_script  str
    controls     list of control names
    menus        list of custom menu data
    text         str
    text_size    float
    text_color   RGBA tuple
    item_id      str (optional stable id, minted when first mirror-linked)
    mirror_id    str (optional mirror partner's item_id)
    pinned       bool (optional; item locked to the viewport as a HUD overlay)
    anchor       str (optional 3x3 viewport anchor code, e.g. "tl")
    offset       [dx, dy] (optional inward pixel offset from the anchor)
"""


class PickerItemData(object):
    """Serializable data model for a single picker item."""

    def __init__(self):
        self.color = None
        self.position = [0, 0]
        self.rotation = 0.0
        self.handles = []
        self.action_mode = False
        self.action_script = None
        self.controls = []
        self.menus = []
        self.text = None
        self.text_size = None
        self.text_color = None
        self.item_id = None
        self.mirror_id = None
        self.pinned = False
        self.anchor = None
        self.offset = None

    @classmethod
    def from_dict(cls, data):
        """Build a model from a picker-item dictionary.

        Args:
            data (dict): picker item data (may be a partial subset, as used by
                copy/paste).

        Returns:
            PickerItemData: populated model.
        """
        model = cls()
        data = data or {}

        if "color" in data:
            model.color = tuple(data["color"])
        if "position" in data:
            model.position = list(data.get("position", [0, 0]))
        if "rotation" in data:
            model.rotation = data.get("rotation")
        if "handles" in data:
            model.handles = [list(handle) for handle in data["handles"]]
        if data.get("action_mode", False):
            model.action_mode = True
            model.action_script = data.get("action_script", None)
        if "controls" in data:
            model.controls = list(data["controls"])
        if "menus" in data:
            model.menus = data["menus"]
        if "text" in data:
            model.text = data["text"]
            model.text_size = data.get("text_size")
            if "text_color" in data:
                model.text_color = tuple(data["text_color"])
        if data.get("id"):
            model.item_id = data["id"]
        if data.get("mirror"):
            model.mirror_id = data["mirror"]
        if data.get("pinned"):
            model.pinned = True
            model.anchor = data.get("anchor")
            model.offset = (
                list(data["offset"]) if "offset" in data else None
            )

        return model

    def to_dict(self):
        """Serialize the model back to the picker-item dictionary schema.

        Only the keys that the legacy ``PickerItem.get_data`` emitted are
        produced, in the same order, so the round-trip is byte-compatible.

        Returns:
            dict: picker item data.
        """
        data = {}
        data["color"] = self.color
        data["position"] = list(self.position)
        data["rotation"] = self.rotation
        data["handles"] = [list(handle) for handle in self.handles]

        if self.action_mode:
            data["action_mode"] = True
            data["action_script"] = self.action_script

        if self.controls:
            data["controls"] = self.controls

        if self.menus:
            data["menus"] = self.menus

        if self.text:
            data["text"] = self.text
            data["text_size"] = self.text_size
            data["text_color"] = self.text_color

        # Mirror link (additive optional keys; absent when unlinked so old
        # readers and unlinked pickers are unaffected).
        if self.item_id:
            data["id"] = self.item_id
        if self.mirror_id:
            data["mirror"] = self.mirror_id

        # Viewport pin (additive optional keys; only emitted when pinned so old
        # readers and non-pinned items are unaffected).
        if self.pinned:
            data["pinned"] = True
            if self.anchor:
                data["anchor"] = self.anchor
            if self.offset is not None:
                data["offset"] = list(self.offset)

        return data
