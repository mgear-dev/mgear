"""Ordered graphics scene for the anim picker.

Extracted from gui.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import picker_widgets
from mgear.anim_picker.handlers import __EDIT_MODE__


class OrderedGraphicsScene(QtWidgets.QGraphicsScene):
    """
    Custom QGraphicsScene with x/y axis line options for origin
    feedback in edition mode
    (provides a center reference to work from, view will fit what ever
    is the content in use mode).

    Had to add z_index support since there was a little z
    conflict when "moving" items to back/front in edit mode
    """

    __DEFAULT_SCENE_WIDTH__ = 6000
    __DEFAULT_SCENE_HEIGHT__ = 6000

    def __init__(self, parent=None):
        QtWidgets.QGraphicsScene.__init__(self, parent=parent)

        self.set_default_size()
        self._z_index = 0

    def set_size(self, width, height):
        """Will set scene size with proper center position"""
        self.setSceneRect(-width / 2, -height / 2, width, height)

    def set_default_size(self):
        self.set_size(
            self.__DEFAULT_SCENE_WIDTH__, self.__DEFAULT_SCENE_HEIGHT__
        )

    def get_bounding_rect(self, margin=0, selection=False):
        """
        Return scene content bounding box with specified margin
        Warning: In edit mode, will return default scene rectangle
        """
        # Return default size in edit mode
        # if __EDIT_MODE__.get():
        #     return self.sceneRect()

        # Get item boundingBox
        if selection:
            sel_items = self.get_selected_items()
            if not sel_items:
                return
            scene_rect = QtCore.QRectF()

            # init coordinates with the first element
            rec = sel_items[0].boundingRect().getCoords()
            x1 = rec[0] + sel_items[0].x()
            y1 = rec[1] + sel_items[0].y()
            x2 = rec[2] + sel_items[0].x()
            y2 = rec[3] + sel_items[0].y()

            for item in sel_items[1:]:
                rec = item.boundingRect().getCoords()
                if (rec[0] + item.x()) < x1:
                    x1 = rec[0] + item.x()
                if (rec[1] + item.y()) < y1:
                    y1 = rec[1] + item.y()
                if (rec[2] + item.x()) > x2:
                    x2 = rec[2] + item.x()
                if (rec[3] + item.y()) > y2:
                    y2 = rec[3] + item.y()
            scene_rect.setCoords(x1, y1, x2, y2)

        else:
            scene_rect = self.itemsBoundingRect()

        # Stop here if no margin
        if not margin:
            return scene_rect

        # Add margin
        scene_rect.setX(scene_rect.x() - margin)
        scene_rect.setY(scene_rect.y() - margin)
        scene_rect.setWidth(scene_rect.width() + margin)
        scene_rect.setHeight(scene_rect.height() + margin)

        return scene_rect

    def clear(self):
        """Reset default z index on clear"""
        QtWidgets.QGraphicsScene.clear(self)
        self._z_index = 0

    def set_picker_items(self, items):
        """Will set picker items"""
        self.clear()
        for item in items:
            QtWidgets.QGraphicsScene.addItem(self, item)
            self.set_z_value(item)
        self.add_axis_lines()

    def get_picker_items(self):
        """Will return all scenes' picker items"""
        picker_items = []
        # Filter picker items (from handles etc)
        for item in list(self.items()):
            if not isinstance(item, picker_widgets.PickerItem):
                continue
            picker_items.append(item)
        return picker_items

    def picker_at(self, scene_pos, transform):
        item_at = self.itemAt(scene_pos, transform)
        if isinstance(item_at, picker_widgets.PickerItem):
            return item_at
        elif item_at and not isinstance(item_at, picker_widgets.PickerItem):
            return item_at.parentItem()
        else:
            return None

    def get_picker_by_uuid(self, picker_uuid):
        """pickers have UUID's for hashing in dictionaries. search via uuid

        Args:
            picker_uuid (str): uuid

        Returns:
            PickerIteem: instance of matching picker
        """
        for picker in self.get_picker_items():
            if picker.uuid == picker_uuid:
                return picker
        return None

    def get_selected_items(self):
        return [
            item for item in self.get_picker_items() if item.polygon.selected
        ]

    def clear_picker_selection(self):
        for picker in self.get_picker_items():
            picker.set_selected_state(False)
        self.update()

    def select_picker_items(self, picker_items, event=None):
        if event is None:
            modifiers = None
        else:
            modifiers = event.modifiers()

        # Shift cases (toggle)
        if modifiers == QtCore.Qt.ShiftModifier:
            for picker in picker_items:
                picker.set_selected_state(True)

        # Controls case
        elif modifiers == QtCore.Qt.ControlModifier:
            for picker in picker_items:
                picker.set_selected_state(False)

        # Alt case (remove)
        # elif modifiers == QtCore.Qt.AltModifier:
        else:
            self.clear_picker_selection()
            for picker in picker_items:
                picker.set_selected_state(True)

    def set_z_value(self, item):
        """set proper z index for item"""
        item.setZValue(self._z_index)
        self._z_index += 1

    def addItem(self, item):
        """Overload to keep axis on top"""
        QtWidgets.QGraphicsScene.addItem(self, item)
        self.set_z_value(item)
