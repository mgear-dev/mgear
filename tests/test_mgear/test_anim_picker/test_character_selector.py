"""Anim Picker character selector: narrow windows.

The option buttons wrap to new rows and the picture hides, so the character
selector doesn't set a wide minimum width for the picker window.
"""

import pytest


@pytest.fixture
def picker_window(qt_app, tmp_path):
    """Yield a shown picker window in anim mode, with temp settings."""
    from maya import cmds

    from mgear.vendor.Qt import QtCore

    from mgear.anim_picker import main_window
    from mgear.anim_picker.handlers import __EDIT_MODE__

    previous = QtCore.QSettings.defaultFormat()
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    QtCore.QSettings.setPath(
        QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, str(tmp_path)
    )
    cmds.file(new=True, force=True)
    win = main_window.MainDockWindow(edit=False)
    win.show()
    qt_app.processEvents()
    yield win
    win._autosave_timer.stop()
    win.cb_manager.removeAllManagedCB()
    win.close()
    win.deleteLater()
    qt_app.processEvents()
    __EDIT_MODE__.set_init(False)
    QtCore.QSettings.setDefaultFormat(previous)


def _resize(qt_app, win, width):
    win.resize(width, win.height())
    qt_app.processEvents()


def _group_rows(win):
    """Return the row tops of the option groups."""
    layout = win.char_btns_layout
    return sorted({layout.itemAt(i).widget().y() for i in range(layout.count())})


def test_narrow_window_wraps_the_options(qt_app, picker_window):
    from mgear.core import pyqt

    win = picker_window
    _resize(qt_app, win, pyqt.dpi_scale(900))
    assert len(_group_rows(win)) == 1
    assert win.pic_widget.isVisible()

    _resize(qt_app, win, pyqt.dpi_scale(300))
    assert win.width() <= pyqt.dpi_scale(300)
    # the option groups moved to new rows and stay inside the selector
    assert len(_group_rows(win)) > 1
    area = win.char_select_widget.width()
    for button in (win.checkbox, win.char_refresh_btn, win.grid_cols_sb):
        assert button.isVisible()
        right = button.mapTo(win.char_select_widget, button.rect().topRight())
        assert right.x() <= area
    assert not win.pic_widget.isVisible()

    _resize(qt_app, win, pyqt.dpi_scale(900))
    assert len(_group_rows(win)) == 1
    assert win.pic_widget.isVisible()


def test_window_opens_narrow(qt_app, picker_window):
    """One resize right after the window opens reaches the narrow width:
    the picture doesn't count in the minimum width."""
    from mgear.core import pyqt

    win = picker_window
    _resize(qt_app, win, pyqt.dpi_scale(200))
    assert win.width() <= pyqt.dpi_scale(300)


def test_long_character_names_dont_widen_the_window(qt_app, picker_window):
    from mgear.core import pyqt

    win = picker_window
    combo = win.char_selector_cb
    combo.addItem("girl_Outfit_A_film_with_a_long_namespace:PICKER_DATA_BIPED")
    assert combo.minimumSizeHint().width() < pyqt.dpi_scale(250)


def test_picture_fits_one_row_of_options(qt_app, picker_window):
    """The picture is as tall as the combo box and one row of options, and
    the option groups share the row height, so they line up."""
    from mgear.core import pyqt

    win = picker_window
    _resize(qt_app, win, pyqt.dpi_scale(900))
    column = win.char_select_widget.column.geometry()
    picture = win.pic_widget
    assert picture.width() == picture.height() == column.height()
    layout = win.char_btns_layout
    groups = [layout.itemAt(i).widget() for i in range(layout.count())]
    assert len({group.height() for group in groups}) == 1
