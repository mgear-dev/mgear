import json

import mgear.pymaya as pm
from mgear.shifter import guide


def updateGuide(*args):
    """Update the guide rig"""
    if pm.selected():
        oSel = pm.selected()[0]
        if oSel.hasAttr("isGearGuide"):
            oSel = oSel.getParent(-1)
        rgGuide = guide.Rig()
        rgGuide.update(oSel)
    else:
        pm.displayWarning("Please select the guide top node")


def guide_toggle_xray(*args):
    guide_root = None
    if pm.selected():
        oSel = pm.selected()[0]
        if oSel.hasAttr("isGearGuide"):
            oSel = oSel.getParent(-1)
        if oSel.hasAttr("ismodel"):
            guide_root = oSel
    if guide_root and guide_root.hasAttr("guide_x_ray"):
        if guide_root.guide_x_ray.get():
            guide_root.guide_x_ray.set(False)
        else:
            guide_root.guide_x_ray.set(True)



# guide differences checkers
##################################


def guide_component_diff(guideA, guideB):
    """Components matching report.

    Compare guide "A" components, against guide "B" components. Considering A
    the guide that we want to check and B the guide used as a checker.

    Return a dictionary with marching components, missing components and
    extra components.

    dictionary keys = match, miss, extra

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template

    Returns:
        dict: Component matching report in dict format.

    """
    compA = guideA["components_list"]
    compB = guideB["components_list"]

    match = [c for c in compA if c in compB]
    miss = list(set(compB).difference(compA))
    extra = list(set(compA).difference(compB))

    diff_dict = {"match": match, "miss": miss, "extra": extra}

    return diff_dict


def guide_transform_diff(guideA, guideB, pos=False):
    """Return guide transform differences

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        pos (bool, optional): If True, will check the positions, instead of
            the full transform.

    Returns:
        list, list: not_match_tra, root_tra_match
    """
    # get matching components
    match_comp = guide_component_diff(guideA, guideB)["match"]

    # check matching components transform
    not_match_tra = component_transform_diff(guideA,
                                             guideB,
                                             match_comp,
                                             componentB=None,
                                             pos=pos)

    # check root position
    root_tra_A = guideA["guide_root"]['tra']
    root_tra_B = guideB["guide_root"]['tra']
    if root_tra_A != root_tra_B:
        root_tra_match = False
    else:
        root_tra_match = True

    return not_match_tra, root_tra_match


def guide_root_settings_diff(guideA, guideB):
    """Summary

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template

    Returns:
        dict: not matching elements
    """
    pvA = guideA["guide_root"]['param_values']
    pvB = guideB["guide_root"]['param_values']

    pdiff = param_diff(pvA, pvB)
    if pdiff:
        not_found_param = pdiff["not_found_param"]
        not_match_param = []
        # need to separate the configuration parameter settings from the pure
        # information parameters and custom step
        not_check_param_list = ["date",
                                "user",
                                "ismodel",
                                "maya_version",
                                "gear_version",
                                "preCustomStep",
                                "postCustomStep"]
        for p in pdiff["not_match_param"]:
            if p[0] not in not_check_param_list:
                not_match_param.append(p)

        not_match = {}
        if not_found_param or not_match_param:
            not_match = {"not_found_param": not_found_param,
                         "not_match_param": not_match_param}
        return not_match


def guide_component_settings_diff(guideA, guideB, comp_diff=None):
    """Summary

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        comp_diff (None, dict): Component difference dictionary

    Returns:
        list: the not matching settings dict and the missing comonent list
    """
    if not comp_diff:
        comp_diff = guide_component_diff(guideA, guideB)

    match = comp_diff["match"]
    miss = comp_diff["miss"]
    comp_sett_diff = component_settings_diff(guideA, guideB, match)

    return [comp_sett_diff, miss]


def pre_custom_step_diff(guideA, guideB):
    """Check pre custom steps list differences.

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template

    Returns:
        list: missing custom steps, diff path, diff statatus, match order bool
    """
    return custom_step_diff(guideA, guideB, "preCustomStep")


def post_custom_step_diff(guideA, guideB):
    """Check post custom steps list differences.

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template

    Returns:
        list: missing custom steps, diff path, diff statatus, match order bool
    """
    return custom_step_diff(guideA, guideB, "postCustomStep")


