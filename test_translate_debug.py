import re
from translate_with_glossary import translate_string, should_skip, process_file

# 测试SDK_manager_ui.py
file_path = "/Users/donix/.hermes/cache/documents/mgear/release/scripts/mgear/rigbits/sdk_manager/SDK_manager_ui.py"

# 手动测试一些字符串
test_strings = [
    "Export SDK's",
    "Import SDK's",
    "Select All SDK Ctls",
]

print("测试翻译函数:")
for s in test_strings:
    print(f"'{s}' -> {translate_string(s)} (跳过: {should_skip(s)})")

print("\n测试文件处理:")
changes = process_file(file_path, dry_run=True)
print(f"Changes found: {len(changes)}")
for old, new in changes[:20]:
    print(f"  '{old}' -> '{new}'")

# 让我们手动检查文件内容
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找所有双引号字符串
pattern = r'"([^"]+)"'
matches = re.findall(pattern, content)
print(f"\n找到 {len(matches)} 个双引号字符串")
for m in matches[:20]:
    print(f"  '{m}'")
    if translate_string(m):
        print(f"    -> {translate_string(m)}")