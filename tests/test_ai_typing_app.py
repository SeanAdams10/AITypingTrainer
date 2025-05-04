"""
Tests for AiTypingApp.py functionality.

This module tests the AI Typing App splash screen, server initialization,
and main menu launch functionality using pytest fixtures and mocks.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, List, Any, Optional, Tuple, cast

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the module to test
from AiTypingApp import SplashScreen, ServerWorker, AiTypingApp


class TestServerWorker:
    """Test the ServerWorker class for managing server processes."""
    
    @pytest.fixture
    def mock_qthread(self):
        """Mock QThread methods."""
        with patch('AiTypingApp.QThread') as mock:
            yield mock
    
    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess module."""
        with patch('AiTypingApp.subprocess') as mock:
            mock_process = MagicMock()
            mock.Popen.return_value = mock_process
            yield mock
    
    @pytest.fixture
    def mock_requests(self):
        """Mock requests module."""
        with patch('AiTypingApp.requests') as mock:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock.post.return_value = mock_response
            mock.get.return_value = mock_response
            mock.RequestException = Exception
            yield mock
    
    @pytest.fixture
    def mock_time(self):
        """Mock time module."""
        with patch('AiTypingApp.time') as mock:
            yield mock
    
    @pytest.fixture
    def api_worker(self, mock_qthread):
        """Create a ServerWorker instance for API tests."""
        worker = ServerWorker(
            server_type="api",
            script_path="mock_script.py",
            cwd="/mock/path"
        )
        worker.status_update = MagicMock()
        worker.server_started = MagicMock()
        return worker
    
    @pytest.fixture
    def web_worker(self, mock_qthread):
        """Create a ServerWorker instance for web server tests."""
        worker = ServerWorker(
            server_type="web",
            cwd="/mock/path",
            npm_command=["npm", "start"]
        )
        worker.status_update = MagicMock()
        worker.server_started = MagicMock()
        return worker
    
    def test_api_worker_initialization(self, api_worker):
        """Test API worker initialization with correct parameters."""
        assert api_worker.server_type == "api"
        assert api_worker.script_path == "mock_script.py"
        assert api_worker.cwd == "/mock/path"
        assert api_worker.npm_command is None
        assert api_worker.process is None
        assert api_worker.is_running is False
    
    def test_web_worker_initialization(self, web_worker):
        """Test web worker initialization with correct parameters."""
        assert web_worker.server_type == "web"
        assert web_worker.script_path is None
        assert web_worker.cwd == "/mock/path"
        assert web_worker.npm_command == ["npm", "start"]
        assert web_worker.process is None
        assert web_worker.is_running is False
    
    def test_api_worker_run_success(self, api_worker, mock_subprocess, mock_requests, mock_time):
        """Test successful API server start and verification."""
        # Run the worker
        api_worker.run()
        
        # Check that subprocess.Popen was called correctly
        mock_subprocess.Popen.assert_called_once()
        
        # Verify status updates
        api_worker.status_update.emit.assert_any_call("Starting GraphQL API server...")
        api_worker.status_update.emit.assert_any_call("GraphQL API server running")
        
        # Verify server started signal
        api_worker.server_started.emit.assert_called_once_with(True)
        
        # Check server status
        assert api_worker.is_running is True
    
    def test_api_worker_run_failure(self, api_worker, mock_subprocess, mock_requests, mock_time):
        """Test API server start failure handling."""
        # Make the requests call fail
        mock_requests.post.side_effect = Exception("Connection error")
        
        # Run the worker
        api_worker.run()
        
        # Check if appropriate error messages were emitted
        api_worker.status_update.emit.assert_any_call("Starting GraphQL API server...")
        api_worker.status_update.emit.assert_any_call("Waiting for API server...")
        
        # Check that server_started signal was emitted with False
        api_worker.server_started.emit.assert_called_with(False)
    
    def test_web_worker_run_success(self, web_worker, mock_subprocess, mock_requests, mock_time):
        """Test successful web server start and verification."""
        # Run the worker
        web_worker.run()
        
        # Check that subprocess.Popen was called correctly
        mock_subprocess.Popen.assert_called_once()
        
        # Verify status updates
        web_worker.status_update.emit.assert_any_call("Starting web server...")
        web_worker.status_update.emit.assert_any_call("Web server running")
        
        # Verify server started signal
        web_worker.server_started.emit.assert_called_once_with(True)
        
        # Check server status
        assert web_worker.is_running is True
    
    def test_worker_stop(self, api_worker, mock_subprocess):
        """Test stopping the server worker."""
        # Set up a mock process
        mock_process = MagicMock()
        api_worker.process = mock_process
        api_worker.is_running = True
        
        # Stop the worker
        api_worker.stop()
        
        # Check that terminate was called
        mock_process.terminate.assert_called_once()
        
        # Check that is_running was set to False
        assert api_worker.is_running is False


