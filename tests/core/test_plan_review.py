"""
Unit tests for plan_review.py

Tests the safety gate that approves or rejects execution plans.
"""

import pytest

from jobflow.app.core.plan_review import review_plan, validate_plan_structure


@pytest.fixture
def valid_plan():
    """A valid execution plan for testing."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [
            "API rate limits",
            "Data quality issues"
        ],
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }


def test_review_plan_rejects_by_default(valid_plan):
    """Test that review_plan returns False by default (fail-safe behavior)."""
    result = review_plan(valid_plan)
    assert result is False


def test_review_plan_approves_with_override_and_policy():
    """Test that review_plan returns True when auto_approve=True and plan passes policy."""
    # Plan must pass policy: allowlisted pipeline, no risks, no forbidden keywords
    safe_plan = {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [],  # No risks - required for policy approval
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }
    result = review_plan(safe_plan, auto_approve=True)
    assert result is True


def test_review_plan_rejects_with_auto_approve_if_policy_fails(valid_plan):
    """Test that auto_approve=True still rejects if plan fails policy."""
    # valid_plan has risks, so it fails policy even with auto_approve=True
    result = review_plan(valid_plan, auto_approve=True)
    assert result is False


def test_review_plan_rejects_invalid_plan_structure():
    """Test that invalid plan structure is rejected."""
    # Not a dict
    result = review_plan("not a dict")
    assert result is False

    result = review_plan(None)
    assert result is False

    result = review_plan([])
    assert result is False


def test_review_plan_rejects_empty_dict():
    """Test that empty dict is rejected."""
    result = review_plan({})
    assert result is False


def test_review_plan_rejects_invalid_even_with_auto_approve():
    """Test that invalid plan structure is rejected even with auto_approve=True (fail-safe)."""
    # This is fail-safe behavior: even with auto_approve, we validate basic structure
    # to prevent executing completely malformed plans
    result = review_plan("not a dict", auto_approve=True)
    assert result is False

    result = review_plan(None, auto_approve=True)
    assert result is False


def test_validate_plan_structure_valid_plan(valid_plan):
    """Test that validate_plan_structure accepts valid plans."""
    is_valid, error = validate_plan_structure(valid_plan)
    assert is_valid is True
    assert error is None


def test_validate_plan_structure_not_dict():
    """Test that non-dict plans are rejected."""
    is_valid, error = validate_plan_structure("not a dict")
    assert is_valid is False
    assert "must be a dictionary" in error


def test_validate_plan_structure_missing_keys():
    """Test that plans with missing required keys are rejected."""
    incomplete_plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1"]
        # Missing: risks, assumptions
    }
    is_valid, error = validate_plan_structure(incomplete_plan)
    assert is_valid is False
    assert "missing required keys" in error
    assert "risks" in error or "assumptions" in error


def test_validate_plan_structure_wrong_types():
    """Test that plans with wrong field types are rejected."""
    # pipeline_name not a string
    plan = {
        "pipeline_name": 123,
        "steps": [],
        "risks": [],
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "pipeline_name must be a string" in error

    # steps not a list
    plan = {
        "pipeline_name": "test",
        "steps": "not a list",
        "risks": [],
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "steps must be a list" in error

    # risks not a list
    plan = {
        "pipeline_name": "test",
        "steps": [],
        "risks": "not a list",
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "risks must be a list" in error

    # assumptions not a list
    plan = {
        "pipeline_name": "test",
        "steps": [],
        "risks": [],
        "assumptions": "not a list"
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "assumptions must be a list" in error


def test_validate_plan_structure_empty_pipeline_name():
    """Test that empty pipeline_name is rejected."""
    plan = {
        "pipeline_name": "",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "pipeline_name cannot be empty" in error


def test_validate_plan_structure_empty_steps():
    """Test that empty steps list is rejected."""
    plan = {
        "pipeline_name": "test",
        "steps": [],
        "risks": [],
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is False
    assert "steps cannot be empty" in error


def test_validate_plan_structure_allows_empty_risks_and_assumptions():
    """Test that empty risks and assumptions are allowed."""
    plan = {
        "pipeline_name": "test",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }
    is_valid, error = validate_plan_structure(plan)
    assert is_valid is True
    assert error is None


def test_review_plan_with_minimal_valid_plan():
    """Test review with minimal but valid plan."""
    minimal_plan = {
        "pipeline_name": "job_discovery",  # Must be allowlisted for policy
        "steps": ["Fetch data"],  # No forbidden keywords
        "risks": [],  # No risks
        "assumptions": []
    }
    # Should still reject by default (safety gate)
    result = review_plan(minimal_plan)
    assert result is False

    # Should approve with auto_approve if plan passes policy
    result = review_plan(minimal_plan, auto_approve=True)
    assert result is True


def test_review_plan_is_pure_function(valid_plan):
    """Test that review_plan has no side effects (pure function)."""
    original_plan = valid_plan.copy()

    # Call multiple times
    review_plan(valid_plan)
    review_plan(valid_plan, auto_approve=True)
    review_plan(valid_plan)

    # Plan should be unmodified
    assert valid_plan == original_plan
