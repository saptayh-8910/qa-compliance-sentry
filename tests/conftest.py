from __future__ import annotations

import os
from pathlib import Path

import pytest

REPORTS_DIR = Path("reports")


@pytest.fixture(scope="session")
def sauce_base_url() -> str:
    return os.getenv("SAUCE_BASE_URL", "https://www.saucedemo.com")


@pytest.fixture(scope="session")
def sauce_username() -> str:
    return os.getenv("SAUCE_USERNAME", "standard_user")


@pytest.fixture(scope="session")
def sauce_password() -> str:
    return os.getenv("SAUCE_PASSWORD", "secret_sauce")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    page = item.funcargs.get("page")
    if page is None:
        return
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = item.nodeid.replace("/", "_").replace("::", "_")
    screenshot_path = REPORTS_DIR / f"{safe_name}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        report.extra = getattr(report, "extra", [])
    except Exception:
        pass
