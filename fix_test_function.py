import re

# Read the entire test file
with open('tests/models/test_ngram_models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Read our corrected test function
with open('test_fix.py', 'r', encoding='utf-8') as f:
    new_test_function = f.read()

# Use regular expression to find and replace the entire test_three_keystrokes_error_at_second function
pattern = r'def test_three_keystrokes_error_at_second.*?def test_'
replacement = new_test_function + '\n\n    def test_'

# Use re.DOTALL to make . match newlines
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write the updated content back to the file
with open('tests/models/test_ngram_models.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Test function successfully replaced in the test file!")
