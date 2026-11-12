"""A standardized module for displaying beautiful and consistent CLI alerts.

This module uses the 'rich' library to provide a rich set of pre-configured
UI components, including colored logging, user prompts, headers, and spinners.
The goal is to provide a single, easy-to-use interface for all CLI output.
"""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from enum import Enum
from shutil import get_terminal_size
from typing import Any, Literal, TypeVar, overload

import typer
from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text
from rich.traceback import Traceback

# Platform-specific imports for single-key press detection
try:
    import termios
    import tty  # For Unix-like systems
except ImportError:
    import msvcrt  # For Windows


# *====[ Core Instances & Types ]====*

# Define a TypeVar for use in generic functions and overloads
T = TypeVar("T")

# A single, shared Console instance for the entire application.
# stderr is used by default to separate primary output (stdout) from alerts.
console_instance = Console(stderr=True, highlight=False)

# A dedicated logger for this module. Using a named logger is a best practice.
_logger = logging.getLogger("qemulab.console")


class _AlertStyles(str, Enum):
    """Encapsulates the rich markup for different alert styles."""

    INFO = "[bold cyan]\\[*][/bold cyan]"
    SUCCESS = "[bold green]\\[+][/bold green]"
    WARNING = "[bold yellow]\\[!][/bold yellow]"
    ERROR = "[bold red]\\[x][/bold red]"
    FATAL = "[bold red]\\[!][/bold red]"
    DEBUG = "[bold magenta]\\[>][/bold magenta]"
    PROMPT = "[bold yellow]\\[?][/bold yellow]"


