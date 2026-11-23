"""Pilot-driven tests of the full app: wizard flow, launch, quit and cleanup paths.

Everything that would touch the system (sudo, tmux, QEMU, the network) is replaced with fakes.
"""

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Button, ContentSwitcher, Input, ListView

from qemulab.config.settings import settings
from qemulab.ui.app import QemuLabApp
from qemulab.ui.modals import CleanupModal, PasswordModal


@pytest.fixture(autouse=True)
def restore_root_logger():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
    root.setLevel(level)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """One board with one version and a two-node scenario, all under tmp_path."""
    images = tmp_path / "images"
    image_dir = images / "board1" / settings.images_subdir
    image_dir.mkdir(parents=True)
    (image_dir / "board1-bzImage-1.0").touch()
    (image_dir / "board1-rootfs.cpio-1.0").touch()

    scenarios = tmp_path / "scenarios"
    scn = scenarios / "ospf"
    scn.mkdir(parents=True)
    (scn / "scenario.json").write_text('{"description": "d"}')
    (scn / "cfg_dut1").write_text("a")
    (scn / "cfg_dut2").write_text("b")

    monkeypatch.setattr(settings, "images_base_path", images)
    monkeypatch.setattr(settings, "scenarios_path", scenarios)
    monkeypatch.setattr(settings, "flash_base_path", str(tmp_path / "flash_"))
    return tmp_path


async def _pick_first(app, pilot, list_id: str) -> None:
    app.query_one(f"#{list_id}", ListView).focus()
    await pilot.pause()
    await pilot.press("down", "enter")
    await pilot.pause()


