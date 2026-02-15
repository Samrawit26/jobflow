"""
Plan Review - Safety gate for plan approval.

This module provides a review mechanism to approve or reject execution plans
before they are executed. It acts as a safety gate to prevent unauthorized
or potentially dangerous operations.

This is NOT business logic - it's a safety mechanism.
"""

from typing import Optional

from jobflow.app.core.approval_policy import evaluate_policy, get_policy_failure_reason


def review_plan_with_reason(plan: dict, auto_approve: bool = False) -> tuple[bool, str]:
    """
    Review an execution plan and provide a detailed reason for the decision.

    This function provides transparency into the approval process by
    returning both the decision and the reason for it.

    Args:
        plan: The execution plan to review (dict with pipeline_name, steps, etc.)
        auto_approve: If True, use policy-based approval (default: False)

    Returns:
        Tuple of (approved: bool, reason: str)
            - (True, reason) if approved
            - (False, reason) if rejected

    Behavior:
        - Invalid plan structure → (False, "Invalid plan structure: expected dict")
        - auto_approve=False → (False, "Rejected by default (auto_approve is False)")
        - auto_approve=True + policy passes → (True, "Auto-approved by policy")
        - auto_approve=True + policy fails → (False, detailed policy failure reason)
    """
    # Validate plan structure first
    if not isinstance(plan, dict):
        return False, "Invalid plan structure: expected dict"

    # If not auto_approve, reject immediately (fail-safe)
    if not auto_approve:
        return False, "Rejected by default (auto_approve is False)"

    # Auto-approve requested: evaluate against safety policies
    approved = evaluate_policy(plan)

    if approved:
        return True, "Auto-approved by policy"
    else:
        # Get detailed reason for policy failure
        failure_reason = get_policy_failure_reason(plan)
        return False, failure_reason


def review_plan(plan: dict, auto_approve: bool = False) -> bool:
    """
    Review an execution plan and decide whether to approve it.

    This is a safety gate that defaults to REJECTING all plans unless
    explicitly overridden. When auto_approve=True, the plan must still
    pass policy-based safety checks.

    Args:
        plan: The execution plan to review (dict with pipeline_name, steps, etc.)
        auto_approve: If True, use policy-based approval (default: False)

    Returns:
        True if the plan is approved for execution, False otherwise

    Approval Logic:
        - If auto_approve=False: REJECT (fail-safe default)
        - If auto_approve=True: Evaluate against safety policies
            - Pipeline must be in allowlist
            - Plan must have no identified risks
            - Steps must not contain forbidden keywords
            - ALL policies must pass for approval

    For detailed reasons, use review_plan_with_reason() instead.

    TODO: Future enhancements:
        - Human approval workflow (e.g., CLI prompt, web UI)
        - More sophisticated risk scoring
        - Audit logging of all approval decisions
        - Integration with approval tracking system
        - Time-based approval expiration
        - Multi-level approval for sensitive operations
    """
    # Use the explainable version and return only the decision
    approved, _reason = review_plan_with_reason(plan, auto_approve)
    return approved


def validate_plan_structure(plan: dict) -> tuple[bool, Optional[str]]:
    """
    Validate that a plan has the required structure.

    This is a helper function for plan review that checks whether
    the plan dict contains all required fields.

    Args:
        plan: The plan dict to validate

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, None)
        - If invalid: (False, "description of problem")

    TODO: Add more validation rules:
        - Validate step format and content
        - Validate risk assessment completeness
        - Check for required assumptions
        - Verify pipeline_name is known/registered
    """
    if not isinstance(plan, dict):
        return False, "Plan must be a dictionary"

    required_keys = {"pipeline_name", "steps", "risks", "assumptions"}
    missing_keys = required_keys - set(plan.keys())

    if missing_keys:
        return False, f"Plan missing required keys: {missing_keys}"

    # Validate field types
    if not isinstance(plan["pipeline_name"], str):
        return False, "pipeline_name must be a string"

    if not isinstance(plan["steps"], list):
        return False, "steps must be a list"

    if not isinstance(plan["risks"], list):
        return False, "risks must be a list"

    if not isinstance(plan["assumptions"], list):
        return False, "assumptions must be a list"

    # Validate non-empty
    if not plan["pipeline_name"]:
        return False, "pipeline_name cannot be empty"

    if not plan["steps"]:
        return False, "steps cannot be empty"

    # TODO: Add more validation
    # - Check that all steps are non-empty strings
    # - Validate pipeline_name against known pipelines
    # - Ensure risks and assumptions are strings
    # - Check for suspicious/dangerous operations in steps

    return True, None
