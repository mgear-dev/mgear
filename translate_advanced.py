#!/usr/bin/env python3
"""
mGear 高级翻译脚本
使用上下文感知的翻译规则
"""

import os
import re
import sys
from pathlib import Path

# 更完整的翻译映射，包含上下文
TRANSLATIONS = {
    # 菜单项（字符串后面有逗号或括号）
    "Create": "创建",
    "Settings": "设置",
    "Reload": "重新加载",
    "Delete": "删除",
    "Guide": "指南",
    "Import": "导入",
    "Export": "导出",
    "Build": "构建",
    "Scene": "场景",
    "Template": "模板",
    "Manager": "管理器",
    "Components": "组件",
    "From Scene": "从场景",
    "From Selection": "从选择",
    "From File": "从文件",
    "All Guides": "所有指南",
    "Selected Guides": "选中的指南",
    "Check Scene": "检查场景",
    "Check Selection": "检查选择",
    
    # 对话框
    "Warning": "警告",
    "Error": "错误",
    "Information": "信息",
    "Confirm": "确认",
    "Question": "问题",
    
    # 按钮
    "OK": "确定",
    "Cancel": "取消",
    "Apply": "应用",
    "Close": "关闭",
    "Save": "保存",
    "Load": "加载",
    "Browse": "浏览",
    "Reset": "重置",
    "Refresh": "刷新",
    "Accept": "接受",
    "Reject": "拒绝",
    "Yes": "是",
    "No": "否",
    
    # 文件操作
    "Open": "打开",
    "Save As": "另存为",
    "New": "新建",
    
    # 编辑
    "Edit": "编辑",
    "Copy": "复制",
    "Paste": "粘贴",
    "Cut": "剪切",
    "Undo": "撤销",
    "Redo": "重做",
    
    # 视图
    "View": "视图",
    "Show": "显示",
    "Hide": "隐藏",
    "Zoom": "缩放",
    "Pan": "平移",
    
    # 选择
    "Select": "选择",
    "All": "全部",
    "None": "无",
    "Invert": "反选",
    
    # Shifter
    "Shifter": "Shifter",
    "New Component": "新建组件",
    "Add Component": "添加组件",
    "Remove Component": "移除组件",
    "Component Settings": "组件设置",
    "Guide Settings": "指南设置",
    "Build Settings": "构建设置",
    "Rig Settings": "绑定设置",
    "Rig Builder": "绑定构建器",
    "Guide Manager": "指南管理器",
    "Guide Template": "指南模板",
    "Template Manager": "模板管理器",
    "Import Template": "导入模板",
    "Export Template": "导出模板",
    "Build Rig": "构建绑定",
    "Build Selected": "构建选中",
    "Build All": "构建全部",
    
    # Rigbits
    "Create Control": "创建控制器",
    "Create Joint": "创建骨骼",
    "Connect": "连接",
    "Disconnect": "断开连接",
    "Space Switch": "空间切换",
    "Space Manager": "空间管理器",
    "Channel Wrangler": "通道管理",
    "SDK Creator": "SDK创建器",
    "Control Shapes": "控制器形状",
    
    # Animbits
    "Keyframe": "关键帧",
    "Pose": "姿势",
    "Animation": "动画",
    "Channel Master": "通道主控",
    "Anim Picker": "动画拾取器",
    
    # CFX
    "Cloth": "布料",
    "Hair": "毛发",
    "Physics": "物理",
    
    # UE Gear
    "Unreal": "虚幻",
    "Engine": "引擎",
    "Export to UE": "导出到虚幻",
    "Import from UE": "从虚幻导入",
    
    # 通用UI
    "Options": "选项",
    "Tools": "工具",
    "Help": "帮助",
    "About": "关于",
    "Version": "版本",
    "Name": "名称",
    "Type": "类型",
    "Path": "路径",
    "File": "文件",
    "Folder": "文件夹",
    "Directory": "目录",
    "Status": "状态",
    "Progress": "进度",
    "Ready": "就绪",
    "Running": "运行中",
    "Complete": "完成",
    "Failed": "失败",
    "Success": "成功",
    "Processing": "处理中",
    
    # Maya相关
    "Maya": "Maya",
    "Object": "对象",
    "Node": "节点",
    "Attribute": "属性",
    "Channel": "通道",
    "Transform": "变换",
    "Position": "位置",
    "Rotation": "旋转",
    "Scale": "缩放",
    "Joint": "骨骼",
    "Control": "控制器",
    "Constraint": "约束",
    "Parent": "父级",
    "Child": "子级",
    "Hierarchy": "层级",
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

def translate_string(text, context=""):
    """翻译字符串，考虑上下文"""
    if should_skip(text):
        return None
    
    # 直接匹配
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    
    # 尝试去除前后空格
    stripped = text.strip()
    if stripped in TRANSLATIONS:
        return TRANSLATIONS[stripped]
    
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
        
        # 双引号
        content = re.sub(r'(")([^"]+)"', replace_match, content)
        # 单引号
        content = re.sub(r"(')([^']+)'" , replace_match, content)
        
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
    
    # 排除已翻译的文件
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
    
    for py_file in sorted(base.rglob("*.py")):
        rel = str(py_file.relative_to(base))
        
        # 跳过已翻译的
        if rel in translated:
            continue
        
        # 跳过vendor和__pycache__
        if 'vendor' in rel or '__pycache__' in rel:
            continue
        
        changes = process_file(py_file, dry_run)
        if changes:
            total_files += 1
            total_strings += len(changes)
            print(f"\n{rel}:")
            for old, new in changes[:5]:
                print(f"  '{old}' -> '{new}'")
            if len(changes) > 5:
                print(f"  ... +{len(changes)-5} more")
    
    print(f"\n{'='*50}")
    print(f"Files: {total_files}, Strings: {total_strings}")
    
    if dry_run:
        print("Run with --apply to modify files")

if __name__ == "__main__":
    main()
