from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.core import pyqt
from functools import partial

import mgear.pymaya as pm
import maya.cmds as cmds

from mgear.core import transform
from mgear.core import curve
from mgear.core import attribute
from mgear.core import utils
from mgear.cfxbits.xgenboost import xgen_handler


_DRAW_GUIDE_CTX = "Draw_guide_context"
_MOVE_GUIDE_CTX = "Move_guide_context"
_DUPLICATE_GUIDE_CTX = "Duplicate_guide_context"
SCALP = None
CRV_GUIDE = None
CRV_GUIDES_LIST = None
DESCRIPTION = None
COLOR = [1, .5, 0]

# create hair guide rig
# the transform of the curve is the position of the first point
# and should be blocking this point
# guide_modifier = is the guide modifier in the xgen igs to add the curve
# as guide


def create_guide_rig(name,
                     pos,
                     scalp,
                     sections,
                     length,
                     thickness):
    global COLOR
    if pos:
        face = transform.getClosestPolygonFromTransform(
            pm.PyNode(scalp), pos)[0]
        rot = transform.get_orientation_from_polygon(face)

        # section distance
        sd = length / (sections - 1)
        points = []
        x = 0.0
        for s in range(sections):
            p = [x, 0, 0]
            points.append(p)
            x += sd
        # create curve
        crv = curve.addCurve(None, name, points)
        crv.rotate.set(rot)
        crv.translate.set(pos)

        # lock first point in the curve
        curve.lock_first_point(crv)

        # set color and thickness
        curve.set_color(crv, COLOR)
        curve.set_thickness(crv, thickness)

        return crv


def create_guide_rig_from_ui(pos, ui):
    global SCALP
    global CRV_GUIDE
    global DESCRIPTION
    global CRV_GUIDES_LIST

    # get the date from the ui

    name = ui.xgen_description_lineEdit.text()
    indx = 0  # need to get the guide index based on the name of the area
    full_name = name.replace("_Shape", "") + "_crvGuide_" + str(indx)
    sections = ui.sections_spinBox.value()
    length = ui.length_doubleSpinBox.value()
    thickness = ui.thickness_spinBox.value()

    CRV_GUIDES_LIST = xgen_handler.get_connected_curve_guides(DESCRIPTION)

    CRV_GUIDE = create_guide_rig(full_name,
                                 pos,
                                 SCALP,
                                 sections,
                                 length,
                                 thickness)

    # set lock length status
    lock = ui.lock_length_checkBox.isChecked()
    curve.lock_length(CRV_GUIDE, lock)

    return CRV_GUIDE

# -----------------------------------------------------------------------------
# Modify functions
# -----------------------------------------------------------------------------


def refresh_guide_rig_from_ui(pos, ui):
    global SCALP
    global CRV_GUIDE

    face = transform.getClosestPolygonFromTransform(
        SCALP, pos)[0]
    rot = transform.get_orientation_from_polygon(face)
    CRV_GUIDE.rotate.set(rot)
    CRV_GUIDE.translate.set(pos)
    average_crv_from_ui(ui)
    cmds.refresh(cv=True, f=True)


def average_crv_from_ui(ui):
    """Will average the curve shape, scl and rotation based on the ui options

    Args:
        ui (pyQt obj): The ui with the option
    """
    global CRV_GUIDE
    global CRV_GUIDES_LIST
    avg_shape = ui.interpolated_shape_checkBox.isChecked()
    avg_scl = ui.interpolated_scale_checkBox.isChecked()
    avg_rot = ui.interpolated_rotate_checkBox.isChecked()
    if avg_shape or avg_scl or avg_rot:
        average = ui.interpolated_max_spinBox.value()
        curve.average_curve(
            CRV_GUIDE, CRV_GUIDES_LIST, average, avg_shape, avg_scl, avg_rot)


def duplicate(ui, dup_guide=None):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    if not dup_guide:
        dup_guide = pm.selected()
    if dup_guide:
        dup_guide = dup_guide[0]
    else:
        pm.displayWarning("Nothing selected to duplicate")
        return

    if dup_guide in xgen_handler.get_connected_curve_guides(description):
        # duplicate
        new_crv = pm.duplicate(dup_guide)[0]

        # config new crv.
        curve.set_thickness(new_crv, ui.thickness_spinBox.value())
        curve.lock_first_point(new_crv)

        xgen_handler.connect_curve_to_xgen_guide(new_crv, description)

        return new_crv

    else:
        pm.displayWarning(
            "Object {0} is not crv guide for {1} and can't be"
            " duplicated".format(dup_guide.name(), name))


