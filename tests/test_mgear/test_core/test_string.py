"""mgear.core.string test"""


def test_convert_rl_name(run_with_maya_standalone, setup_path):
    from mgear.core.string import convertRLName

    names = {
        "token_L": "token_R",
        "token_L_token": "token_R_token",
        "token_R_token": "token_L_token",
        "L_token": "R_token",
        "L_token_L_token": "R_token_R_token",
        "arm_L0_ctl": "arm_R0_ctl",
        "arm_R0_ctl": "arm_L0_ctl",
        "leg_l.vtx": "leg_r.vtx",
        "L": "R",
        "R": "L",
        "l": "r",
        "token": "token",
    }
    for name, expected in names.items():
        assert convertRLName(name) == expected


def test_normalize(run_with_maya_standalone, setup_path):
    from mgear.core.string import normalize
    from mgear.core.string import normalize2

    value = "1234-mgear=string@normalize"
    # normalize keeps "-", normalize2 replaces it too.
    assert normalize(value) == "_1234-mgear_string_normalize"
    assert normalize2(value) == "_1234_mgear_string_normalize"


def test_remove_invalid_character(run_with_maya_standalone, setup_path):
    from mgear.core.string import removeInvalidCharacter
    from mgear.core.string import removeInvalidCharacter2

    value = "1234-mgear=string@normalize_v1.0"
    assert removeInvalidCharacter(value) == "1234mgearstringnormalizev10"
    assert removeInvalidCharacter2(value) == "1234mgearstringnormalize_v1.0"


def test_replace_sharp_with_padding(run_with_maya_standalone, setup_path):
    from mgear.core.string import replaceSharpWithPadding

    assert replaceSharpWithPadding("value_###", 30) == "value_030"
    assert replaceSharpWithPadding("value", 12) == "value12"
    assert replaceSharpWithPadding("value", 2) == "value2"
    assert replaceSharpWithPadding("value#", 2) == "value2"
    assert replaceSharpWithPadding("value##", 2) == "value02"
