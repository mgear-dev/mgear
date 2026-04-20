import re
from translate_with_glossary import translate_string, should_skip

def process_file_debug(file_path, dry_run=True):
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
            print(f"匹配到: 引号='{quote}', 文本='{text}'")
            
            translation = translate_string(text)
            if translation:
                print(f"  翻译: '{text}' -> '{translation}'")
                changes.append((text, translation))
                return f'{quote}{translation}{quote}'
            return match.group(0)
        
        # 双引号
        print("测试双引号模式...")
        content = re.sub(r'(\")([^\"]+)\"', replace_match, content)
        # 单引号
        print("测试单引号模式...")
        content = re.sub(r"(')([^']+)'" , replace_match, content)
        
        if changes and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return changes
    
    except Exception as e:
        print(f"Error: {file_path}: {e}")
        return []

# 测试
file_path = "/Users/donix/.hermes/cache/documents/mgear/release/scripts/mgear/rigbits/sdk_manager/SDK_manager_ui.py"
changes = process_file_debug(file_path, dry_run=True)
print(f"\n总共找到 {len(changes)} 个更改")