def custom_step_diff(guideA, guideB, customStep_param):
    """Check custom steps list differences.

    The function will check for missing custom steps, matching custon steps
    but with different path, different status and general order of execution

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        customStep_param (str): Custom step parameter name

    Returns:
        dict: missing custom steps, diff path, diff statatus, match order bool
    """
    cs_valA = guideA["guide_root"]["param_values"][customStep_param]
    csA = custom_step_values(cs_valA)
    cs_valB = guideB["guide_root"]["param_values"][customStep_param]
    csB = custom_step_values(cs_valB)
    # find if any custom step from B is missing in A
    miss = [cs for cs in csB["names"] if cs not in csA["names"]]
    # same custom steps with diff path
    match = [cs for cs in csA["names"] if cs in csB["names"]]
    diff_path = [cs for cs in match if csA["path"][cs] != csB["path"][cs]]
    diff_stat = [cs for cs in match if csA["status"][cs] != csB["status"][cs]]
    # custom step order
    matchB = [cs for cs in csB["names"] if cs in csA["names"]]
    if match == matchB:
        match_order = True
    else:
        match_order = False

    return {"miss": miss,
            "path": diff_path,
            "status": diff_stat,
            "order": match_order}


# component difference checkers
##################################


def componentAB_type_diff(guideA, guideB, componentA, componentB=None):
    """Return list of not matching types components and the types found

    Usually componentA list and componentB list is the same list. But keeping
    this separated we can check an arbitrary list with not matching names.
    In this case the componentB list should match the order and number of
    componentA types

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        componentA (str or str list): Names of the components to check
        componentB (None, optional): If None will use the component A list in
            both guides

    Returns:
        list: Not matching components
    """
    componentA, componentB = to_list_AB(componentA, componentB)

    not_match = []
    for ca, cb in zip(componentA, componentB):
        typeA = guideA["components_dict"][ca]['param_values']['comp_type']
        typeB = guideB["components_dict"][cb]['param_values']['comp_type']
        if typeA != typeB:
            not_match.append([ca, cb, typeA, typeB])
    return not_match


def component_type_diff(guideA, guideB, component):
    """Return Dictionary with not maching components and types

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        componentA (str or str list): Names of the components to check

    Returns:
        dict: Not matching components
    """
    not_match = componentAB_type_diff(guideA, guideB, component)
    not_match_dict = {}
    for c in not_match:
        not_match_dict[c[0]] = [c[2], c[3]]

    return not_match_dict


def component_transform_diff(guideA,
                             guideB,
                             componentA,
                             componentB=None,
                             pos=False):
    """Return a dictionary with the not matching transform and blades

    If the position information is miss or missmatch the report
    will inform

    Usually componentA list and componentB list is the same list. But keeping
    this separated we can check an arbitrary list with not matching names.
    In this case the componentB list should match the order and number of
    componentA types

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        componentA (str or str list): Names of the components to check
        componentB (None, optional): If None will use the component A list in
            both guides
        pos (bool, optional): If True will check only the position not the full
            transformation of the componet locators

    Returns:
        dict: Not matching components transform
    """
    if pos:
        check = "pos"
    else:
        check = "tra"

    componentA, componentB = to_list_AB(componentA, componentB)
    not_match_dict = {}
    for ca, cb in zip(componentA, componentB):
        # check transform
        traA_dict = guideA["components_dict"][ca][check]
        traB_dict = guideB["components_dict"][cb][check]
        not_found_tra, not_match_tra = tra_diff(traA_dict, traB_dict)

        # check blades
        bladesA = guideA["components_dict"][ca]['blade']
        bladesB = guideB["components_dict"][cb]['blade']
        not_found_blades, not_match_blades = tra_diff(bladesA, bladesB)

        if (not_found_tra
                or not_match_tra
                or not_found_blades
                or not_match_blades):
            not_match_dict[ca] = {"not_found_tra": not_found_tra,
                                  "not_match_tra": not_match_tra,
                                  "not_found_blades": not_found_blades,
                                  "not_match_blades": not_match_blades}

    return not_match_dict


