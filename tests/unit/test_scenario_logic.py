from qemulab.models.scenario import Scenario, ScenarioConfig


def test_scenario_file_discovery(tmp_path):
    """
    Creates a fake directory structure:
    - cfg_dut1
    - cfg_dut2
    - cfg_dut3
    - scenario.json
    - random_file.txt (should be ignored)
    - cfg_dut_invalid (should be ignored)
    """
    scenario_dir = tmp_path / "ospf_topo"
    scenario_dir.mkdir()

    # Create valid files
    (scenario_dir / "cfg_dut1").touch()
    (scenario_dir / "cfg_dut2").touch()
    (scenario_dir / "cfg_dut3").touch()

    # Create noise
    (scenario_dir / "random.txt").touch()
    (scenario_dir / "cfg_dut_backup").touch()  # Invalid format

    # Create dummy config
    config = ScenarioConfig(description="Test")

    # Instantiate Model
    scenario = Scenario(name="ospf_topo", path=scenario_dir, config=config)

    # Assertions
    assert scenario.default_node_count == 3
    assert scenario.available_node_ids == [1, 2, 3]
    assert 1 in scenario.dut_files
    assert 4 not in scenario.dut_files  # Matches strict counting


def test_missing_config_files(tmp_path):
    """Test a scenario that has json but no cfg files."""
    scenario_dir = tmp_path / "empty_topo"
    scenario_dir.mkdir()
    config = ScenarioConfig(description="Empty")

    scenario = Scenario(name="empty", path=scenario_dir, config=config)

    assert scenario.default_node_count == 0
    assert scenario.dut_files == {}
