"""The `main` entry function hands over to the Typer app."""

from unittest.mock import patch

from qemulab import main as main_module


def test_main_invokes_cli_app():
    with patch.object(main_module, "app") as app:
        main_module.main()
    app.assert_called_once_with()
