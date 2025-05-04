"""
Test for the API server manager functionality
"""
import os
import pytest
import requests
import time
import subprocess
from unittest.mock import patch, Mock
from typing import Optional, Dict, Any, List
import sys
from desktop_ui.api_server_manager import APIServerManager


class TestAPIServerManager:
    """Test API server manager functionality"""

    @pytest.fixture
    def mock_subprocess(self):
        """Create a mock for subprocess.Popen"""
        with patch("desktop_ui.api_server_manager.subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process
            yield mock_popen
            
    @pytest.fixture
    def mock_requests(self):
        """Create a mock for requests.get"""
        with patch("desktop_ui.api_server_manager.requests.get") as mock_get:
            yield mock_get
            
    def test_server_already_running(self, mock_requests):
        """Test when server is already running"""
        # Mock a successful response
        mock_response = Mock()
        mock_response.status_code = 400  # Even error codes mean the server is running
        mock_requests.return_value = mock_response
        
        manager = APIServerManager()
        result = manager.ensure_server_running()
        
        # Should return True and not start a new process
        assert result is True
        mock_requests.assert_called_once()
        
    def test_server_not_running(self, mock_requests, mock_subprocess):
        """Test when server is not running and needs to be started"""
        # Mock a connection error to simulate server not running
        mock_requests.side_effect = requests.exceptions.ConnectionError()
        
        # Create API server manager and ensure server running
        manager = APIServerManager()
        result = manager.ensure_server_running()
        
        # Should return True and start a new process
        assert result is True
        mock_requests.assert_called_once()
        mock_subprocess.assert_called_once()
        
        # Verify correct command was used to start the server
        args, kwargs = mock_subprocess.call_args
        cmd = args[0]
        
        # Command should include python and run_library_api.py
        assert "python" in cmd[0].lower() or "python3" in cmd[0].lower()
        assert "run_library_api.py" in cmd[1]
        
        # Should be started with appropriate flags
        assert kwargs.get("start_new_session", False) is True
        
    def test_shutdown_server(self, mock_subprocess):
        """Test shutting down a server that was started by the manager"""
        manager = APIServerManager()
        
        # Mock a server process
        mock_process = Mock()
        manager._server_process = mock_process
        
        # Call shutdown
        manager.shutdown_server()
        
        # Verify process was terminated
        mock_process.terminate.assert_called_once()
        assert manager._server_process is None
