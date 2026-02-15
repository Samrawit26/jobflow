"""
Approval Policy - Policy-based auto-approval rules.

This module enforces safety policies for automatic plan approval.
Even when auto_approve=True, plans must pass policy checks.

This is NOT business logic - it's a safety/security mechanism.
"""

from typing import Set


# Policy Configuration
# TODO: Move these to a configuration file or environment-based config

# Pipelines that are safe for auto-approval
ALLOWED_PIPELINES: Set[str] = {
    "job_discovery",
}

# Keywords that indicate potentially dangerous operations
# Plans containing these keywords in steps will be rejected
FORBIDDEN_KEYWORDS: Set[str] = {
    "write",
    "delete",
    "update",
    "send",
    "apply",
    "http",
    "api",
}


def evaluate_policy(plan: dict) -> bool:
    """
    Evaluate whether a plan passes auto-approval policies.

    This function implements safety policies that must ALL pass for
    a plan to be auto-approved. This provides defense-in-depth:
    even with auto_approve=True, dangerous plans are rejected.

    Policy Rules (ALL must pass):
    1. Pipeline must be in the allowlist
    2. Plan must have no identified risks
    3. Plan steps must not contain forbidden keywords

    Args:
        plan: The execution plan to evaluate

    Returns:
        True if ALL policies pass, False if any policy fails

    TODO: Future enhancements:
        - Risk scoring (allow low-risk items)
        - Per-pipeline keyword allowlists/denylists
        - Time-based restrictions (e.g., no auto-approve outside business hours)
        - User/role-based policies
        - Environment-based policies (more restrictive in prod)
        - Rate limiting (max N auto-approvals per hour)
        - Plan complexity limits (max steps, max duration)
    """
    # Validate plan structure first
    if not isinstance(plan, dict):
        return False

    # Policy 1: Pipeline must be in allowlist
    pipeline_name = plan.get("pipeline_name", "")
    if not _is_pipeline_allowed(pipeline_name):
        return False

    # Policy 2: No identified risks
    risks = plan.get("risks", [])
    if not _are_risks_acceptable(risks):
        return False

    # Policy 3: No forbidden keywords in steps
    steps = plan.get("steps", [])
    if not _are_steps_safe(steps):
        return False

    # All policies passed
    return True


def _is_pipeline_allowed(pipeline_name: str) -> bool:
    """
    Check if a pipeline is in the allowlist.

    Args:
        pipeline_name: Name of the pipeline to check

    Returns:
        True if pipeline is allowed, False otherwise
    """
    if not isinstance(pipeline_name, str):
        return False

    if not pipeline_name:
        return False

    return pipeline_name in ALLOWED_PIPELINES


def _are_risks_acceptable(risks: list) -> bool:
    """
    Check if the identified risks are acceptable for auto-approval.

    Current policy: ANY identified risks cause rejection.
    Future: Could implement risk scoring and thresholds.

    Args:
        risks: List of identified risks

    Returns:
        True if risks are acceptable, False otherwise
    """
    if not isinstance(risks, list):
        return False

    # Current policy: No risks allowed for auto-approval
    # Even empty string risks are considered risks
    return len(risks) == 0


def _are_steps_safe(steps: list) -> bool:
    """
    Check if plan steps contain forbidden keywords.

    Args:
        steps: List of execution steps

    Returns:
        True if steps are safe, False if forbidden keywords found
    """
    if not isinstance(steps, list):
        return False

    # Check each step for forbidden keywords
    for step in steps:
        if not isinstance(step, str):
            # Non-string steps are suspicious
            return False

        # Check for forbidden keywords (case-insensitive)
        step_lower = step.lower()
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in step_lower:
                # Found a forbidden keyword
                return False

    # No forbidden keywords found
    return True


def get_policy_failure_reason(plan: dict) -> str:
    """
    Get a detailed explanation of why a plan failed policy evaluation.

    This is useful for debugging and providing clear feedback.

    Args:
        plan: The plan that failed evaluation

    Returns:
        Human-readable explanation of policy failure
    """
    if not isinstance(plan, dict):
        return "Plan is not a valid dictionary"

    reasons = []

    # Check each policy
    pipeline_name = plan.get("pipeline_name", "")
    if not _is_pipeline_allowed(pipeline_name):
        reasons.append(
            f"Pipeline '{pipeline_name}' is not in the allowlist. "
            f"Allowed pipelines: {sorted(ALLOWED_PIPELINES)}"
        )

    risks = plan.get("risks", [])
    if not _are_risks_acceptable(risks):
        reasons.append(
            f"Plan has {len(risks)} identified risk(s). "
            f"Auto-approval requires zero risks. Risks: {risks}"
        )

    steps = plan.get("steps", [])
    if not _are_steps_safe(steps):
        # Find which keywords were found
        found_keywords = []
        for step in steps:
            if isinstance(step, str):
                step_lower = step.lower()
                for keyword in FORBIDDEN_KEYWORDS:
                    if keyword in step_lower:
                        found_keywords.append(keyword)
        reasons.append(
            f"Plan steps contain forbidden keywords: {sorted(set(found_keywords))}. "
            f"Steps must not contain: {sorted(FORBIDDEN_KEYWORDS)}"
        )

    if not reasons:
        return "Plan passed all policies (unexpected - should not be called)"

    return " | ".join(reasons)
