"""
Unit tests for planner.py

These tests mock the OpenAI API to avoid network calls and API costs.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from jobflow.app.services.planner import build_plan


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response with valid plan data."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = json.dumps({
        "pipeline_name": "job_discovery",
        "steps": [
            "Fetch job sources",
            "Parse and normalize",
            "Deduplicate",
            "Store jobs"
        ],
        "risks": [
            "API rate limits",
            "Data quality issues"
        ],
        "assumptions": [
            "Directives directory exists",
            "OpenAI API is available"
        ]
    })
    return mock_response


@pytest.fixture
def mock_env_with_api_key(monkeypatch):
    """Set OPENAI_API_KEY environment variable for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-12345")


def test_build_plan_success(mock_env_with_api_key, mock_openai_response):
    """Test successful plan generation with valid directive."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        # Call function
        result = build_plan("job_discovery")

        # Verify OpenAI was called
        assert mock_openai_class.called
        assert mock_client.chat.completions.create.called

        # Verify API key was used
        mock_openai_class.assert_called_once_with(api_key="test-api-key-12345")

        # Verify model parameter
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o"

        # Verify result structure
        assert isinstance(result, dict)
        assert result["pipeline_name"] == "job_discovery"
        assert isinstance(result["steps"], list)
        assert len(result["steps"]) == 4
        assert isinstance(result["risks"], list)
        assert isinstance(result["assumptions"], list)


def test_build_plan_includes_directive_content(mock_env_with_api_key, mock_openai_response):
    """Test that directive content is included in the OpenAI request."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        # Call function
        build_plan("job_discovery")

        # Get the messages sent to OpenAI
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # Verify messages structure
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Verify directive content is in user message
        user_message = messages[1]["content"]
        assert "job_discovery" in user_message.lower() or "Job Discovery" in user_message
        # The directive content should be substantial
        assert len(user_message) > 100


def test_build_plan_missing_directive_file(mock_env_with_api_key):
    """Test that missing directive file raises clear exception."""
    with pytest.raises(FileNotFoundError) as exc_info:
        build_plan("nonexistent_directive")

    error_message = str(exc_info.value)
    assert "Directive not found" in error_message
    assert "nonexistent_directive.md" in error_message
    assert "Please create the directive file" in error_message


def test_build_plan_missing_api_key():
    """Test that missing OPENAI_API_KEY raises ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            build_plan("job_discovery")

        error_message = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_message
        assert "not set" in error_message


def test_build_plan_invalid_json_response(mock_env_with_api_key):
    """Test that invalid JSON response raises RuntimeError."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        # Setup mock with invalid JSON
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            build_plan("job_discovery")

        error_message = str(exc_info.value)
        assert "Failed to parse LLM response as JSON" in error_message


def test_build_plan_missing_required_keys(mock_env_with_api_key):
    """Test that response missing required keys raises RuntimeError."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        # Setup mock with incomplete JSON
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "pipeline_name": "job_discovery",
            "steps": ["step1"]
            # Missing: risks, assumptions
        })
        mock_client.chat.completions.create.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            build_plan("job_discovery")

        error_message = str(exc_info.value)
        assert "missing required keys" in error_message
        assert "risks" in error_message or "assumptions" in error_message


def test_build_plan_api_error(mock_env_with_api_key):
    """Test that OpenAI API errors are handled gracefully."""
    with patch("jobflow.app.services.planner.OpenAI") as mock_openai_class:
        # Setup mock to raise an exception
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API connection failed")

        with pytest.raises(RuntimeError) as exc_info:
            build_plan("job_discovery")

        error_message = str(exc_info.value)
        assert "LLM request failed" in error_message
