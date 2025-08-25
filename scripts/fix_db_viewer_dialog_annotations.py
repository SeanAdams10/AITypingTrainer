#!/usr/bin/env python3
"""
Batch fix script to add missing type annotations to test_db_viewer_dialog.py.
This script systematically adds type annotations to all test functions.
"""

import re
from pathlib import Path


def fix_test_db_viewer_dialog_annotations():
    """Fix missing type annotations in test_db_viewer_dialog.py."""
    
    file_path = Path("tests/desktop_ui/test_db_viewer_dialog.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Applying fixes...")
    
    # Fix 1: Add type annotations to test functions with standard parameters
    standard_test_pattern = r'def (test_\w+)\(qtapp, mock_db_viewer_service, qtbot\):'
    standard_replacement = r'def \1(qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot) -> None:'
    content = re.sub(standard_test_pattern, standard_replacement, content)
    
    # Fix 2: Add type annotations to test functions with qtapp and qtbot only
    qtapp_qtbot_pattern = r'def (test_\w+)\(qtapp, qtbot\):'
    qtapp_qtbot_replacement = r'def \1(qtapp: QApplication, qtbot: QtBot) -> None:'
    content = re.sub(qtapp_qtbot_pattern, qtapp_qtbot_replacement, content)
    
    # Fix 3: Add type annotations to test_export_to_csv with mock decorators
    export_pattern = (r'def (test_export_to_csv)\(mock_info_box, mock_get_save_filename, '
                     r'qtapp, mock_db_viewer_service, qtbot\):')
    export_replacement = (r'def \1(mock_info_box: Any, mock_get_save_filename: Any, '
                         r'qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot) -> None:')
    content = re.sub(export_pattern, export_replacement, content)
    
    # Fix 4: Add type annotation to nested custom_export function
    custom_export_pattern = r'def custom_export\(\):'
    custom_export_replacement = r'def custom_export() -> None:'
    content = re.sub(custom_export_pattern, custom_export_replacement, content)
    
    # Fix 5: Handle any remaining test functions that might have been missed
    remaining_test_pattern = r'def (test_\w+)\(([^)]+)\):'
    def fix_remaining_tests(match):
        func_name = match.group(1)
        params = match.group(2)
        
        # Skip if already has type annotations
        if ':' in params:
            return match.group(0)
        
        # Add type annotations based on parameter names
        typed_params = []
        for param in params.split(', '):
            param = param.strip()
            if param == 'qtapp':
                typed_params.append('qtapp: QApplication')
            elif param == 'mock_db_viewer_service':
                typed_params.append('mock_db_viewer_service: MagicMock')
            elif param == 'qtbot':
                typed_params.append('qtbot: QtBot')
            elif param.startswith('mock_'):
                typed_params.append(f'{param}: Any')
            else:
                typed_params.append(f'{param}: Any')
        
        return f'def {func_name}({", ".join(typed_params)}) -> None:'
    
    content = re.sub(remaining_test_pattern, fix_remaining_tests, content)
    
    print(f"Writing fixed content back to {file_path}...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully applied type annotation fixes to test_db_viewer_dialog.py")
    print()
    print("Fixed issues:")
    print("- Added type annotations to all test function parameters")
    print("- Added return type annotations (-> None) to all test functions")
    print("- Fixed nested custom_export function annotation")
    print("- Handled mock decorator parameters with Any type")


if __name__ == "__main__":
    fix_test_db_viewer_dialog_annotations()