class TestSplashScreen:
    """Test the SplashScreen class."""
    
    @pytest.fixture
    def mock_qdialog(self):
        """Mock QDialog methods."""
        with patch('AiTypingApp.QDialog') as mock:
            yield mock
    
    @pytest.fixture
    def mock_qapplication(self):
        """Mock QApplication methods."""
        with patch('AiTypingApp.QApplication') as mock:
            yield mock
    
    @pytest.fixture
    def mock_qtimer(self):
        """Mock QTimer methods."""
        with patch('AiTypingApp.QTimer') as mock:
            yield mock
    
    @pytest.fixture
    def mock_requests(self):
        """Mock requests module."""
        with patch('AiTypingApp.requests') as mock:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock.post.return_value = mock_response
            mock.get.return_value = mock_response
            mock.RequestException = Exception
            yield mock
    
    @pytest.fixture
    def mock_webbrowser(self):
        """Mock webbrowser module."""
        with patch('AiTypingApp.webbrowser') as mock:
            yield mock
    
    @pytest.fixture
    def mock_server_worker(self):
        """Mock ServerWorker class."""
        with patch('AiTypingApp.ServerWorker') as mock:
            mock_worker = MagicMock()
            mock.return_value = mock_worker
            yield mock, mock_worker
    
    @pytest.fixture
    def splash_screen(self, mock_qdialog, mock_qapplication, mock_qtimer, mock_server_worker):
        """Create a SplashScreen instance with mocked dependencies."""
        with patch('AiTypingApp.QVBoxLayout'), \
             patch('AiTypingApp.QLabel'), \
             patch('AiTypingApp.QDesktopWidget'), \
             patch('AiTypingApp.QFrame'):
            
            # Disable actual initialization sequence
            with patch.object(SplashScreen, 'start_initialization'):
                splash = SplashScreen()
                splash.update_status = MagicMock()
                return splash
    
    def test_splash_screen_initialization(self, splash_screen):
        """Test splash screen initialization."""
        assert splash_screen.api_server_running is False
        assert splash_screen.web_server_running is False
        assert hasattr(splash_screen, 'api_worker')
        assert hasattr(splash_screen, 'web_worker')
    
    def test_check_api_server_running(self, splash_screen, mock_requests, mock_qtimer):
        """Test API server check when server is already running."""
        # Mock that the API server is running
        mock_requests.post.return_value.status_code = 200
        
        # Set up check_web_server mock
        splash_screen.check_web_server = MagicMock()
        
        # Call the method
        splash_screen.check_api_server()
        
        # Verify update_status was called
        splash_screen.update_status.assert_called_with("Checking if GraphQL API server is running...")
        
        # Check that api_server_running is set to True
        assert splash_screen.api_server_running is True
        
        # Check that QTimer.singleShot was called to move to web server check
        mock_qtimer.singleShot.assert_called_once()
    
    def test_check_api_server_not_running(self, splash_screen, mock_requests):
        """Test API server check when server is not running."""
        # Mock that the API server is not running
        mock_requests.post.side_effect = Exception("Connection error")
        
        # Call the method
        splash_screen.check_api_server()
        
        # Verify update_status was called
        splash_screen.update_status.assert_called_with("Checking if GraphQL API server is running...")
        
        # Check that api_worker.start was called
        splash_screen.api_worker.start.assert_called_once()
    
    def test_api_server_status_success(self, splash_screen, mock_qtimer):
        """Test handling successful API server start."""
        # Set up check_web_server mock
        splash_screen.check_web_server = MagicMock()
        
        # Call the method
        splash_screen.api_server_status(True)
        
        # Check that api_server_running is set to True
        assert splash_screen.api_server_running is True
        
        # Check that QTimer.singleShot was called to move to web server check
        mock_qtimer.singleShot.assert_called_once()
    
    def test_api_server_status_failure(self, splash_screen, mock_qtimer):
        """Test handling failed API server start."""
        # Call the method
        splash_screen.api_server_status(False)
        
        # Check that api_server_running is set to False
        assert splash_screen.api_server_running is False
        
        # Check that update_status was called with error message
        splash_screen.update_status.assert_called_with(
            "Failed to start GraphQL API server. Please check logs."
        )
        
        # Check that QTimer.singleShot was called to close
        mock_qtimer.singleShot.assert_called_once()
    
    def test_finalize_startup(self, splash_screen, mock_qtimer):
        """Test finalize_startup method."""
        # Set up launch_main_menu mock
        splash_screen.launch_main_menu = MagicMock()
        
        # Call the method
        splash_screen.finalize_startup()
        
        # Check that update_status was called
        splash_screen.update_status.assert_called_with("Almost there...")
        
        # Check that QTimer.singleShot was called
        mock_qtimer.singleShot.assert_called_once()
    
    def test_launch_main_menu_with_web(self, splash_screen, mock_webbrowser):
        """Test launch_main_menu when web server is running."""
        # Set up web server as running
        splash_screen.web_server_running = True
        
        # Set up accept mock
        splash_screen.accept = MagicMock()
        
        # Call the method
        splash_screen.launch_main_menu()
        
        # Check that webbrowser.open was called
        mock_webbrowser.open.assert_called_once_with("http://localhost:3000")
        
        # Check that accept was called
        splash_screen.accept.assert_called_once()
    
    def test_launch_main_menu_without_web(self, splash_screen, mock_webbrowser):
        """Test launch_main_menu when web server is not running."""
        # Set up web server as not running
        splash_screen.web_server_running = False
        
        # Set up accept mock
        splash_screen.accept = MagicMock()
        
        # Call the method
        splash_screen.launch_main_menu()
        
        # Check that webbrowser.open was not called
        mock_webbrowser.open.assert_not_called()
        
        # Check that accept was called
        splash_screen.accept.assert_called_once()


