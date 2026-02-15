"""
Google Drive API client (read-only).

Provides minimal wrapper for listing and downloading files from Google Drive.
"""

import io
import os
from pathlib import Path


class DriveClient:
    """
    Google Drive client with read-only access.

    Uses Service Account authentication via GOOGLE_APPLICATION_CREDENTIALS env var.
    """

    # Read-only Drive scope
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    def __init__(self):
        """
        Initialize Drive client with Service Account credentials.

        Raises:
            RuntimeError: If GOOGLE_APPLICATION_CREDENTIALS is not set
            ImportError: If google-api-python-client is not installed
        """
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseDownload
        except ImportError as e:
            raise ImportError(
                "google-api-python-client not installed. "
                "Install with: pip install google-api-python-client google-auth"
            ) from e

        # Check for credentials env var
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. "
                "Set it to the path of your service account JSON file."
            )

        if not Path(creds_path).exists():
            raise RuntimeError(
                f"Credentials file not found: {creds_path}"
            )

        # Load credentials
        self.credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=self.SCOPES
        )

        # Build Drive service
        self.service = build("drive", "v3", credentials=self.credentials)
        self._media_download_class = MediaIoBaseDownload

    def list_children(self, folder_id: str) -> list[dict]:
        """
        List immediate children of a folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of dicts with keys: id, name, mimeType

        Notes:
            - Only lists immediate children (not recursive)
            - Returns both files and folders
            - Sorted by name for deterministic ordering
        """
        query = f"'{folder_id}' in parents and trashed = false"

        results = []
        page_token = None

        while True:
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            ).execute()

            files = response.get("files", [])
            results.extend(files)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        # Sort by name for deterministic ordering
        results.sort(key=lambda x: x["name"])

        return results

    def download_file(self, file_id: str, dest_path: str) -> None:
        """
        Download a file from Google Drive.

        Args:
            file_id: Google Drive file ID
            dest_path: Local destination file path

        Notes:
            - Creates parent directories if needed
            - Overwrites existing file
            - Uses chunked download for large files
        """
        # Create parent directories
        dest_path_obj = Path(dest_path)
        dest_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Request file download
        request = self.service.files().get_media(fileId=file_id)

        # Download to file
        with open(dest_path, "wb") as f:
            downloader = self._media_download_class(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
