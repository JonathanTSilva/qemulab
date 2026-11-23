"""setup_logging: config loading and failure handling. Root logger state is restored after."""

import json
import logging

import pytest

from qemulab.utils import logging as qlog


@pytest.fixture
def restore_root():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield root
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
    root.setLevel(level)


def _config(log_file) -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"plain": {"format": "%(message)s"}},
        "handlers": {
            "console": {"class": "logging.NullHandler", "level": "INFO"},
            "file": {
                "class": "logging.FileHandler",
                "filename": str(log_file),
                "formatter": "plain",
            },
        },
        "root": {"level": "DEBUG", "handlers": ["console", "file"]},
    }


def test_rich_console_formatter_passes_message_through():
    record = logging.LogRecord("n", logging.INFO, "p", 1, "[b]%s[/b]", ("x",), None)
    assert qlog.RichConsoleFormatter().format(record) == "[b]x[/b]"


def test_json_formatter_survives_unparseable_markup():
    record = logging.LogRecord("n", logging.INFO, "p", 1, "oops [/nope] here", (), None)
    data = json.loads(qlog.JSONFormatter().format(record))
    assert "oops" in data["message"]


def test_json_formatter_includes_extra_data():
    record = logging.LogRecord("n", logging.INFO, "p", 1, "m", (), None)
    record.extra_data = {"raw_message": "m", "node": 3}
    data = json.loads(qlog.JSONFormatter().format(record))
    assert data["node"] == 3


def test_setup_logging_loads_config_file(tmp_path, restore_root):
    cfg_path = tmp_path / "logging.json"
    cfg_path.write_text(json.dumps(_config(tmp_path / "sub" / "out.log")))
    qlog.setup_logging(config_path=cfg_path, default_level="debug")
    assert (tmp_path / "sub").is_dir()
    assert any(isinstance(h, logging.handlers.QueueHandler) for h in restore_root.handlers)


def test_setup_logging_bad_config_file_falls_back_to_defaults(tmp_path, monkeypatch, restore_root):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    default = _config(tmp_path / "default.log")
    monkeypatch.setattr(qlog, "DEFAULT_LOGGING_CONFIG", default)
    qlog.setup_logging(config_path=bad)
    assert (tmp_path / "default.log").exists()


def test_setup_logging_missing_config_file_uses_defaults(tmp_path, monkeypatch, restore_root):
    monkeypatch.setattr(qlog, "DEFAULT_LOGGING_CONFIG", _config(tmp_path / "d.log"))
    qlog.setup_logging(config_path=tmp_path / "absent.json")
    assert (tmp_path / "d.log").exists()


def test_setup_logging_tolerates_unwritable_log_dir(tmp_path, monkeypatch, restore_root):
    monkeypatch.setattr(qlog, "DEFAULT_LOGGING_CONFIG", _config(tmp_path / "ok.log"))

    def fail_mkdir(self, *args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr(qlog.Path, "mkdir", fail_mkdir)
    qlog.setup_logging()
    assert any(isinstance(h, logging.handlers.QueueHandler) for h in restore_root.handlers)
