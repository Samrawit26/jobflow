"""
Approval Issuance CLI - Generate approval artifacts without execution.

This script reviews directives and issues cryptographic approval artifacts
when policies are satisfied. It NEVER executes anything.

Usage:
    python -m jobflow.scripts.approve job_discovery --approved-by "policy"
    python -m jobflow.scripts.approve job_discovery --approved-by "admin" --auto-approve
    python -m jobflow.scripts.approve job_discovery --approved-by "user@example.com" --scope session --out approval.json
"""

import argparse
import json
import sys

from jobflow.app.core.approval_artifact import create_approval
from jobflow.app.core.plan_review_runner import review_directive


def main() -> int:
    """
    Main entry point for approval issuance CLI.

    Reviews a directive and issues an approval artifact if approved.
    NEVER executes anything.

    Returns:
        0 if approval issued
        2 if plan rejected
        1 if error
    """
    parser = argparse.ArgumentParser(
        description="Issue approval artifacts for directives (dry-run only)",
        epilog="""
Examples:
  # Review and issue approval if policy passes
  python -m jobflow.scripts.approve job_discovery --approved-by "policy" --auto-approve

  # Issue approval for specific user with session scope
  python -m jobflow.scripts.approve job_discovery --approved-by "admin@example.com" --scope session

  # Save approval to file
  python -m jobflow.scripts.approve job_discovery --approved-by "policy" --auto-approve --out approval.json

Note: This command NEVER executes plans. Use it for:
  - Generating approval artifacts for later execution
  - Auditing plan review decisions
  - Pre-approving directives
"""
    )

    parser.add_argument(
        "directive_name",
        help="Name of the directive to review (e.g., job_discovery)"
    )

    parser.add_argument(
        "--approved-by",
        required=True,
        help="Identifier of who/what is approving (e.g., 'policy', 'user@example.com')"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Use policy-based approval (default: False, will reject)"
    )

    parser.add_argument(
        "--scope",
        choices=["single-run", "session"],
        default="single-run",
        help="Approval scope (default: single-run)"
    )

    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Write approval to file instead of stdout"
    )

    args = parser.parse_args()

    try:
        # Step 1: Review the directive
        review_result = review_directive(args.directive_name, auto_approve=args.auto_approve)

        # Step 2: Check if approved
        if not review_result["approved"]:
            # Plan rejected - return rejection details
            output = {
                "directive_name": review_result["directive_name"],
                "approved": False,
                "reason": review_result["reason"]
            }

            output_json = json.dumps(output, indent=2, sort_keys=True)
            print(output_json)

            return 2  # Exit code 2 for rejection

        # Step 3: Plan approved - create approval artifact
        approval = create_approval(
            review_result["plan"],
            approved_by=args.approved_by,
            scope=args.scope
        )

        # Step 4: Prepare output
        output = {
            "directive_name": review_result["directive_name"],
            "approved": True,
            "reason": review_result["reason"],
            "plan_hash": approval["plan_hash"],
            "approval": approval
        }

        output_json = json.dumps(output, indent=2, sort_keys=True)

        # Step 5: Write to file or stdout
        if args.out:
            # Write to file
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(output_json)

            # Print confirmation to stdout
            print(f"Approval artifact written to {args.out}")
        else:
            # Print to stdout
            print(output_json)

        return 0  # Success

    except FileNotFoundError as e:
        # Directive file not found
        error = {
            "directive_name": args.directive_name,
            "error": "FileNotFoundError",
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except ValueError as e:
        # Missing environment variables or other value errors
        error = {
            "directive_name": args.directive_name,
            "error": "ValueError",
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    except Exception as e:
        # Unexpected errors
        error = {
            "directive_name": args.directive_name,
            "error": type(e).__name__,
            "message": str(e)
        }
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
