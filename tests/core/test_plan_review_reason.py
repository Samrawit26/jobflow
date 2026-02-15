"""
Unit tests for review_plan_with_reason() in plan_review.py

Tests explainable plan review with detailed rejection/approval reasons.
"""

import pytest

from jobflow.app.core.plan_review import review_plan_with_reason


@pytest.fixture
def safe_plan():
    """A plan that passes all policies."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [],
        "assumptions": [
            "Database is accessible",
            "API credentials are valid"
        ]
    }


@pytest.fixture
def plan_with_risks():
    """A plan with identified risks."""
    return {
        "pipeline_name": "job_discovery",
        "steps": ["Fetch data"],
        "risks": ["API rate limits", "Data quality issues"],
        "assumptions": []
    }


@pytest.fixture
def plan_with_forbidden_keywords():
    """A plan with forbidden keywords in steps."""
    return {
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch data",
            "Write to database",  # Forbidden keyword
            "Send notifications"  # Forbidden keyword
        ],
        "risks": [],
        "assumptions": []
    }


@pytest.fixture
def plan_with_non_allowlisted_pipeline():
    """A plan with a non-allowlisted pipeline."""
    return {
        "pipeline_name": "dangerous_pipeline",
        "steps": ["Do something"],
        "risks": [],
        "assumptions": []
    }


def test_review_plan_with_reason_default_rejection(safe_plan):
    """Test default rejection reason when auto_approve=False."""
    approved, reason = review_plan_with_reason(safe_plan, auto_approve=False)

    assert approved is False
    assert reason == "Rejected by default (auto_approve is False)"


def test_review_plan_with_reason_invalid_structure_not_dict():
    """Test invalid plan structure reason for non-dict input."""
    approved, reason = review_plan_with_reason("not a dict")

    assert approved is False
    assert reason == "Invalid plan structure: expected dict"


def test_review_plan_with_reason_invalid_structure_none():
    """Test invalid plan structure reason for None input."""
    approved, reason = review_plan_with_reason(None)

    assert approved is False
    assert reason == "Invalid plan structure: expected dict"


def test_review_plan_with_reason_invalid_structure_list():
    """Test invalid plan structure reason for list input."""
    approved, reason = review_plan_with_reason([])

    assert approved is False
    assert reason == "Invalid plan structure: expected dict"


def test_review_plan_with_reason_auto_approve_success(safe_plan):
    """Test auto-approve success reason."""
    approved, reason = review_plan_with_reason(safe_plan, auto_approve=True)

    assert approved is True
    assert reason == "Auto-approved by policy"


def test_review_plan_with_reason_rejection_with_risks(plan_with_risks):
    """Test rejection reason includes risk details."""
    approved, reason = review_plan_with_reason(plan_with_risks, auto_approve=True)

    assert approved is False
    assert "risk" in reason.lower()
    assert "2" in reason  # Number of risks
    # Should include the actual risks
    assert "API rate limits" in reason or "Data quality issues" in reason


def test_review_plan_with_reason_rejection_non_allowlisted(plan_with_non_allowlisted_pipeline):
    """Test rejection reason includes allowlist details."""
    approved, reason = review_plan_with_reason(
        plan_with_non_allowlisted_pipeline,
        auto_approve=True
    )

    assert approved is False
    assert "not in the allowlist" in reason
    assert "dangerous_pipeline" in reason
    assert "job_discovery" in reason  # Show allowed pipelines


def test_review_plan_with_reason_rejection_forbidden_keywords(plan_with_forbidden_keywords):
    """Test rejection reason includes forbidden keyword details."""
    approved, reason = review_plan_with_reason(
        plan_with_forbidden_keywords,
        auto_approve=True
    )

    assert approved is False
    assert "forbidden keywords" in reason
    # Should mention at least one of the forbidden keywords found
    assert "write" in reason.lower() or "send" in reason.lower()


def test_review_plan_with_reason_multiple_violations():
    """Test rejection reason includes multiple policy violations."""
    bad_plan = {
        "pipeline_name": "unknown_pipeline",  # Not allowlisted
        "steps": ["Delete all data", "Send emails"],  # Forbidden keywords
        "risks": ["High risk operation"],  # Has risks
        "assumptions": []
    }

    approved, reason = review_plan_with_reason(bad_plan, auto_approve=True)

    assert approved is False
    # Reason should include all violations (separated by |)
    assert "not in the allowlist" in reason
    assert "risk" in reason.lower()
    assert "forbidden keywords" in reason


def test_review_plan_with_reason_consistency_with_review_plan(safe_plan):
    """Test that review_plan_with_reason is consistent with review_plan."""
    from jobflow.app.core.plan_review import review_plan

    # Test with auto_approve=False
    approved_with_reason, _ = review_plan_with_reason(safe_plan, auto_approve=False)
    approved_without_reason = review_plan(safe_plan, auto_approve=False)
    assert approved_with_reason == approved_without_reason

    # Test with auto_approve=True
    approved_with_reason, _ = review_plan_with_reason(safe_plan, auto_approve=True)
    approved_without_reason = review_plan(safe_plan, auto_approve=True)
    assert approved_with_reason == approved_without_reason


def test_review_plan_with_reason_empty_dict():
    """Test rejection reason for empty dict."""
    approved, reason = review_plan_with_reason({}, auto_approve=True)

    assert approved is False
    # Empty dict fails policy (no pipeline_name or other fields)
    # The exact reason depends on what the policy checks first
    assert len(reason) > 0  # Should have a meaningful reason


def test_review_plan_with_reason_returns_tuple():
    """Test that function returns a tuple with correct types."""
    result = review_plan_with_reason({"pipeline_name": "test"})

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)


def test_review_plan_with_reason_non_empty_reason_on_rejection():
    """Test that rejection always includes a non-empty reason."""
    test_cases = [
        ("not a dict", False),
        (None, False),
        ({}, True),
        ({"pipeline_name": "unknown"}, True),
    ]

    for plan, auto_approve in test_cases:
        approved, reason = review_plan_with_reason(plan, auto_approve=auto_approve)
        if not approved:
            assert len(reason) > 0, f"Empty reason for plan={plan}, auto_approve={auto_approve}"
            assert isinstance(reason, str)


def test_review_plan_with_reason_no_side_effects(safe_plan):
    """Test that review_plan_with_reason has no side effects."""
    original_plan = safe_plan.copy()

    # Call multiple times
    review_plan_with_reason(safe_plan)
    review_plan_with_reason(safe_plan, auto_approve=True)
    review_plan_with_reason(safe_plan, auto_approve=False)

    # Plan should be unmodified
    assert safe_plan == original_plan
