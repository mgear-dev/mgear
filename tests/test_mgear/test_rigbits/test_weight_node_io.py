"""mgear.rigbits weight driver IO: export and import the node data files"""

import json

import pytest


@pytest.mark.parametrize("module_name", ["mGearWeightNode_io", "weightNode_io"])
def test_export_and_import_nodes(setup_path, monkeypatch, tmp_path, module_name):
    """exportNodes and importNodes write and read the file through rbf_io."""
    import importlib

    from mgear.rigbits import rbf_io

    try:
        module = importlib.import_module("mgear.rigbits." + module_name)
    except Exception as error:
        pytest.skip("{} can't load: {}".format(module_name, error))
    infos = {"driver_WD": {"poses": {"input": [[0.0]]}}}
    monkeypatch.setattr(module, "getNodesInfo", lambda nodes: dict(infos))
    created = []
    monkeypatch.setattr(
        module,
        "createRBFFromInfo",
        lambda data: created.append(data) or list(data),
    )
    path = str(tmp_path / "nodes.rbf")
    module.exportNodes(path, ["driver_WD"])
    with open(path) as handle:
        assert json.load(handle) == infos
    module.importNodes(path)
    assert created == [infos]
    # the older private names still work
    assert getattr(rbf_io, "__importData") is rbf_io._importData
    assert getattr(rbf_io, "__exportData") is rbf_io._exportData
