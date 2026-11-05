"""Tests for the custom step log helper."""

import pytest


@pytest.fixture
def step(setup_path):
    """A custom step named "test_step"."""
    from mgear.shifter import custom_step

    class Step(custom_step.customShifterMainStep):
        def setup(self):
            self.name = "test_step"

        def run(self):
            pass

    instance = Step({})
    instance.setup()
    return instance


@pytest.fixture
def log_handler(setup_path):
    """A build log handler receiving the pm.display* messages."""
    from mgear.shifter.build_log import core
    from mgear.shifter.build_log import ui

    handler = core.BuildLogHandler()
    ui._install_display_hooks(handler)
    try:
        yield handler
    finally:
        ui._uninstall_display_hooks()


@pytest.mark.parametrize(
    "level,severity",
    (("error", "sev_error"), ("warning", "sev_warning")),
)
def test_log_level_reaches_build_log(step, log_handler, level, severity):
    """Errors and warnings are logged without raising (#652)."""
    import mgear

    step.log("Missing component", level=level)
    assert [(r.message, r.severity) for r in log_handler.records] == [
        ("[test_step] Missing component", getattr(mgear, severity))
    ]


def test_log_info_prints(step, log_handler, capsys):
    """Info messages print with the step name prefix."""
    step.log("Processing controls")
    assert "[test_step] Processing controls" in capsys.readouterr().out
    assert log_handler.records == []
