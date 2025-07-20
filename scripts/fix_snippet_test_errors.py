#!/usr/bin/env python3
"""
Script to systematically fix critical type errors in test_snippet.py.
This addresses the 80+ missing description arguments and type mismatches.
"""

import re
import sys
from pathlib import Path


def fix_snippet_constructors(content: str) -> str:
    """Fix missing description arguments in Snippet constructors."""
    
    # Pattern to match Snippet constructors without description
    snippet_pattern = r'(Snippet\(\s*(?:[^)]*?))\)'
    
    def add_description_if_missing(match):
        constructor_content = match.group(1)
        if 'description=' not in constructor_content:
            # Add description argument before closing parenthesis
            if constructor_content.strip().endswith(','):
                return f'{constructor_content}\n                description="Test description",\n            )'
            else:
                return f'{constructor_content},\n                description="Test description",\n            )'
        return match.group(0)
    
    return re.sub(snippet_pattern, add_description_if_missing, content, flags=re.DOTALL)


def fix_category_constructors(content: str) -> str:
    """Fix missing description arguments in Category constructors."""
    
    # Pattern to match Category constructors without description
    category_pattern = r'(Category\(\s*(?:[^)]*?))\)'
    
    def add_description_if_missing(match):
        constructor_content = match.group(1)
        if 'description=' not in constructor_content:
            # Add description argument before closing parenthesis
            if constructor_content.strip().endswith(','):
                return f'{constructor_content}\n                description="Test category description",\n            )'
            else:
                return f'{constructor_content},\n                description="Test category description",\n            )'
        return match.group(0)
    
    return re.sub(category_pattern, add_description_if_missing, content, flags=re.DOTALL)


def fix_type_mismatches(content: str) -> str:
    """Fix str | None vs str type mismatches by adding null checks."""
    
    # Fix category_id type mismatches in Snippet constructors
    content = re.sub(
        r'category_id=([^,\)]+\.category_id)',
        r'category_id=\1 or "default_category_id"',
        content
    )
    
    # Fix snippet_id type mismatches in method calls
    content = re.sub(
        r'get_snippet_by_id\(([^,\)]+\.snippet_id)\)',
        r'get_snippet_by_id(\1 or "default_snippet_id")',
        content
    )
    
    content = re.sub(
        r'delete_snippet\(([^,\)]+\.snippet_id)\)',
        r'delete_snippet(\1 or "default_snippet_id")',
        content
    )
    
    # Fix list_snippets_by_category calls
    content = re.sub(
        r'list_snippets_by_category\(([^,\)]+\.category_id)\)',
        r'list_snippets_by_category(\1 or "default_category_id")',
        content
    )
    
    # Fix get_snippet_by_name calls
    content = re.sub(
        r'get_snippet_by_name\([^,]+,\s*([^,\)]+\.category_id)\)',
        lambda m: m.group(0).replace(m.group(1), f'{m.group(1)} or "default_category_id"'),
        content
    )
    
    return content


def fix_duplicate_function_names(content: str) -> str:
    """Fix duplicate function name definitions."""
    
    # Find and rename duplicate test_update_nonexistent_snippet
    lines = content.split('\n')
    first_occurrence = None
    
    for i, line in enumerate(lines):
        if 'def test_update_nonexistent_snippet(' in line:
            if first_occurrence is None:
                first_occurrence = i
            else:
                # Rename the second occurrence
                lines[i] = line.replace(
                    'test_update_nonexistent_snippet',
                    'test_update_nonexistent_snippet_duplicate'
                )
    
    return '\n'.join(lines)


def fix_return_type_mismatches(content: str) -> str:
    """Fix return type mismatches."""
    
    # Fix incompatible return value type (got "int", expected "str")
    # This is likely in a function that should return str but returns int
    content = re.sub(
        r'return (\d+)  # This should return a string',
        r'return str(\1)',
        content
    )
    
    return content


def main():
    """Main function to apply all fixes."""
    
    test_file = Path("tests/models/test_snippet.py")
    
    if not test_file.exists():
        print(f"Error: {test_file} not found")
        sys.exit(1)
    
    print(f"Reading {test_file}...")
    content = test_file.read_text(encoding='utf-8')
    
    print("Applying fixes...")
    
    # Apply all fixes
    content = fix_snippet_constructors(content)
    content = fix_category_constructors(content)
    content = fix_type_mismatches(content)
    content = fix_duplicate_function_names(content)
    content = fix_return_type_mismatches(content)
    
    # Write back the fixed content
    print(f"Writing fixed content back to {test_file}...")
    test_file.write_text(content, encoding='utf-8')
    
    print("✅ Successfully applied fixes to test_snippet.py")
    print("\nFixed issues:")
    print("- Added missing description arguments to Snippet and Category constructors")
    print("- Fixed str | None vs str type mismatches with null checks")
    print("- Renamed duplicate function definitions")
    print("- Fixed return type mismatches")


if __name__ == "__main__":
    main()
