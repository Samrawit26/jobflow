"""
Directive Router - Maps directive names to pipeline names.

This is a simple lookup layer with no logic, parsing, or LLM calls.
"""


# Directive to pipeline mapping
DIRECTIVE_TO_PIPELINE = {
    "job_discovery": "job_discovery",
    "batch_run": "batch_candidate_processing",
}


def resolve_pipeline(directive_name: str) -> str:
    """
    Resolve a directive name to its corresponding pipeline name.

    Args:
        directive_name: The name of the directive

    Returns:
        The name of the pipeline to execute

    Raises:
        ValueError: If the directive name is not recognized
    """
    if directive_name not in DIRECTIVE_TO_PIPELINE:
        raise ValueError(f"Unknown directive: {directive_name}")

    return DIRECTIVE_TO_PIPELINE[directive_name]
