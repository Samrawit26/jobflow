"""
Execution CLI - Execute directives with approval artifacts.

This script executes approved directives by loading approval artifacts
and calling the execution engine.

Usage:
    python -m jobflow.scripts.execute job_discovery --approval approval.json
    python -m jobflow.scripts.execute job_discovery --approval approval.json --payload data.json
"""

import argparse
import json
import sys
from pathlib import Path

from jobflow.app.core.plan_executor import execute_from_directive, PlanRejectedError


def main() -> int:
    """
    Main entry point for execution CLI.

    Executes a directive with a pre-issued approval artifact.

    Returns:
        0 if execution succeeds
        3 if execution rejected (approval verification failed)
        1 if error (file not found, invalid JSON, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Execute directives with approval artifacts",
        epilog="""
Examples:
  # Execute with approval artifact
  python -m jobflow.scripts.execute job_discovery --approval approval.json

  # Execute with approval and payload
  python -m jobflow.scripts.execute job_discovery --approval approval.json --payload data.json

Note: This command requires a valid approval artifact.
Use jobflow.scripts.approve to generate approval artifacts.
"""
    )

    parser.add_argument(
        "directive_name",
        help="Name of the directive to execute (e.g., job_discovery)"
    )

    parser.add_argument(
        "--approval",
        required=True,
        metavar="PATH",
        help="Path to approval artifact JSON file (required)"
    )

    parser.add_argument(
        "--payload",
        metavar="PATH",
        help="Path to payload JSON file (optional)"
    )

    args = parser.parse_args()

    try:
        # Step 1: Load approval artifact from file
        approval_path = Path(args.approval)
        if not approval_path.exists():
            raise FileNotFoundError(f"Approval file not found: {args.approval}")

        with open(approval_path, "r", encoding="utf-8") as f:
            approval = json.load(f)

        # Step 2: Load payload from file (if provided)
        payload = {}
        if args.payload:
            payload_path = Path(args.payload)
            if not payload_path.exists():
                raise FileNotFoundError(f"Payload file not found: {args.payload}")

            with open(payload_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

        # Step 3: Execute with approval artifact
        result = execute_from_directive(
            args.directive_name,
            approval=approval,
            payload=payload
        )

        # Step 4: Print result as JSON
        output_json = json.dumps(result, indent=2, sort_keys=True)
        print(output_json)

        return 0  # Success

    except PlanRejectedError as e:
        # Execution rejected due to approval verification failure
        error = {
            "directive_name": args.directive_name,
            "error_type": "PlanRejectedError",
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 3  # Exit code 3 for rejection

    except FileNotFoundError as e:
        # File not found (approval or payload)
        error = {
            "directive_name": args.directive_name,
            "error_type": "FileNotFoundError",
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except json.JSONDecodeError as e:
        # Invalid JSON in approval or payload file
        error = {
            "directive_name": args.directive_name,
            "error_type": "JSONDecodeError",
            "message": f"Invalid JSON: {str(e)}"
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except ValueError as e:
        # Missing environment variables or other value errors
        error = {
            "directive_name": args.directive_name,
            "error_type": "ValueError",
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except Exception as e:
        # Unexpected errors
        error = {
            "directive_name": args.directive_name,
            "error_type": type(e).__name__,
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
