"""
Unit tests for approval_artifact.py

Tests cryptographic approval artifacts that bind authorization to plan hashes.
"""

from datetime import datetime

import pytest

from jobflow.app.core.approval_artifact import (
    compute_plan_hash,
    create_approval,
    verify_approval,
)


def test_compute_plan_hash_deterministic():
    """Test that the same plan produces the same hash."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1", "step2"],
        "risks": [],
        "assumptions": ["assumption1"]
    }

    hash1 = compute_plan_hash(plan)
    hash2 = compute_plan_hash(plan)

    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex digest is 64 chars


def test_compute_plan_hash_independent_of_key_order():
    """Test that hash is same regardless of dict key ordering."""
    plan1 = {
        "pipeline_name": "test",
        "steps": ["a"],
        "risks": [],
        "assumptions": []
    }

    plan2 = {
        "assumptions": [],
        "risks": [],
        "steps": ["a"],
        "pipeline_name": "test"
    }

    hash1 = compute_plan_hash(plan1)
    hash2 = compute_plan_hash(plan2)

    assert hash1 == hash2


def test_compute_plan_hash_changes_with_plan():
    """Test that different plans produce different hashes."""
    plan1 = {
        "pipeline_name": "job_discovery",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }

    plan2 = {
        "pipeline_name": "job_discovery",
        "steps": ["step2"],  # Changed
        "risks": [],
        "assumptions": []
    }

    hash1 = compute_plan_hash(plan1)
    hash2 = compute_plan_hash(plan2)

    assert hash1 != hash2


def test_compute_plan_hash_sensitive_to_values():
    """Test that hash changes with any value change."""
    plan1 = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}
    plan2 = {"pipeline_name": "test", "steps": [], "risks": ["risk1"], "assumptions": []}
    plan3 = {"pipeline_name": "other", "steps": [], "risks": [], "assumptions": []}

    hash1 = compute_plan_hash(plan1)
    hash2 = compute_plan_hash(plan2)
    hash3 = compute_plan_hash(plan3)

    assert hash1 != hash2
    assert hash1 != hash3
    assert hash2 != hash3


def test_create_approval_structure():
    """Test that create_approval returns correct structure."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1"],
        "risks": [],
        "assumptions": []
    }

    approval = create_approval(plan, "policy", scope="single-run")

    # Verify required keys
    assert "plan_hash" in approval
    assert "approved_by" in approval
    assert "scope" in approval
    assert "approved_at" in approval

    # Verify values
    assert approval["approved_by"] == "policy"
    assert approval["scope"] == "single-run"
    assert approval["plan_hash"] == compute_plan_hash(plan)


def test_create_approval_default_scope():
    """Test that create_approval defaults to single-run scope."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = create_approval(plan, "user@example.com")

    assert approval["scope"] == "single-run"


def test_create_approval_timestamp_format():
    """Test that approved_at is a valid ISO8601 timestamp."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = create_approval(plan, "policy")

    # Should be parseable as ISO8601
    timestamp = approval["approved_at"]
    assert isinstance(timestamp, str)

    # Should parse successfully
    parsed = datetime.fromisoformat(timestamp)
    assert parsed is not None


def test_create_approval_with_session_scope():
    """Test create_approval with session scope."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = create_approval(plan, "admin", scope="session")

    assert approval["scope"] == "session"


def test_verify_approval_valid():
    """Test that verify_approval accepts valid approvals."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1", "step2"],
        "risks": [],
        "assumptions": []
    }

    approval = create_approval(plan, "policy")

    valid, reason = verify_approval(plan, approval)

    assert valid is True
    assert reason == "OK"


def test_verify_approval_plan_mismatch():
    """Test that verify_approval rejects mismatched plan hashes."""
    plan1 = {"pipeline_name": "test", "steps": ["a"], "risks": [], "assumptions": []}
    plan2 = {"pipeline_name": "test", "steps": ["b"], "risks": [], "assumptions": []}

    approval = create_approval(plan1, "policy")

    valid, reason = verify_approval(plan2, approval)

    assert valid is False
    assert "Plan hash mismatch" in reason
    assert compute_plan_hash(plan2) in reason


