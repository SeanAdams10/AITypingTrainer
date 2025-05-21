"""
Script to fix the test_three_keystrokes_no_errors test method.
"""

def fix_test_file():
    file_path = 'tests/models/test_ngram_models.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the error-prone trigrams assertion
    old_line = 'assert len(error_prone_trigrams) == 1, "Should be one error-prone trigram"'
    new_line = 'assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"'
    content = content.replace(old_line, new_line)
    
    # Also remove the next line that references the undefined variable
    old_line = 'assert error_prone_trigrams[0].text == error_trigram_text, f"Error-prone trigram should be \'{error_trigram_text}\'"'
    new_line = ''
    content = content.replace(old_line, new_line)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Test file updated successfully!")

if __name__ == "__main__":
    fix_test_file()
