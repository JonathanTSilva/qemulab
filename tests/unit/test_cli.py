"""Comprehensive tests for the CLI interface."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from qemulab.cli import app

runner = CliRunner()


# ============================================================================
# Basic Command Tests
# ============================================================================


class TestStartCommand:
    """Tests for the 'start' command."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_command_success(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test standard launch flow succeeds."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        mock_sys_check.check_all.assert_called_once()
        mock_app_instance.run.assert_called_once()
        mock_logging.assert_called_once()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_start_command_fails_checks(self, mock_logging, mock_sys_check):
        """Test launch aborts if system checks fail."""
        mock_sys_check.check_all.return_value = False

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "System checks failed" in result.stdout

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_skip_checks(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test --force flag skips system checks."""
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "--force"])

        assert result.exit_code == 0
        mock_sys_check.check_all.assert_not_called()
        mock_app_instance.run.assert_called_once()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_with_verbose(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test --verbose flag enables debug logging."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "--verbose"])

        assert result.exit_code == 0
        # Check that setup_logging was called with DEBUG level
        mock_logging.assert_called_once_with(config_path=None, default_level="DEBUG")

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_without_verbose(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test default logging level is INFO."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(config_path=None, default_level="INFO")

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_app_crash_handling(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test graceful handling of app crashes."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_instance.run.side_effect = RuntimeError("App crashed!")
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "Application crashed" in result.stdout


class TestCheckCommand:
    """Tests for the 'check' command."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_check_command_success(self, mock_logging, mock_sys_check):
        """Test check command succeeds when all checks pass."""
        mock_sys_check.check_all.return_value = True

        result = runner.invoke(app, ["check"])

        assert result.exit_code == 0
        assert "All systems go!" in result.stdout
        mock_sys_check.check_all.assert_called_once()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_check_command_failure(self, mock_logging, mock_sys_check):
        """Test check command fails when checks don't pass."""
        mock_sys_check.check_all.return_value = False

        result = runner.invoke(app, ["check"])

        assert result.exit_code == 1
        assert "System checks failed" in result.stdout


# ============================================================================
# Flag Combination Tests
# ============================================================================


class TestFlagCombinations:
    """Test various flag combinations."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_verbose_and_force(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test combining --verbose and --force flags."""
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "-v", "-f"])

        assert result.exit_code == 0
        mock_sys_check.check_all.assert_not_called()
        mock_logging.assert_called_once_with(config_path=None, default_level="DEBUG")

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_short_flags(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test short flag versions work."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "-v"])

        assert result.exit_code == 0
        mock_logging.assert_called_once_with(config_path=None, default_level="DEBUG")


# ============================================================================
# System Check Integration Tests
# ============================================================================


class TestSystemCheckIntegration:
    """Test CLI integration with SystemCheck."""

    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    @patch("qemulab.cli.SystemCheck.check_all")
    def test_system_check_called_by_default(self, mock_check_all, mock_logging, mock_app_cls):
        """Test system checks are called by default."""
        mock_check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        mock_check_all.assert_called_once()

    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    @patch("qemulab.cli.SystemCheck.check_all")
    def test_system_check_skipped_with_force(self, mock_check_all, mock_logging, mock_app_cls):
        """Test --force skips system checks."""
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "--force"])

        assert result.exit_code == 0
        mock_check_all.assert_not_called()


# ============================================================================
# Logging Tests
# ============================================================================


class TestLogging:
    """Test logging configuration."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_logging_setup_called(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test setup_logging is always called."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        runner.invoke(app, ["start"])

        mock_logging.assert_called_once()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_logging_level_debug_with_verbose(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test debug logging level with verbose flag."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        runner.invoke(app, ["start", "--verbose"])

        call_args = mock_logging.call_args
        assert call_args[1]["default_level"] == "DEBUG"

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_logging_level_info_without_verbose(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test info logging level without verbose flag."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        runner.invoke(app, ["start"])

        call_args = mock_logging.call_args
        assert call_args[1]["default_level"] == "INFO"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test CLI error handling."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_system_check_exception_handling(self, mock_logging, mock_sys_check):
        """Test graceful handling of exceptions in system checks."""
        mock_sys_check.check_all.side_effect = RuntimeError("Check failed!")

        result = runner.invoke(app, ["start"])

        # Should not crash, should exit with error code
        assert result.exit_code != 0

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_app_creation_exception(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test handling of exception during app creation."""
        mock_sys_check.check_all.return_value = True
        mock_app_cls.side_effect = RuntimeError("Failed to create app!")

        result = runner.invoke(app, ["start"])

        assert result.exit_code == 1
        assert "Application crashed" in result.stdout


