#!/usr/bin/env python3
"""
使用TERMINOLOGY.md术语表的翻译脚本
"""

import os
import re
import sys
from pathlib import Path

# 从术语表中提取的翻译映射
# 格式: 英文 -> 中文
GLOSSARY = {
    # 核心术语
    "Guide": "指南",
    "Component": "组件",
    "Build": "构建",
    "Template": "模板",
    "Import": "导入",
    "Export": "导出",
    "Settings": "设置",
    "Options": "选项",
    "Tools": "工具",
    "Help": "帮助",
    "About": "关于",
    "Close": "关闭",
    "Cancel": "取消",
    "OK": "确定",
    "Apply": "应用",
    "Reset": "重置",
    "Clear": "清除",
    "Browse": "浏览",
    "Select": "选择",
    "All": "全部",
    "None": "无",
    "Delete": "删除",
    "Remove": "移除",
    "Add": "添加",
    "New": "新建",
    "Open": "打开",
    "Save": "保存",
    "Save As": "另存为",
    "Load": "加载",
    "Refresh": "刷新",
    "Update": "更新",
    "Create": "创建",
    "Generate": "生成",
    "Edit": "编辑",
    "View": "视图",
    "Show": "显示",
    "Hide": "隐藏",
    
    # Maya/动画术语
    "Joint": "骨骼",
    "Bone": "骨骼",
    "Control": "控制器",
    "Controller": "控制器",
    "FK": "FK",
    "IK": "IK",
    "IK/FK": "IK/FK",
    "Blend": "混合",
    "Constraint": "约束",
    "Parent": "父级",
    "Child": "子级",
    "Hierarchy": "层级",
    "Transform": "变换",
    "Position": "位置",
    "Rotation": "旋转",
    "Scale": "缩放",
    "Translate": "移动",
    "Axis": "轴",
    "World": "世界",
    "Local": "本地",
    "Object": "对象",
    "Node": "节点",
    "Attribute": "属性",
    "Channel": "通道",
    "Keyframe": "关键帧",
    "Animation": "动画",
    "Pose": "姿势",
    "Skeleton": "骨骼架",
    "Skin": "蒙皮",
    "Bind": "绑定",
    "Weight": "权重",
    "Mesh": "网格",
    "Geometry": "几何体",
    "Curve": "曲线",
    "Nurbs": "NURBS",
    "Polygon": "多边形",
    "Vertex": "顶点",
    "Edge": "边",
    "Face": "面",
    
    # Shifter术语
    "Shifter": "Shifter",
    "Build Settings": "构建设置",
    "Guide Settings": "指南设置",
    "Guide Template": "指南模板",
    "Import Template": "导入模板",
    "Export Template": "导出模板",
    "Rig": "绑定",
    "Rigging": "绑定",
    "Character": "角色",
    "Part": "部件",
    "Module": "模块",
    "Root": "根",
    "End": "末端",
    "Mid": "中间",
    "Start": "开始",
    
    # UI控件
    "Button": "按钮",
    "Label": "标签",
    "Text Field": "文本框",
    "Input": "输入",
    "Output": "输出",
    "Slider": "滑块",
    "Spin Box": "数字框",
    "Check Box": "复选框",
    "Radio Button": "单选按钮",
    "Combo Box": "下拉框",
    "Drop Down": "下拉菜单",
    "List": "列表",
    "Tree": "树形",
    "Tab": "标签页",
    "Page": "页面",
    "Panel": "面板",
    "Group Box": "分组框",
    "Frame": "框架",
    "Window": "窗口",
    "Dialog": "对话框",
    "Menu": "菜单",
    "Menu Bar": "菜单栏",
    "Tool Bar": "工具栏",
    "Status Bar": "状态栏",
    "Progress Bar": "进度条",
    "Scroll Bar": "滚动条",
    
    # 文件操作
    "File": "文件",
    "Folder": "文件夹",
    "Directory": "目录",
    "Path": "路径",
    "Name": "名称",
    "Type": "类型",
    "Size": "大小",
    "Date": "日期",
    "Modified": "修改时间",
    "Created": "创建时间",
    
    # 状态/消息
    "Success": "成功",
    "Error": "错误",
    "Warning": "警告",
    "Info": "信息",
    "Ready": "就绪",
    "Running": "运行中",
    "Complete": "完成",
    "Failed": "失败",
    "Processing": "处理中",
    "Loading": "加载中",
    "Saving": "保存中",
    
    # 额外的常见术语（从现有脚本中提取）
    "Reload": "重新加载",
    "Scene": "场景",
    "Manager": "管理器",
    "Components": "组件",
    "From Scene": "从场景",
    "From Selection": "从选择",
    "From File": "从文件",
    "All Guides": "所有指南",
    "Selected Guides": "选中的指南",
    "Check Scene": "检查场景",
    "Check Selection": "检查选择",
    "Information": "信息",
    "Confirm": "确认",
    "Question": "问题",
    "Accept": "接受",
    "Reject": "拒绝",
    "Yes": "是",
    "No": "否",
    "Copy": "复制",
    "Paste": "粘贴",
    "Cut": "剪切",
    "Undo": "撤销",
    "Redo": "重做",
    "Zoom": "缩放",
    "Pan": "平移",
    "Invert": "反选",
    "New Component": "新建组件",
    "Add Component": "添加组件",
    "Remove Component": "移除组件",
    "Component Settings": "组件设置",
    "Rig Settings": "绑定设置",
    "Rig Builder": "绑定构建器",
    "Guide Manager": "指南管理器",
    "Template Manager": "模板管理器",
    "Build Rig": "构建绑定",
    "Build Selected": "构建选中",
    "Build All": "构建全部",
    "Create Control": "创建控制器",
    "Create Joint": "创建骨骼",
    "Connect": "连接",
    "Disconnect": "断开连接",
    "Space Switch": "空间切换",
    "Space Manager": "空间管理器",
    "Channel Wrangler": "通道管理",
    "SDK Creator": "SDK创建器",
    "Control Shapes": "控制器形状",
    "Channel Master": "通道主控",
    "Anim Picker": "动画拾取器",
    "Cloth": "布料",
    "Hair": "毛发",
    "Physics": "物理",
    "Unreal": "虚幻",
    "Engine": "引擎",
    "Export to UE": "导出到虚幻",
    "Import from UE": "从虚幻导入",
    "Version": "版本",
    "Status": "状态",
    "Progress": "进度",
    
    # SDK Manager相关
    "Export SDK's": "导出SDK",
    "Import SDK's": "导入SDK",
    "Select All SDK Ctls": "选择所有SDK控制器",
    "Select All Anim Ctls": "选择所有动画控制器",
    "Select All SDK Jnts": "选择所有SDK骨骼",
    "Select All SDK Nodes": "选择所有SDK节点",
    "Pre-infinity": "前无限",
    "Post-infinity": "后无限",
    "Auto": "自动",
    "Spline": "样条",
    "Flat": "平坦",
    "Linear": "线性",
    "Plateau": "平台",
    "Stepped": "阶梯",
    "Auto Set Limits On Selected Controls": "自动设置选中控制器的限制",
    "Auto Remove Limits On Selected Controls": "自动移除选中控制器的限制",
    "Rescale Driver range to fit Driven": "缩放驱动范围以适应被驱动",
    "Lock/Unlock Animation Ctls": "锁定/解锁动画控制器",
    "Lock/Unlock SDK Ctls": "锁定/解锁SDK控制器",
    "Prune SDKs with no input/output": "修剪没有输入/输出的SDK",
    "Reset All Ctls": "重置所有控制器",
    "Reset SDK Ctls": "重置SDK控制器",
    "Reset Anim Tweaks": "重置动画调整",
    
    # Tangent类型
    "Tangent In": "切线入",
    "Tangent Out": "切线出",
    
    # 其他常见术语
    "Toggle Infinity on SDK ctls": "切换SDK控制器的无限",
    "Set Tangent Type": "设置切线类型",
}