@utils.one_undo
def duplicate_sym(ui, dup_guides=None, skip_all=False, re_sym_all=False):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    crv_guides = xgen_handler.get_connected_curve_guides(description)
    new_guides = []
    if not dup_guides:
        dup_guides = pm.selected()
    for crv in dup_guides:
        if crv in crv_guides:
            if not crv.hasAttr("sym_guide"):
                crv.addAttr("sym_guide", at='message', multi=False)
            else:
                sym_cnx = crv.sym_guide.listConnections()
                if sym_cnx:
                    if skip_all:
                        continue
                    if re_sym_all:
                        pm.displayInfo(
                            "Re symmetry guide {}".format(crv.name()))
                        pm.delete(sym_cnx)
                    else:
                        dup_option = show_dup_sym_options(crv.name())
                        if dup_option == 1:  # skip all
                            skip_all = True
                            continue
                        elif dup_option == 2:  # re sym
                            pm.displayInfo(
                                "Re symmetry guide {}".format(crv.name()))
                            pm.delete(sym_cnx)
                        elif dup_option == 3:  # re sym all
                            re_sym_all = True
                            pm.displayInfo(
                                "Re symmetry guide {}".format(crv.name()))
                            pm.delete(sym_cnx)
                        elif dup_option == 4:  # cancel
                            break
                        else:  # skip. Also if close the menu will skip
                            continue

            # duplicate
            new_crv = pm.duplicate(crv)[0]
            # transform
            t = crv.getTransformation()
            t = transform.getSymmetricalTransform(t)
            new_crv.setTransformation(t)
            # create message connection
            pm.connectAttr(new_crv.sym_guide, crv.sym_guide, f=True)
            pm.connectAttr(crv.sym_guide, new_crv.sym_guide, f=True)
            # config new crv.
            curve.set_thickness(new_crv, ui.thickness_spinBox.value())
            curve.lock_first_point(new_crv)
            # connect
            xgen_handler.connect_curve_to_xgen_guide(new_crv, description)
            new_guides.append(new_crv)
        else:
            pm.displayWarning(
                "Object {0} is not crv guide for {1} and can't be"
                " duplicated".format(crv.name(), name))
    if new_guides:
        pm.select(new_guides)
    return new_guides


def toggle_hair_visibility(ui):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if description:
        attribute.toggle_bool_attr(description.visibility)


def toggle_guides_visibility(ui):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if description:
        for crv in xgen_handler.get_connected_curve_guides(description):
            attribute.toggle_bool_attr(crv.visibility)


def toggle_scalp_visibility(ui):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if description:
        scalp = xgen_handler.get_scalp(description)
        attribute.toggle_bool_attr(scalp.visibility)


def lock_length(ui):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    lock = ui.lock_length_checkBox.isChecked()
    if description:
        try:
            for crv in xgen_handler.get_connected_curve_guides(description):
                curve.lock_length(crv, lock)
        except TypeError:
            pass

# -----------------------------------------------------------------------------
# Context functions
# -----------------------------------------------------------------------------


def draw_guide_rig(ui):
    global SCALP
    global CRV_GUIDE

    mpx, mpy, _ = cmds.draggerContext(_DRAW_GUIDE_CTX,
                                      query=True,
                                      anchorPoint=True)

    pos = transform.get_raycast_translation_from_mouse_click(
        SCALP.name(), mpx, mpy)
    # if the raycast dont intersect with the scalp don't continue calculation
    if pos:
        create_guide_rig_from_ui(pos, ui)
        average_crv_from_ui(ui)
        cmds.refresh(cv=True, f=True)
    else:
        CRV_GUIDE = None


# draw the guide rig on top os the scalp and align with the scalp normal
def drag_guide_rig(ui, context):
    global CRV_GUIDE
    global SCALP
    mpx, mpy, _ = cmds.draggerContext(context,
                                      query=True,
                                      dragPoint=True)

    pos = transform.get_raycast_translation_from_mouse_click(
        SCALP.name(), mpx, mpy)
    # if the raycast dont intersect with the scalp don't continue calculation
    if pos and CRV_GUIDE:
        refresh_guide_rig_from_ui(pos, ui)


