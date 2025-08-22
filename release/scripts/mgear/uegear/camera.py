import maya.cmds as cmds

def mm_to_inches(mm_value):
    """
    Converts the mm value to an Inch value

    mm_value
        Millimeter value that will be converted into Inches
    """
    return mm_value / 25.4


def has_filmback_attribute(obj_name):
    """
    Checks if the object (Usually a camera) has any film back attributes added to it.
    """
    attributes = cmds.listAttr(obj_name)

    if any('Filmback' in name for name in attributes):
        return True
    return False

def get_sensor_attributes(obj_name):
    """Retrieves the Sensor / filmback attributes"""
    sensor_names = ("SensorHeight", "SensorWidth")
    found_attributes = [None, None]

    for attribute_name in cmds.listAttr(obj_name):
        for i, sensor_name in enumerate(sensor_names):
            if sensor_name in attribute_name:
                found_attributes[i] = attribute_name

    return found_attributes


def get_keys_for_attribute(obj_name, attribute):
    """Gets the keyframe data for the specific attribute"""
    full_attr = f"{obj_name}.{attribute}"
    key_times = cmds.keyframe(full_attr, query=True, timeChange=True)
    key_values = cmds.keyframe(full_attr, query=True, valueChange=True)
    return key_times, key_values

def apply_updated_keys(obj_name, attribute, key_times, updated_values):
    """Adds keys to the specific attribute using the keys time and value arrays"""
    full_attr = f"{obj_name}.{attribute}"
    for time, value in zip(key_times, updated_values):
        cmds.setKeyframe(full_attr, time=time, value=value)

def unreal_to_maya_sensor_conversion(camera_name):
    """
    Converts an Unreal mm Film Back sensor into a Maya inch film apature value, and applies
    it to the camera shape
    """
    sensor_exists = has_filmback_attribute(camera_name)

    if sensor_exists:
        sensor_names = get_sensor_attributes(camera_name)

        for sensor_name in sensor_names:
            frames, values = get_keys_for_attribute(camera_name, sensor_name)
            values = [mm_to_inches(val) for val in values]

            if 'Height' in sensor_name:
                apply_updated_keys(camera_name, 'verticalFilmAperture', frames, values)
            if 'Width' in sensor_name:
                apply_updated_keys(camera_name, 'horizontalFilmAperture', frames, values)