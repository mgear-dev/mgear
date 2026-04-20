import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as OpenMayaUI
import os

if cmds.about(api=True) >= 201700:
    from PySide2 import QtGui
else:
    from PySide import QtGui
import cvwrap.bindui

NAME_WIDGET = "cvwrap_name"
RADIUS_WIDGET = "cvwrap_radius"
NEW_BIND_MESH_WIDGET = "cvwrap_newbindmesh"
BIND_FILE_WIDGET = "cvwrap_bindfile"
MENU_ITEMS = []


def create_menuitems():
    global MENU_ITEMS
    if MENU_ITEMS:
        # Already created
        return
    if cmds.about(api=True) < 201600:
        cmds.warning("cvWrap菜单仅在Maya 2016及更高版本中可用。")
        return
    for menu in ["mainDeformMenu", "mainRigDeformationsMenu"]:
        # Make sure the menu widgets exist first.
        mel.eval("ChaDeformationsMenu MayaWindow|{0};".format(menu))
        items = cmds.menu(menu, q=True, ia=True)
        for item in items:
            if cmds.menuItem(item, q=True, divider=True):
                section = cmds.menuItem(item, q=True, label=True)
            menu_label = cmds.menuItem(item, q=True, label=True)
            if menu_label == "Wrap":
                if section == "Create":
                    cvwrap_item = cmds.menuItem(
                        label="cvWrap",
                        command=create_cvwrap,
                        sourceType="python",
                        insertAfter=item,
                        parent=menu,
                    )
                    cvwrap_options = cmds.menuItem(
                        command=display_cvwrap_options,
                        insertAfter=cvwrap_item,
                        parent=menu,
                        optionBox=True,
                    )
                    MENU_ITEMS.append(cvwrap_item)
                    MENU_ITEMS.append(cvwrap_options)
                elif section == "Edit":
                    submenu = cmds.menuItem(
                        label="cvWrap", subMenu=True, insertAfter=item, parent=menu
                    )
                    MENU_ITEMS.append(submenu)
                    item = cmds.menuItem(
                        label="编辑绑定",
                        command=edit_binding,
                        sourceType="python",
                        parent=submenu,
                    )
                    MENU_ITEMS.append(item)
                    item = cmds.menuItem(
                        label="导入绑定",
                        command=import_binding,
                        sourceType="python",
                        parent=submenu,
                    )
                    MENU_ITEMS.append(item)
                    item = cmds.menuItem(
                        label="导出绑定",
                        command=export_binding,
                        sourceType="python",
                        parent=submenu,
                    )
                    MENU_ITEMS.append(item)
            elif menu_label == "Cluster" and section == "Paint Weights":
                item = cmds.menuItem(
                    label="cvWrap",
                    command=paint_cvwrap_weights,
                    sourceType="python",
                    insertAfter=item,
                    parent=menu,
                )
                MENU_ITEMS.append(item)


def create_cvwrap(*args, **kwargs):
    cmds.loadPlugin("cvwrap", qt=True)
    sel = cmds.ls(sl=True)
    if len(sel) >= 2:
        kwargs = get_create_command_kwargs()
        result = cmds.cvWrap(**kwargs)
        print(result)
    else:
        raise RuntimeError("请至少选择一个曲面和一个影响对象。")