# *====[ Primary Alert Functions ]====*
def _log_alert(
    level: int,
    marker: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Central helper to format and dispatch logs."""
    console_message = f"{marker} {message}"

    # Create a clean, ASCII-only version for raw text logs
    try:
        plain_text = Text.from_markup(message).plain
        ascii_text = plain_text.encode("ascii", "ignore").decode("ascii")
        raw_message = " ".join(ascii_text.split())
    except Exception:
        raw_message = message

    log_context = context if context is not None else {}
    _logger.log(
        level,
        console_message,
        stacklevel=3,
        extra={"extra_data": {"raw_message": raw_message, **log_context}},
    )


def info(message: str, context: dict[str, Any] | None = None) -> None:
    _log_alert(logging.INFO, _AlertStyles.INFO.value, message, context)


def success(message: str, context: dict[str, Any] | None = None) -> None:
    _log_alert(logging.INFO, _AlertStyles.SUCCESS.value, message, context)


def warning(message: str, context: dict[str, Any] | None = None) -> None:
    _log_alert(logging.WARNING, _AlertStyles.WARNING.value, message, context)


def error(
    message: str,
    *,
    exc_info: bool = False,
    context: dict[str, Any] | None = None,
) -> None:
    _log_alert(logging.ERROR, _AlertStyles.ERROR.value, message, context)
    if exc_info and sys.exc_info()[0] is not None:
        tb = Traceback.from_exception(*sys.exc_info(), show_locals=False)
        console_instance.print(tb)


def fatal(
    message: str,
    *,
    exit_code: int = 1,
    context: dict[str, Any] | None = None,
) -> None:
    fatal_message = f"FATAL: {message}"
    _log_alert(logging.CRITICAL, _AlertStyles.FATAL.value, fatal_message, context)
    raise typer.Exit(code=exit_code)


def debug(message: str, context: dict[str, Any] | None = None) -> None:
    _log_alert(logging.DEBUG, _AlertStyles.DEBUG.value, message, context)


# *====[ UI & Structural Elements ]====*
def section(title: str, style: str = "bold white on #005f87") -> None:
    """Displays a full-width, styled section header."""
    title_text = f" » {title.upper()} "
    try:
        terminal_width = get_terminal_size().columns
    except OSError:
        terminal_width = 80

    padding_size = max(terminal_width - len(title_text), 0)
    full_line_markup = f"[{style}]{title_text}{' ' * padding_size}[/]"

    # Log a blank line, then the section to ensure correct order.
    _logger.info("", extra={"console_only": True})
    _logger.info(full_line_markup, extra={"console_only": True})


def header(title: str, style: str = "bold blue") -> None:
    """Displays a prominent, centered header with a rule line."""
    prefix, suffix, end_marker = "╭───⦗  ", "  ⦘", "╮"
    full_title = f"{prefix}{title}{suffix}"
    try:
        term_width = get_terminal_size().columns
    except OSError:
        term_width = 80

    rule_fill_len = max(0, term_width - len(full_title) - len(end_marker))
    rule_fill = "─" * rule_fill_len
    line_markup = f"[{style}]{full_title}{rule_fill}{end_marker}[/]"

    _logger.info("", extra={"console_only": True})
    _logger.info(line_markup, extra={"console_only": True})


def panel(
    content: RenderableType | str,
    *,
    title: str | None = None,
    title_align: Literal["left", "center", "right"] = "center",
    style: str = "cyan",
    padding: tuple[int, int] = (1, 2),
) -> None:
    renderable_content = Text.from_markup(content) if isinstance(content, str) else content
    panel_title = Text.from_markup(title) if title else None

    console_instance.print(
        Panel(
            renderable_content,
            title=panel_title,
            title_align=title_align,
            border_style=style,
            padding=padding,
            expand=True,
        )
    )


@contextmanager
def spinner(text: str = "Processing...", *, style: str = "cyan") -> Iterator[None]:
    """Provides a context manager that displays a spinner for long operations."""
    with console_instance.status(Text(text, style=style), spinner="dots"):
        yield


# *====[ Interactive Prompts ]====*
def _get_key_windows() -> str:
    key = msvcrt.getch()  # type: ignore[name-defined]
    if key == b"\r":
        return "ENTER"
    if key == b"\x03":
        raise KeyboardInterrupt
    if key in {b"\xe0", b"\x00"}:
        second_byte = msvcrt.getch()  # type: ignore[name-defined]
        key_map = {b"H": "UP", b"P": "DOWN"}
        return key_map.get(second_byte, "")
    return ""


def _get_key_unix() -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        char = sys.stdin.read(1)
        if char == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if char == "\r":
            return "ENTER"
        if char == "\x1b" and sys.stdin.read(1) == "[":
            arrow_key = sys.stdin.read(1)
            key_map = {"A": "UP", "B": "DOWN"}
            return key_map.get(arrow_key, "")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ""


def _get_key() -> str:
    return _get_key_windows() if "msvcrt" in sys.modules else _get_key_unix()


def selection[T](message: str, choices: list[T]) -> T:
    """Displays an interactive, navigable selection menu."""
    if not choices:
        raise ValueError("Cannot make a selection from an empty list.")

    current_index = 0
    prompt_text = Text.from_markup(f"{_AlertStyles.PROMPT.value} {message}\n")

    def generate_menu() -> Text:
        menu = Text()
        for i, choice in enumerate(choices):
            if i == current_index:
                menu.append("  » ", style="bold orange1")
                menu.append(f"{choice}\n", style="bold orange1")
            else:
                menu.append(f"    {choice}\n", style="dim")
        return prompt_text + menu

    try:
        # Use transient=True so the menu disappears after selection
        with Live(
            generate_menu(), console=console_instance, auto_refresh=False, transient=True
        ) as live:
            while True:
                key = _get_key()
                if key == "UP":
                    current_index = (current_index - 1) % len(choices)
                elif key == "DOWN":
                    current_index = (current_index + 1) % len(choices)
                elif key == "ENTER":
                    break
                live.update(generate_menu(), refresh=True)
    except KeyboardInterrupt:
        console_instance.show_cursor(show=True)
        fatal("User cancelled operation.", exit_code=0)

    selected_choice = choices[current_index]
    success(f"Selected: {selected_choice}")
    return selected_choice


@overload
def prompt[T](
    message: str, *, default: T, secret: bool = False, choices: list[str] | None = None
) -> T: ...


@overload
def prompt(
    message: str, *, default: None = None, secret: bool = False, choices: list[str] | None = None
) -> str: ...


def prompt(
    message: str, *, default: Any = None, secret: bool = False, choices: list[str] | None = None
) -> Any:
    prompt_text = Text.from_markup(f"{_AlertStyles.PROMPT.value} {message}")
    return Prompt.ask(
        prompt_text,
        password=secret,
        default=default,
        choices=choices,
        console=console_instance,
    )


def confirm(message: str, *, default: bool = False) -> bool:
    prompt_text = Text.from_markup(f"{_AlertStyles.PROMPT.value} {message}")
    return Confirm.ask(prompt_text, default=default, console=console_instance)
