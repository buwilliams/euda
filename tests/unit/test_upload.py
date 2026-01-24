"""
Unit tests for upload route.

Tests for src/web/routes/upload.py
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock


class TestUploadRoute:
    """Test file upload functionality."""

    def test_text_file_stored_in_long_term_memory(self, patch_data_dir):
        """Text file content is stored in user's long-term memory."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        # Create required directories
        user_dir = patch_data_dir / "agents" / "user" / "memory"
        user_dir.mkdir(parents=True, exist_ok=True)
        chat_dir = patch_data_dir / "agents" / "chat"
        chat_dir.mkdir(parents=True, exist_ok=True)

        # Create prompts directory with template
        prompts_dir = patch_data_dir / "system" / "prompts" / "upload"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "extract_memories.md").write_text(
            "Extract memories from {filename}.\n\nContent:\n{content}"
        )

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            mock_write.return_value = {"status": "added"}

            with patch("src.web.routes.upload.create_job") as mock_create_job:
                mock_create_job.return_value = {"id": "job-test123"}

                with patch("src.web.routes.upload.get_agent_inbox_job") as mock_inbox:
                    mock_inbox.return_value = {"id": "job-inbox"}

                    client = TestClient(app)
                    response = client.post(
                        "/api/upload",
                        files={"file": ("test.txt", BytesIO(b"Hello world"), "text/plain")}
                    )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "uploaded"
        assert result["filename"] == "test.txt"
        assert result["job_id"] == "job-test123"

        # Verify long-term memory was written
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert "test.txt" in call_args.kwargs["content"]
        assert "Hello world" in call_args.kwargs["content"]
        assert call_args.kwargs["agent_id"] == "user"
        assert call_args.kwargs["source"] == "Upload"

    def test_text_file_creates_job_for_memory_extraction(self, patch_data_dir):
        """Uploading text file creates job assigned to chat agent."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        # Create required directories
        user_dir = patch_data_dir / "agents" / "user" / "memory"
        user_dir.mkdir(parents=True, exist_ok=True)
        chat_dir = patch_data_dir / "agents" / "chat"
        chat_dir.mkdir(parents=True, exist_ok=True)

        # Create prompts directory with template
        prompts_dir = patch_data_dir / "system" / "prompts" / "upload"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "extract_memories.md").write_text(
            "Extract memories from {filename}.\n\nContent:\n{content}"
        )

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            mock_write.return_value = {"status": "added"}

            with patch("src.web.routes.upload.create_job") as mock_create_job:
                mock_create_job.return_value = {"id": "job-test456"}

                with patch("src.web.routes.upload.get_agent_inbox_job") as mock_inbox:
                    mock_inbox.return_value = {"id": "job-inbox"}

                    client = TestClient(app)
                    response = client.post(
                        "/api/upload",
                        files={"file": ("notes.md", BytesIO(b"# My Notes\n\nSome content"), "text/markdown")}
                    )

        assert response.status_code == 200

        # Verify job was created with correct parameters
        mock_create_job.assert_called_once()
        call_args = mock_create_job.call_args
        assert call_args.kwargs["name"] == "euno:extract-memories:notes.md"
        assert call_args.kwargs["assignee"] == "chat"
        assert call_args.kwargs["tags"] == ["euno:internal"]
        assert call_args.kwargs["parent_id"] == "job-inbox"
        assert call_args.kwargs["created_by"] == "system"
        # Description should contain filename from template
        assert "notes.md" in call_args.kwargs["description"]

    def test_binary_file_not_stored(self, patch_data_dir):
        """Binary files are not stored in memory."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            with patch("src.web.routes.upload.create_job") as mock_create_job:
                client = TestClient(app)
                response = client.post(
                    "/api/upload",
                    files={"file": ("image.png", BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
                )

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "uploaded"
        assert result["filename"] == "image.png"
        assert "job_id" not in result
        assert "Binary file" in result["message"]

        # Verify no memory written and no job created
        mock_write.assert_not_called()
        mock_create_job.assert_not_called()

    def test_various_text_extensions_recognized(self, patch_data_dir):
        """Various text file extensions are recognized as text."""
        from src.web.routes.upload import is_text_file

        text_files = [
            "file.txt", "file.md", "file.py", "file.js", "file.json",
            "file.yaml", "file.yml", "file.csv", "file.html", "file.css",
            "file.rs", "file.go", "file.java", "file.sh", "file.sql"
        ]

        for filename in text_files:
            assert is_text_file(filename), f"{filename} should be recognized as text"

    def test_binary_extensions_not_recognized_as_text(self, patch_data_dir):
        """Binary file extensions are not recognized as text."""
        from src.web.routes.upload import is_text_file

        binary_files = [
            "file.png", "file.jpg", "file.gif", "file.pdf", "file.zip",
            "file.exe", "file.bin", "file.mp3", "file.mp4", "file.doc"
        ]

        for filename in binary_files:
            assert not is_text_file(filename), f"{filename} should not be recognized as text"

    def test_content_truncated_for_job_description(self, patch_data_dir):
        """Large file content is truncated in job description."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        # Create required directories
        user_dir = patch_data_dir / "agents" / "user" / "memory"
        user_dir.mkdir(parents=True, exist_ok=True)
        chat_dir = patch_data_dir / "agents" / "chat"
        chat_dir.mkdir(parents=True, exist_ok=True)

        # Create prompts directory with template that includes content
        prompts_dir = patch_data_dir / "system" / "prompts" / "upload"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "extract_memories.md").write_text(
            "Extract memories.\n\nContent:\n{content}"
        )

        # Create content larger than 8000 chars
        large_content = "x" * 10000

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            mock_write.return_value = {"status": "added"}

            with patch("src.web.routes.upload.create_job") as mock_create_job:
                mock_create_job.return_value = {"id": "job-test789"}

                with patch("src.web.routes.upload.get_agent_inbox_job") as mock_inbox:
                    mock_inbox.return_value = None

                    client = TestClient(app)
                    response = client.post(
                        "/api/upload",
                        files={"file": ("large.txt", BytesIO(large_content.encode()), "text/plain")}
                    )

        assert response.status_code == 200

        # Verify job description has truncated content
        call_args = mock_create_job.call_args
        description = call_args.kwargs["description"]
        # Template includes {content} which should be truncated
        assert "..." in description or len(description) < len(large_content)

    def test_file_size_formatted_correctly(self, patch_data_dir):
        """File size is formatted in KB for larger files."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            with patch("src.web.routes.upload.create_job") as mock_create_job:
                # Test binary file to avoid job creation complexity
                client = TestClient(app)

                # Small file (bytes)
                response = client.post(
                    "/api/upload",
                    files={"file": ("small.bin", BytesIO(b"x" * 500), "application/octet-stream")}
                )
                assert "500B" in response.json()["size"]

                # Larger file (KB)
                response = client.post(
                    "/api/upload",
                    files={"file": ("large.bin", BytesIO(b"x" * 2048), "application/octet-stream")}
                )
                assert "KB" in response.json()["size"]

    def test_no_parent_when_inbox_not_found(self, patch_data_dir):
        """Job created without parent when chat inbox doesn't exist."""
        from fastapi.testclient import TestClient
        from src.web.app import app

        # Create required directories
        user_dir = patch_data_dir / "agents" / "user" / "memory"
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create prompts directory with template
        prompts_dir = patch_data_dir / "system" / "prompts" / "upload"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "extract_memories.md").write_text(
            "Extract memories from {filename}.\n\nContent:\n{content}"
        )

        with patch("src.web.routes.upload.write_long_term_memory") as mock_write:
            mock_write.return_value = {"status": "added"}

            with patch("src.web.routes.upload.create_job") as mock_create_job:
                mock_create_job.return_value = {"id": "job-orphan"}

                with patch("src.web.routes.upload.get_agent_inbox_job") as mock_inbox:
                    mock_inbox.return_value = None  # No inbox found

                    client = TestClient(app)
                    response = client.post(
                        "/api/upload",
                        files={"file": ("orphan.txt", BytesIO(b"content"), "text/plain")}
                    )

        assert response.status_code == 200

        # Verify job was created with parent_id=None
        call_args = mock_create_job.call_args
        assert call_args.kwargs["parent_id"] is None