def release_guide_rig():
    global CRV_GUIDE
    global SCALP
    global DESCRIPTION
    if CRV_GUIDE:
        # connect to xgen modifier node
        xgen_handler.connect_curve_to_xgen_guide(CRV_GUIDE, DESCRIPTION)
        pm.select(CRV_GUIDE)


def move_guide_rig(ui, crv_guide=None, context=_MOVE_GUIDE_CTX):
    global SCALP
    global DESCRIPTION
    global CRV_GUIDE
    global CRV_GUIDES_LIST

    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    crv_guides = xgen_handler.get_connected_curve_guides(description)

    if not crv_guide:
        crv_guide = pm.selected()
    if crv_guide:
        crv_guide = crv_guide[0]
    if crv_guide not in crv_guides:
        return

    CRV_GUIDE = crv_guide

    # diconnect curve
    xgen_handler.disconnect_curve_from_xgen_guide(crv_guide)

    # list the curve guides after diconnecting the one that we are moving
    CRV_GUIDES_LIST = xgen_handler.get_connected_curve_guides(DESCRIPTION)

    mpx, mpy, _ = cmds.draggerContext(context,
                                      query=True,
                                      anchorPoint=True)

    pos = transform.get_raycast_translation_from_mouse_click(
        SCALP.name(), mpx, mpy)
    # if the raycast dont intersect with the scalp don't continue calculation
    if pos:
        refresh_guide_rig_from_ui(pos, ui)


def duplicate_guide_rig(ui, dup_guide=None):
    global CRV_GUIDE
    # set CRV_GUIDE to none here, it will set it on move_guide_rig if the
    # curve is duplicated correctly
    CRV_GUIDE = None
    crv = duplicate(ui, dup_guide=dup_guide)
    if crv:
        pm.select(crv)
        move_guide_rig(ui, crv_guide=None, context=_DUPLICATE_GUIDE_CTX)


def guide_set_sections(ui, crvs=None):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    if crvs:
        if not isinstance(crvs, list):
            crvs = [crvs]
    else:
        crvs = pm.selected()
    # filter crvs
    crvs = xgen_handler.filter_curve_guides(crvs, description)
    sections = ui.sections_spinBox.value()
    # disconnect crv from  guide
    xgen_handler.disconnect_curve_from_xgen_guide(crvs)

    # change sections
    curve.rebuild_curve(crvs, sections - 2)

    # connect again
    xgen_handler.connect_curve_to_xgen_guide(crvs, description)

    # re-select
    pm.select(crvs)


def guide_set_color_thickness(ui, color=None, thickness=False, crvs=None):
    global COLOR
    if color:
        COLOR = color
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    if crvs:
        if not isinstance(crvs, list):
            crvs = [crvs]
    else:
        crvs = pm.selected()

    crvs = xgen_handler.filter_curve_guides(crvs, description)
    for crv in crvs:
        if color:
            curve.set_color(crv, COLOR)
        if thickness:
            curve.set_thickness(crv, ui.thickness_spinBox.value())

    # re-select
    pm.select(crvs)


def smooth_deform(ui, crvs=None):
    name = ui.xgen_description_lineEdit.text()
    description = xgen_handler.get_description(name)
    if not description:
        return
    if crvs:
        if not isinstance(crvs, list):
            crvs = [crvs]
    else:
        crvs = pm.selected()

    crv_guides = xgen_handler.get_connected_curve_guides(description)
    def_curv = []
    for crv in crvs:
        if crv in crv_guides:
            def_curv.append(crv)
    factor = 1.0 - (1.0 / ui.smooth_def_perc_spinBox.value())
    print(factor)
    curve.smooth_curve(def_curv, factor)

    # context creators -------------------------------------


def draw_guide_ctx(ui):
    global SCALP
    global DESCRIPTION
    if cmds.draggerContext(_DRAW_GUIDE_CTX, exists=True):
        cmds.deleteUI(_DRAW_GUIDE_CTX)

    name = ui.xgen_description_lineEdit.text()
    DESCRIPTION = xgen_handler.get_description(name)
    SCALP = xgen_handler.get_scalp(DESCRIPTION)

    cmds.draggerContext(
        _DRAW_GUIDE_CTX,
        pressCommand=partial(draw_guide_rig, ui),
        dragCommand=partial(drag_guide_rig, ui, _DRAW_GUIDE_CTX),
        releaseCommand=release_guide_rig,
        name=_DRAW_GUIDE_CTX,
        cursor='crossHair',
        undoMode='step')
    cmds.setToolTo(_DRAW_GUIDE_CTX)