def component_settings_diff(guideA, guideB, componentA, componentB=None):
    """Return list of not matching types components and the types found

    Usually componentA list and componentB list is the same list. But keeping
    this separated we can check an arbitrary list with not matching names.
    In this case the componentB list should match the order and number of
    componentA types

    Args:
        guideA (dict): Guide dictionary template
        guideB (dict): Guide dictionary template
        componentA (str or str list): Names of the components to check
        componentB (None, optional): If None will use the component A list in
            both guides

    Returns:
        dict: Not matching components settings
    """
    componentA, componentB = to_list_AB(componentA, componentB)
    not_match = {}
    for ca, cb in zip(componentA, componentB):
        pvA = guideA["components_dict"][ca]['param_values']
        pvB = guideB["components_dict"][cb]['param_values']
        cp_not_match = param_diff(pvA, pvB)
        if cp_not_match:
            not_match[ca] = cp_not_match

    return not_match


# Guide difference Report
def guide_diff(guide,
               master_guide,
               check_missing_guide_component_diff=True,
               check_extra_guide_component_diff=False,
               check_guide_transform_diff=True,
               check_guide_root_settings_diff=True,
               check_component_settings_diff=True,
               check_guide_custom_step_diff=True):
    """Compare a guide agaisnt a master guide. This check will return false,
    if the guide match the elments found in master_guide.

    Args:
        guide (dict): Guide dictionary template
        master_guide (dict): Guide dictionary template
        check_missing_guide_component_diff (bool, optional):
            If true, will check missing components diff
        check_extra_guide_component_diff (bool, optional):
            If true, will check extra components diff
        check_guide_transform_diff (bool, optional):
            If true, will check the transform differences
        check_guide_root_settings_diff (bool, optional):
            If true, will check the root parameter settings differences
        check_component_settings_diff (bool, optional):
            If true, will check the component settings differences
        check_guide_custom_step_diff (bool, optional):
            If true, will chekc the custom steps differences


    Returns:
        dict: Differences dictionary. False if the test pass
    """
    gdiff = {}
    if check_missing_guide_component_diff or check_extra_guide_component_diff:
        comp_diff = guide_component_diff(guide, master_guide)
    if check_missing_guide_component_diff:
        if comp_diff and comp_diff["miss"]:
            gdiff["components_miss"] = comp_diff["miss"]

    if check_extra_guide_component_diff:
        if comp_diff and comp_diff["extra"]:
            gdiff["components_extra"] = comp_diff["extra"]

    if check_guide_transform_diff:
        not_match_tra, root_tra = guide_transform_diff(guide, master_guide)
        if not_match_tra:
            gdiff["component_transform_diff"] = not_match_tra
        if not root_tra:
            gdiff["root_transform_not_match"] = root_tra

    if check_guide_root_settings_diff:
        root_sett_diff = guide_root_settings_diff(guide, master_guide)
        if root_sett_diff:
            if (root_sett_diff["not_found_param"]
                    or root_sett_diff["not_match_param"]):
                gdiff["root_settings_diff"] = root_sett_diff

    if check_component_settings_diff:
        comp_sett_diff = guide_component_settings_diff(guide, master_guide)
        if comp_sett_diff and comp_sett_diff[0]:
            gdiff["component_settings_diff"] = comp_sett_diff[0]

    if check_guide_custom_step_diff:
        pre_diff = pre_custom_step_diff(guide, master_guide)
        if (pre_diff["miss"]
                or pre_diff["path"]
                or pre_diff["status"]
                or not pre_diff["order"]):
            gdiff["pre_diff"] = pre_diff

        post_diff = post_custom_step_diff(guide, master_guide)
        if (post_diff["miss"]
                or post_diff["path"]
                or post_diff["status"]
                or not post_diff["order"]):
            gdiff["post_diff"] = post_diff

    if gdiff:
        return gdiff


