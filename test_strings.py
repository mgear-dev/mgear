import re
from translate_with_glossary import translate_string, should_skip

text = "Export SDK's"
print(f"文本: '{text}'")
print(f"应该跳过: {should_skip(text)}")
print(f"翻译: {translate_string(text)}")

# 测试其他字符串
test_strings = [
    "Export SDK's",
    "Import SDK's",
    "Select All SDK Ctls",
    "Select All Anim Ctls",
    "Select All SDK Jnts",
    "Select All SDK Nodes",
    "Pre-infinity",
    "Post-infinity",
    "Auto",
    "Spline",
    "Flat",
    "Linear",
    "Plateau",
    "Stepped",
    "Auto Set Limits On Selected Controls",
    "Auto Remove Limits On Selected Controls",
    "Rescale Driver range to fit Driven",
    "Lock/Unlock Animation Ctls",
    "Lock/Unlock SDK Ctls",
    "Prune SDKs with no input/output",
    "Reset All Ctls",
    "Reset SDK Ctls",
    "Reset Anim Tweaks",
    "About",
    "File",
    "Select",
    "Tools",
    "Reset",
    "Help",
]

for s in test_strings:
    print(f"'{s}' -> {translate_string(s)}")