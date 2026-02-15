"""
Unit tests for directive_router.py
"""

import pytest
from jobflow.app.core.directive_router import resolve_pipeline


def test_resolve_pipeline_job_discovery():
    """Test that job_discovery directive maps to job_discovery pipeline."""
    result = resolve_pipeline("job_discovery")
    assert result == "job_discovery"


def test_resolve_pipeline_unknown_directive():
    """Test that unknown directives raise ValueError."""
    with pytest.raises(ValueError, match="Unknown directive: nonexistent"):
        resolve_pipeline("nonexistent")


def test_resolve_pipeline_empty_string():
    """Test that empty string raises ValueError."""
    with pytest.raises(ValueError, match="Unknown directive: "):
        resolve_pipeline("")
