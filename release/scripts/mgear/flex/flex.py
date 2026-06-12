
""" flex.flex

Flex is the main module that allows you to run the update tool

:module: flex.flex
"""

# imports
from __future__ import absolute_import

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCompat
from maya import OpenMayaUI, cmds
from mgear.flex import logger
from mgear.flex.analyze import analyze_groups
from mgear.flex.analyze_widget import FLEX_ANALYZE_NAME
from mgear.flex.analyze_widget import FlexAnalyzeDialog
from mgear.flex.decorators import finished_running
from mgear.flex.decorators import hold_selection
from mgear.flex.decorators import isolate_view
from mgear.flex.decorators import set_focus
from mgear.flex.decorators import show_view
from mgear.flex.flex_widget import FLEX_UI_NAME
from mgear.flex.flex_widget import FlexDialog
from mgear.flex.query import get_transform_selection, get_parent
from mgear.flex.query import is_maya_batch
from mgear.flex.query import is_valid_group
from mgear.flex.update import update_rig

try:
    long
except NameError:
    # Python 3 compatibility
    long = int


class Flex(object):
    """ Flex is the mGear rig update tool

    Flex class object allows you to trigger updates on a given rig.
    You can use this object to execute the update with specific features
    """

    def __init__(self):
        super(Flex, self).__init__()

        # define properties
        self.__source_group = None
        self.__target_group = None
        self.__user_attributes = True
        self.__update_options = {"deformed": True,
                                 "transformed": True,
                                 "object_display": False,
                                 "user_attributes": True,
                                 "render_attributes": True,
                                 "component_display": False,
                                 "plugin_attributes": False,
                                 "hold_transform_values": True,
                                 "mismatched_topologies": True,
                                 }

    def __check_source_and_target_properties(self):
        """ Raises ValueError if source_group and target_group are not set
        """

        message = ("You need to provided a source and target group in order to"
                   " run the rig update.")

        # check if values have been set
        if not self.source_group or not self.target_group:
            raise ValueError(message)

        return

    def __gather_ui_options(self):
        """ Gathers all the UI execution options available in a dict

        :return: A dict with the bool statements of options gathered
        :rtype: dict

        .. important: This is a list of options that need to be gathered.
           * deformed
           * transformed
           * object_display
           * component_display
           * render_attributes
           * plugin_attributes
           * hold_transform_values
           * mismatched_topologies
        """

        # gather ui options
        ui_options = {}

        ui_options["deformed"] = self.ui.deformed_check.isChecked()
        ui_options["transformed"] = self.ui.transformed_check.isChecked()
        ui_options["user_attributes"] = (
            self.ui.user_attributes_check.isChecked())
        ui_options["object_display"] = (
            self.ui.display_attributes_check.isChecked())
        ui_options["component_display"] = (
            self.ui.component_attributes_check.isChecked())
        ui_options["render_attributes"] = (
            self.ui.render_attributes_check.isChecked())
        ui_options["plugin_attributes"] = (
            self.ui.plugin_attributes_check.isChecked())
        ui_options["hold_transform_values"] = (
            self.ui.transformed_hold_check.isChecked())
        ui_options["mismatched_topologies"] = (
            self.ui.mismatched_topologies.isChecked())

        return ui_options

    @staticmethod
    def __kill_analyze_instance():
        """ Kills flex analyze ui instance
        """

        # finds Flex widget
        widget = OpenMayaUI.MQtUtil.findWindow(FLEX_UI_NAME)

        if not widget:
            return

        # go through flex widgets to find analyze widget
        qt_object = QtCompat.wrapInstance(long(widget), QtWidgets.QDialog)
        for child in qt_object.children():
            if child.objectName() == FLEX_ANALYZE_NAME:
                Flex.__kill_widget(child)

    @staticmethod
    def __kill_flex_instance():
        """ Kills flex ui instance
        """

        # finds Flex widget
        widget = OpenMayaUI.MQtUtil.findWindow(FLEX_UI_NAME)

        if not widget:
            return

        qt_object = QtCompat.wrapInstance(long(widget), QtWidgets.QDialog)
        Flex.__kill_widget(qt_object)

    @staticmethod
    def __kill_widget(widget_object):
        """ Kills the given qt widget object

        :param widget_object: The qt widget object to destroy
        :type widget_object: QtWidget.QtWidget
        """

        widget_object.setParent(None)
        widget_object.deleteLater()
        del(widget_object)

    def __property_check(self, value):
        """ Flex properties check

        :param value: value to check
        :type value: type
        """

        if value and not is_valid_group(value):
            raise ValueError("The given group ({}) is not a valid Maya "
                             "transform node or it simply doesn't exist on "
                             "your current Maya session".format(value))

        if self.source_group == self.target_group and not value:
            raise ValueError("The given source and target objects are the same"
                             ". Nothing to update!")

    def __repr__(self):
        return "{}".format(self.__class__)

    @staticmethod
    def __select_object(widget):
        """ Selects the corresponding transform for the selected widget shape

        :param widget: the table widget
        :type widget: QtWidgets.QtQTableWidget
        """

        selected_idx = widget.selectedIndexes()

        cmds.select(clear=True)
        for idx in selected_idx:
            object_name = widget.itemFromIndex(idx).text()
            cmds.select(get_parent(object_name), add=True)

    def __set_button_edits(self, widget):
        """ "Sets Flex source and target groups properties

        When triggering the push buttons Flex properties gets updated.

        :param widget: the widget been edited
        :type widget: PySide2.QtWidgets
        """

        widget_name = widget.objectName().split("_")[0]
        value = get_transform_selection()

        if widget_name == "source":
            self.source_group = value
            self.ui.source_text.setText(value)
        else:
            self.target_group = value
            self.ui.target_text.setText(value)

    def __set_text_edits(self, widget):
        """ Updates Flex source and target groups properties

        When typing inside the text widget the properties gets updated.

        :param widget: the widget been edited
        :type widget: PySide2.QtWidgets
        """

        widget_name = widget.objectName().split("_")[0]

        if widget_name == "source":
            if not self.ui.source_text.text():
                self.source_group = None
                return
            self.source_group = self.ui.source_text.text()
            return

        else:
            if not self.ui.target_text.text():
                self.target_group = None
                return
            self.target_group = self.ui.target_text.text()
            return

    def __setup_ui_signals(self):
        """ Setups how the UI interacts with the API and the tool

        Connects the widget signals to Flex methods
        """

        # source button
        self.ui.add_source_button.clicked.connect(
            lambda: self.__set_button_edits(self.ui.add_source_button))
        # target button
        self.ui.add_target_button.clicked.connect(
            lambda: self.__set_button_edits(self.ui.add_target_button))

        # source text edit
        self.ui.source_text.returnPressed.connect(
            lambda: self.__set_text_edits(self.ui.source_text))
        # target text edit
        self.ui.target_text.returnPressed.connect(
            lambda: self.__set_text_edits(self.ui.target_text))

        # analyse button
        self.ui.analyse_button.clicked.connect(self.show_analyse)

        # run button
        self.ui.run_button.clicked.connect(self.update_rig)

    def __str__(self):
        return "mGear: Flex == > An awesome rig update tool"

    def __update_ui(self):
        """ Updates the ui content
        """

        try:
            if self.ui.isVisible():
                self.ui.source_text.setText(self.__source_group)
                self.ui.target_text.setText(self.__target_group)

        except AttributeError:
            return

    @staticmethod
    def __warp_maya_window():
        """ Returns a qt widget warp of the Maya window

        :return: Maya window on a qt widget. Returns None if Maya is on batch
        :rtype: PySide2.QtWidgets or None
        """

        if not is_maya_batch:
            return None

        # gets Maya main window object
        maya_window = OpenMayaUI.MQtUtil.mainWindow()
        return QtCompat.wrapInstance(long(maya_window), QtWidgets.QMainWindow)

    def analyze_groups(self, update_ui=False):
        """ Scans the shapes inside the source and target group

        This function will query each source and corresponding target shape
        checking if their type, vertices count and bounding box matches

        :param update_ui: whether or not the analyze ui should be updated
        :type: bool
        """

        # checks if groups are set
        self.__check_source_and_target_properties()

        # check if values are correct
        self.__property_check(None)

        # runs analyze
        matching_shapes, mismatched_types, mismatched_count, \
            mismatched_bbox = analyze_groups(source=self.source_group,
                                             target=self.target_group)

        if update_ui:
            [self.analyze_ui.add_item(shape, matching_shapes[shape],
                                      mismatched_types, mismatched_count,
                                      mismatched_bbox)
             for shape in matching_shapes]

    @set_focus
    def launch(self):
        """ Displays the user interface
        """

        # if maya is batch return
        if is_maya_batch():
            return

        # kill previous Flex ui instances
        self.__kill_flex_instance()

        # initialise Flex user interface
        self.ui = FlexDialog(self.__warp_maya_window())

        # connect user interface signals
        self.__setup_ui_signals()

        # displays ui
        self.ui.show()
        self.__update_ui()

    @set_focus
    def show_analyse(self):
        """ Runs a scan of the source and target shapes
        """

        # if maya is batch return
        if is_maya_batch():
            return

        # checks if groups are set
        self.__check_source_and_target_properties()

        # kill previous analyze widgets
        self.__kill_analyze_instance()

        # initialise analyze ui and displays it
        self.analyze_ui = FlexAnalyzeDialog(self.ui)

        # hook signal
        self.analyze_ui.table_widget.itemSelectionChanged.connect(
            lambda: self.__select_object(self.analyze_ui.table_widget))
        self.analyze_ui.show()

        # analyse the groups
        self.analyze_groups(update_ui=True)

    @property
    def source_group(self):
        """ Flex source group name (property)
        """

        return self.__source_group

    @source_group.setter
    def source_group(self, value):
        """ Setter for the source_group property

        :param value: Maya transform node name containing all the source shapes
        :type value: str
        """

        # check if values are correct
        self.__property_check(value)

        # set value
        self.__source_group = value

        # ui update
        self.__update_ui()

    @property
    def target_group(self):
        """ Flex target group name (property)
        """

        return self.__target_group

    @target_group.setter
    def target_group(self, value):
        """ Setter for the target_group property

        :param value: Maya transform node name containing all the target shapes
        :type value: str
        """

        # check if values are correct
        self.__property_check(value)

        # set value
        self.__target_group = value

        # ui update
        self.__update_ui()

    @property
    def update_options(self):
        """ Flex update options (property)

        .. note:: This are the default update options
                  {
                   "deformed": True,
                   "transformed": True,
                   "object_display": False,
                   "user_attributes": True,
                   "render_attributes": True,
                   "component_display": False,
                   "plugin_attributes": False,
                   "hold_transform_values": True,
                  }
        """

        return self.__update_options

    @show_view
    @finished_running
    @hold_selection
    def update_rig(self, run_options=None):
        """ Launches the rig update process

        :param analytic: Update rig runs in analytic mode
        :type analytic: bool

        :param run_options: Options that will be used during the rig update
        :type run_options: dict
        """

        # checks if groups are set
        self.__check_source_and_target_properties()

        # check if values are correct
        self.__property_check(None)

        if not run_options:
            try:
                run_options = self.__gather_ui_options()
            except AttributeError:
                run_options = self.update_options

        # triggers the update
        try:
            update_rig(source=self.source_group, target=self.target_group,
                       options=run_options)
        except Exception as error:
            logger.critical("-" * 90)
            logger.critical("FLEX RAN WITH ERROR(S). Please contact mGear's "
                            "developers.\n".format(error), exc_info=True)
            logger.critical("-" * 90)
            return
