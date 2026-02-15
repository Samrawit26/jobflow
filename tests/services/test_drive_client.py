"""
Unit tests for drive_client.py

Tests DriveClient initialization and error handling with mocked Google API.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# Mock google modules before any imports
def mock_google_modules():
    """Mock google-api-python-client modules."""
    mock_service_account = MagicMock()
    mock_discovery = MagicMock()
    mock_http = MagicMock()

    sys.modules["google"] = MagicMock()
    sys.modules["google.oauth2"] = MagicMock()
    sys.modules["google.oauth2.service_account"] = mock_service_account
    sys.modules["googleapiclient"] = MagicMock()
    sys.modules["googleapiclient.discovery"] = mock_discovery
    sys.modules["googleapiclient.http"] = mock_http

    return mock_service_account, mock_discovery, mock_http


# Apply mocks globally for this test module
_mock_sa, _mock_disco, _mock_http = mock_google_modules()


def test_drive_client_init_missing_env_var(monkeypatch):
    """Test that DriveClient raises error when GOOGLE_APPLICATION_CREDENTIALS not set."""
    # Remove env var
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    from jobflow.app.services.drive_client import DriveClient

    with pytest.raises(RuntimeError, match="GOOGLE_APPLICATION_CREDENTIALS environment variable not set"):
        DriveClient()


def test_drive_client_init_missing_file(monkeypatch, tmp_path):
    """Test that DriveClient raises error when credentials file doesn't exist."""
    nonexistent_path = tmp_path / "nonexistent.json"
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(nonexistent_path))

    from jobflow.app.services.drive_client import DriveClient

    with pytest.raises(RuntimeError, match="Credentials file not found"):
        DriveClient()


def test_drive_client_init_success(monkeypatch, tmp_path):
    """Test successful DriveClient initialization."""
    # Create dummy credentials file
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{"type": "service_account"}')
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))

    # Reset mocks
    _mock_sa.reset_mock()
    _mock_disco.reset_mock()

    # Mock credentials and service
    mock_creds = Mock()
    _mock_sa.Credentials.from_service_account_file.return_value = mock_creds
    mock_service = Mock()
    _mock_disco.build.return_value = mock_service

    from jobflow.app.services.drive_client import DriveClient

    client = DriveClient()

    # Verify client initialized successfully
    assert hasattr(client, "service")
    assert hasattr(client, "credentials")
    assert client.service is not None


def test_drive_client_list_children(monkeypatch, tmp_path):
    """Test list_children returns sorted children."""
    # Setup
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{"type": "service_account"}')
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))

    mock_creds = Mock()
    _mock_sa.Credentials.from_service_account_file.return_value = mock_creds

    # Mock Drive service
    mock_service = Mock()
    _mock_disco.build.return_value = mock_service

    # Mock list response
    mock_files_list = Mock()
    mock_service.files.return_value.list.return_value = mock_files_list
    mock_files_list.execute.return_value = {
        "files": [
            {"id": "2", "name": "Zebra", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "1", "name": "Apple", "mimeType": "application/vnd.google-apps.folder"},
        ],
        "nextPageToken": None,
    }

    from jobflow.app.services.drive_client import DriveClient

    client = DriveClient()
    children = client.list_children("root_folder_id")

    # Verify sorted by name
    assert len(children) == 2
    assert children[0]["name"] == "Apple"
    assert children[1]["name"] == "Zebra"


def test_drive_client_download_file(monkeypatch, tmp_path):
    """Test download_file downloads file to dest."""
    # Setup
    creds_file = tmp_path / "creds.json"
    creds_file.write_text('{"type": "service_account"}')
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))

    mock_creds = Mock()
    _mock_sa.Credentials.from_service_account_file.return_value = mock_creds

    mock_service = Mock()
    _mock_disco.build.return_value = mock_service

    # Mock get_media
    mock_request = Mock()
    mock_service.files.return_value.get_media.return_value = mock_request

    # Mock downloader
    mock_downloader = Mock()
    mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]  # Two chunks, then done
    _mock_http.MediaIoBaseDownload.return_value = mock_downloader

    from jobflow.app.services.drive_client import DriveClient

    client = DriveClient()

    # Download file
    dest_path = tmp_path / "downloads" / "file.txt"
    client.download_file("file_id_123", str(dest_path))

    # Verify file was created (parent dir)
    assert dest_path.parent.exists()
    assert dest_path.exists()