def get_create_command_kwargs():
    """Gets the cvWrap command arguments either from the option box widgets or the saved
    option vars.  If the widgets exist, their values will be saved to the option vars.
    @return A dictionary of the kwargs to the cvWrap command."""
    args = {}
    if cmds.textFieldGrp(NAME_WIDGET, exists=True):
        args["name"] = cmds.textFieldGrp(NAME_WIDGET, q=True, text=True)
        cmds.optionVar(sv=(NAME_WIDGET, args["name"]))
    else:
        args["name"] = cmds.optionVar(q=NAME_WIDGET) or "cvWrap#"
    if cmds.floatSliderGrp(RADIUS_WIDGET, exists=True):
        args["radius"] = cmds.floatSliderGrp(RADIUS_WIDGET, q=True, value=True)
        cmds.optionVar(fv=(RADIUS_WIDGET, args["radius"]))
    else:
        args["radius"] = cmds.optionVar(q=RADIUS_WIDGET)

    if cmds.checkBoxGrp(NEW_BIND_MESH_WIDGET, exists=True):
        if cmds.checkBoxGrp(NEW_BIND_MESH_WIDGET, q=True, v1=True):
            args["newBindMesh"] = True
            cmds.optionVar(iv=(NEW_BIND_MESH_WIDGET, 1))
        else:
            cmds.optionVar(iv=(NEW_BIND_MESH_WIDGET, 0))
    else:
        value = cmds.optionVar(q=NEW_BIND_MESH_WIDGET)
        if value:
            args["newBindMesh"] = True

    if cmds.textFieldButtonGrp(BIND_FILE_WIDGET, exists=True):
        bind_file = cmds.textFieldButtonGrp(BIND_FILE_WIDGET, q=True, text=True)
        bind_file = os.path.expandvars(bind_file.strip())
        if bind_file:
            if os.path.exists(bind_file):
                args["binding"] = bind_file
            else:
                cmds.warning("{0} 不存在。".format(bind_file))

    return args


def display_cvwrap_options(*args, **kwargs):
    cmds.loadPlugin("cvwrap", qt=True)
    layout = mel.eval("getOptionBox")
    cmds.setParent(layout)
    cmds.columnLayout(adj=True)

    for widget in [NAME_WIDGET, RADIUS_WIDGET, BIND_FILE_WIDGET, NEW_BIND_MESH_WIDGET]:
        # Delete the widgets so we don't create multiple controls with the same name
        try:
            cmds.deleteUI(widget, control=True)
        except:
            pass

    cmds.textFieldGrp(NAME_WIDGET, label="节点名称", text="cvWrap#")
    radius = cmds.optionVar(q=RADIUS_WIDGET)
    cmds.floatSliderGrp(
        RADIUS_WIDGET,
        label="采样半径",
        field=True,
        minValue=0.0,
        maxValue=100.0,
        fieldMinValue=0.0,
        fieldMaxValue=100.0,
        value=radius,
        step=0.01,
        precision=2,
    )
    cmds.textFieldButtonGrp(
        BIND_FILE_WIDGET,
        label="绑定文件 ",
        text="",
        buttonLabel="浏览",
        bc=display_bind_file_dialog,
    )
    use_new_bind_mesh = cmds.optionVar(q=NEW_BIND_MESH_WIDGET)
    cmds.checkBoxGrp(
        NEW_BIND_MESH_WIDGET,
        numberOfCheckBoxes=1,
        label="创建新绑定网格",
        v1=use_new_bind_mesh,
    )
    mel.eval('setOptionBoxTitle("cvWrap 选项");')
    mel.eval('setOptionBoxCommandName("cvWrap");')
    apply_close_button = mel.eval("getOptionBoxApplyAndCloseBtn;")
    cmds.button(apply_close_button, e=True, command=apply_and_close)
    apply_button = mel.eval("getOptionBoxApplyBtn;")
    cmds.button(apply_button, e=True, command=create_cvwrap)
    reset_button = mel.eval("getOptionBoxResetBtn;")
    # For some reason, the buttons in the menu only accept MEL.
    cmds.button(
        reset_button,
        e=True,
        command='python("import cvwrap.menu; cvwrap.menu.reset_to_defaults()");',
    )
    close_button = mel.eval("getOptionBoxCloseBtn;")
    cmds.button(close_button, e=True, command=close_option_box)
    save_button = mel.eval("getOptionBoxSaveBtn;")
    cmds.button(
        save_button,
        e=True,
        command='python("import cvwrap.menu; cvwrap.menu.get_create_command_kwargs()");',
    )
    mel.eval("showOptionBox")


def apply_and_close(*args, **kwargs):
    """Create the cvWrap deformer and close the option box."""
    create_cvwrap()
    mel.eval("saveOptionBoxSize")
    close_option_box()


