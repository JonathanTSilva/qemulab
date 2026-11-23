"""SessionContext node-count rules."""

from qemulab.models.context import SessionContext
from qemulab.models.scenario import Scenario, ScenarioConfig


def _scenario(tmp_path, nodes: int) -> Scenario:
    for i in range(1, nodes + 1):
        (tmp_path / f"cfg_dut{i}").write_text("x")
    return Scenario(name="s", path=tmp_path, config=ScenarioConfig())


def test_node_count_defaults_to_zero():
    assert SessionContext(selected_board="b").node_count == 0


def test_node_count_follows_scenario_then_manual_override(tmp_path):
    ctx = SessionContext(selected_board="b", selected_scenario=_scenario(tmp_path, 3))
    assert ctx.node_count == 3
    ctx.set_manual_node_count(2)
    assert ctx.node_count == 2
    ctx.reset_node_count()
    assert ctx.node_count == 3


def test_scenario_with_missing_directory_has_no_nodes(tmp_path):
    scenario = Scenario(name="s", path=tmp_path / "gone", config=ScenarioConfig())
    assert scenario.dut_files == {}
    assert scenario.default_node_count == 0
