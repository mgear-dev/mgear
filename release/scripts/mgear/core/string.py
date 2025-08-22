"""string management methods"""

##########################################################
# GLOBAL
##########################################################
import re
import os

##########################################################
# FUNCTIONS
##########################################################


def normalize(string):
    """Replace all invalid characters with "_"

    :param string string: A string to normalize.
    :return string: Normalized string

    """
    string = str(string)

    if re.match("^[0-9]", string):
        string = "_" + string

    return re.sub("[^A-Za-z0-9_-]", "_", str(string))


def normalize2(string):
    """Replace all invalid characters with "_". including "-"
    This ensure that the name is compatible with Maya naming rules

    :param string string: A string to normalize.
    :return string: Normalized string

    """
    string = str(string)

    if re.match("^[0-9]", string):
        string = "_" + string

    return re.sub("[^A-Za-z0-9_]", "_", str(string))


def normalize_path(string):
    """Ensure that string path use always forward slash

    Args:
        string (TYPE): Description

    Returns:
        TYPE: Description
    """
    return string.replace("\\", "/")


def normalize_with_padding(string):
    """Replace all invalid characters with "_". including "-"
    This ensure that the name is compatible with Maya naming rules

    Also list of # symbol with properly padded index.

    ie. count_### > count_001

    :param string string: A string to normalize.
    :return string: Normalized string

    """
    string = str(string)

    if re.match("^[0-9]", string):
        string = "_" + string

    return re.sub("[^A-Za-z0-9_#]", "_", str(string))


def removeInvalidCharacter(string):
    """Remove all invalid character.

    :param string string: A string to normalize.
    :return string: Normalized string.

    """
    return re.sub("[^A-Za-z0-9]", "", str(string))


def removeInvalidCharacter2(string):
    """Remove all invalid character. Incluede "_" and "."as valid character.

    :param string string: A string to normalize.
    :return string: Normalized string.

    """
    return re.sub("[^A-Za-z0-9_.]", "", str(string))


def replaceSharpWithPadding(string, index):
    """Replace a list of # symbol with properly padded index.

    ie. count_### > count_001

    :param string string: A string to set. Should include '#'
    :param integer index: Index to replace.
    :return string: Normalized string.

    """
    if string.count("#") == 0:
        string += "#"

    digit = str(index)
    while len(digit) < string.count("#"):
        digit = "0" + digit

    return re.sub("#+", digit, string)


def convertRLName(name):
    """Convert a string with underscore

    i.e: "_\L", "_L0\_", "L\_", "_L" to "R". And vice and versa.

    :param string name: string to convert
    :return: Tuple of Integer

    """
    if name == "L":
        return "R"
    elif name == "R":
        return "L"
    elif name == "l":
        return "r"
    elif name == "r":
        return "l"

    re_str = "_[RLrl][0-9]+_|^[RLrl][0-9]+_"
    re_str = re_str + "|_[RLrl][0-9]+$|_[RLrl]_|^[RLrl]_|_[RLrl]$"
    re_str = re_str + "|_[RLrl][.]|^[RLrl][.]"
    re_str = re_str + "|_[RLrl][0-9]+[.]|^[RLrl][0-9]+[.]"
    rePattern = re.compile(re_str)

    matches = re.findall(rePattern, name)
    if matches:
        for match in matches:
            if match.find("R") != -1:
                rep = match.replace("R", "L")
            elif match.find("L") != -1:
                rep = match.replace("L", "R")
            elif match.find("r") != -1:
                rep = match.replace("r", "l")
            elif match.find("l") != -1:
                rep = match.replace("l", "r")
            name = re.sub(match, rep, name)

    return name


# NOTE: Keeping the old version just in case an error ocurs
# TODO: Delete old function when the new one is well tested
def convertRLName_old(name):
    """Convert a string with underscore

    i.e: "_\L", "_L0\_", "L\_", "_L" to "R". And vice and versa.

    :param string name: string to convert
    :return: Tuple of Integer

    """
    if name == "L":
        return "R"
    elif name == "R":
        return "L"
    elif name == "l":
        return "r"
    elif name == "r":
        return "l"

    # re_str = "_[RL][0-9]+_|^[RL][0-9]+_|_[RL][0-9]+$|_[RL]_|^[RL]_|_[RL]$"

    # adding support to conver l and r lowecase side label.
    re_str = "_[RLrl][0-9]+_|^[RLrl][0-9]+_"
    re_str = re_str + "|_[RLrl][0-9]+$|_[RLrl]_|^[RLrl]_|_[RLrl]$"
    re_str = re_str + "|_[RLrl][.]|^[RLrl][.]"
    re_str = re_str + "|_[RLrl][0-9]+[.]|^[RLrl][0-9]+[.]"
    rePattern = re.compile(re_str)

    reMatch = re.search(rePattern, name)
    if reMatch:
        instance = reMatch.group(0)
        if instance.find("R") != -1:
            rep = instance.replace("R", "L")
        elif instance.find("L") != -1:
            rep = instance.replace("L", "R")
        elif instance.find("r") != -1:
            rep = instance.replace("r", "l")
        elif instance.find("l") != -1:
            rep = instance.replace("l", "r")
        name = re.sub(rePattern, rep, name)

    return name


# String renamer in files
def replace_string_in_file(search_string, replace_string, new_filename,
                           source_path):
    """Replace all occurrences of a string in an ASCII file and save a copy.

    Args:
        search_string (str): string to search in the file.
        replace_string (str): string to replace the search_string with.
        new_filename (str): Name for the modified file.
        source_path (str): Path to the original ASCII file.

    Returns:
        tuple: (str) Path to the modified file,
               (int) Number of replacements made.
    """
    if not os.path.isfile(source_path):
        raise IOError("Source file does not exist: {}".format(source_path))

    with open(source_path, 'r') as src_file:
        content = src_file.read()

    count = content.count(search_string)
    content = content.replace(search_string, replace_string)

    folder = os.path.dirname(source_path)
    new_path = os.path.join(folder, new_filename)

    with open(new_path, 'w') as new_file:
        new_file.write(content)

    return new_path, count
