"""
Batch candidate processing CLI.

Processes multiple candidate folders and generates aggregated results.
"""

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    """
    Main CLI entry point.

    Args:
        argv: Command line arguments (for testing)

    Returns:
        Exit code (0=success, 1=error, 2=no candidates)
    """
    parser = argparse.ArgumentParser(
        description="Batch process candidate folders for job discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all candidates in directory with matching enabled
  python -m jobflow.scripts.batch_run \\
    --candidates-dir ./candidates \\
    --jobs ./jobs.json \\
    --out ./results

  # Process without matching
  python -m jobflow.scripts.batch_run \\
    --candidates-dir ./candidates \\
    --jobs ./jobs.json \\
    --out ./results \\
    --no-match
""",
    )

    parser.add_argument(
        "--candidates-dir",
        required=True,
        help="Directory containing candidate folders (each with application + resume)",
    )

    parser.add_argument(
        "--jobs",
        required=True,
        help="Path to JSON file with job postings for FileJobSource",
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for results (will create if needed)",
    )

    parser.add_argument(
        "--no-match",
        action="store_true",
        help="Disable job matching (only aggregate jobs, no scoring)",
    )

    parser.add_argument(
        "--no-apply-pack",
        action="store_true",
        help="Disable apply pack exports (JSON/CSV submission-ready outputs)",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top jobs to include in apply packs (default: 25)",
    )

    parser.add_argument(
        "--company-domain",
        action="append",
        dest="company_domains",
        help="Known company domain to allowlist for URL validation (can be specified multiple times)",
    )

    args = parser.parse_args(argv)

    try:
        # Validate inputs
        candidates_dir = Path(args.candidates_dir)
        if not candidates_dir.exists():
            result = {
                "status": "error",
                "error": f"Candidates directory not found: {args.candidates_dir}",
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1

        jobs_file = Path(args.jobs)
        if not jobs_file.exists():
            result = {
                "status": "error",
                "error": f"Jobs file not found: {args.jobs}",
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1

        # Import after validation
        from jobflow.app.core.batch_runner import discover_candidate_folders, run_batch
        from jobflow.app.core.file_job_source import FileJobSource

        # Check for candidate folders
        candidate_folders = discover_candidate_folders(str(candidates_dir))
        if not candidate_folders:
            result = {
                "status": "no_candidates",
                "error": f"No candidate folders found in: {args.candidates_dir}",
                "candidates_dir": str(candidates_dir.absolute()),
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2

        # Create job source
        job_source = FileJobSource("jobs", str(jobs_file))

        # Run batch processing
        match_jobs = not args.no_match
        export_apply_packs = not args.no_apply_pack
        company_domains = set(args.company_domains) if args.company_domains else None

        batch_result = run_batch(
            candidates_dir=str(candidates_dir),
            job_sources=[job_source],
            out_dir=args.out,
            match_jobs=match_jobs,
            export_apply_packs=export_apply_packs,
            top_n=args.top_n,
            company_domains=company_domains,
        )

        # Build output
        result = {
            "status": "success",
            "candidates_dir": str(candidates_dir.absolute()),
            "jobs_file": str(jobs_file.absolute()),
            "output_dir": str(Path(args.out).absolute()),
            "match_jobs": match_jobs,
            "export_apply_packs": export_apply_packs,
            "top_n": args.top_n,
            "processed": batch_result["processed"],
            "succeeded": batch_result["succeeded"],
            "failed": batch_result["failed"],
            "summary_path": batch_result["summary_path"],
            "errors_path": batch_result["errors_path"],
            "results_dir": batch_result["results_dir"],
        }

        # Include apply packs dir if enabled
        if "apply_packs_dir" in batch_result:
            result["apply_packs_dir"] = batch_result["apply_packs_dir"]

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