# 需要跳过的模式
SKIP_PATTERNS = [
    r'^[a-z_]+$',  # 全小写或snake_case（变量名）
    r'^\d+$',  # 纯数字
    r'^[A-Z_]+$',  # 全大写（常量）
    r'mGear|Maya|Python|PySide|Qt|JSON|XML',  # 技术名词
    r'\.(py|json|xml|txt|md)$',  # 文件扩展名
    r'^https?://',  # URL
    r'^[a-zA-Z]:[/\\]',  # Windows路径
]

def should_skip(text):
    """判断是否应该跳过"""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def translate_string(text):
    """翻译字符串"""
    if should_skip(text):
        return None
    
    # 直接匹配
    if text in GLOSSARY:
        return GLOSSARY[text]
    
    # 尝试去除前后空格
    stripped = text.strip()
    if stripped in GLOSSARY:
        return GLOSSARY[stripped]
    
    return None

def process_file(file_path, dry_run=True):
    """处理文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = []
        
        # 匹配引号内的字符串
        def replace_match(match):
            quote = match.group(1)
            text = match.group(2)
            
            translation = translate_string(text)
            if translation:
                changes.append((text, translation))
                return f'{quote}{translation}{quote}'
            return match.group(0)
        
        # 双引号（单行，非贪婪）
        content = re.sub(r'(\")([^\"]*?)\"', replace_match, content)
        # 单引号（单行，非贪婪）
        content = re.sub(r"(')([^']*?)'" , replace_match, content)
        
        if changes and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return changes
    
    except Exception as e:
        print(f"Error: {file_path}: {e}", file=sys.stderr)
        return []

def main():
    dry_run = '--apply' not in sys.argv
    
    base = Path("/Users/donix/.hermes/cache/documents/mgear/release/scripts/mgear")
    
    # 排除已翻译的文件（根据之前的信息）
    translated = {
        "core/dagmenu.py", "core/menu.py",
        "shifter/menu.py", "shifter/guide_ui.py", "shifter/plebes.py",
        "shifter/guide_manager_gui.py", "shifter/guide_template_manager/ui.py",
        "shifter/guide_template_manager/widgets.py",
        "shifter/build_log/ui.py", "shifter/guide_explorer/guide_explorer_widget.py",
        "shifter/guide_explorer/guide_tree_widget.py",
        "rigbits/menu.py", "rigbits/sdk_creator/core.py",
        "animbits/menu.py", "cfxbits/menu.py",
        "uegear/menu.py", "utilbits/menu.py",
        "simpleRig/menu.py", "crank/menu.py",
        "anim_picker/menu.py", "menu.py",
    }
    
    total_files = 0
    total_strings = 0
    
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLYING CHANGES'}")
    print("-" * 50)
    
    # 只处理指定的模块
    target_modules = ["rigbits", "animbits", "cfxbits"]
    
    for py_file in sorted(base.rglob("*.py")):
        rel = str(py_file.relative_to(base))
        
        # 只处理目标模块
        if not any(rel.startswith(module) for module in target_modules):
            continue
        
        # 跳过已翻译的
        if rel in translated:
            print(f"Skipping already translated: {rel}")
            continue
        
        # 跳过vendor和__pycache__
        if 'vendor' in rel or '__pycache__' in rel:
            continue
        
        changes = process_file(py_file, dry_run)
        if changes:
            total_files += 1
            total_strings += len(changes)
            print(f"\n{rel}:")
            for old, new in changes[:10]:
                print(f"  '{old}' -> '{new}'")
            if len(changes) > 10:
                print(f"  ... +{len(changes)-10} more")
    
    print(f"\n{'='*50}")
    print(f"Files: {total_files}, Strings: {total_strings}")
    
    if dry_run:
        print("Run with --apply to modify files")

if __name__ == "__main__":
    main()