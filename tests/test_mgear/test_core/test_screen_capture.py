"""mgear.core.screen_capture test"""

import pytest


def _module():
    # Skips where Qt is not importable (e.g. CI without Maya).
    return pytest.importorskip("mgear.core.screen_capture")


def test_normalize_rect(setup_path):
    screen_capture = _module()

    # Drag down-right, up-left, and the other diagonals give the same rect.
    expected = (10, 20, 30, 40)
    assert screen_capture.normalize_rect((10, 20), (40, 60)) == expected
    assert screen_capture.normalize_rect((40, 60), (10, 20)) == expected
    assert screen_capture.normalize_rect((10, 60), (40, 20)) == expected
    assert screen_capture.normalize_rect((40, 20), (10, 60)) == expected

    # A click without drag is an empty rect.
    assert screen_capture.normalize_rect((5, 5), (5, 5)) == (5, 5, 0, 0)


def test_logical_to_device_rect(setup_path):
    screen_capture = _module()

    rect = (10, 20, 30, 40)
    assert screen_capture.logical_to_device_rect(rect, 1.0) == rect
    assert screen_capture.logical_to_device_rect(rect, 2.0) == (20, 40, 60, 80)
    assert screen_capture.logical_to_device_rect(rect, 1.5) == (15, 30, 45, 60)

    # Fractional results round to the nearest physical pixel.
    assert screen_capture.logical_to_device_rect((1, 1, 3, 3), 1.25) == (
        1,
        1,
        4,
        4,
    )
