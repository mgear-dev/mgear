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
    text_align   str (optional placement: center/top/bottom/left/right)
    text_offset  float (optional gap in pixels from the aligned edge)
    item_id      str (optional stable id, minted when first mirror-linked)
    mirror_id    str (optional mirror partner's item_id)
    pinned       bool (optional; item locked to the viewport as a HUD overlay)
    anchor       str (optional 3x3 viewport anchor code, e.g. "tl")
    offset       [dx, dy] (optional inward pixel offset from the anchor)
    pin_scale    float (optional screen scale baked into the pin transform)
    widget       str (optional interactive type: checkbox/slider/slider2d)
    binding      dict (optional attribute(s) + range the widget drives)
    scripts      dict (optional per-state scripts for the widget)
    backdrop     bool (optional; item is a backdrop container behind others)
    title        str (optional backdrop title)
    corner_radius float (optional backdrop corner radius; 0 = straight)
    visibility   dict (optional condition; show only when a channel / zoom test
                 passes -- see ``widgets.visibility``)
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
        self.text_align = None
        self.text_offset = None
        self.item_id = None
        self.mirror_id = None
        self.pinned = False
        self.anchor = None
        self.offset = None
        self.pin_scale = None
        self.widget = None
        self.binding = None
        self.scripts = None
        self.backdrop = False
        self.title = None
        self.corner_radius = None
        self.visibility = None

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
            model.text_align = data.get("text_align")
            model.text_offset = data.get("text_offset")
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
            model.pin_scale = data.get("pin_scale")
        if data.get("widget"):
            model.widget = data["widget"]
            model.binding = dict(data["binding"]) if "binding" in data else None
            model.scripts = dict(data["scripts"]) if "scripts" in data else None
        if data.get("backdrop"):
            model.backdrop = True
            model.title = data.get("title")
            model.corner_radius = data.get("corner_radius")
        if data.get("visibility"):
            model.visibility = dict(data["visibility"])

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
            # Additive optional text placement (absent for legacy centered text).
            if self.text_align and self.text_align != "center":
                data["text_align"] = self.text_align
            if self.text_offset:
                data["text_offset"] = self.text_offset

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
            if self.pin_scale is not None:
                data["pin_scale"] = self.pin_scale

        # Interactive widget (additive optional keys; emitted only for a
        # non-button widget so old readers and plain buttons are unaffected).
        if self.widget:
            data["widget"] = self.widget
            if self.binding:
                data["binding"] = dict(self.binding)
            if self.scripts:
                data["scripts"] = dict(self.scripts)

        # Backdrop container (additive optional keys; only emitted for a
        # backdrop so old readers and normal items are unaffected).
        if self.backdrop:
            data["backdrop"] = True
            if self.title:
                data["title"] = self.title
            if self.corner_radius is not None:
                data["corner_radius"] = self.corner_radius

        # Visibility condition (additive optional key; only emitted when set so
        # old readers and unconditioned items are unaffected).
        if self.visibility:
            data["visibility"] = dict(self.visibility)

        return data
