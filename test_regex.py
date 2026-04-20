import re

text = '        self.export_SDKs_action = QtWidgets.QAction("Export SDK\'s", self)'

# 测试双引号模式
pattern = r'(")([^"]+)"'
matches = re.findall(pattern, text)
print(f"双引号匹配: {matches}")

# 测试单引号模式
pattern2 = r"(')([^']+)'"
matches2 = re.findall(pattern2, text)
print(f"单引号匹配: {matches2}")

# 测试完整的模式
def test_pattern(pattern, text):
    matches = re.findall(pattern, text)
    print(f"模式 '{pattern}' 匹配: {matches}")

test_pattern(r'(")([^"]+)"', text)
test_pattern(r'(")([^"]*?)(")', text)

# 测试更宽松的模式
pattern3 = r'\"([^\"]+)\"'
matches3 = re.findall(pattern3, text)
print(f"宽松模式匹配: {matches3}")