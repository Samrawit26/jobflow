"""
Google Drive candidate folder synchronization.

Stages candidate folders from Google Drive to local filesystem for processing.
"""

from pathlib import Path

from jobflow.app.core.batch_runner import safe_slug


# Supported file extensions
RESUME_EXTENSIONS = {".txt", ".md", ".docx"}
APPLICATION_EXTENSIONS = {".xlsx"}
DEPRECATED_EXTENSIONS = {".doc"}  # Warn but skip

# Drive folder mime type
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def sync_candidate_folders(
    drive_client,
    root_folder_id: str,
    staging_dir: str,
    dry_run: bool = False,
    max_candidates: int | None = None
) -> dict:
    """
    Sync candidate folders from Google Drive to local staging directory.

    Args:
        drive_client: DriveClient instance
        root_folder_id: Google Drive ID of root folder containing candidate folders
        staging_dir: Local directory to stage candidates
        dry_run: If True, list files but don't download (default False)
        max_candidates: Optional limit on number of candidates to process

    Returns:
        Dict with:
            - processed: Number of candidate folders processed
            - downloaded: Number of files downloaded
            - skipped: Number of files skipped
            - warnings: List of warning messages
            - candidates: List of per-candidate details (name, folder_path, files)

    Notes:
        - Each immediate subfolder of root_folder_id is treated as a candidate folder
        - Only downloads supported file types (resume: .txt/.md/.docx, application: .xlsx)
        - Skips .doc files with warning
        - Creates staging_dir/<safe_slug(folder_name)>/ for each candidate
        - Preserves original filenames
    """
    staging_path = Path(staging_dir)

    # Create staging dir if not dry run
    if not dry_run:
        staging_path.mkdir(parents=True, exist_ok=True)

    # List candidate folders (immediate children of root)
    children = drive_client.list_children(root_folder_id)
    candidate_folders = [
        child for child in children
        if child["mimeType"] == DRIVE_FOLDER_MIME
    ]

    if not candidate_folders:
        return {
            "processed": 0,
            "downloaded": 0,
            "skipped": 0,
            "warnings": [],
            "candidates": [],
        }

    # Limit candidates if specified
    if max_candidates:
        candidate_folders = candidate_folders[:max_candidates]

    # Process each candidate folder
    processed = 0
    total_downloaded = 0
    total_skipped = 0
    warnings = []
    candidates_details = []

    for folder in candidate_folders:
        folder_name = folder["name"]
        folder_id = folder["id"]

        # Create safe slug for local directory
        slug = safe_slug(folder_name)
        candidate_staging = staging_path / slug

        # Create candidate directory if not dry run
        if not dry_run:
            candidate_staging.mkdir(parents=True, exist_ok=True)

        # List files in candidate folder
        files = drive_client.list_children(folder_id)

        # Filter to downloadable files
        downloaded_files = []
        skipped_files = []

        for file_item in files:
            # Skip subfolders
            if file_item["mimeType"] == DRIVE_FOLDER_MIME:
                continue

            file_name = file_item["name"]
            file_id = file_item["id"]
            file_ext = Path(file_name).suffix.lower()

            # Check if supported
            if file_ext in RESUME_EXTENSIONS or file_ext in APPLICATION_EXTENSIONS:
                # Download file
                dest_path = candidate_staging / file_name

                if not dry_run:
                    drive_client.download_file(file_id, str(dest_path))

                downloaded_files.append({
                    "name": file_name,
                    "path": str(dest_path) if not dry_run else str(dest_path),
                    "type": "resume" if file_ext in RESUME_EXTENSIONS else "application",
                })
                total_downloaded += 1

            elif file_ext in DEPRECATED_EXTENSIONS:
                # Warn about deprecated format
                warning_msg = f"Skipped deprecated format: {folder_name}/{file_name} ({file_ext} not supported, use .docx)"
                warnings.append(warning_msg)
                skipped_files.append(file_name)
                total_skipped += 1

            else:
                # Skip unsupported file type silently
                skipped_files.append(file_name)
                total_skipped += 1

        # Add candidate details
        candidates_details.append({
            "name": folder_name,
            "slug": slug,
            "folder_path": str(candidate_staging),
            "drive_folder_id": folder_id,
            "files_downloaded": len(downloaded_files),
            "files_skipped": len(skipped_files),
            "files": downloaded_files,
        })

        processed += 1

    return {
        "processed": processed,
        "downloaded": total_downloaded,
        "skipped": total_skipped,
        "warnings": warnings,
        "candidates": candidates_details,
    }
