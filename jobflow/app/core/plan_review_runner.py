"""
Plan Review Runner - Dry-run interface for plan review without execution.

This module provides a safe "preview" pathway that:
- Builds plans using the LLM planner
- Reviews plans through the approval gate
- Returns the review results WITHOUT executing anything

CRITICAL: This module NEVER executes plans. It is for:
- Testing plan generation
- Previewing approval decisions
- Debugging policy rules
- Dry-run scenarios

This is NOT the execution pathway. Use plan_executor for actual execution.
"""

from jobflow.app.core.plan_review import review_plan_with_reason
from jobflow.app.services.planner import build_plan


def review_directive(directive_name: str, auto_approve: bool = False) -> dict:
    """
    Review a directive without executing it (dry-run mode).

    This function builds a plan and reviews it, but NEVER executes.
    It provides a safe way to preview what would happen without
    actually running any workflows.

    Flow:
        1. Build plan using LLM planner
        2. Review plan through approval gate
        3. Return results (approved, reason, plan)
        4. DO NOT execute anything

    Args:
        directive_name: Name of the directive to review (e.g., "job_discovery")
        auto_approve: If True, use policy-based approval (default: False)

    Returns:
        Dictionary with:
            - directive_name (str): The directive that was reviewed
            - approved (bool): Whether the plan was approved
            - reason (str): Detailed reason for approval/rejection
            - plan (dict): The generated plan (with pipeline_name, steps, risks, assumptions)

    Raises:
        FileNotFoundError: If the directive file doesn't exist
        ValueError: If required environment variables are missing
        RuntimeError: If plan generation fails

    Example:
        # Preview without approval
        result = review_directive("job_discovery")
        print(f"Approved: {result['approved']}")
        print(f"Reason: {result['reason']}")

        # Preview with policy-based approval
        result = review_directive("job_discovery", auto_approve=True)
        if result['approved']:
            print("Plan would be approved and executed")
        else:
            print(f"Plan would be rejected: {result['reason']}")
    """
    # Step 1: Build plan using LLM
    # This calls OpenAI to analyze the directive and generate a structured plan
    plan = build_plan(directive_name)

    # Step 2: Review plan through approval gate
    # This evaluates the plan against policies and returns approval decision
    approved, reason = review_plan_with_reason(plan, auto_approve=auto_approve)

    # Step 3: Return results WITHOUT executing anything
    # This is the key difference from plan_executor - we stop here
    return {
        "directive_name": directive_name,
        "approved": approved,
        "reason": reason,
        "plan": plan
    }
