# mgear
import mgear


ANIM_PICKER_TITLE = "Anim Picker {ap_version} | mGear {m_version}"

# maya color index
MAYA_OVERRIDE_COLOR = {
    0: [48, 48, 48],
    1: [0, 0, 0],
    2: [13, 13, 13],
    3: [81, 81, 81],
    4: [84, 0, 5],
    5: [0, 0, 30],
    6: [0, 0, 255],
    7: [0, 16, 2],
    8: [5, 0, 14],
    9: [147, 0, 147],
    10: [65, 17, 8],
    11: [13, 4, 3],
    12: [81, 5, 0],
    13: [255, 0, 0],
    14: [0, 255, 0],
    15: [0, 13, 81],
    16: [255, 255, 255],
    17: [255, 255, 0],
    18: [32, 183, 255],
    19: [14, 255, 93],
    20: [255, 111, 111],
    21: [198, 105, 49],
    22: [255, 255, 32],
    23: [0, 81, 23],
    24: [91, 37, 8],
    25: [87, 91, 8],
    26: [35, 91, 8],
    27: [8, 91, 28],
    28: [8, 91, 91],
    29: [8, 35, 91],
    30: [41, 8, 91],
    31: [91, 8, 37],
}

GROUPBOX_BG_CSS = """QGroupBox {{
      background-color: rgba{color};
      border: 0px solid rgba{color};
}}"""


_mgear_version = mgear.getVersion()

PICKER_EXTRACTION_NAME = "pickerData_extraction"
ANIM_PICKER_RELATIVE_IMAGES = "ANIM_PICKER_RELATIVE_IMAGES"

"""
/animpickers/characterA/publish/pkr/charact.pkr
/animpickers/characterA/publish/pkr/../images
examples "../images", "../../images", ""
"""
# default image location is assumed same as .pkr file
DEFAULT_RELATIVE_IMAGES_PATH = ""
