"""
Plan Executor - Orchestrates the complete planning and execution flow.

This module integrates:
- Planner (LLM-based plan generation)
- Approval Artifact Verification (cryptographic approval enforcement)
- Directive Router (directive → pipeline mapping)
- Orchestrator (pipeline execution)

CRITICAL SAFETY RULE: Execution is IMPOSSIBLE without a valid approval artifact.
Every execution requires cryptographic proof of approval via approval artifact.
"""

from jobflow.app.core.approval_artifact import verify_approval
from jobflow.app.core.directive_router import resolve_pipeline
from jobflow.app.core.orchestrator import run_pipeline
from jobflow.app.services.planner import build_plan


class PlanRejectedError(PermissionError):
    """Raised when a plan is rejected due to missing or invalid approval."""
    pass


def execute_from_directive(
    directive_name: str,
    approval: dict,
    payload: dict = None
) -> dict:
    """
    Execute a directive with cryptographic approval enforcement.

    This function orchestrates the complete flow:
    1. Build plan using LLM planner (reads directive, calls OpenAI)
    2. Verify approval artifact matches the plan (cryptographic check)
    3. If invalid → raise PlanRejectedError with exact reason
    4. If valid → resolve pipeline and execute via orchestrator

    CRITICAL SAFETY: Execution is IMPOSSIBLE without a valid approval artifact.
    The approval artifact cryptographically binds authorization to the exact plan.
    Any plan tampering will cause verification to fail.

    Args:
        directive_name: Name of the directive to execute (e.g., "job_discovery")
        approval: Approval artifact (from create_approval) proving authorization
        payload: Data payload to pass to the pipeline (default: empty dict)

    Returns:
        Dictionary with execution results from the orchestrator, including
        approval metadata (approved_by, approved_at, scope)

    Raises:
        PlanRejectedError: If approval is missing, invalid, or doesn't match plan
        FileNotFoundError: If the directive file doesn't exist
        ValueError: If required environment variables are missing
        RuntimeError: If plan generation or execution fails

    Example:
        # Step 1: Review and create approval
        from jobflow.app.core.plan_review_runner import review_directive
        from jobflow.app.core.approval_artifact import create_approval

        review_result = review_directive("job_discovery", auto_approve=True)
        if review_result["approved"]:
            approval = create_approval(review_result["plan"], "policy")

            # Step 2: Execute with approval
            result = execute_from_directive("job_discovery", approval)
    """
    if payload is None:
        payload = {}

    # Step 1: Build plan using LLM
    # This calls OpenAI to analyze the directive and generate a structured plan
    plan = build_plan(directive_name)

    # Step 2: Verify approval artifact matches plan
    # CRITICAL: This cryptographically verifies the approval is valid for THIS plan
    # Any plan modification after approval will cause verification to fail
    valid, reason = verify_approval(plan, approval)

    if not valid:
        raise PlanRejectedError(
            f"Plan execution rejected for directive '{directive_name}'. "
            f"Approval verification failed: {reason}. "
            f"Plan details: pipeline={plan.get('pipeline_name')}, "
            f"steps={len(plan.get('steps', []))} step(s)"
        )

    # Step 3: Resolve directive to pipeline name
    # Note: The planner also suggests a pipeline_name, but we use the
    # directive router as the authoritative source for safety
    pipeline_name = resolve_pipeline(directive_name)

    # Optional: Validate that planner's suggestion matches router
    # This helps detect misalignment between LLM suggestions and actual routing
    if plan.get("pipeline_name") != pipeline_name:
        # Log warning but proceed with authoritative router decision
        # TODO: Add proper logging here
        pass

    # Step 4: Execute pipeline via orchestrator
    result = run_pipeline(pipeline_name, payload)

    # Include plan and approval metadata in result for auditability
    result["_plan_metadata"] = {
        "directive_name": directive_name,
        "pipeline_name": pipeline_name,
        "planned_steps": plan.get("steps", []),
        "identified_risks": plan.get("risks", []),
        "assumptions": plan.get("assumptions", [])
    }

    result["_approval_metadata"] = {
        "approved_by": approval.get("approved_by"),
        "approved_at": approval.get("approved_at"),
        "scope": approval.get("scope")
    }

    return result
