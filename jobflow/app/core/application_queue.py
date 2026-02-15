"""
Application queue management with merge-safe status tracking.

Preserves human-edited fields (status, notes) across reruns while
updating job data from new discoveries.
"""

import csv
import hashlib
from pathlib import Path


# Exact column order for queue CSV
QUEUE_COLUMNS = [
    "job_fingerprint",
    "rank",
    "score",
    "decision",
    "company",
    "job_title",
    "location",
    "apply_url",
    "source",
    "status",
    "notes",
    "matched_keywords",
    "missing_keywords",
]


def build_queue_rows(apply_pack: dict) -> list[dict]:
    """
    Build queue rows from apply pack applications.

    Args:
        apply_pack: Apply pack dict from build_apply_pack()

    Returns:
        List of queue row dicts with QUEUE_COLUMNS keys

    Notes:
        - Stable ordering by rank ascending
        - Default status: "queued"
        - Default notes: ""
        - Keywords joined with semicolons
        - Generates fingerprint if missing
    """
    applications = apply_pack.get("applications", [])
    queue_rows = []

    for app in applications:
        # Get or generate fingerprint
        fingerprint = app.get("job_fingerprint", "")
        if not fingerprint:
            # Generate stable hash from key fields
            fingerprint = _generate_fingerprint(
                app.get("apply_url", ""),
                app.get("company", ""),
                app.get("job_title", ""),
            )

        row = {
            "job_fingerprint": fingerprint,
            "rank": app.get("rank", ""),
            "score": app.get("score", ""),
            "decision": app.get("decision", ""),
            "company": app.get("company", ""),
            "job_title": app.get("job_title", ""),
            "location": app.get("location", ""),
            "apply_url": app.get("apply_url", ""),
            "source": app.get("source", ""),
            "status": "queued",  # Default status
            "notes": "",  # Default notes
            "matched_keywords": "; ".join(app.get("matched_keywords", [])),
            "missing_keywords": "; ".join(app.get("missing_keywords", [])),
        }
        queue_rows.append(row)

    # Sort by rank for stable ordering
    queue_rows.sort(key=lambda r: (r.get("rank") or 0))

    return queue_rows


def read_queue_csv(path: str) -> list[dict]:
    """
    Read existing queue CSV.

    Args:
        path: Path to queue CSV file

    Returns:
        List of queue row dicts, or [] if file doesn't exist

    Notes:
        - Normalizes column names
        - Ignores extra columns gracefully
        - Returns empty list if file not found
    """
    queue_path = Path(path)

    if not queue_path.exists():
        return []

    rows = []

    with open(queue_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Keep only columns we care about, use defaults for missing
            normalized_row = {
                col: row.get(col, "") for col in QUEUE_COLUMNS
            }
            rows.append(normalized_row)

    return rows


def merge_queue(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """
    Merge existing queue with new job data.

    Preserves human-edited fields (status, notes) while updating job data.

    Args:
        existing_rows: Existing queue rows from read_queue_csv()
        new_rows: New queue rows from build_queue_rows()

    Returns:
        Merged queue rows sorted by (rank asc, job_fingerprint asc)

    Merge Rules:
        - Primary key: job_fingerprint
        - For existing jobs: preserve status and notes, update all other fields
        - For new jobs: add with default status="queued", notes=""
        - Output sorted by rank then fingerprint for deterministic ordering

    Notes:
        - Preserves status and notes from existing rows ALWAYS
        - Updates rank, score, decision, company, title, etc. from new rows
        - New jobs appended with defaults
        - Deterministic sort for reproducibility
    """
    # Build lookup map of existing rows by fingerprint
    existing_map = {
        row["job_fingerprint"]: row
        for row in existing_rows
        if row.get("job_fingerprint")
    }

    merged_rows = []

    # Process new rows
    for new_row in new_rows:
        fingerprint = new_row["job_fingerprint"]

        if fingerprint in existing_map:
            # Job exists - merge with preservation
            existing = existing_map[fingerprint]

            merged = {**new_row}  # Start with new data
            # Preserve human-edited fields
            merged["status"] = existing.get("status", "queued")
            merged["notes"] = existing.get("notes", "")

            merged_rows.append(merged)
            # Mark as processed
            existing_map[fingerprint] = None
        else:
            # New job - use as is (already has defaults)
            merged_rows.append(new_row)

    # Add any existing jobs that weren't in new_rows (removed from results)
    # Keep them to preserve human work
    for fingerprint, existing in existing_map.items():
        if existing is not None:  # Not marked as processed
            merged_rows.append(existing)

    # Sort for deterministic output: rank ascending, then fingerprint
    merged_rows.sort(key=lambda r: (r.get("rank") or 999999, r.get("job_fingerprint", "")))

    return merged_rows


def write_queue_csv(rows: list[dict], path: str) -> None:
    """
    Write queue rows to CSV.

    Args:
        rows: Queue rows to write
        path: Output CSV path

    Notes:
        - Creates parent directories if needed
        - Writes columns in QUEUE_COLUMNS order
        - Uses newline="" for proper CSV formatting
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _generate_fingerprint(apply_url: str, company: str, job_title: str) -> str:
    """
    Generate stable fingerprint from key job fields.

    Args:
        apply_url: Job application URL
        company: Company name
        job_title: Job title

    Returns:
        Hexadecimal fingerprint (first 16 chars of SHA256)

    Notes:
        - Used as fallback when job_fingerprint not provided
        - Deterministic: same inputs always produce same hash
        - Short format for readability
    """
    # Combine fields with delimiter
    content = f"{apply_url}|{company}|{job_title}"

    # Generate SHA256 hash
    hash_obj = hashlib.sha256(content.encode("utf-8"))

    # Return first 16 chars for brevity
    return hash_obj.hexdigest()[:16]
