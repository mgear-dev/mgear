#!/usr/bin/env python3
import re
from translate_with_glossary import translate_string, process_file

# 测试SDK_manager_ui.py
file_path = "/Users/donix/.hermes/cache/documents/mgear/release/scripts/mgear/rigbits/sdk_manager/SDK_manager_ui.py"

changes = process_file(file_path, dry_run=True)
print(f"Changes found: {len(changes)}")
for old, new in changes[:20]:
    print(f"  '{old}' -> '{new}'")