# ============================================================================
# Help and Documentation Tests
# ============================================================================


class TestHelpAndDocumentation:
    """Test help messages and documentation."""

    def test_app_help(self):
        """Test main app help message."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Check for key terms that should be in help
        assert "start" in result.stdout.lower() or "check" in result.stdout.lower()

    def test_start_help(self):
        """Test start command help message."""
        result = runner.invoke(app, ["start", "--help"])

        assert result.exit_code == 0
        # Should show start command documentation
        assert "--verbose" in result.stdout or "-v" in result.stdout

    def test_check_help(self):
        """Test check command help message."""
        result = runner.invoke(app, ["check", "--help"])

        assert result.exit_code == 0
        # Should show check command documentation


# ============================================================================
# Integration Tests
# ============================================================================


class TestCLIIntegration:
    """Integration tests for CLI with other components."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_full_check_workflow(self, mock_logging, mock_sys_check):
        """Test complete check command workflow."""
        # Setup mock to simulate all checks passing
        mock_sys_check.check_all.return_value = True

        result = runner.invoke(app, ["check"])

        # Verify workflow
        assert result.exit_code == 0
        mock_logging.assert_called_once()
        mock_sys_check.check_all.assert_called_once()
        assert "All systems go!" in result.stdout

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_full_start_workflow(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test complete start command workflow."""
        # Setup mocks
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])

        # Verify workflow
        assert result.exit_code == 0
        mock_logging.assert_called_once()
        mock_sys_check.check_all.assert_called_once()
        mock_app_instance.run.assert_called_once()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_with_all_options(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test start with all options enabled."""
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(
            app, ["start", "--verbose", "--force", "--config", "/fake/config.yaml"]
        )

        assert result.exit_code == 0
        mock_sys_check.check_all.assert_not_called()  # --force skips checks
        mock_logging.assert_called_once_with(config_path=None, default_level="DEBUG")


# ============================================================================
# Regression Tests
# ============================================================================


class TestRegressions:
    """Tests to prevent known issues from recurring."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_no_double_logging_setup(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test logging is only setup once."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        runner.invoke(app, ["start"])

        # setup_logging should only be called once
        assert mock_logging.call_count == 1

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_app_not_created_when_checks_fail(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test app is not created if system checks fail."""
        mock_sys_check.check_all.return_value = False

        runner.invoke(app, ["start"])

        # App should not be created if checks fail
        mock_app_cls.assert_not_called()

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_exit_codes_correct(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test exit codes are correct for different scenarios."""
        # Success
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start"])
        assert result.exit_code == 0

        # System check failure
        mock_sys_check.check_all.return_value = False
        result = runner.invoke(app, ["start"])
        assert result.exit_code == 1


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test CLI performance characteristics."""

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.setup_logging")
    def test_check_command_performance(self, mock_logging, mock_sys_check):
        """Test check command completes quickly."""
        import time

        mock_sys_check.check_all.return_value = True

        start = time.time()
        runner.invoke(app, ["check"])
        elapsed = time.time() - start

        # Check should complete in under 1 second (generous for CI)
        assert elapsed < 1.0

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_start_initialization_performance(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test start command initializes quickly."""
        import time

        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        # Make run() return immediately
        mock_app_instance.run.return_value = None
        mock_app_cls.return_value = mock_app_instance

        start = time.time()
        runner.invoke(app, ["start"])
        elapsed = time.time() - start

        # Initialization should be fast (under 2 seconds including mocks)
        assert elapsed < 2.0


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_no_command(self):
        """Test running app with no command shows usage."""
        result = runner.invoke(app)

        # Typer returns exit code 0 for help display
        # Or might return 2 if it requires a command
        assert result.exit_code in [0, 2]

    def test_invalid_command(self):
        """Test invalid command shows error."""
        result = runner.invoke(app, ["invalid"])

        assert result.exit_code != 0

    @patch("qemulab.cli.SystemCheck")
    @patch("qemulab.cli.QemuLabApp")
    @patch("qemulab.cli.setup_logging")
    def test_empty_config_path(self, mock_logging, mock_app_cls, mock_sys_check):
        """Test handling of empty config path."""
        mock_sys_check.check_all.return_value = True
        mock_app_instance = MagicMock()
        mock_app_cls.return_value = mock_app_instance

        result = runner.invoke(app, ["start", "--config", ""])

        # Should handle empty config path gracefully
        assert result.exit_code == 0
