"""Atheris fuzz target for the qemulab config loader.

Run (atheris is not a project dependency). libFuzzer writes new inputs into the corpus
directory it is given, so fuzz a scratch copy and keep `fuzz/corpus/` for hand-written seeds:

    cp -r fuzz/corpus/config_loader /tmp/cfg-corpus
    uv run --with atheris python fuzz/fuzz_config_loader.py -runs=100000 /tmp/cfg-corpus

The target writes the fuzz input to a temporary user config file and loads it through
`yaml_config_settings_source` and `Settings`. A malformed config may raise the documented
errors only: `yaml.YAMLError` (bad YAML), `UnicodeDecodeError` (not UTF-8),
`ConfigFormatError` (not a mapping with string keys) or `pydantic.ValidationError` (bad
values). Anything else is a crash.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import yaml
from pydantic import ValidationError

# `python fuzz/<file>.py` puts fuzz/ on sys.path, not the repo root (qemulab is not installed).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qemulab.config.settings import (  # noqa: E402
    USER_CONFIG_ENV,
    ConfigFormatError,
    Settings,
    yaml_config_settings_source,
)

DOCUMENTED_ERRORS = (yaml.YAMLError, ValidationError, UnicodeDecodeError, ConfigFormatError)


def fuzz_one(data: bytes) -> None:
    """Load `data` as a user config file; only the documented errors may escape."""
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.yaml"
        config.write_bytes(data)
        with mock.patch.dict(os.environ, {USER_CONFIG_ENV: str(config)}):
            try:
                yaml_config_settings_source()
                Settings()
            except DOCUMENTED_ERRORS:
                pass


def main() -> None:
    """Instrument the target and hand control to libFuzzer."""
    import atheris

    atheris.instrument_all()
    atheris.Setup(sys.argv, fuzz_one)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
