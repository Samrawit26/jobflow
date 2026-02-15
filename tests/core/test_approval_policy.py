"""
Unit tests for approval_policy.py

Tests policy-based auto-approval rules.
"""

import pytest

from jobflow.app.core.approval_policy import (
    ALLOWED_PIPELINES,
    FORBIDDEN_KEYWORDS,
    evaluate_policy,
    get_policy_failure_reason,
)


@pytest.fixture
def safe_plan():
    """A plan that should pass all policies."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [],  # No risks
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }


def test_evaluate_policy_safe_plan_approved(safe_plan):
    """Test that a safe plan passes all policies."""
    result = evaluate_policy(safe_plan)
    assert result is True


def test_evaluate_policy_rejects_plan_with_risks(safe_plan):
    """Test that plans with identified risks are rejected."""
    safe_plan["risks"] = ["API rate limits"]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_multiple_risks(safe_plan):
    """Test that plans with multiple risks are rejected."""
    safe_plan["risks"] = [
        "API rate limits",
        "Data quality issues",
        "Network failure"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_non_allowlisted_pipeline(safe_plan):
    """Test that non-allowlisted pipelines are rejected."""
    safe_plan["pipeline_name"] = "dangerous_pipeline"
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_empty_pipeline_name(safe_plan):
    """Test that empty pipeline name is rejected."""
    safe_plan["pipeline_name"] = ""
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_write(safe_plan):
    """Test that 'write' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Fetch data",
        "Write to database",  # Forbidden keyword
        "Complete"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_delete(safe_plan):
    """Test that 'delete' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Fetch data",
        "Delete old records",  # Forbidden keyword
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_update(safe_plan):
    """Test that 'update' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Update user profile",  # Forbidden keyword
        "Complete"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_send(safe_plan):
    """Test that 'send' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Process data",
        "Send email notification",  # Forbidden keyword
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_http(safe_plan):
    """Test that 'http' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Make HTTP request",  # Forbidden keyword
        "Process response"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_forbidden_keyword_api(safe_plan):
    """Test that 'api' keyword in steps causes rejection."""
    safe_plan["steps"] = [
        "Call external API",  # Forbidden keyword
        "Parse result"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_case_insensitive_keywords(safe_plan):
    """Test that forbidden keyword detection is case-insensitive."""
    safe_plan["steps"] = [
        "WRITE data",  # Uppercase
        "Complete"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False

    safe_plan["steps"] = [
        "WrItE data",  # Mixed case
        "Complete"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_keyword_in_middle_of_word(safe_plan):
    """Test that keywords are detected even within words."""
    safe_plan["steps"] = [
        "Rewrite configuration",  # Contains 'write'
        "Complete"
    ]
    result = evaluate_policy(safe_plan)
    assert result is False


def test_evaluate_policy_rejects_invalid_plan_structure():
    """Test that invalid plan structures are rejected."""
    # Not a dict
    assert evaluate_policy("not a dict") is False
    assert evaluate_policy(None) is False
    assert evaluate_policy([]) is False


def test_evaluate_policy_handles_missing_fields():
    """Test that plans with missing fields use safe defaults."""
    # Missing fields default to empty lists via .get()
    # An incomplete but safe plan (allowlisted, no risks, no forbidden keywords)
    # will pass policy checks
    incomplete_plan = {
        "pipeline_name": "job_discovery",
        # Missing: steps, risks, assumptions
    }
    result = evaluate_policy(incomplete_plan)
    # This passes policy because:
    # - pipeline is allowlisted
    # - risks defaults to [] (no risks)
    # - steps defaults to [] (no forbidden keywords)
    # Note: This plan might still fail validation elsewhere
    assert result is True


def test_evaluate_policy_rejects_non_string_pipeline():
    """Test that non-string pipeline names are rejected."""
    plan = {
        "pipeline_name": 123,  # Not a string
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }
    result = evaluate_policy(plan)
    assert result is False


def test_evaluate_policy_rejects_non_list_risks():
    """Test that non-list risks are rejected."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1"],
        "risks": "not a list",  # Should be a list
        "assumptions": []
    }
    result = evaluate_policy(plan)
    assert result is False


def test_evaluate_policy_rejects_non_list_steps():
    """Test that non-list steps are rejected."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": "not a list",  # Should be a list
        "risks": [],
        "assumptions": []
    }
    result = evaluate_policy(plan)
    assert result is False


def test_evaluate_policy_rejects_non_string_steps():
    """Test that non-string steps are rejected."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": [
            "Valid step",
            123,  # Not a string
            "Another step"
        ],
        "risks": [],
        "assumptions": []
    }
    result = evaluate_policy(plan)
    assert result is False


def test_evaluate_policy_multiple_violations(safe_plan):
    """Test plan with multiple policy violations."""
    safe_plan["pipeline_name"] = "unknown_pipeline"  # Not allowlisted
    safe_plan["risks"] = ["High risk operation"]  # Has risks
    safe_plan["steps"] = ["Delete all data"]  # Forbidden keyword

    result = evaluate_policy(safe_plan)
    assert result is False


def test_get_policy_failure_reason_pipeline_not_allowed():
    """Test failure reason for non-allowlisted pipeline."""
    plan = {
        "pipeline_name": "unknown_pipeline",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }
    reason = get_policy_failure_reason(plan)
    assert "unknown_pipeline" in reason
    assert "not in the allowlist" in reason
    assert "job_discovery" in reason  # Show allowed pipelines


def test_get_policy_failure_reason_has_risks():
    """Test failure reason for plans with risks."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1"],
        "risks": ["API rate limits", "Data issues"],
        "assumptions": []
    }
    reason = get_policy_failure_reason(plan)
    assert "risk" in reason.lower()
    assert "API rate limits" in reason


def test_get_policy_failure_reason_forbidden_keywords():
    """Test failure reason for forbidden keywords."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["Write data", "Delete records"],
        "risks": [],
        "assumptions": []
    }
    reason = get_policy_failure_reason(plan)
    assert "forbidden keywords" in reason
    assert "write" in reason.lower()
    assert "delete" in reason.lower()


def test_get_policy_failure_reason_multiple_failures():
    """Test failure reason includes all violations."""
    plan = {
        "pipeline_name": "bad_pipeline",
        "steps": ["Delete all", "Send emails"],
        "risks": ["High risk"],
        "assumptions": []
    }
    reason = get_policy_failure_reason(plan)
    # Should mention all three violations
    assert "not in the allowlist" in reason
    assert "risk" in reason.lower()
    assert "forbidden keywords" in reason


def test_allowed_pipelines_constant():
    """Test that ALLOWED_PIPELINES contains job_discovery."""
    assert "job_discovery" in ALLOWED_PIPELINES
    assert isinstance(ALLOWED_PIPELINES, set)


def test_forbidden_keywords_constant():
    """Test that FORBIDDEN_KEYWORDS contains expected keywords."""
    expected_keywords = {"write", "delete", "update", "send", "apply", "http", "api"}
    assert expected_keywords.issubset(FORBIDDEN_KEYWORDS)
    assert isinstance(FORBIDDEN_KEYWORDS, set)
