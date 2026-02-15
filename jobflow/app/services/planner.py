"""
LLM Planner Service - Advisory planning using OpenAI.

This service is READ-ONLY and advisory only. It:
- Reads directive documents
- Calls OpenAI to generate structured plans
- Returns suggestions as structured data

It does NOT:
- Execute code
- Modify files
- Access databases
- Import from orchestrator, pipelines, execution, tasks, or models
"""

import json
import os
from pathlib import Path
from typing import TypedDict

from openai import OpenAI


class PlanOutput(TypedDict):
    """Structure of the plan output."""
    pipeline_name: str
    steps: list[str]
    risks: list[str]
    assumptions: list[str]


def build_plan(directive_name: str) -> dict:
    """
    Build an execution plan from a directive using LLM analysis.

    This function is advisory only. It reads a directive document,
    sends it to OpenAI for analysis, and returns a structured plan.

    Args:
        directive_name: Name of the directive (without .md extension)

    Returns:
        Dictionary with keys: pipeline_name, steps, risks, assumptions

    Raises:
        FileNotFoundError: If the directive file doesn't exist
        ValueError: If OPENAI_API_KEY is not set
        RuntimeError: If the LLM response is invalid or cannot be parsed
    """
    # Validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    # Load directive content
    directive_path = Path("directives") / f"{directive_name}.md"
    if not directive_path.exists():
        raise FileNotFoundError(
            f"Directive not found: {directive_path}. "
            f"Please create the directive file before building a plan."
        )

    directive_content = directive_path.read_text(encoding="utf-8")

    # Build prompt
    system_prompt = """You are a workflow planning assistant. Analyze the given directive and return a structured plan.

You must return ONLY valid JSON with this exact structure:
{
  "pipeline_name": "string - name of the pipeline to execute",
  "steps": ["list", "of", "execution", "steps"],
  "risks": ["list", "of", "potential", "risks"],
  "assumptions": ["list", "of", "assumptions", "being", "made"]
}

Do not include any markdown formatting, explanations, or text outside the JSON."""

    user_prompt = f"""Analyze this directive and create an execution plan:

{directive_content}

Return the plan as JSON with pipeline_name, steps, risks, and assumptions."""

    # Call OpenAI
    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract response text
        response_text = response.choices[0].message.content

        # Parse JSON
        plan_data = json.loads(response_text)

        # Validate structure
        required_keys = {"pipeline_name", "steps", "risks", "assumptions"}
        if not required_keys.issubset(plan_data.keys()):
            missing = required_keys - set(plan_data.keys())
            raise RuntimeError(f"LLM response missing required keys: {missing}")

        return plan_data

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"LLM request failed: {e}")
