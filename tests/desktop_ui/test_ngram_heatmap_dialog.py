"""Test suite for NGram Heatmap Dialog.

This module tests the modal dialog functionality, UI initialization,
and interaction with the NGramAnalyticsService.
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6 import QtCore, QtWidgets

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from desktop_ui.ngram_heatmap_screen import NGramHeatmapDialog
from models.keyboard import Keyboard
from models.ngram_analytics_service import NGramHeatmapData
from models.user import User


class TestNGramHeatmapDialog:
    """Test suite for NGramHeatmapDialog."""
    
    @pytest.fixture
    def mock_user(self) -> User:
        """Test objective: Create mock User instance."""
        mock = Mock(spec=User)
        mock.user_id = 1
        mock.first_name = "Test"
        mock.surname = "User"
        return mock
    
    @pytest.fixture
    def mock_keyboard(self) -> Keyboard:
        """Test objective: Create mock Keyboard instance."""
        mock = Mock(spec=Keyboard)
        mock.keyboard_id = 1
        mock.name = "Test Keyboard"
        mock.keyboard_name = "Test Keyboard"
        return mock
    
    @pytest.fixture
    def mock_analytics_service(self) -> Mock:
        """Test objective: Create a mock analytics service for testing."""
        service = Mock()
        service.get_speed_heatmap_data.return_value = [
            NGramHeatmapData(
                ngram_text="th",
                ngram_size=2,
                decaying_average_ms=155.0,
                decaying_average_wpm=38.7,
                target_performance_pct=75.0,
                sample_count=10,
                last_measured=None,
                performance_category="amber",
                color_code="#FFA500"
            ),
            NGramHeatmapData(
                ngram_text="he",
                ngram_size=2,
                decaying_average_ms=98.0,
                decaying_average_wpm=61.2,
                target_performance_pct=85.0,
                sample_count=15,
                last_measured=None,
                performance_category="green",
                color_code="#00FF00"
            )
        ]
        return service
    
    @pytest.fixture
    def app(self) -> QtWidgets.QApplication:
        """Test objective: Create QApplication instance for testing."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        return app
    
    @pytest.fixture
    def dialog(
        self, 
        app: QtWidgets.QApplication, 
        mock_user: User, 
        mock_keyboard: Keyboard, 
        mock_analytics_service: Mock
    ) -> NGramHeatmapDialog:
        """Test objective: Create NGramHeatmapDialog instance for testing."""
        with patch('desktop_ui.ngram_heatmap_screen.DatabaseManager') as mock_db_manager, \
             patch('desktop_ui.ngram_heatmap_screen.NGramAnalyticsService') as mock_service_class, \
             patch('desktop_ui.ngram_heatmap_screen.NGramManager'):
            
            mock_service_class.return_value = mock_analytics_service
            mock_db = Mock()
            mock_db_manager.return_value = mock_db
            dialog = NGramHeatmapDialog(mock_db, mock_user, mock_keyboard)
            return dialog
    
    def test_dialog_initialization(
        self, 
        dialog: NGramHeatmapDialog, 
        mock_user: User, 
        mock_keyboard: Keyboard
    ) -> None:
        """Test objective: Verify dialog is properly initialized as QDialog."""
        assert isinstance(dialog, QtWidgets.QDialog)
        assert dialog.isModal()
        assert dialog.user == mock_user
        assert dialog.keyboard == mock_keyboard
        assert dialog.windowTitle() == "N-gram Speed Heatmap"
        
    def test_dialog_ui_components(self, dialog: NGramHeatmapDialog) -> None:
        """Test objective: Verify all UI components are created."""
        # Check main UI components exist
        assert hasattr(dialog, 'heatmap_table')
        assert hasattr(dialog, 'ngram_size_combo')
        assert hasattr(dialog, 'speed_min_spin')
        assert hasattr(dialog, 'speed_max_spin')
        assert hasattr(dialog, 'performance_combo')
        assert hasattr(dialog, 'sort_combo')
        assert hasattr(dialog, 'status_label')
        
        # Verify table is properly configured
        assert dialog.heatmap_table.columnCount() == 6
        expected_headers = [
            "N-gram", "Size", "Avg Speed (ms)", "Sample Count", "Performance", "Color"
        ]
        for i, header in enumerate(expected_headers):
            assert dialog.heatmap_table.horizontalHeaderItem(i).text() == header
    
    def test_dialog_buttons(self, dialog: NGramHeatmapDialog) -> None:
        """Test objective: Verify dialog buttons are properly configured."""
        assert dialog.button_box is not None
        buttons = dialog.button_box.buttons()
        assert len(buttons) == 3
        
        # Check button types
        refresh_btn = dialog.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Reset)
        assert refresh_btn is not None
        assert refresh_btn.text() == "Refresh Data"
        
        # Check other buttons exist
        assert dialog.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Save) is not None
        assert dialog.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Close) is not None
    
    def test_load_data(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify data loading functionality."""
        # Note: load_data is already called during dialog initialization
        
        # Verify analytics service was called during initialization
        mock_analytics_service.get_speed_heatmap_data.assert_called_with(
            user_id=dialog.user.user_id,
            keyboard_id=dialog.keyboard.keyboard_id
        )
        
        # Verify data was loaded
        assert hasattr(dialog, 'heatmap_data')
        assert hasattr(dialog, 'filtered_data')
        assert len(dialog.heatmap_data) == 2
        assert len(dialog.filtered_data) == 2
        assert dialog.status_label.text() == "Loaded 2 n-grams"
    
    def test_apply_filters(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify filter functionality."""
        # Load data first
        dialog.load_data()
        
        # Set filter values
        dialog.speed_min_spin.setValue(120)
        dialog.speed_max_spin.setValue(180)
        dialog.ngram_size_combo.setCurrentText("2")
        dialog.performance_combo.setCurrentText("Good")
        
        # Apply filters
        dialog.apply_filters()
        
        # Check that filtered data is populated
        assert hasattr(dialog, 'filtered_data')
        assert isinstance(dialog.filtered_data, list)
        assert dialog.filtered_data[0].ngram_text == "th"
        assert "Showing 1 of 2 n-grams" in dialog.status_label.text()
    
    def test_apply_sorting(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify sorting functionality."""
        # Load data first
        dialog.load_data()
        
        # Test sorting by speed
        dialog.sort_combo.setCurrentText("Speed")
        dialog.apply_sorting()
        
        # Should be sorted by decaying_average_ms (ascending)
        assert dialog.filtered_data[0].ngram_text == "he"  # 98ms
        assert dialog.filtered_data[1].ngram_text == "th"  # 155ms
    
    def test_refresh_data(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify refresh functionality."""
        dialog.load_data()
        mock_analytics_service.get_speed_heatmap_data.reset_mock()
        
        dialog.refresh_data()
        
        # Verify service was called again
        mock_analytics_service.get_speed_heatmap_data.assert_called_once()
    
    def test_export_data_no_data(self, dialog: NGramHeatmapDialog) -> None:
        """Test objective: Verify export shows message when no data."""
        dialog.filtered_data = []
        
        with patch('desktop_ui.ngram_heatmap_screen.QtWidgets.QMessageBox.information') as mock_msg:
            dialog.export_data()
            mock_msg.assert_called_once_with(dialog, "No Data", "No data to export.")
    
    def test_export_data_success(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify successful export functionality."""
        dialog.load_data()
        
        file_dialog_patch = 'desktop_ui.ngram_heatmap_screen.QtWidgets.QFileDialog.getSaveFileName'
        open_patch = 'desktop_ui.ngram_heatmap_screen.open'
        writer_patch = 'desktop_ui.ngram_heatmap_screen.csv.writer'
        msg_patch = 'desktop_ui.ngram_heatmap_screen.QtWidgets.QMessageBox.information'
        
        with patch(file_dialog_patch) as mock_file_dlg, \
             patch(open_patch, create=True) as mock_open, \
             patch(writer_patch) as mock_writer, \
             patch(msg_patch) as mock_msg:
            
            mock_file_dlg.return_value = ("test.csv", "")
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            mock_csv_writer = MagicMock()
            mock_writer.return_value = mock_csv_writer
            
            dialog.export_data()
            
            mock_open.assert_called_once_with("test.csv", 'w', newline='', encoding='utf-8')
            mock_writer.assert_called_once_with(mock_file)
            mock_csv_writer.writerow.assert_called()
            expected_msg = "Data exported successfully to test.csv"
            mock_msg.assert_called_once_with(dialog, "Export Complete", expected_msg)
    
    def test_export_data_cancelled(self, dialog: NGramHeatmapDialog, mock_analytics_service: Mock) -> None:
        """Test objective: Verify export handles cancellation properly."""
        dialog.load_data()
        
        file_dialog_patch = 'desktop_ui.ngram_heatmap_screen.QtWidgets.QFileDialog.getSaveFileName'
        with patch(file_dialog_patch) as mock_file_dlg:
            mock_file_dlg.return_value = ("", "")  # User cancelled
            
            # Should not raise exception
            dialog.export_data()
    
    def test_modal_behavior(self, dialog: NGramHeatmapDialog) -> None:
        """Test objective: Verify dialog has modal behavior."""
        assert dialog.isModal()
        assert dialog.windowModality() == QtCore.Qt.WindowModality.ApplicationModal
    
    def test_dialog_window_flags(self, dialog: NGramHeatmapDialog) -> None:
        """Test objective: Verify dialog has appropriate window flags."""
        # Check that it's a dialog with proper chrome
        flags = dialog.windowFlags()
        assert flags & QtCore.Qt.WindowType.Dialog
        assert flags & QtCore.Qt.WindowType.WindowTitleHint
        assert flags & QtCore.Qt.WindowType.WindowSystemMenuHint


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
