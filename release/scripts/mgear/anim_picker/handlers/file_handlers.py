from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import os
import json
import functools

from mgear.core import pyqt
from mgear.core import string
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic

ANIM_PICKER_VAR = "ANIM_PICKER_PATH"

# i/o -------------------------------------------------------------------------


def _importData(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)


def _exportData(data, file_path):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)


def replace_token_with_path(file_path):
    """
    Replaces the token [ANIM_PICKER_PATH] in the string with the value of
    the environment variable ANIM_PICKER_PATH.

    Args:
        file_path (str): String containing the token to be replaced.

    Returns:
        str: The string with the token replaced by the full path.

    """
    env_path = os.getenv(ANIM_PICKER_VAR)

    if not env_path:
        return file_path

    return file_path.replace(
        f"[{ANIM_PICKER_VAR}]", string.normalize_path(env_path)
    )


def replace_path_with_token(file_path):
    """
    Replaces the full path in the string with the token [ANIM_PICKER_PATH],
    if the path starts with the value of the environment variable
    ANIM_PICKER_PATH.

    Args:
        file_path (str): String containing the full path to be replaced.

    Returns:
        str: The string with the full path replaced by the token.

    """
    env_path = os.getenv(ANIM_PICKER_VAR)

    if env_path and file_path.startswith(env_path):
        return file_path.replace(
            string.normalize_path(env_path), f"[{ANIM_PICKER_VAR}]"
        )

    return file_path


def read_data_file(file_path):
    """Read data from file"""
    file_path = replace_token_with_path(file_path)
    msg = "{} does not seem to be a file".format(file_path)
    assert os.path.isfile(file_path), msg
    pkr_data = _importData(file_path) or {}
    return pkr_data


def write_data_file(file_path, data={}, force=False):
    """Write data to file

    # kwargs:
    file_path: the file path to write to
    data: the data to write
    f (bool): force write mode, if false, will ask for confirmation when
    overwriting existing files
    """
    file_path = replace_token_with_path(file_path)

    # Ask for confirmation on existing file
    if os.path.exists(file_path) and not force:
        decision = basic.promptAcceptance(
            pyqt.maya_main_window(),
            "File already exists! Overwrite?",
            "YOU SURE?",
        )
        if decision in [
            QtWidgets.QMessageBox.Discard,
            QtWidgets.QMessageBox.Cancel,
        ]:
            return

    # write file
    _exportData(data, file_path)
