"""Test workspace scaffolding and package imports."""

import shared


def test_shared_version() -> None:
    """Verify shared package imports properly."""
    assert shared.__version__ == "0.1.0"
