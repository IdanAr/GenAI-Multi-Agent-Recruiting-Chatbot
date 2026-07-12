"""test_main.py - smoke tests.

Phase 0: a single smoke test that proves the package imports cleanly.
Real unit tests for the tools and advisors are added in later phases.
"""

import importlib


def test_packages_import():
    """Every package/module in the skeleton imports without error."""
    for name in [
        "app",
        "app.main",
        "app.modules",
        "app.modules.config",
        "app.modules.data_exploration",
        "app.modules.embedding",
        "app.modules.scheduling_tool",
        "app.modules.main_agent",
        "app.modules.advisors",
        "app.modules.advisors.info_advisor",
        "app.modules.advisors.scheduling_advisor",
        "app.modules.advisors.exit_advisor",
    ]:
        importlib.import_module(name)
