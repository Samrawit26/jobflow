"""
Apply pack export functions for JSON and CSV formats.

Writes submission-ready application packs to disk in multiple formats.
"""

import csv
import json
from pathlib import Path


def write_apply_pack_json(pack: dict, path: str) -> None:
    """
    Write apply pack to JSON file.

    Args:
        pack: Apply pack dictionary from build_apply_pack()
        path: Output file path (will be created/overwritten)

    Notes:
        - Creates parent directories if needed
        - Pretty-printed JSON with 2-space indent
        - Sorted keys for stable output
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, sort_keys=True, ensure_ascii=False)


def write_apply_pack_csv(pack: dict, path: str) -> None:
    """
    Write apply pack applications to CSV file.

    Args:
        pack: Apply pack dictionary from build_apply_pack()
        path: Output file path (will be created/overwritten)

    CSV Columns:
        rank, score, decision, company, job_title, location, apply_url, source,
        url_policy, url_reason, reasons, matched_keywords, missing_keywords

    Notes:
        - Creates parent directories if needed
        - List fields (reasons, keywords) are joined with semicolons
        - Empty applications list creates CSV with headers only
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    applications = pack.get("applications", [])

    # Define CSV columns
    fieldnames = [
        "rank",
        "score",
        "decision",
        "company",
        "job_title",
        "location",
        "apply_url",
        "source",
        "url_policy",
        "url_reason",
        "reasons",
        "matched_keywords",
        "missing_keywords",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for app in applications:
            # Convert list fields to semicolon-separated strings
            row = {
                "rank": app.get("rank", ""),
                "score": app.get("score", ""),
                "decision": app.get("decision", ""),
                "company": app.get("company", ""),
                "job_title": app.get("job_title", ""),
                "location": app.get("location", ""),
                "apply_url": app.get("apply_url", ""),
                "source": app.get("source", ""),
                "url_policy": app.get("url_policy", ""),
                "url_reason": app.get("url_reason", ""),
                "reasons": "; ".join(app.get("reasons", [])),
                "matched_keywords": "; ".join(app.get("matched_keywords", [])),
                "missing_keywords": "; ".join(app.get("missing_keywords", [])),
            }
            writer.writerow(row)