async def test_full_wizard_flow_reaches_confirmation(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        wizard = app._wizard_screen
        assert wizard.boards == ["board1"]

        await _pick_first(app, pilot, "list-board")
        assert app.ctx.selected_board == "board1"
        assert wizard.current_step_idx == 1

        await _pick_first(app, pilot, "list-version")
        assert app.ctx.selected_version == "1.0"
        assert app.ctx.kernel_path is not None
        assert wizard.current_step_idx == 2

        await _pick_first(app, pilot, "list-scenario")
        assert app.ctx.selected_scenario.name == "ospf"
        assert wizard.current_step_idx == 3

        await _pick_first(app, pilot, "list-node-count")
        assert app.ctx.node_count == 1
        assert wizard.current_step_idx == 4
        assert app.query_one("#btn-launch", Button)

        # Going back works from the wizard, and stops at the first step.
        await pilot.press("b")
        assert wizard.current_step_idx == 3


async def test_wizard_step_click_only_goes_backwards(lab):
    from qemulab.ui.components import StepClicked

    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        wizard = app._wizard_screen
        wizard.switch_to_step(2)
        wizard.on_step_clicked(StepClicked(0))
        assert wizard.current_step_idx == 0
        wizard.on_step_clicked(StepClicked(3))
        assert wizard.current_step_idx == 0


async def test_wizard_rejects_version_without_kernel(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.ctx.selected_board = "board1"
        app._wizard_screen.versions = ["1.0"]
        from qemulab.ui.components import ItemSelected

        with patch(
            "qemulab.ui.screens.wizard.Scanner.resolve_image_paths", return_value=(None, None)
        ):
            app._wizard_screen.on_item_selected(ItemSelected("list-version", 0, "1.0"))
        assert app.ctx.kernel_path is None
        assert app._wizard_screen.current_step_idx == 0


async def test_node_count_options_need_a_scenario(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._wizard_screen.load_node_count_options()
        assert app._wizard_screen.current_step_idx == 0


async def test_back_is_ignored_on_running_screen(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._wizard_screen.switch_to_step(2)
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        await pilot.press("b")
        assert app._wizard_screen.current_step_idx == 2


async def test_toggle_and_save_logs_on_running_screen(lab, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        await pilot.pause()
        running = app._running_screen
        await pilot.press("l")
        assert running.logs_visible is True
        logging.getLogger().info("hello log line")
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        saved = list(tmp_path.glob("qemulab_session_*.log"))
        assert len(saved) == 1
        assert "hello log line" in saved[0].read_text()


async def test_toggle_and_save_logs_ignored_on_wizard(lab, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("l", "s")
        assert app._running_screen.logs_visible is False
        assert not list(tmp_path.glob("qemulab_session_*.log"))


async def test_save_logs_failure_is_reported(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            ok, message = app._running_screen.save_logs()
        assert ok is False
        assert "disk full" in message


async def test_quit_without_environment_exits_immediately(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
    assert app.return_code == 0


async def test_quit_with_environment_asks_for_cleanup(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.engine = MagicMock()
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        await pilot.press("q")
        await pilot.pause()
        assert isinstance(app.screen, CleanupModal)
        with patch.object(app, "perform_cleanup") as cleanup:
            await pilot.press("escape")
            await pilot.pause()
        cleanup.assert_not_called()


async def test_cleanup_modal_yes_triggers_cleanup(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.engine = MagicMock()
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        with patch.object(app, "perform_cleanup") as cleanup:
            await pilot.press("q")
            await pilot.pause()
            await pilot.click("#btn-yes")
            await pilot.pause()
        cleanup.assert_called_once()
        assert app.env_status == "stopped"


async def test_cleanup_modal_no_keeps_environment(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.engine = MagicMock()
        app.query_one("#main-content", ContentSwitcher).current = "running-content"
        with patch.object(app, "perform_cleanup") as cleanup:
            await pilot.press("q")
            await pilot.pause()
            await pilot.click("#btn-no")
            await pilot.pause()
        cleanup.assert_not_called()


async def test_launch_button_opens_password_modal_and_empty_password_aborts(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app._wizard_screen.switch_to_step(4)
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert isinstance(app.screen, PasswordModal)
        with patch.object(app, "start_launch_sequence") as launch:
            await pilot.click("#btn-auth")
            await pilot.pause()
        launch.assert_not_called()
        assert not isinstance(app.screen, PasswordModal)


async def test_password_submitted_with_enter_authenticates(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        with (
            patch("qemulab.ui.app.subprocess.run") as run,
            patch.object(app, "start_launch_sequence") as launch,
        ):
            app.check_sudo_and_launch()
            await pilot.pause()
            app.screen.query_one("#password-input", Input).focus()
            await pilot.press("p", "w", "enter")
            await pilot.pause()
        assert run.call_args.kwargs["input"] == "pw\n"
        assert app.ctx.sudo_password == "pw"
        launch.assert_called_once()


async def test_wrong_password_is_rejected(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        error = subprocess.CalledProcessError(1, "sudo")
        with (
            patch("qemulab.ui.app.subprocess.run", side_effect=error),
            patch.object(app, "start_launch_sequence") as launch,
        ):
            app.on_password_entered("nope")
        launch.assert_not_called()
        assert app.ctx.sudo_password is None


async def test_start_launch_sequence_switches_screen_and_starts_worker(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch.object(app, "run_worker") as worker:
            app.start_launch_sequence()
        assert app.env_status == "starting"
        assert app.query_one("#main-content", ContentSwitcher).current == "running-content"
        worker.assert_called_once_with(app._engine_worker, thread=True)


def _inline_call_from_thread(app):
    return patch.object(app, "call_from_thread", side_effect=lambda fn, *a, **k: fn(*a, **k))


async def test_engine_worker_success_marks_environment_running(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("qemulab.ui.app.Engine") as engine_cls, _inline_call_from_thread(app):
            app._engine_worker()
        engine = engine_cls.return_value
        engine.prepare_environment.assert_called_once()
        engine.start.assert_called_once()
        engine.configure_nodes.assert_called_once()
        assert app.env_status == "running"
        assert app._running_screen.logs_visible is True


async def test_engine_worker_failure_notifies_without_markup(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("qemulab.ui.app.Engine") as engine_cls, _inline_call_from_thread(app):
            engine_cls.return_value.start.side_effect = RuntimeError("[red]bad[/red]")
            with patch.object(app, "notify") as notify:
                app._engine_worker()
        assert "bad" in notify.call_args.args[0]
        assert notify.call_args.kwargs["markup"] is False
        assert app.env_status != "running"


async def test_perform_cleanup_runs_every_step_once(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.ctx.selected_board = "board1"
        app.ctx.sudo_password = "pw"
        app.ctx.set_manual_node_count(2)
        app.engine = MagicMock()
        flash = Path(f"{settings.flash_base_path}1")
        flash.mkdir()
        procs = []

        def fake_popen(cmd, **kwargs):
            proc = MagicMock()
            proc.cmd = cmd
            procs.append(proc)
            return proc

        with (
            patch("qemulab.ui.app.subprocess.Popen", side_effect=fake_popen),
            patch("qemulab.ui.app.subprocess.run") as run,
            patch("qemulab.ui.app.time.sleep"),
            patch("qemulab.ui.app.remove_tree") as remove,
        ):
            app.perform_cleanup()
            app.perform_cleanup()  # second call is a no-op
            remove.call_args.args[1](flash)

        sent = [c.args[1] for c in app.engine.tmux.send_keys.call_args_list]
        assert sent == ["\x02x", "\x02x"]
        run.assert_called_once()  # tmux kill-session
        cmds = [p.cmd for p in procs]
        assert ["sudo", "-S", "pkill", "-f", "QEMU_board1"] in cmds
        assert ["sudo", "-S", "ip", "link", "delete", "tap_qlab2_1"] in cmds
        assert cmds[-1] == ["sudo", "-S", "rm", "-rf", str(flash)]
        assert app.cleanup_performed is True


async def test_perform_cleanup_without_password_uses_plain_sudo(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.ctx.set_manual_node_count(1)
        with (
            patch("qemulab.ui.app.subprocess.run") as run,
            patch("qemulab.ui.app.time.sleep"),
        ):
            app.perform_cleanup()
        sudo_calls = [c.args[0] for c in run.call_args_list if c.args[0][0] == "sudo"]
        assert ["sudo", "ip", "link", "delete", "tap_qlab1_0"] in sudo_calls


async def test_perform_cleanup_tolerates_every_failure(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.ctx.set_manual_node_count(1)
        app.engine = MagicMock()
        app.engine.tmux.send_keys.side_effect = RuntimeError("pane gone")
        Path(f"{settings.flash_base_path}1").mkdir()
        with (
            patch("qemulab.ui.app.subprocess.run", side_effect=RuntimeError("no sudo")),
            patch("qemulab.ui.app.time.sleep"),
            patch("qemulab.ui.app.remove_tree", side_effect=OSError("busy")),
        ):
            app.perform_cleanup()
        assert app.cleanup_performed is True


async def test_perform_cleanup_reports_unexpected_error(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch.object(app, "notify", side_effect=[RuntimeError("ui"), None]) as notify:
            app.perform_cleanup()
        assert "Cleanup error" in notify.call_args.args[0]


async def test_perform_cleanup_shutdown_loop_error_is_logged(lab):
    app = QemuLabApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.ctx.set_manual_node_count(1)
        app.engine = MagicMock()
        with (
            patch("qemulab.ui.app.subprocess.run"),
            patch("qemulab.ui.app.time.sleep", side_effect=RuntimeError("clock")),
        ):
            app.perform_cleanup()
        assert app.cleanup_performed is True
