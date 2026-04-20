import re

text = 'self.export_SDKs_action = QtWidgets.QAction("Export SDK\'s", self)'
pattern = r'"([^"]+)"'
matches = re.findall(pattern, text)
print(f"匹配: {matches}")

# 测试process_file中的正则表达式
pattern2 = r'(")([^"]+)"'
matches2 = re.findall(pattern2, text)
print(f"匹配2: {matches2}")

# 测试更宽松的模式
pattern3 = r'\"([^\"]*?)\"'
matches3 = re.findall(pattern3, text)
print(f"匹配3: {matches3}")