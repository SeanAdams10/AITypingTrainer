#!/usr/bin/env python3
"""Script to fix test_snippet.py issues."""

import re


def fix_snippet_constructors():
    """Fix Snippet constructor calls to include description parameter."""
    with open('tests/models/test_snippet.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix Category constructor calls to include description
    category_pattern = r'Category\(\s*category_name=([^)]+)\)'
    def add_category_description(match):
        category_name = match.group(1)
        return f'Category(category_name={category_name}, description="")'
    
    content = re.sub(category_pattern, add_category_description, content)

    # Fix Snippet constructor calls with basic pattern
    # This pattern covers single-line constructors
    basic_pattern = r'Snippet\(\s*category_id=([^,\n]+),\s*snippet_name=([^,\n]+),\s*content=([^)\n]+)\)'
    def add_basic_description(match):
        category_id = match.group(1).strip()
        snippet_name = match.group(2).strip()
        content = match.group(3).strip()
        return f'''Snippet(
        category_id={category_id},
        snippet_name={snippet_name},
        content={content},
        description=""
    )'''
    
    content = re.sub(basic_pattern, add_basic_description, content)

    # Fix random_id fixture return type
    content = re.sub(r'return random\.randint\(1000, 9999\)', 'return str(random.randint(1000, 9999))', content)

    # Write back
    with open('tests/models/test_snippet.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print('Fixed Snippet and Category constructors')

if __name__ == '__main__':
    fix_snippet_constructors()
