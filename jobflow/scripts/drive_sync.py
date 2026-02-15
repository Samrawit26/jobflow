"""
Google Drive sync CLI.

Stages candidate folders from Google Drive to local filesystem.
"""

import argparse
import json
import sys


def main(argv=None):
    """
    Main CLI entry point for Drive sync.

    Args:
        argv: Command line arguments (for testing)

    Returns:
        Exit code (0=success, 1=error, 2=no candidates)
    """
    parser = argparse.ArgumentParser(
        description="Sync candidate folders from Google Drive to local staging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be synced
  python -m jobflow.scripts.drive_sync \\
    --root-folder-id 1234567890abcdefgh \\
    --staging ./staged_candidates \\
    --dry-run

  # Sync all candidates
  python -m jobflow.scripts.drive_sync \\
    --root-folder-id 1234567890abcdefgh \\
    --staging ./staged_candidates

  # Sync first 10 candidates
  python -m jobflow.scripts.drive_sync \\
    --root-folder-id 1234567890abcdefgh \\
    --staging ./staged_candidates \\
    --max-candidates 10

Prerequisites:
  - Set GOOGLE_APPLICATION_CREDENTIALS to service account JSON path
  - Service account must have Drive read-only access
  - Root folder must be shared with service account
""",
    )

    parser.add_argument(
        "--root-folder-id",
        required=True,
        help="Google Drive folder ID containing candidate folders",
    )

    parser.add_argument(
        "--staging",
        required=True,
        help="Local directory to stage candidate folders",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files but don't download (default: False)",
    )

    parser.add_argument(
        "--max-candidates",
        type=int,
        help="Maximum number of candidates to process (default: all)",
    )

    args = parser.parse_args(argv)

    try:
        # Import after validation
        from jobflow.app.services.drive_client import DriveClient
        from jobflow.app.services.drive_sync import sync_candidate_folders

        # Initialize Drive client
        try:
            drive_client = DriveClient()
        except RuntimeError as e:
            result = {
                "status": "error",
                "error": str(e),
                "error_type": "CredentialsError",
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1
        except ImportError as e:
            result = {
                "status": "error",
                "error": str(e),
                "error_type": "DependencyError",
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1

        # Sync candidate folders
        sync_result = sync_candidate_folders(
            drive_client=drive_client,
            root_folder_id=args.root_folder_id,
            staging_dir=args.staging,
            dry_run=args.dry_run,
            max_candidates=args.max_candidates,
        )

        # Check if any candidates found
        if sync_result["processed"] == 0:
            result = {
                "status": "no_candidates",
                "error": f"No candidate folders found in Drive folder: {args.root_folder_id}",
                "root_folder_id": args.root_folder_id,
                "staging_dir": args.staging,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2

        # Build success output
        result = {
            "status": "success",
            "root_folder_id": args.root_folder_id,
            "staging_dir": args.staging,
            "dry_run": args.dry_run,
            "processed": sync_result["processed"],
            "downloaded": sync_result["downloaded"],
            "skipped": sync_result["skipped"],
            "warnings": sync_result["warnings"],
            "candidates": sync_result["candidates"],
        }

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    except Exception as e:
        result = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
