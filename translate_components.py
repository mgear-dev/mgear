#!/usr/bin/env python3
"""
批量翻译shifter_classic_components和shifter_epic_components目录下的UI字符串
"""

import os
import re
import sys

# 术语映射表（基于TERMINOLOGY.md）
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
    "Guide": "指南",
    "Component": "组件",
    "Build Settings": "构建设置",
    "Guide Settings": "指南设置",
    "Template": "模板",
    "Guide Template": "指南模板",
    "Import Template": "导入模板",
    "Export Template": "导出模板",
    "Build": "构建",
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
    
    # 常见UI字符串
    "IK/FK Blend": "IK/FK混合",
    "Max Stretch": "最大拉伸",
    "Divisions": "分段",
    "IK separated Trans and Rot ctl": "IK分离移动和旋转控制器",
    "Mirror IK Ctl axis behaviour": "镜像IK控制器轴行为",
    "Mirror Mid, UPV and Tangent Ctl axis behaviour": "镜像中间、上矢量和切线控制器轴行为",
    "Align wrist to world orientation": "对齐手腕到世界方向",
    "Squash and Stretch Profile": "挤压和拉伸轮廓",
    "IK Reference Array": "IK参考阵列",
    "Copy from UpV Ref": "从上矢量参考复制",
    "UpV Reference Array": "上矢量参考阵列",
    "Copy from IK Ref": "从IK参考复制",
    "Pin Elbow Reference Array": "固定肘部参考阵列",
}

def translate_string(english_str):
    """翻译英文字符串"""
    # 精确匹配
    if english_str in GLOSSARY:
        return GLOSSARY[english_str]
    
    # 尝试部分匹配（对于长字符串）
    for eng, chn in GLOSSARY.items():
        if eng in english_str:
            # 替换匹配的部分
            return english_str.replace(eng, chn)
    
    # 没有匹配，返回原字符串
    return english_str

def process_file(filepath):
    """处理单个文件"""
    print(f"处理文件: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 查找所有gqt.fakeTranslate调用
    pattern = r'gqt\.fakeTranslate\("([^"]+)",\s*"([^"]+)",\s*([^,]+),\s*([^)]+)\)'
    
    def replace_match(match):
        context = match.group(1)
        english_str = match.group(2)
        other_args = match.group(3) + ", " + match.group(4)
        
        # 翻译字符串
        translated = translate_string(english_str)
        
        # 如果翻译没有变化，返回原字符串
        if translated == english_str:
            return match.group(0)
        
        # 返回替换后的字符串
        return f'gqt.fakeTranslate("{context}", "{translated}", {other_args})'
    
    # 替换所有匹配
    content = re.sub(pattern, replace_match, content)
    
    # 检查是否有变化
    if content != original_content:
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """主函数"""
    # 要处理的目录
    directories = [
        "release/scripts/mgear/shifter_classic_components",
        "release/scripts/mgear/shifter_epic_components",
    ]
    
    total_files = 0
    modified_files = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            print(f"目录不存在: {directory}")
            continue
        
        # 遍历所有Python文件
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    total_files += 1
                    
                    try:
                        if process_file(filepath):
                            modified_files += 1
                            print(f"  已修改: {filepath}")
                    except Exception as e:
                        print(f"  处理失败: {filepath}, 错误: {e}")
    
    print(f"\n处理完成:")
    print(f"  总文件数: {total_files}")
    print(f"  修改文件数: {modified_files}")
    
    # 提示用户提交更改
    if modified_files > 0:
        print(f"\n请运行以下命令提交更改:")
        print(f"  git add .")
        print(f"  git commit -m '汉化：批量翻译shifter组件文件'")

if __name__ == "__main__":
    main()