def close_option_box(*args, **kwargs):
    mel.eval("hideOptionBox")


def display_bind_file_dialog(*args, **kwargs):
    """Displays the dialog to choose the binding file with which to create the cvWrap deformer."""
    root_dir = cmds.workspace(q=True, rootDirectory=True)
    start_directory = os.path.join(root_dir, "data")
    file_path = cmds.fileDialog2(
        fileFilter="*.wrap",
        dialogStyle=2,
        fileMode=1,
        startingDirectory=start_directory,
    )
    if file_path:
        cmds.textFieldButtonGrp(BIND_FILE_WIDGET, e=True, text=file_path[0])


def reset_to_defaults(*args, **kwargs):
    """Reset the cvWrap option box widgets to their defaults."""
    cmds.textFieldGrp(NAME_WIDGET, e=True, text="cvWrap#")
    cmds.floatSliderGrp(RADIUS_WIDGET, e=True, value=0)
    cmds.textFieldButtonGrp(BIND_FILE_WIDGET, e=True, text="")
    cmds.checkBoxGrp(NEW_BIND_MESH_WIDGET, e=True, v1=False)


def edit_binding(*args, **kwargs):
    cvwrap.bindui.show()


def export_binding(*args, **kwargs):
    """Export a wrap binding from the selected wrap node or mesh."""
    cmds.loadPlugin("cvwrap", qt=True)
    wrap_node = get_wrap_node_from_selected()
    if wrap_node:
        data_dir = os.path.join(cmds.workspace(q=True, rd=True), "data")
        file_path = cmds.fileDialog2(
            fileFilter="*.wrap",
            dialogStyle=2,
            cap="导出绑定",
            startingDirectory=data_dir,
            fm=0,
        )
        if file_path:
            cmds.cvWrap(wrap_node, ex=file_path[0])


def import_binding(*args, **kwargs):
    """Import a wrap binding onto the selected wrap node or mesh."""
    cmds.loadPlugin("cvwrap", qt=True)
    wrap_node = get_wrap_node_from_selected()
    if wrap_node:
        data_dir = os.path.join(cmds.workspace(q=True, rd=True), "data")
        file_path = cmds.fileDialog2(
            fileFilter="*.wrap",
            dialogStyle=2,
            cap="导入绑定",
            startingDirectory=data_dir,
            fm=1,
        )
        if file_path:
            cmds.cvWrap(wrap_node, im=file_path[0])


def get_wrap_node_from_selected():
    """Get a wrap node from the selected geometry."""
    sel = cmds.ls(sl=True) or []
    if not sel:
        raise RuntimeError("所选对象上未找到cvWrap。")
    if cmds.nodeType(sel[0]) == "cvWrap":
        return sel[0]
    history = cmds.listHistory(sel[0], pdo=0) or []
    wrap_nodes = [node for node in history if cmds.nodeType(node) == "cvWrap"]
    if not wrap_nodes:
        raise RuntimeError("在 {0} 上未找到cvWrap节点。".format(sel[0]))
    if len(wrap_nodes) == 1:
        return wrap_nodes[0]
    else:
        # Multiple wrap nodes are deforming the mesh.  Let the user choose which one
        # to use.
        return QtGui.QInputDialog.getItem(
            None, "选择cvWrap节点", "cvWrap节点:", wrap_nodes
        )


def destroy_menuitems():
    """Remove the cvWrap items from the menus."""
    global MENU_ITEMS
    for item in MENU_ITEMS:
        cmds.deleteUI(item, menuItem=True)
    MENU_ITEMS = []


def paint_cvwrap_weights(*args, **kwargs):
    """Activates the paint cvWrap weights context."""
    sel = cmds.ls(sl=True)
    if sel:
        wrap_node = get_wrap_node_from_selected()
        if wrap_node:
            mel.eval(
                'artSetToolAndSelectAttr("artAttrCtx", "cvWrap.{0}.weights");'.format(
                    wrap_node
                )
            )
