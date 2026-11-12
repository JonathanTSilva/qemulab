from pathlib import Path

import typer

from qemulab.ui.app import QemuLabApp
from qemulab.utils.logging import setup_logging
from qemulab.utils.system import SystemCheck

app = typer.Typer(
    name="qemulab",
    help="Modern TUI-based QEMU environment manager for network-appliance labs.",
    add_completion=False,
)


@app.command()
def start(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="Path to custom config file."
    ),
    skip_checks: bool = typer.Option(
        False, "--force", "-f", help="Skip system requirement checks."
    ),
):
    """Launch the QemuLab TUI."""
    # Setup Logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(
        config_path=None, default_level=log_level
    )  # We can pass config_path if strictly logging config

    # System Checks
    if not skip_checks and not SystemCheck.check_all():
        typer.secho("System checks failed. Check logs.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Launch TUI
    try:
        tui = QemuLabApp()
        tui.run()
    except Exception as e:
        typer.secho(f"Application crashed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def check():
    """Run system checks and exit."""
    setup_logging()
    if SystemCheck.check_all():
        typer.secho("All systems go!", fg=typer.colors.GREEN)
    else:
        typer.secho("System checks failed.", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
