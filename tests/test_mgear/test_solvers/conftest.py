"""Fixtures shared by the mgear_solvers plug-in tests."""

import pytest


@pytest.fixture
def solvers(load_repo_plugin):
    """The mgear_solvers plug-in of this repository, in a new scene.

    The plug-in built for the running Maya in ``release/platforms`` is
    loaded first, so tests run against the repository build.
    """
    from maya import cmds

    if not load_repo_plugin("mgear_solvers"):
        pytest.skip("mgear_solvers plug-in not available")
    cmds.file(new=True, force=True)
    return cmds
