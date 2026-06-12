import os
import sys
import shutil
import re
import traceback
from datetime import datetime

try:
    from maya.app.startup import basic
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        from shiboken2 import wrapInstance
    except ModuleNotFoundError:
        from PySide6 import QtWidgets, QtCore, QtGui
        from shiboken6 import wrapInstance
    import maya.OpenMayaUI as OpenMayaUI
    import maya.cmds as cmds
    import maya.api.OpenMaya as om
    is_maya = True

except ImportError():
    is_maya = False

# -- constants
TITLE = "Install mGear"
VERSION = 1.4
MGEAR_MOD_PATH = "MGEAR_MODULE_PATH"
MAYA_MOD_PATH = "MAYA_MODULE_PATH"
PLUGINS = ["mgear_solvers.mll", "mGearWeightDriver.mll"]
DEFAULT_ITEMS = ["platforms", "mGear.mod", "scripts", "icons"]
CURRENT_FOLDER = os.path.dirname(__file__)


def onMayaDroppedPythonFile(*args, **kwargs):
    """
    This function is only supported since Maya 2017 Update 3.
    Maya requires this in order to successfully execute.
    """
    pass


def maya_main_window():
    """
    Return the Maya main window widget as a Python object.
    """
    main_window_ptr = OpenMayaUI.MQtUtil.mainWindow()

    if sys.version_info.major >= 3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class InstallUI(QtWidgets.QDialog):

    def __init__(self, parent=maya_main_window()):
        super(InstallUI, self).__init__(parent)

        self.setWindowTitle(TITLE)
        self.setFixedSize(550, 580)
        self.setWindowFlags(QtCore.Qt.WindowType.Window)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        """Creation of all widgets goes under this section."""
        self.create_title_label()

        self.info_label = QtWidgets.QLabel(
            "Make sure to SAVE your scene before continuing.")
        self.install_label = QtWidgets.QLabel("Install Path:")
        self.install_info_label = QtWidgets.QLabel(
            "The path where all the files will be installed.")
        self.install_info_label.setDisabled(True)

        self.install_path_line_edit = QtWidgets.QLineEdit()
        self.install_path_button = QtWidgets.QPushButton("...")

        self.install_button = QtWidgets.QPushButton("Install")
        self.uninstall_button = QtWidgets.QPushButton("Uninstall")
        self.help_button = QtWidgets.QPushButton("Help")
        self.help_button.setMaximumWidth(80)

        self.logging_widget = QtWidgets.QPlainTextEdit()
        self.logging_widget.setReadOnly(True)
        self.logging_widget.setMaximumHeight(320)

    def create_layout(self):
        """Layout of all widgets goes under this section."""

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        install_group_layout = QtWidgets.QGroupBox("Paths:")
        progress_group_layout = QtWidgets.QGroupBox("Progress:")

        install_layout = QtWidgets.QGridLayout()
        install_layout.addWidget(self.install_label, 1, 0)
        install_layout.addWidget(self.install_path_line_edit, 1, 1)
        install_layout.addWidget(self.install_path_button, 1, 2)
        install_layout.addWidget(self.install_info_label, 2, 1)

        install_group_layout.setLayout(install_layout)

        progress_layout = QtWidgets.QVBoxLayout()
        progress_layout.addWidget(self.logging_widget)
        progress_layout.setContentsMargins(6, 6, 6, 6)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.help_button)
        button_layout.setSpacing(4)

        progress_group_layout.setLayout(progress_layout)

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(install_group_layout)
        main_layout.addWidget(progress_group_layout)
        main_layout.addLayout(button_layout)
        main_layout.setSpacing(3)

    def create_connections(self):
        """Connection setup of all widgets goes under this section."""

        self.install_button.clicked.connect(self.on_install_button_clicked)
        self.install_path_button.clicked.connect(
            self.on_install_path_button_clicked)
        self.uninstall_button.clicked.connect(self.on_uninstall_button_clicked)
        self.help_button.clicked.connect(self.on_help_button_clicked)

    def on_install_button_clicked(self):
        """Installation button command."""

        self.start_install()

    def create_title_label(self):
        """Creation of the main logo displayed on the installation window. """

        # -- path to mgear logo
        image_path = os.path.normpath(os.path.join(CURRENT_FOLDER,
                                                   "release",
                                                   "icons",
                                                   "mgear_logo.png"))

        image = QtGui.QImage(image_path)
        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        self.title_label = QtWidgets.QLabel("")
        self.title_label.setPixmap(pixmap)

    def on_install_path_button_clicked(self):
        """Installation path button command."""

        self.show_file_dialog_window(self.install_path_line_edit)

    def on_help_button_clicked(self):
        """Help button command."""

        QtGui.QDesktopServices.openUrl(QtCore.QUrl(
            "http://forum.mgear-framework.com/t/official-installation-support-help"))

    def on_uninstall_button_clicked(self):
        """Uninstall button command."""

        # -- folder of all the contents of mgear resides
        self.start_uninstall(self.get_line_edit_text(
            self.install_path_line_edit))

    def start_install(self):
        """Main install command to run through."""

        # -- folder of all the contents of mgear resides
        mgear_folder = os.path.normpath(
            os.path.join(CURRENT_FOLDER, "release"))

        # -- flush the undo que in case there is anything that might disrupt
        # -- the install
        cmds.flushUndo()

        # -- create a fresh scene in case there are any solvers still
        # -- loaded in memory
        cmds.file(new=True, force=True)

        install_path = self.get_line_edit_text(self.install_path_line_edit)
        mgear_install_path = os.path.join(install_path, "mgear")
        self.update_logging_widget("{0}".format(mgear_install_path))

        # -- in case there is a left over folder
        if os.path.exists(mgear_install_path):
            self.remove_directory(mgear_install_path)

        # -- look in install directory for files of same name
        # -- construct path names
        full_path = [os.path.join(install_path, x) for x in DEFAULT_ITEMS]

        # -- files of the same name
        found = self.files_exist(full_path)
        if found:
            message = "mGear files already exist in the install location.\n"
            message += "Would you like to overwrite them?"
            message_box = QtWidgets.QMessageBox.warning(
                self,
                "Delete Existing Files",
                message,
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Close)

            # -- don't save was clicked
            if message_box == QtWidgets.QMessageBox.Close:
                self.update_logging_widget("Installation Cancelled.")
                return

        # -- iterate over folders and remove them
        self.start_uninstall(install_path)
        # -- let's copy the folder over
        shutil.copytree(mgear_folder, mgear_install_path)

        for item in os.listdir(mgear_folder):
            # -- move the folder to the install path
            try:
                shutil.move(os.path.join(
                    install_path, "mgear", item), install_path)
                self.update_logging_widget("Moved: {0}".format(
                    os.path.join(install_path, item)))
            except OSError as err:
                self.update_logging_widget("Warning: Failed to move {0}".format(
                    os.path.join(install_path, item)))

        self.remove_directory(mgear_install_path)

        # -- we look for the Maya.env file and write the path to it
        env_file = os.path.normpath(os.path.join(os.environ["MAYA_APP_DIR"],
                                                 cmds.about(version=True),
                                                 "Maya.env"))

        # -- figure out if custom path or standard
        if install_path != self.get_default_modules_folder():
            if os.path.exists(env_file):
                self.update_logging_widget(
                    "Found .env file: {0}".format(env_file))

            self.update_logging_widget(
                "Custom path installation: {0}".format(install_path))
            # -- check if env file has any information
            if self.get_paths_from_file(env_file):
                message = "The Maya.env file might contain important information.\n"
                message += "Would you like to make a backup?"
                message_box = QtWidgets.QMessageBox.warning(self,
                                                            "Make Backup File?",
                                                            message,
                                                            QtWidgets.QMessageBox.Save |
                                                            QtWidgets.QMessageBox.Discard |
                                                            QtWidgets.QMessageBox.Cancel)

                if message_box == QtWidgets.QMessageBox.Save:
                    self.make_env_backup(env_file)
                    self.update_env_file(env_file, install_path)
                elif message_box == QtWidgets.QMessageBox.Discard:
                    self.update_env_file(env_file, install_path)
                elif message_box == QtWidgets.QMessageBox.Cancel:
                    self.update_logging_widget("Installation Cancelled!")
                    return
            else:
                self.update_env_file(env_file, install_path)

            message = "Please restart Maya to complete the installation."
            QtWidgets.QMessageBox.warning(self,
                                          "Installation Complete",
                                          message,
                                          QtWidgets.QMessageBox.Close)

        else:
            # -- now let's get mgear up and running
            # -- add to the system path
            if not os.path.join(install_path, "scripts") in sys.path:
                sys.path.append(os.path.join(install_path, "scripts"))
                self.update_logging_widget("Added to PYTHONPATH: {0}".format(
                    os.path.join(install_path, "scripts")))

            # -- allows for not having to restart maya
            cmds.loadModule(scan=True)
            cmds.loadModule(allModules=True)

            # -- force load the plugins just in-case it does not happen
            failed_list = self.load_plugins()

            # -- reload user setup files
            basic.executeUserSetup()

        if len(failed_list):
            self.update_logging_widget(
                "Installation Unsuccessful, errors occurred!")
            om.MGlobal.displayWarning("Installation Incomplete")
        else:
            self.update_logging_widget("Installation Successful!")
            om.MGlobal.displayInfo("Installation Complete")

    def start_uninstall(self, destination):
        """
        Uninstall any existing folders on disk
        :param destination: folder to remove files from.
        """

        failed_list = self.unload_plugins()

        # -- iterate over folders and remove them
        for item in DEFAULT_ITEMS:
            if os.path.exists(os.path.join(destination, item)):
                # -- delete file and folders
                if os.path.isfile(os.path.join(destination, item)):
                    self.remove_file(os.path.join(destination, item))
                elif os.path.isdir(os.path.join(destination, item)):
                    self.remove_directory(os.path.join(destination, item))

        if len(failed_list):
            self.update_logging_widget(
                "Uninstall Unsuccessful, errors occurred!")
        else:
            self.update_logging_widget("Uninstalled Successfully!")

    def update_env_file(self, env_file, install_path):
        """
        Update the maya environment file with the needed paths.
        :param str env_file: path to environment file, will be created if not found.
        :param str install_path: the user specified path to install mgear.
        """

        result = self.get_paths_from_file(env_file)

        # -- if there is no information, let's add in the information we need.
        if not result:
            self.append_new_line(env_file, "{0}={1}".format(
                MGEAR_MOD_PATH, install_path))
            self.update_logging_widget(
                "The .env was empty, added {0}.".format(MGEAR_MOD_PATH))

            self.append_new_line(env_file, "{0}=%{1}%;".format(
                MAYA_MOD_PATH, MGEAR_MOD_PATH))
            self.update_logging_widget(
                "The .env was empty, added {0}.".format(MAYA_MOD_PATH))

        else:
            # -- check for mgear module path
            mgear_path = self.check_module_path(result, MGEAR_MOD_PATH)
            if not mgear_path:
                # -- we want to add the module path to beginning of file
                # -- so that we can access as variable
                self.pre_append_line(env_file, '{0}="{1}"'.format(
                    MGEAR_MOD_PATH, install_path))
                self.update_logging_widget(
                    "Added {0} to .env file.".format(MGEAR_MOD_PATH))

            # -- check if there is a maya module path present
            maya_module_path = self.check_module_path(result, MAYA_MOD_PATH)
            if not maya_module_path:
                # -- if not module path found, we add the path
                maya_module_path = "\n{0}=%{1}%;".format(
                    MAYA_MOD_PATH, MGEAR_MOD_PATH)
                self.append_new_line(env_file, maya_module_path)
                self.update_logging_widget(
                    "Added {0} to .env file.".format(MAYA_MOD_PATH))
            else:
                # -- check if mgear module path is there already
                match = re.search(r"(%{0}%)".format(
                    MGEAR_MOD_PATH), str(result))
                if not match:
                    # -- add mgear to module path
                    self.add_to_module_path(
                        env_file, result, MAYA_MOD_PATH, MGEAR_MOD_PATH)
                    self.update_logging_widget(
                        "Added {0} to .env file.".format(MGEAR_MOD_PATH))

    def make_env_backup(self, file_path):
        """
        Back the maya environment file.
        :param str file_path: path to maya envornment file.
        :return: the path to the backup file.
        :rtype: str
        """

        path, ext = file_path.split(".")
        temp_ext = "bak"
        backup_file = os.path.join("{0}.{1}".format(path, temp_ext))
        with open(file_path, "r") as read_obj, open(backup_file, "w") as write_obj:
            for line in read_obj:
                write_obj.write(line)

        self.update_logging_widget(
            "Made backup of .env file: {0}".format(backup_file))

        return backup_file

    def update_logging_widget(self, message=""):
        """
        Updates the logging field.
        :param str message: information to display.
        """

        if not len(message):
            message = " "
        lines = message if isinstance(message, list) else [message]
        for i in range(len(lines)):
            lines[i] = "{} : {}".format(self.current_time(), lines[i])
        message = "\n".join(lines)

        self.logging_widget.appendPlainText(message)
        QtCore.QCoreApplication.processEvents()

    def get_default_modules_folder(self):
        """Default modules folder to install to."""
        return os.path.normpath(os.path.join(os.environ['MAYA_APP_DIR'], "modules"))

    def inplace_change(self, filename, old_string, new_string):
        """
        Change the string the the same location (Search and Replace)
        :param str filename: path to file that we want to edit.
        :param str old_string: string to search for.
        :param str new_string: string to replace with.
        """
        with open(filename, "r") as read_obj:
            s = read_obj.read()
            if old_string not in s:
                return

        with open(filename, 'w') as write_obj:
            s = s.replace(old_string, new_string)
            write_obj.write(s)

    def pre_append_line(self, file_path, line):
        """
        Want to add a string to beginning of file.
        :param str file_path: path to add text to.
        :param str line: the string to add.
        """

        path, ext = file_path.split(".")
        temp_ext = "txt"
        new_env_file = os.path.join("{0}.{1}".format(path, temp_ext))
        with open(file_path, "r") as read_obj, open(new_env_file, "w") as write_obj:
            write_obj.write("{0}\n".format(line))
            for line in read_obj:
                write_obj.write(line)

        os.remove(file_path)
        os.rename(new_env_file, file_path)

    def append_new_line(self, file_path, line):
        """Append given text as a new line at the end of file"""
        # -- open the file in append and read mode ('a+')
        with open(file_path, "a+") as file_object:
            file_object.write("\n")
            # -- append text at the end of file
            file_object.write(line)

    def get_paths_from_file(self, file_path):
        """
        Get's the items as a list from file.
        :param str file_path: path of file to read.
        :return: strings as lists.
        :rtype: list(str)
        """

        with open(file_path, "r") as f:
            result = [line.rstrip() for line in f] or []

        return result

    def check_module_path(self, paths, check):
        """
        Check if the module path is in any of the given results.
        :param list(str) paths: paths found in the file
        :param str check: match any strings found.
        :return: path if there is a match
        :rtype: str if True, or False
        """

        for path in paths:
            # -- check if the line starts with the module path variable
            match = re.search(r"^({0})".format(check), path)
            if match:
                return path

        return False

    def add_to_module_path(self, file_path, paths, module_match, module_add):
        """
        Check for maya module path, and do a search and replace.
        :param str file_path: path to file to edit.
        :param list(str) paths: list of strings of paths to check.
        :param str module_match: name of the module string to find
        :param str module_add: name of the path to add.
        """

        old_maya_module_path = self.check_module_path(paths, module_match)
        if old_maya_module_path:
            if old_maya_module_path.endswith("="):
                maya_module_path = "{0}%{1}%".format(
                    old_maya_module_path, module_add)
            elif old_maya_module_path.endswith(";"):
                maya_module_path = "{0}%{1}%".format(
                    old_maya_module_path, module_add)
            else:
                maya_module_path = "{0};%{1}%".format(
                    old_maya_module_path, module_add)

            self.inplace_change(
                file_path, old_maya_module_path, maya_module_path)

    def files_exist(self, file_list):
        """Get all file paths that exist.
        :param list file_list: List of paths to iterate through.
        :return: All paths found
        :rtype: list
        """
        file_found = []
        for item in file_list:
            if os.path.exists(item):
                found = item
                file_found.append(found)
                self.update_logging_widget(
                    "Found existing file: {0}".format(found))

        return file_found

    def current_time(self):
        """Return the current time as a nice formatted string.
        :return: The current date and time.
        :rtype: str
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def unload_plugins(self):
        """
        Unload all of our plugins.
        :return: List of plugins that failed to load, if any
        :rtype: list
        """
        failed_list = []
        for p in PLUGINS:
            if self.is_plugin_loaded(p):
                status = self.unload_plugin(p)
                if status == True:
                    self.update_logging_widget("Unloaded '{0}' plugin".format(p))
                else:
                    self.update_logging_widget(
                        "Error: unable to unload '{0}' plugin!".format(p))
                    failed_list.append(p)

        return failed_list

    def load_plugins(self):
        """
        Load in all of our plugins if they are not already.
        :return: List of plugins that failed to load, if any
        :rtype: list
        """
        failed_list = []
        for p in PLUGINS:
            if not self.is_plugin_loaded(p):
                status = self.load_plugin(p)
                if status == True:
                    self.update_logging_widget("Loaded '{0}' plugin".format(p))
                else:
                    self.update_logging_widget(
                        "Error: unable to load '{0}' plugin!".format(p))
                    failed_list.append(p)

        return failed_list

    def unload_plugin(self, plugin_name):
        """
        Helper function to unload the specified plugins.
        :param str plugin_name: the name of the plugin to unload
        :return: True, if plugin sucessfully unloaded
        :rtype: bool
        """
        try:
            cmds.unloadPlugin(plugin_name, force=True)
            return True
        except:
            self.update_logging_widget(traceback.format_exc())
            return False

    def load_plugin(self, plugin_name):
        """
        Helper function to load the specified plugins.
        :param str plugin_name: the name of the plugin to load
        :return: True, if plugin sucessfully loaded
        :rtype: bool
        """
        try:
            cmds.loadPlugin(plugin_name)
            return True
        except:
            self.update_logging_widget(traceback.format_exc())
            return False

    def is_plugin_loaded(self, plugin_name):
        """
        Check if plugin is loaded or not.
        :param str plugin_name: the name of our plugin
        :return: True, if plugin is loaded
        :rtype: bool
        """
        return cmds.pluginInfo(plugin_name, query=True, loaded=True)

    def add_directory(self, source, destination):
        """
        Add directory
        :param str source: source folder to copy contents from
        :param str destination: destincation folder that user has given to copy to.
        :return: True, if the copy has been successful.
        :rtype: bool
        """

        try:
            shutil.copytree(source, destination)
            self.update_logging_widget(
                "Copying: {0} to: {1}".format(source, destination))
        except shutil.Error as error:
            message = "Error copying: {0} to: {1}".format(source, destination)
            self.update_logging_widget(message)
            self.update_logging_widget(str(error))
            return False
        return True

    def remove_directory(self, path):
        """Delete the folder at the given path.
        :param str path: The full path of the folder to delete.
        :return: True, if deleting was successful.
        :rtype: bool
        """
        if os.path.exists(path):
            shutil.rmtree(path)
            self.update_logging_widget("Removed: {0}".format(path))
        else:
            return False
        return True

    def remove_file(self, file_name):
        """Delete the file at the given path.
        :param str file_name: The full path of the file to delete.
        :return: True, if deleting was successful.
        :rtype: bool
        """
        try:
            os.remove(file_name)
            self.update_logging_widget("Deleting: {0}".format(file_name))
        except:
            message = "Error deleting file: {0}".format(file_name)
            self.update_logging_widget(message)
            return False
        return True

    def set_line_edit_text(self, line_edit, text):
        """
        Set text to the given line edit.
        :param QLineEdit line_edit: line edit item.
        :param str text: text to which to set to the line edit item
        """

        line_edit.setText(text)

    def get_line_edit_text(self, line_edit):
        """
        Get current line edit text.
        :param QLineEdit line_edit: line edit item.
        :return: Current text from line edit
        :rtype: str
        """

        return line_edit.text()

    def show_file_dialog_window(self, line_edit):
        """
        File path that the user has chosen.
        """
        file_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select an install directory",
            os.path.normpath(os.environ['MAYA_APP_DIR']))
        if file_path:
            line_edit.setText(file_path)

    def showEvent(self, event):
        """Overwrite of the default showEvent of current widget."""
        super(InstallUI, self).showEvent(event)

        self.set_line_edit_text(
            self.install_path_line_edit, self.get_default_modules_folder())

    def closeEvent(self, event):
        """Overwrite of the default showEvent of current widget."""
        if isinstance(self, InstallUI):
            super(InstallUI, self).closeEvent(event)

        self.close()


def _dropped_install():

    installer_window = InstallUI()
    installer_window.show()


if is_maya:
    _dropped_install()
