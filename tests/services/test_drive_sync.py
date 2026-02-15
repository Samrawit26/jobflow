"""
Unit tests for drive_sync.py

Tests candidate folder synchronization with FakeDriveClient stub.
"""

from pathlib import Path

import pytest


class FakeDriveClient:
    """
    Fake Drive client for testing (no external API).

    Simulates folder structure and file downloads with in-memory data.
    """

    def __init__(self, folder_structure: dict):
        """
        Initialize fake client with folder structure.

        Args:
            folder_structure: Dict mapping folder_id -> list of child dicts
                Each child: {"id": str, "name": str, "mimeType": str, "content": bytes}
        """
        self.folder_structure = folder_structure

    def list_children(self, folder_id: str) -> list[dict]:
        """List children of folder (sorted by name)."""
        children = self.folder_structure.get(folder_id, [])
        # Return copy without content field
        result = [
            {"id": child["id"], "name": child["name"], "mimeType": child["mimeType"]}
            for child in children
        ]
        result.sort(key=lambda x: x["name"])
        return result

    def download_file(self, file_id: str, dest_path: str) -> None:
        """Download file by writing content to dest_path."""
        # Find file in structure
        for folder_children in self.folder_structure.values():
            for child in folder_children:
                if child["id"] == file_id:
                    # Write content
                    dest_path_obj = Path(dest_path)
                    dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    dest_path_obj.write_bytes(child.get("content", b"fake content"))
                    return

        raise ValueError(f"File not found: {file_id}")


def test_sync_candidate_folders_basic(tmp_path):
    """Test basic candidate folder sync."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    # Setup fake folder structure
    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain", "content": b"resume content"},
            {"id": "file2", "name": "application.xlsx", "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "content": b"xlsx content"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify result
    assert result["processed"] == 1
    assert result["downloaded"] == 2
    assert result["skipped"] == 0
    assert result["warnings"] == []

    # Verify files downloaded
    candidate_dir = staging_dir / "candidate_a"
    assert candidate_dir.exists()
    assert (candidate_dir / "resume.txt").exists()
    assert (candidate_dir / "application.xlsx").exists()

    # Verify content
    assert (candidate_dir / "resume.txt").read_bytes() == b"resume content"


def test_sync_candidate_folders_dry_run(tmp_path):
    """Test dry run performs no downloads."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=True,
    )

    # Verify counts
    assert result["processed"] == 1
    assert result["downloaded"] == 1  # Counted but not actually downloaded

    # Verify no files written
    candidate_dir = staging_dir / "candidate_a"
    assert not candidate_dir.exists()


def test_sync_candidate_folders_skips_doc(tmp_path):
    """Test that .doc files are skipped with warning."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.doc", "mimeType": "application/msword"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify counts
    assert result["processed"] == 1
    assert result["downloaded"] == 0
    assert result["skipped"] == 1

    # Verify warning
    assert len(result["warnings"]) == 1
    assert ".doc not supported" in result["warnings"][0]


def test_sync_candidate_folders_multiple_candidates(tmp_path):
    """Test syncing multiple candidate folders."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "folder2", "name": "Candidate B", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain"},
        ],
        "folder2": [
            {"id": "file2", "name": "resume.md", "mimeType": "text/markdown"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify counts
    assert result["processed"] == 2
    assert result["downloaded"] == 2

    # Verify both candidate folders created
    assert (staging_dir / "candidate_a").exists()
    assert (staging_dir / "candidate_b").exists()


def test_sync_candidate_folders_max_candidates(tmp_path):
    """Test max_candidates limits processing."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "folder2", "name": "Candidate B", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "folder3", "name": "Candidate C", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain"},
        ],
        "folder2": [
            {"id": "file2", "name": "resume.txt", "mimeType": "text/plain"},
        ],
        "folder3": [
            {"id": "file3", "name": "resume.txt", "mimeType": "text/plain"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
        max_candidates=2,
    )

    # Verify only 2 processed
    assert result["processed"] == 2
    assert result["downloaded"] == 2


def test_sync_candidate_folders_no_candidates(tmp_path):
    """Test handling of empty root folder."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [],  # No children
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify zero counts
    assert result["processed"] == 0
    assert result["downloaded"] == 0
    assert result["skipped"] == 0
    assert result["candidates"] == []


def test_sync_candidate_folders_skips_unsupported_extensions(tmp_path):
    """Test that unsupported file extensions are skipped silently."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain"},
            {"id": "file2", "name": "photo.jpg", "mimeType": "image/jpeg"},
            {"id": "file3", "name": "notes.pdf", "mimeType": "application/pdf"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify counts
    assert result["processed"] == 1
    assert result["downloaded"] == 1  # Only resume.txt
    assert result["skipped"] == 2  # jpg and pdf

    # Verify only resume downloaded
    candidate_dir = staging_dir / "candidate_a"
    assert (candidate_dir / "resume.txt").exists()
    assert not (candidate_dir / "photo.jpg").exists()
    assert not (candidate_dir / "notes.pdf").exists()


def test_sync_candidate_folders_preserves_filenames(tmp_path):
    """Test that original filenames are preserved."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "John_Doe_Resume.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
            {"id": "file2", "name": "Application_Form_2024.xlsx", "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify filenames preserved
    candidate_dir = staging_dir / "candidate_a"
    assert (candidate_dir / "John_Doe_Resume.docx").exists()
    assert (candidate_dir / "Application_Form_2024.xlsx").exists()


def test_sync_candidate_folders_details_structure(tmp_path):
    """Test that candidate details have correct structure."""
    from jobflow.app.services.drive_sync import sync_candidate_folders

    folder_structure = {
        "root": [
            {"id": "folder1", "name": "Candidate A", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "folder1": [
            {"id": "file1", "name": "resume.txt", "mimeType": "text/plain"},
        ],
    }

    fake_client = FakeDriveClient(folder_structure)
    staging_dir = tmp_path / "staging"

    result = sync_candidate_folders(
        drive_client=fake_client,
        root_folder_id="root",
        staging_dir=str(staging_dir),
        dry_run=False,
    )

    # Verify candidate details structure
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]

    assert candidate["name"] == "Candidate A"
    assert candidate["slug"] == "candidate_a"
    assert "folder_path" in candidate
    assert candidate["drive_folder_id"] == "folder1"
    assert candidate["files_downloaded"] == 1
    assert candidate["files_skipped"] == 0
    assert len(candidate["files"]) == 1

    # Verify file detail structure
    file_detail = candidate["files"][0]
    assert file_detail["name"] == "resume.txt"
    assert "path" in file_detail
    assert file_detail["type"] == "resume"