def test_verify_approval_not_dict():
    """Test that verify_approval rejects non-dict approvals."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    valid, reason = verify_approval(plan, "not a dict")

    assert valid is False
    assert "must be a dict" in reason


def test_verify_approval_missing_keys():
    """Test that verify_approval rejects approvals with missing keys."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    # Missing plan_hash
    approval = {
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "missing required keys" in reason
    assert "plan_hash" in reason


def test_verify_approval_wrong_types():
    """Test that verify_approval rejects approvals with wrong types."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    # plan_hash is not a string
    approval = {
        "plan_hash": 12345,
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "plan_hash must be a string" in reason


def test_verify_approval_wrong_approved_by_type():
    """Test that verify_approval rejects non-string approved_by."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = {
        "plan_hash": compute_plan_hash(plan),
        "approved_by": 123,  # Not a string
        "scope": "single-run",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "approved_by must be a string" in reason


def test_verify_approval_wrong_scope_type():
    """Test that verify_approval rejects non-string scope."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = {
        "plan_hash": compute_plan_hash(plan),
        "approved_by": "policy",
        "scope": 123,  # Not a string
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "scope must be a string" in reason


def test_verify_approval_wrong_approved_at_type():
    """Test that verify_approval rejects non-string approved_at."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = {
        "plan_hash": compute_plan_hash(plan),
        "approved_by": "policy",
        "scope": "single-run",
        "approved_at": 123  # Not a string
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "approved_at must be a string" in reason


def test_verify_approval_invalid_scope():
    """Test that verify_approval rejects invalid scope values."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = {
        "plan_hash": compute_plan_hash(plan),
        "approved_by": "policy",
        "scope": "invalid-scope",
        "approved_at": "2025-01-01T00:00:00+00:00"
    }

    valid, reason = verify_approval(plan, approval)

    assert valid is False
    assert "Invalid scope" in reason
    assert "invalid-scope" in reason
    assert "single-run" in reason
    assert "session" in reason


def test_verify_approval_single_run_scope():
    """Test that verify_approval accepts single-run scope."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = create_approval(plan, "policy", scope="single-run")

    valid, reason = verify_approval(plan, approval)

    assert valid is True
    assert reason == "OK"


def test_verify_approval_session_scope():
    """Test that verify_approval accepts session scope."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval = create_approval(plan, "admin", scope="session")

    valid, reason = verify_approval(plan, approval)

    assert valid is True
    assert reason == "OK"


def test_approval_binds_to_exact_plan():
    """Test that approval is bound to exact plan content."""
    plan = {
        "pipeline_name": "job_discovery",
        "steps": ["step1", "step2"],
        "risks": [],
        "assumptions": ["db available"]
    }

    approval = create_approval(plan, "policy")

    # Original plan verifies
    valid, _ = verify_approval(plan, approval)
    assert valid is True

    # Modified pipeline_name fails
    modified_plan = dict(plan)
    modified_plan["pipeline_name"] = "different"
    valid, _ = verify_approval(modified_plan, approval)
    assert valid is False

    # Modified steps fails
    modified_plan = dict(plan)
    modified_plan["steps"] = ["step1", "step2", "step3"]
    valid, _ = verify_approval(modified_plan, approval)
    assert valid is False

    # Modified risks fails
    modified_plan = dict(plan)
    modified_plan["risks"] = ["new risk"]
    valid, _ = verify_approval(modified_plan, approval)
    assert valid is False

    # Modified assumptions fails
    modified_plan = dict(plan)
    modified_plan["assumptions"] = []
    valid, _ = verify_approval(modified_plan, approval)
    assert valid is False


def test_approval_artifact_immutability():
    """Test that approval artifacts provide tamper detection."""
    plan = {"pipeline_name": "test", "steps": ["a", "b"], "risks": [], "assumptions": []}

    approval = create_approval(plan, "human-approver")

    # Store original hash
    original_hash = approval["plan_hash"]

    # Verify original works
    valid, _ = verify_approval(plan, approval)
    assert valid is True

    # Tamper with approval artifact
    approval["plan_hash"] = "0" * 64  # Invalid hash

    valid, reason = verify_approval(plan, approval)
    assert valid is False
    assert "Plan hash mismatch" in reason


def test_compute_plan_hash_empty_plan():
    """Test hash computation with minimal/empty plan."""
    plan = {}

    hash1 = compute_plan_hash(plan)
    hash2 = compute_plan_hash(plan)

    assert hash1 == hash2
    assert len(hash1) == 64


def test_create_approval_with_different_approvers():
    """Test that different approvers produce different artifacts."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    approval1 = create_approval(plan, "policy")
    approval2 = create_approval(plan, "admin")

    # Same plan hash
    assert approval1["plan_hash"] == approval2["plan_hash"]

    # Different approvers
    assert approval1["approved_by"] == "policy"
    assert approval2["approved_by"] == "admin"

    # Both verify
    assert verify_approval(plan, approval1) == (True, "OK")
    assert verify_approval(plan, approval2) == (True, "OK")


def test_verify_approval_all_required_keys():
    """Test that all four required keys must be present."""
    plan = {"pipeline_name": "test", "steps": [], "risks": [], "assumptions": []}

    # Missing each key one at a time
    keys_to_test = ["plan_hash", "approved_by", "scope", "approved_at"]

    for missing_key in keys_to_test:
        approval = create_approval(plan, "policy")
        del approval[missing_key]

        valid, reason = verify_approval(plan, approval)

        assert valid is False
        assert "missing required keys" in reason
        assert missing_key in reason
