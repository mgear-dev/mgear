"""mgear package test"""


def test_mgear_version(setup_path):
    import mgear

    assert len(mgear.VERSION) == 3
    assert all(isinstance(number, int) for number in mgear.VERSION)
    assert mgear.getVersion() == "{}.{}.{}".format(*mgear.VERSION)
