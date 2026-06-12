## Contributing to mGear

### Code Formatter: Black

We use **Black** for code formatting with its default **88 character line length**.

```bash
# Format a file
black myfile.py

# Check without modifying
black --check myfile.py
```

Write code in Black format from the start. Black handles:
- Double quotes for strings
- Trailing commas in multi-line structures
- Consistent line breaking and indentation
- Spaces around operators

```python
# Black multi-line style
result = some_function(
    argument_one,
    argument_two,
    argument_three,
)

data = {
    "key1": "value1",
    "key2": "value2",
}
```

<br>

### Imports

**One import per line.** No grouping multiple names on the same line.

**Wrong**

```python
from mgear.core import attribute, transform, primitive
```

**Right**

```python
from mgear.core import attribute
from mgear.core import transform
from mgear.core import primitive
```

**Import order** (separated by blank lines):

```python
"""Module docstring"""

# Standard library
import json
import math
import os
from functools import partial
# Maya
from maya import cmds
from maya import mel
import maya.api.OpenMaya as om2

# mGear vendor
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

# mGear
import mgear
import mgear.pymaya as pm
from mgear.pymaya import datatypes
from mgear.core import attribute
from mgear.core import transform
from mgear.core import primitive



# Relative imports (last)
from . import setup
```

<br>

### Avoid `import as`

Where possible, avoid the use of `import ... as ...`.

```python
from mgear.core import rigbits as rb
```

This makes it more difficult to understand where a particular call is coming from, when read by someone who didn't initially make that import.

```python
swg.run_important_function()
# What does this do? :O
```

**Allowed exceptions** (widely understood aliases):

```python
import mgear.pymaya as pm
import maya.api.OpenMaya as om2
from mgear.core import widgets as mwgt
```

<br>

### Argument shorthands

In Maya, some arguments have a short equivalent. Don't use it.

**Wrong**

```python
pm.workspace(q=True, rd=True)
```

**Right**

```python
pm.workspace(query=True, rootDirectory=True)
```

The reason is readability. These shorthands exist to reduce the filesize of Maya's `.ma` files, not to make your Python code shorter.

<br>

### Members & `__init__`

Always declare all members of a class in the `__init__` method.

**Wrong**

```python
class MyClass(object):
    def __init__(self):
        super(MyClass, self).__init__()

        self.height = 5

    def resize(self, width, height):
        self.height = height
        self.width = width
```

**Right**

```python
class MyClass(object):
    def __init__(self):
        super(MyClass, self).__init__()

        self.height = 5
        self.width = 5

    def resize(self, width, height):
        self.height = height
        self.width = width
```

The reason is discoverability. When members are attached to `self` in any subsequent method, it becomes difficult to tell whether it is being created, or modified.

<br>

### Relative imports

Where possible, relatively reference the root mgear package.

**Wrong**

```python
from mgear.core import rigbits
```

**Right**

```python
from .core import rigbits
```

This enables mgear to be bundled together with another library and avoids mgear being picked up from another location on a user's PYTHONPATH.

<br>

### Tuple versus List

Use List when mutability is required or intended, tuple otherwise.

```python
for item in ("good", "use", "of", "tuple"):
    pass
```

Tuples will tell you and the user when used in an unintended way, whereas a list would silently allow mutation.

<br>

### Mutable arguments

Never use a mutable object in an argument signature.

**Wrong**

```python
def function(wrong=[]):
    wrong.append(1)
    print(wrong)
```

**Right**

```python
def function(items=None):
    items = items or []
    items.append(1)
    print(items)
```

The same goes for `{}`. Pass `None` and convert internally.

<br>

### No type hints

mGear does not use Python type hints. Document types in **docstrings only**.

**Wrong**

```python
def create_shader(name: str, color: tuple) -> tuple:
    ...
```

**Right**

```python
def create_shader(name, color):
    """Create a shader.

    Args:
        name (str): Shader name.
        color (tuple): RGB color (r, g, b) with values 0-1.

    Returns:
        tuple: Tuple of (shader_node, shading_group) names.
    """
    ...
```

<br>

### No PyMEL

Use `mgear.pymaya` instead of PyMEL.

**Wrong**

```python
import pymel.core as pm
```

**Right**

```python
import mgear.pymaya as pm
```

<br>

### Docstrings

All docstrings are written in Google style with `Args:` (not `Arguments:`).

```python
def function(a, b=True):
    """Summary here, no line breaks.

    Long description here.

    Args:
        a (str): A first argument, mandatory.
        b (bool, optional): A second argument.

    Returns:
        bool: The result value.

    Example:
        >>> print("A doctest")
        'A doctest'

    """
```

<br>

### Naming Conventions

mGear historically uses **camelCase**. For consistency:

| Code Context | Convention | Example |
|--------------|------------|---------|
| **Existing modules** (editing/extending) | camelCase | `getTranslation()`, `myValue` |
| **New standalone tools** | PEP8 snake_case | `get_translation()`, `my_value` |
| **New code in existing modules** | Match surrounding code | (usually camelCase) |
| **Classes** | PascalCase | `SpringManager` |
| **Constants** | UPPER_SNAKE_CASE | `FILE_EXT` |
| **Private** | Leading underscore | `_getParent()` |

Within a single file, use ONE consistent style. Don't mix conventions.
