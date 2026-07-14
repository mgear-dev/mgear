"""Picker item copy/paste dialog and state handling.

Extracted from picker_widgets.py during the Phase 2 decomposition.
PickerItem is imported lazily inside the methods that need it to avoid a
circular import with picker_item.py.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic


class State(object):
    """State object, for easy state handling"""

    def __init__(self, state, name=False):
        self.state = state
        self.name = name

    def __lt__(self, other):
        """Override for "sort" function"""
        return self.name < other.name

    def get(self):
        return self.state

    def set(self, state):
        self.state = state


class DataCopyDialog(QtWidgets.QDialog):
    """PickerItem data copying dialog handler"""

    __DATA__ = {}

    __STATES__ = []
    __DO_POS__ = State(False, "position")
    __STATES__.append(__DO_POS__)
    __DO_ROT__ = State(False, "rotation")
    __STATES__.append(__DO_ROT__)
    __DO_COLOR__ = State(True, "color")
    __STATES__.append(__DO_COLOR__)
    __DO_ACTION_MODE__ = State(True, "action_mode")
    __STATES__.append(__DO_ACTION_MODE__)
    __DO_ACTION_SCRIPT__ = State(True, "action_script")
    __STATES__.append(__DO_ACTION_SCRIPT__)
    __DO_HANDLES__ = State(True, "handles")
    __STATES__.append(__DO_HANDLES__)
    __DO_TEXT__ = State(True, "text")
    __STATES__.append(__DO_TEXT__)
    __DO_TEXT_SIZE__ = State(True, "text_size")
    __STATES__.append(__DO_TEXT_SIZE__)
    __DO_TEXT_COLOR__ = State(True, "text_color")
    __STATES__.append(__DO_TEXT_COLOR__)
    __DO_CTRLS__ = State(True, "controls")
    __STATES__.append(__DO_CTRLS__)
    __DO_MENUS__ = State(True, "menus")
    __STATES__.append(__DO_MENUS__)

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle("Copy/Paste")

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add data field options
        for state in self.__STATES__:
            label_name = state.name.capitalize().replace("_", " ")
            cb = basic.CallbackCheckBoxWidget(
                callback=self.check_box_event,
                value=state.get(),
                label=label_name,
                state_obj=state,
            )
            self.main_layout.addWidget(cb)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

    def check_box_event(self, value=False, state_obj=None):
        """Update state object value on checkbox state change event"""
        state_obj.set(value)

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    @classmethod
    def options(cls, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls()
        win.exec_()
        win.raise_()

        if not win.apply:
            return
        # win.set(item)

    @staticmethod
    def set_pos(item=None, x=True, y=True):
        """Set the position date for a specific picker item

        Args:
            item (object, optional): picker object item
            x (bool, optional): if true will set X position
            y (bool, optional): if true will set Y position
        """
        # Sanity check
        # Lazy import to avoid a circular import with picker_item.py
        from mgear.anim_picker.widgets.picker_item import PickerItem

        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg
        assert DataCopyDialog.__DATA__, "No stored data to paste"

        keys = []
        keys.append("position")

        # Build valid data
        data = {}
        for key in keys:
            if key not in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]

        # Get picker item data
        item_data = item.get_data()

        if x:
            data["position"][1] = item_data["position"][1]
        if y:
            data["position"][0] = item_data["position"][0]
        item.set_data(data)

    @staticmethod
    def set(item=None):
        """Set the data to specific picker item

        Args:
            item (object, optional): Picker object
        """
        # Sanity check
        # Lazy import to avoid a circular import with picker_item.py
        from mgear.anim_picker.widgets.picker_item import PickerItem

        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg
        assert DataCopyDialog.__DATA__, "No stored data to paste"

        # Filter data keys to copy
        keys = []
        for state in DataCopyDialog.__STATES__:
            if not state.get():
                continue
            keys.append(state.name)

        # Build valid data
        data = {}
        for key in keys:
            if key not in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]

        # Get picker item data
        item.set_data(data)

    @staticmethod
    def get(item=None):
        """Will get and store data for specified item"""
        # Sanity check
        # Lazy import to avoid a circular import with picker_item.py
        from mgear.anim_picker.widgets.picker_item import PickerItem

        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg

        # Get picker item data
        data = item.get_data()

        # Store data
        DataCopyDialog.__DATA__ = data

        return data
