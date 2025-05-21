# Script to fix the test file
with open('tests/models/test_ngram_models.py', 'r') as f:
    content = f.read()

# Replace the assertion for error-prone trigrams
old_line = 'assert len(error_prone_trigrams) == 0, "Should be no error-prone trigrams"'
new_lines = 'assert len(error_prone_trigrams) == 1, "Should be one error-prone trigram"\n        assert error_prone_trigrams[0].text == error_trigram_text, f"Error-prone trigram should be \'{error_trigram_text}\'"'
fixed_content = content.replace(old_line, new_lines)

with open('tests/models/test_ngram_models.py', 'w') as f:
    f.write(fixed_content)

print("Test file updated successfully")
