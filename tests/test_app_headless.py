"""Headless smoke test: the app must start under Textual's run_test()."""

import logging

from textual.widgets import ContentSwitcher

from qemulab.ui.app import QemuLabApp


async def test_app_starts_headless_and_exits_cleanly():
    root = logging.getLogger()
    handlers_before = list(root.handlers)
    level_before = root.level
    try:
        app = QemuLabApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            switcher = app.query_one("#main-content", ContentSwitcher)
            assert switcher.current == "wizard-content"
            assert app._wizard_screen is not None
            assert app._running_screen is not None
    finally:
        for handler in list(root.handlers):
            if handler not in handlers_before:
                root.removeHandler(handler)
        root.setLevel(level_before)
