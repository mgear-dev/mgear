#!/usr/bin/env python3
"""
mGear 批量翻译脚本
自动扫描Python文件中的UI字符串并替换为中文
"""

import os
import re
import json
from pathlib import Path

# 翻译映射表
TRANSLATIONS = {
    # 菜单项
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
    
    # 对话框标题
    "Warning": "警告",
    "Error": "错误",
    "Information": "信息",
    "Confirm": "确认",
    
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
    
    # Shifter相关
    "Shifter": "Shifter",
    "New Component": "新建组件",
    "Add Component": "添加组件",
    "Remove Component": "移除组件",
    "Component Settings": "组件设置",
    "Guide Settings": "指南设置",
    "Build Settings": "构建设置",
    "Rig Settings": "绑定设置",
    
    # Rigbits
    "Create Control": "创建控制器",
    "Create Joint": "创建骨骼",
    "Connect": "连接",
    "Disconnect": "断开连接",
    
    # Animbits
    "Keyframe": "关键帧",
    "Pose": "姿势",
    "Animation": "动画",
    
    # 通用
    "Select": "选择",
    "All": "全部",
    "None": "无",
    "Invert": "反选",
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
}

def should_translate(text):
    """判断是否应该翻译这个字符串"""
    # 跳过空字符串
    if not text or text.isspace():
        return False
    
    # 跳过纯数字
    if text.replace('.', '').replace('-', '').isdigit():
        return False
    
    # 跳过变量名风格的字符串（全小写或snake_case）
    if text.islower() or '_' in text:
        return False
    
    # 跳过太短的字符串（单个字符）
    if len(text) <= 1:
        return False
    
    # 跳过技术性字符串
    technical = ['mGear', 'Maya', 'Python', 'PySide', 'Qt', 'JSON', 'XML', 'YAML', 'HTTP', 'URL', 'API', 'SDK', 'FK', 'IK']
    if text in technical:
        return False
    
    return True

def translate_text(text):
    """翻译文本"""
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    return None

def process_file(file_path, dry_run=False):
    """处理单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # 查找可能需要翻译的字符串
        # 匹配模式：引号内的字符串
        patterns = [
            (r'"([^"]+)"', '"'),  # 双引号
            (r"'([^']+)'", "'"),  # 单引号
        ]
        
        for pattern, quote in patterns:
            def replace_func(match):
                text = match.group(1)
                if should_translate(text):
                    translation = translate_text(text)
                    if translation:
                        changes.append((text, translation))
                        return f'{quote}{translation}{quote}'
                return match.group(0)
            
            content = re.sub(pattern, replace_func, content)
        
        # 如果有修改且不是dry_run，写入文件
        if changes and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return changes
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def scan_directory(directory, dry_run=True):
    """扫描目录中的所有Python文件"""
    all_changes = {}
    
    for root, dirs, files in os.walk(directory):
        # 跳过某些目录
        skip_dirs = ['__pycache__', '.git', 'vendor', 'node_modules']
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                changes = process_file(file_path, dry_run)
                if changes:
                    all_changes[file_path] = changes
    
    return all_changes

def main():
    import sys
    
    # 默认目录
    base_dir = "/Users/donix/.hermes/cache/documents/mgear/release/scripts/mgear"
    
    # 解析命令行参数
    dry_run = True
    target_dir = None
    
    for arg in sys.argv[1:]:
        if arg == '--apply':
            dry_run = False
        elif os.path.isdir(arg):
            target_dir = arg
    
    if target_dir is None:
        target_dir = base_dir
    
    print(f"Scanning: {target_dir}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY CHANGES'}")
    print("-" * 50)
    
    changes = scan_directory(target_dir, dry_run)
    
    # 统计
    total_files = len(changes)
    total_strings = sum(len(c) for c in changes.values())
    
    print(f"\nFiles with changes: {total_files}")
    print(f"Total strings to translate: {total_strings}")
    
    if dry_run:
        print("\n=== DRY RUN - No files modified ===")
        print("Run with --apply to actually modify files")
    else:
        print("\n=== FILES MODIFIED ===")
    
    # 显示详细变化
    for file_path, file_changes in changes.items():
        rel_path = os.path.relpath(file_path, base_dir)
        print(f"\n{rel_path}:")
        for old, new in file_changes[:10]:  # 只显示前10个
            print(f"  '{old}' -> '{new}'")
        if len(file_changes) > 10:
            print(f"  ... and {len(file_changes) - 10} more")

if __name__ == "__main__":
    main()