class TestAiTypingApp:
    """Test the AiTypingApp class."""
    
    @pytest.fixture
    def mock_qapplication(self):
        """Mock QApplication."""
        with patch('AiTypingApp.QApplication') as mock:
            yield mock
    
    @pytest.fixture
    def mock_qfontdatabase(self):
        """Mock QFontDatabase."""
        with patch('AiTypingApp.QFontDatabase') as mock:
            yield mock
    
    @pytest.fixture
    def mock_splash_screen(self):
        """Mock SplashScreen class."""
        with patch('AiTypingApp.SplashScreen') as mock:
            mock_splash = MagicMock()
            mock_splash.exec_.return_value = 1  # QDialog.Accepted
            mock.return_value = mock_splash
            yield mock, mock_splash
    
    @pytest.fixture
    def mock_main_menu(self):
        """Mock MainMenuWindow class."""
        with patch('AiTypingApp.MainMenuWindow') as mock:
            mock_window = MagicMock()
            mock.return_value = mock_window
            yield mock, mock_window
    
    @pytest.fixture
    def ai_typing_app(self, mock_qapplication, mock_qfontdatabase, mock_splash_screen, mock_main_menu):
        """Create an AiTypingApp instance with mocked dependencies."""
        app = AiTypingApp()
        return app
    
    def test_app_initialization(self, ai_typing_app, mock_qapplication, mock_qfontdatabase):
        """Test app initialization."""
        assert ai_typing_app.app is mock_qapplication.return_value
        assert ai_typing_app.main_window is None
        assert ai_typing_app.api_worker is None
        assert ai_typing_app.web_worker is None
        mock_qfontdatabase.addApplicationFont.assert_called_once()
    
    def test_start_success(self, ai_typing_app, mock_splash_screen, mock_main_menu):
        """Test app start with successful splash screen."""
        # Set splash screen to accept (successful initialization)
        mock_splash, mock_splash_instance = mock_splash_screen
        mock_splash_instance.exec_.return_value = 1  # QDialog.Accepted
        
        # Add mock workers to splash
        mock_splash_instance.api_worker = MagicMock()
        mock_splash_instance.web_worker = MagicMock()
        
        # Call start
        result = ai_typing_app.start()
        
        # Check that MainMenuWindow was created and shown
        mock_main_menu[0].assert_called_once()
        mock_main_menu[1].show.assert_called_once()
        
        # Check that app.exec_ was called
        ai_typing_app.app.exec_.assert_called_once()
        
        # Check that worker references were stored
        assert ai_typing_app.api_worker is mock_splash_instance.api_worker
        assert ai_typing_app.web_worker is mock_splash_instance.web_worker
    
    def test_start_failure(self, ai_typing_app, mock_splash_screen, mock_main_menu):
        """Test app start with failed splash screen."""
        # Set splash screen to reject (failed initialization)
        mock_splash, mock_splash_instance = mock_splash_screen
        mock_splash_instance.exec_.return_value = 0  # QDialog.Rejected
        
        # Call start
        result = ai_typing_app.start()
        
        # Check that MainMenuWindow was not created
        mock_main_menu[0].assert_not_called()
        
        # Check that app.exec_ was not called
        ai_typing_app.app.exec_.assert_not_called()
        
        # Check return value
        assert result == 1
    
    def test_cleanup(self, ai_typing_app):
        """Test app cleanup."""
        # Set up mock workers
        ai_typing_app.api_worker = MagicMock()
        ai_typing_app.web_worker = MagicMock()
        
        # Call cleanup
        ai_typing_app.cleanup()
        
        # Check that workers were stopped
        ai_typing_app.api_worker.stop.assert_called_once()
        ai_typing_app.web_worker.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