def move_guide_ctx(ui):
    global SCALP
    global DESCRIPTION
    if cmds.draggerContext(_MOVE_GUIDE_CTX, exists=True):
        cmds.deleteUI(_MOVE_GUIDE_CTX)

    name = ui.xgen_description_lineEdit.text()
    if not name:
        pm.displayWarning("No Xgen IGS description selected")
        return

    if not pm.selected():
        pm.displayWarning("Nothing selected to move")
        return
    DESCRIPTION = xgen_handler.get_description(name)
    SCALP = xgen_handler.get_scalp(DESCRIPTION)

    cmds.draggerContext(
        _MOVE_GUIDE_CTX,
        pressCommand=partial(move_guide_rig, ui),
        dragCommand=partial(drag_guide_rig, ui, _MOVE_GUIDE_CTX),
        releaseCommand=release_guide_rig,
        name=_MOVE_GUIDE_CTX,
        cursor='crossHair',
        undoMode='step')
    cmds.setToolTo(_MOVE_GUIDE_CTX)


def duplicate_guide_ctx(ui):
    global SCALP
    global DESCRIPTION
    if cmds.draggerContext(_DUPLICATE_GUIDE_CTX, exists=True):
        cmds.deleteUI(_DUPLICATE_GUIDE_CTX)

    name = ui.xgen_description_lineEdit.text()
    if not name:
        pm.displayWarning("No Xgen IGS description selected")
        return

    if not pm.selected():
        pm.displayWarning("Nothing selected to duplicate")
        return

    DESCRIPTION = xgen_handler.get_description(name)
    SCALP = xgen_handler.get_scalp(DESCRIPTION)

    cmds.draggerContext(
        _DUPLICATE_GUIDE_CTX,
        pressCommand=partial(duplicate_guide_rig, ui),
        dragCommand=partial(drag_guide_rig, ui, _DUPLICATE_GUIDE_CTX),
        releaseCommand=release_guide_rig,
        name=_DUPLICATE_GUIDE_CTX,
        cursor='crossHair',
        undoMode='step')
    cmds.setToolTo(_DUPLICATE_GUIDE_CTX)


# -----------------------------------------------------------------------------
# option UI
# -----------------------------------------------------------------------------

# Duplicate symmetry options dialog


class DuplicateSymOptions(QtWidgets.QDialog):

    def __init__(self, guide_name="", parent=pyqt.maya_main_window()):
        super(DuplicateSymOptions, self).__init__(parent)

        self.setWindowTitle("Duplicate Symmetrical Options")
        self.setWindowFlags(self.windowFlags()
                            ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.guide_name = guide_name

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.option = 0  # cancel

    def create_widgets(self):
        self.skip_btn = QtWidgets.QPushButton("Skip")
        self.skip_all_btn = QtWidgets.QPushButton("Skip All")
        self.re_sym_btn = QtWidgets.QPushButton("Re Sym")
        self.re_sym_all_btn = QtWidgets.QPushButton("Re Sym All")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):

        wdg_layout = QtWidgets.QHBoxLayout()
        wdg_layout.addWidget(QtWidgets.QLabel(
            "Duplicate symmetry: {}".format(self.guide_name)))

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.skip_btn)
        btn_layout.addWidget(self.skip_all_btn)
        btn_layout.addWidget(self.re_sym_btn)
        btn_layout.addWidget(self.re_sym_all_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(wdg_layout)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.skip_btn.clicked.connect(self.skip_btn_slot)
        self.skip_all_btn.clicked.connect(self.skip_all_btn_slot)
        self.re_sym_btn.clicked.connect(self.re_sym_btn_slot)
        self.re_sym_all_btn.clicked.connect(self.re_sym_all_btn_slot)
        self.cancel_btn.clicked.connect(self.cancel_btn_slot)

    def skip_btn_slot(self):
        self.option = 0
        self.accept()

    def skip_all_btn_slot(self):
        self.option = 1
        self.accept()

    def re_sym_btn_slot(self):
        self.option = 2
        self.accept()

    def re_sym_all_btn_slot(self):
        self.option = 3
        self.accept()

    def cancel_btn_slot(self):
        self.option = 4
        self.accept()


def show_dup_sym_options(guide_name):
    """
    Display a user created dialog
    """
    dup_sym_options = DuplicateSymOptions(guide_name)

    dup_sym_options.exec_()

    return dup_sym_options.option
