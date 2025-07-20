#!/usr/bin/env python3
"""
Targeted fix script to resolve remaining critical type errors
without breaking existing syntax.
"""

import re
from pathlib import Path


def fix_test_snippet_py() -> None:
    """Fix remaining critical type errors in test_snippet.py"""
    file_path = Path("tests/models/test_snippet.py")
    if not file_path.exists():
        print(f"File {file_path} not found")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Fix malformed uuid.uuid4 calls that were broken by previous regex
    content = re.sub(r'\(str\(uuid\.uuid4\(\s*or\s*""\)\)\)', r'str(uuid.uuid4())', content)
    
    # Fix missing description arguments in Snippet constructors
    # Look for Snippet constructors without description
    snippet_pattern = r'Snippet\(\s*([^)]*?)\s*\)'
    
    def fix_snippet_constructor(match):
        args = match.group(1)
        # If description is not present, add it
        if 'description=' not in args:
            # Add description before the closing parenthesis
            if args.strip().endswith(','):
                return f'Snippet({args} description="")'
            else:
                return f'Snippet({args}, description="")'
        return match.group(0)
    
    content = re.sub(snippet_pattern, fix_snippet_constructor, content, flags=re.DOTALL)
    
    # Fix str | None type issues with proper null coalescing
    # Fix get_snippet_by_id calls
    content = re.sub(
        r'get_snippet_by_id\(([^)]+)\.snippet_id\)',
        r'get_snippet_by_id(\1.snippet_id or "")',
        content
    )
    
    # Fix list_snippets_by_category calls
    content = re.sub(
        r'list_snippets_by_category\(([^)]+)\.category_id\)',
        r'list_snippets_by_category(\1.category_id or "")',
        content
    )
    
    # Fix delete_snippet calls
    content = re.sub(
        r'delete_snippet\(([^)]+)\.snippet_id\)',
        r'delete_snippet(\1.snippet_id or "")',
        content
    )
    
    # Fix get_snippet_by_name calls with category_id
    content = re.sub(
        r'get_snippet_by_name\(([^,]+),\s*([^)]+)\.category_id\)',
        r'get_snippet_by_name(\1, \2.category_id or "")',
        content
    )
    
    # Fix return type mismatch (int to str)
    content = re.sub(r'return len\(([^)]+)\)', r'return str(len(\1))', content)
    
    # Fix assignment type mismatches
    content = re.sub(
        r'category_id = ([^=\n]+)\.category_id',
        r'category_id = \1.category_id or ""',
        content
    )
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed critical type errors in {file_path}")


def fix_test_snippet_manager_py() -> None:
    """Fix critical type errors in test_snippet_manager.py"""
    file_path = Path("tests/models/test_snippet_manager.py")
    if not file_path.exists():
        print(f"File {file_path} not found")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Fix missing description argument and category_id type
    # Look for Snippet constructors without description
    snippet_pattern = r'Snippet\(\s*([^)]*?)\s*\)'
    
    def fix_snippet_constructor(match):
        args = match.group(1)
        # If description is not present, add it
        if 'description=' not in args:
            if args.strip().endswith(','):
                args = args + ' description=""'
            else:
                args = args + ', description=""'
        
        # Fix category_id type issues
        args = re.sub(r'category_id=([^,)]+)', r'category_id=\1 or ""', args)
        
        return f'Snippet({args})'
    
    content = re.sub(snippet_pattern, fix_snippet_constructor, content, flags=re.DOTALL)
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed critical type errors in {file_path}")


def fix_conftest_py() -> None:
    """Fix critical type errors in conftest.py"""
    file_path = Path("tests/models/conftest.py")
    if not file_path.exists():
        print(f"File {file_path} not found")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Fix return type mismatch in fixture (dict to tuple)
    content = re.sub(
        r'return\s*\{\s*"db_manager":\s*db_manager,\s*"service":\s*service,\s*"user_id":\s*user_id,\s*"keyboard_id":\s*keyboard_id,\s*"snippet_id":\s*snippet_id,?\s*\}',
        r'return (db_manager, service, user_id, keyboard_id, snippet_id)',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Fix missing description argument for Category
    content = re.sub(
        r'Category\(\s*category_name="([^"]*)",\s*category_id=([^,)]+)\s*\)',
        r'Category(category_name="\1", category_id=\2, description="")',
        content
    )
    
    # Fix str | None return type
    content = re.sub(r'return\s+([^=\n]+)\.category_id', r'return \1.category_id or ""', content)
    
    # Fix Session constructor arguments with str | None
    content = re.sub(r'snippet_id=([^,)]+),', r'snippet_id=\1 or "",', content)
    content = re.sub(r'user_id=([^,)]+),', r'user_id=\1 or "",', content)
    content = re.sub(r'keyboard_id=([^,)]+)\)', r'keyboard_id=\1 or "")', content)
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed critical type errors in {file_path}")


def fix_test_ngram_size_py() -> None:
    """Fix critical type errors in test_ngram_size.py"""
    file_path = Path("tests/models/test_ngram_size.py")
    if not file_path.exists():
        print(f"File {file_path} not found")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Fix Keystroke import conflict
    content = re.sub(
        r'from models\.keystroke import Keystroke',
        r'from models.ngram_manager import Keystroke',
        content
    )
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed critical type errors in {file_path}")


def fix_test_ngram_analytics_service_py() -> None:
    """Fix undefined name errors in test_ngram_analytics_service.py"""
    file_path = Path("tests/models/test_ngram_analytics_service.py")
    if not file_path.exists():
        print(f"File {file_path} not found")
        return
    
    content = file_path.read_text(encoding='utf-8')
    
    # Fix undefined temp_db references
    content = re.sub(r'\btemp_db\b', r'temp_db_path', content)
    
    file_path.write_text(content, encoding='utf-8')
    print(f"Fixed undefined name errors in {file_path}")


def main() -> None:
    """Run targeted fixes for critical type errors"""
    print("Starting targeted fix for remaining critical type errors...")
    
    fix_test_snippet_py()
    fix_test_snippet_manager_py()
    fix_conftest_py()
    fix_test_ngram_size_py()
    fix_test_ngram_analytics_service_py()
    
    print("\nTargeted critical type error fixes completed!")
    print("Run 'uv run mypy <file>' to verify fixes.")


if __name__ == "__main__":
    main()
