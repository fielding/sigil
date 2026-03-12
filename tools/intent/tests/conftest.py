"""Shared pytest configuration for Sigil integration-style tests."""


def pytest_addoption(parser):
    """Register custom flags used by integration and real-world test suites."""
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden snapshot files",
    )
    parser.addoption(
        "--skip-clone",
        action="store_true",
        default=False,
        help="Skip real-world tests if repos are not cached",
    )
