import string
import re
import mgear.pymaya as pm

# default fields/tokens
NAMING_RULE_TOKENS = ["component",
                      "side",
                      "index",
                      "description",
                      "extension"]
DEFAULT_NAMING_RULE = r"{component}_{side}{index}_{description}_{extension}"
DEFAULT_SIDE_L_NAME = "L"
DEFAULT_SIDE_R_NAME = "R"
DEFAULT_SIDE_C_NAME = "C"
DEFAULT_JOINT_SIDE_L_NAME = "L"
DEFAULT_JOINT_SIDE_R_NAME = "R"
DEFAULT_JOINT_SIDE_C_NAME = "C"
DEFAULT_CTL_EXT_NAME = "ctl"
DEFAULT_JOINT_EXT_NAME = "jnt"


def normalize_name_rule(text):
    """Normalize naming rule templates removing
    invalid characters

    :param text string: A text to normalize.
    :return text: Normalized text

    """
    text = str(text)

    if re.match("^[0-9]", text):
        text = "_" + text

    return re.sub("[^A-Za-z0-9_{}]", "", str(text))


def name_rule_validator(rule, valid_tokens, log=True):
    """Validate name rule

    Args:
        rule (str): Rule to validadte
        valid_tokens (list): Valid tokens for the rule
        log (bool, optional): if True will display warnings

    Returns:
        bool: True if the rule is valid
    """
    invalid_tokens = []
    for token in string.Formatter().parse(rule):

        if token[1] and token[1] in valid_tokens:
            continue
        # compare to None to avoid errors with empty token
        elif token[1] is None and token[0]:
            continue
        else:
            invalid_tokens.append(token[1])

    if invalid_tokens:
        if log:
            pm.displayWarning(
                "{} not valid token".format(invalid_tokens))
            pm.displayInfo("Valid tokens are: {}".format(NAMING_RULE_TOKENS))
        return
    else:
        return True


def name_solve(rule, values, validate=True):
    """Solve the name of the object based on the rule

    Args:
        rule (str): name rule
        values (dict): Values to populate the name rule
        validate (bool, optional): If True will validate the rule
            before solve it

    Returns:
        str: The solved name
    """
    # index padding
    values["index"] = str.zfill(values["index"], values["padding"])
    included_val = dict()
    if validate and not name_rule_validator(rule, NAMING_RULE_TOKENS):
        return
    for token in string.Formatter().parse(rule):
        if token[1]:
            try:
                included_val[token[1]] = values[token[1]]
            except KeyError:
                continue
        elif token[0]:
            continue
        else:
            return

    return rule.format(**included_val)


def letter_case_solve(name, letter_case=0):
    """Change the letter case

    Args:
        name (str): name
        letter_case (int, optional):
            0 = will not change the leter casing
            1 = will convert all letters to upper case
            2 = will convert all letters to lower case
            3 = will capitalize the first letter of the name

    Returns:
        TYPE: Description
    """
    if letter_case == 1:
        name = name.upper()
    elif letter_case == 2:
        name = name.lower()
    elif letter_case == 3:
        name = name.capitalize()
    return name


def get_component_and_relative_name(guide_name):
    """Get the component name and the relative local name of the guide

        The component name:
            ie. "arm_C0_root" return "arm_C0"

        The local relative name:
            ie. "arm_C0_root" return "root"
    Args:
        guide_name (str): Name of the guide object

    Returns:
        TYPE: Description
    """
    guide_name_split = guide_name.split("_")
    # chains are the only component that have 2 parts at the end
    if guide_name.endswith("_loc"):
        n = 2
    else:
        n = 1
    comp_name = "_".join(guide_name_split[:-n])
    local_relative_name = "_".join(guide_name_split[-n:])

    return comp_name, local_relative_name
