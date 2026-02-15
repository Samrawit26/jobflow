"""
Review CLI - Command-line interface for reviewing directives without execution.

This script provides a safe, read-only way to preview plans and approval
decisions without actually executing anything.

Usage:
    python -m jobflow.scripts.review job_discovery
    python -m jobflow.scripts.review job_discovery --auto-approve

CRITICAL: This script NEVER executes plans. It is review-only.
"""

import argparse
import json
import sys

from jobflow.app.core.plan_review_runner import review_directive


def main():
    """
    Main entry point for the review CLI.

    This command reviews a directive and prints the results as JSON.
    It NEVER executes the directive - it is for preview only.

    Returns:
        Always exits with code 0 (even if plan is rejected).
        Rejection is not a failure - it's a valid review result.
    """
    parser = argparse.ArgumentParser(
        description="Review a directive without executing it (dry-run mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review without approval (will be rejected by default)
  python -m jobflow.scripts.review job_discovery

  # Review with policy-based approval
  python -m jobflow.scripts.review job_discovery --auto-approve

Note: This command NEVER executes plans. Use it for:
  - Testing plan generation
  - Previewing approval decisions
  - Debugging policy rules
  - Dry-run scenarios
        """
    )

    parser.add_argument(
        "directive_name",
        help="Name of the directive to review (e.g., job_discovery)"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Use policy-based approval (default: False, will reject)"
    )

    args = parser.parse_args()

    try:
        # Call the review runner (dry-run mode, never executes)
        result = review_directive(args.directive_name, auto_approve=args.auto_approve)

        # Print results as formatted JSON
        output = json.dumps(result, indent=2, sort_keys=True)
        print(output)

        # Always exit with 0 - rejection is not a failure, it's a valid result
        return 0

    except FileNotFoundError as e:
        # Directive file not found
        error_result = {
            "error": "FileNotFoundError",
            "message": str(e),
            "directive_name": args.directive_name
        }
        print(json.dumps(error_result, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except ValueError as e:
        # Missing environment variable (e.g., OPENAI_API_KEY)
        error_result = {
            "error": "ValueError",
            "message": str(e),
            "directive_name": args.directive_name
        }
        print(json.dumps(error_result, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except Exception as e:
        # Unexpected error
        error_result = {
            "error": type(e).__name__,
            "message": str(e),
            "directive_name": args.directive_name
        }
        print(json.dumps(error_result, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
