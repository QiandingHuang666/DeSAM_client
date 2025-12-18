"""Basic tests for desam-client package."""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_import():
    """Test that the package can be imported."""
    import desam_client
    assert desam_client.__version__ == "0.1.0"


def test_client_class():
    """Test that DeSAMClient class exists."""
    from desam_client import DeSAMClient
    assert DeSAMClient is not None


def test_models():
    """Test that model classes exist."""
    from desam_client import Job, Resource
    assert Job is not None
    assert Resource is not None


def test_exceptions():
    """Test that exception classes exist."""
    from desam_client.exceptions import (
        DeSAMError,
        AuthenticationError,
        JobNotFoundError,
        DeSAMConnectionError,
        SubmitError,
    )
    assert DeSAMError is not None
    assert AuthenticationError is not None
    assert JobNotFoundError is not None
    assert DeSAMConnectionError is not None
    assert SubmitError is not None
