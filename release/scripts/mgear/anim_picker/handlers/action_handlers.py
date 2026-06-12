from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from mgear.core import anim_utils
from mgear.core.anim_utils import stripNamespace

from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets

# from PySide2 import QtWidgets


class SpaceChangeList(QtWidgets.QMenu):

    """Space switcher list with automatic matching

    Attributes:
        combo_attr (str): attribute with the spaces
        ctl (str): control with the spaces
        namespace (str): namespace
        self_widget (str): __SELF__ anim picker widget reference
        ui_host (str): control host with the combo attribute
    """

    def __init__(
        self, namespace, ui_host, combo_attr, ctl, self_widget, *args, **kwargs
    ):
        super(SpaceChangeList, self).__init__(*args, **kwargs)
        self.namespace = namespace
        if namespace:
            ui_host = namespace + ":" + ui_host
        self.ui_host = ui_host
        self.combo_attr = combo_attr
        self.ctl = ctl
        self.self_widget = self_widget

        self.init_gui()

    def init_gui(self):
        """initialize the gui"""
        self.listWidget = QtWidgets.QListWidget(self)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(self.listWidget)
        self.addAction(action)
        self.listWidget.setFocus()

        self.key_list = anim_utils.getComboKeys(
            self.namespace, self.ui_host, self.combo_attr
        )
        self.listWidget.addItems(self.key_list)
        current_idx = anim_utils.getComboIndex(
            self.namespace, self.ui_host, self.combo_attr
        )
        self.listWidget.setCurrentRow(current_idx)

        self.listWidget.currentRowChanged.connect(self.accept)

    def accept(self):
        """sets the new space"""
        if self.listWidget.currentRow() == self.listWidget.count() - 1:
            self.listWidget.setCurrentRow(
                anim_utils.getComboIndex_with_namespace(
                    self.namespace, self.ui_host, self.combo_attr
                )
            )

            anim_utils.ParentSpaceTransfer.showUI(
                self.listWidget,
                self.ui_host,
                stripNamespace(self.ui_host),
                self.combo_attr,
                self.ctl,
            )
        else:
            anim_utils.changeSpace_with_namespace(
                self.namespace,
                self.ui_host,
                self.combo_attr,
                self.listWidget.currentRow(),
                self.ctl,
            )
            space = self.listWidget.item(self.listWidget.currentRow()).text()
            self.self_widget.text.set_text(space)
        self.close()
        self.deleteLater()


def show_space_chage_list(
    namespace, ui_host, combo_attr, ctl, self_widget, env_init
):
    """Shows wht space switch list and also initialize the picker widget name

    Args:
        namespace (str): namespace
        ui_host (str): the control UI host with combobox
        combo_attr (str): combo attribute with the available spaces
        ctl (str): control with to switch the space
        self_widget (obj): __SELF__ the anim picker widget reference
        env_init (bool): __INIT__  flag
    """
    try:
        if env_init:
            key_list = anim_utils.getComboKeys_with_namespace(
                namespace, ui_host, combo_attr
            )
            current_idx = anim_utils.getComboIndex_with_namespace(
                namespace, ui_host, combo_attr
            )
            self_widget.text.set_text(key_list[current_idx])

        else:
            maya_window = pyqt.get_main_window()
            ql = pyqt.get_instance(maya_window, SpaceChangeList)
            if ql:
                ql.deleteLater()
            # create a new instance

            ql = SpaceChangeList(
                namespace, ui_host, combo_attr, ctl, self_widget, maya_window
            )

            pyqt.position_window(ql)
            ql.exec_()
    except Exception as e:
        print(
            "Could not build space change list for ctl {}. Rig components renamed?".format(
                ctl
            )
        )
        print("Error: " + str(e))
        return


def spine_ik_fk_transfer(namespace, fkControls, ikControls):
    """spine IK FK transfer

    Args:
        namespace (str): namespace string
        fkControls (list): list with the names of the fk controls
        ikControls (list): list with the names of the ik controls
    """
    if namespace:
        fkControls = [namespace + ":" + ctl for ctl in fkControls]
        ikControls = [namespace + ":" + ctl for ctl in ikControls]

    anim_utils.SpineIkFkTransfer.showUI(
        "root", namespace, fkControls, ikControls
    )


def ik_fk_transfer(namespace, ikfk_attr, uihost, fks, ik, upv, ik_rot=None):
    """IK FK transfer forl 2 joint limbs (arms and legs)

    Args:
        namespace (str): namespace
        ikfk_attr (str): bland IK FK attribute
        uihost (str): contorls with the ik.fk blend attribute
        fks (list): list with the fk controls
        ik (str): ik control
        upv (str): up vector control
        ik_rot (None or str, optional): ik rotation control if exist
    """
    if namespace:
        model = namespace + ":" + uihost
    else:
        model = uihost

    anim_utils.IkFkTransfer.showUI(
        model, ikfk_attr, uihost, fks, ik, upv, ik_rot
    )
