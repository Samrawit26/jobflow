"""
Approval Artifact - Cryptographic binding of approvals to execution plans.

This module provides tamper-proof approval artifacts that bind authorization
decisions to specific plan hashes. This ensures:
- Plans cannot be modified after approval
- Approvals are auditable and traceable
- Authorization scope is clearly defined

IMPORTANT: This is a security mechanism. All functions are pure and deterministic
(except timestamp generation in create_approval).
"""

import hashlib
import json
from datetime import datetime, timezone


def compute_plan_hash(plan: dict) -> str:
    """
    Compute a deterministic SHA-256 hash of a plan.

    Uses JSON canonicalization to ensure the same plan always produces
    the same hash, regardless of key ordering or whitespace.

    Args:
        plan: The execution plan to hash

    Returns:
        Hex-encoded SHA-256 hash (64 characters)

    Example:
        >>> plan = {"pipeline_name": "test", "steps": ["a", "b"]}
        >>> hash1 = compute_plan_hash(plan)
        >>> hash2 = compute_plan_hash(plan)
        >>> hash1 == hash2
        True
    """
    # Canonicalize JSON: sorted keys, no whitespace
    canonical_json = json.dumps(plan, sort_keys=True, separators=(",", ":"))

    # Compute SHA-256 hash
    hash_bytes = hashlib.sha256(canonical_json.encode("utf-8")).digest()

    # Return hex-encoded hash
    return hash_bytes.hex()


def create_approval(plan: dict, approved_by: str, scope: str = "single-run") -> dict:
    """
    Create an approval artifact for a plan.

    The approval artifact cryptographically binds authorization to a specific
    plan using a hash. This prevents tampering and provides auditability.

    Args:
        plan: The execution plan being approved
        approved_by: Identifier of who/what approved (e.g., "policy", "user@example.com")
        scope: Approval scope - "single-run" or "session" (default: "single-run")

    Returns:
        Approval artifact dict with:
            - plan_hash: SHA-256 hash of the plan
            - approved_by: Who approved it
            - scope: Authorization scope
            - approved_at: ISO8601 timestamp in UTC

    Example:
        >>> plan = {"pipeline_name": "job_discovery", "steps": []}
        >>> approval = create_approval(plan, "policy")
        >>> "plan_hash" in approval
        True
        >>> approval["approved_by"]
        'policy'
        >>> approval["scope"]
        'single-run'
    """
    return {
        "plan_hash": compute_plan_hash(plan),
        "approved_by": approved_by,
        "scope": scope,
        "approved_at": datetime.now(timezone.utc).isoformat()
    }


def verify_approval(plan: dict, approval: dict) -> tuple[bool, str]:
    """
    Verify that an approval artifact is valid for a given plan.

    Performs comprehensive validation:
    - Approval structure is correct
    - Plan hash matches current plan
    - Scope is valid

    This prevents:
    - Plan tampering after approval
    - Use of approvals with wrong plans
    - Invalid approval artifacts

    Args:
        plan: The execution plan to verify against
        approval: The approval artifact to validate

    Returns:
        Tuple of (valid: bool, reason: str)
            - (True, "OK") if valid
            - (False, reason) if invalid

    Example:
        >>> plan = {"pipeline_name": "test", "steps": []}
        >>> approval = create_approval(plan, "policy")
        >>> verify_approval(plan, approval)
        (True, 'OK')

        >>> modified_plan = {"pipeline_name": "test", "steps": ["changed"]}
        >>> verify_approval(modified_plan, approval)
        (False, 'Plan hash mismatch...')
    """
    # Validate approval is a dict
    if not isinstance(approval, dict):
        return False, "Approval must be a dict"

    # Validate required keys exist
    required_keys = {"plan_hash", "approved_by", "scope", "approved_at"}
    missing_keys = required_keys - set(approval.keys())
    if missing_keys:
        return False, f"Approval missing required keys: {sorted(missing_keys)}"

    # Validate types
    if not isinstance(approval["plan_hash"], str):
        return False, "plan_hash must be a string"
    if not isinstance(approval["approved_by"], str):
        return False, "approved_by must be a string"
    if not isinstance(approval["scope"], str):
        return False, "scope must be a string"
    if not isinstance(approval["approved_at"], str):
        return False, "approved_at must be a string"

    # Validate scope
    valid_scopes = {"single-run", "session"}
    if approval["scope"] not in valid_scopes:
        return False, f"Invalid scope '{approval['scope']}'. Must be one of: {sorted(valid_scopes)}"

    # Validate plan hash matches
    expected_hash = compute_plan_hash(plan)
    if approval["plan_hash"] != expected_hash:
        return False, f"Plan hash mismatch. Expected {expected_hash}, got {approval['plan_hash']}"

    return True, "OK"