def print_guide_diff(diff_report):

    if diff_report:

        if "components_miss" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("The guide is missing some components:")
            print(json.dumps(diff_report["components_miss"], indent=4))

        if "components_extra" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("The guide has some extra components:")
            print(json.dumps(diff_report["components_extra"], indent=4))

        if "root_transform_not_match" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("The guide root position is not matching")
            print(json.dumps(diff_report["root_transform_not_match"],
                             indent=4))

        if "component_transform_diff" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("The guide components position is not "
                              "matching")
            print(json.dumps(diff_report["component_transform_diff"],
                             indent=4))

        if "root_settings_diff" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("Guide root not matching settings "
                              "parameters")
            print(json.dumps(diff_report["root_settings_diff"], indent=4))

        if "component_settings_diff" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("Components not matching parameters"
                              " found")
            print(json.dumps(diff_report["component_settings_diff"], indent=4))

        if "pre_diff" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("Pre Custom steps differences found")
            print(json.dumps(diff_report["pre_diff"], indent=4))

        if "post_diff" in diff_report.keys():
            print("".join(["="] * 80))
            pm.displayWarning("post Custom steps differences found")
            print(json.dumps(diff_report["post_diff"], indent=4))


# helper functions
def to_list(item):
    """Convert items to list

    Args:
        item (var): item to convert to list, if it is not list

    Returns:
        list: list with the items
    """
    if not isinstance(item, list):
        return list(item)
    else:
        return item


def to_list_AB(componentA, componentB):
    """Conver to list  and copy list A to B if B is None

    Args:
        componentA (list): Components list
        componentB (list): Components list

    Returns:
        list, list: componentA, componentB
    """
    componentA = to_list(componentA)
    if not componentB:
        componentB = componentA
    componentB = to_list(componentB)

    return componentA, componentB


def param_diff(pvA, pvB):
    """Compare the parameter differences

    Args:
        pvA (dict): parameter values dictionary
        pvB (dict): parameter values dictionary

    Returns:
        dict: Not matching settings
    """

    not_match = {}
    not_found_param, not_match_param = dict_diff(pvA, pvB)
    if not_found_param or not_match_param:
        not_match = {"not_found_param": not_found_param,
                     "not_match_param": not_match_param}
    return not_match


def dict_diff(dictA, dictB):
    """Return key and value differences from 2 given dictionaries

    Args:
        dictA (dict): Dictionary A
        dictB (dict): Dictionary B

    Returns:
        list, lit: Not found keys, not matching values
    """
    not_found_key = []
    not_match_value = []
    for k in dictA.keys():
        if k in dictB.keys():
            if dictA[k] != dictB[k]:
                not_match_value.append([k, dictA[k], dictB[k]])
        else:
            not_found_key.append(k)

    return not_found_key, not_match_value


def truncate_tra_dict_values(tra_dict):
    """We need to truncate the values in order to avoid precision errors.

    In some situations if import and export the guide, due Maya's precision
    limitations we may find some minimal values change.

    i.e: from 2.9797855669897326e-16  to 2.9797855669897321e-16 (Note the value
     is e-16, so is really close to 0 in both)

    Args:
        tra_dict (dict): Transform or position dictionary

    Returns:
        dict: the same transform dictionary with some precision truncated
    """
    for k in tra_dict.keys():
        for ic, col in enumerate(tra_dict[k]):
            if isinstance(col, list):
                for i, v in enumerate(col):
                    col[i] = float('{:f}'.format(v))

            else:
                for e, v in enumerate(tra_dict[k]):
                    tra_dict[k][e] = float('{:f}'.format(v))
    return tra_dict


def tra_diff(tra_dictA, tra_dictB):
    """Check the differences between 2 transform dictionary

    This function will truncate the values before make the comparation.

    Args:
        tra_dictA (dict): Transform or position dictionary
        tra_dictB (dict): Transform or position dictionary

    Returns:
        dict: Not matching transforms or positions
    """
    tra_dictA = truncate_tra_dict_values(tra_dictA)
    tra_dictB = truncate_tra_dict_values(tra_dictB)

    return dict_diff(tra_dictA, tra_dictB)


def custom_step_values(customStep_val):
    cs_names = []
    cs_path = {}
    # if the custom step is on/off
    cs_status = {}
    if customStep_val:
        cs_val = customStep_val.split(",")

        for cs in cs_val:
            cs_parts = cs.split("|")
            name = cs_parts[0][:-1]
            if name.startswith("*"):
                name = name[1:]
                cs_status[name] = False
            else:
                cs_status[name] = True
            cs_names.append(name)
            cs_path[name] = cs_parts[1][0:]

    return {"names": cs_names, "path": cs_path, "status": cs_status}
