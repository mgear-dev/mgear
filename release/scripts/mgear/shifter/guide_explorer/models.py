from dataclasses import dataclass


@dataclass
class ShifterComponent:
    """
    Reference to a Shifter component in the scene.

    :param full_name: mGear guide key, for example "arm_L0".
    :param comp_type: mGear component type, for example "arm_2jnt".
    :param root_name: Root transform of the component.
    :param side: Component side string, for example "L" or "R".
    :param index: Component index on the given side.
    :param uuid: UUID of the component root transform.
    """
    full_name: str
    comp_type: str
    root_name: str
    side: str
    index: int
    uuid: str