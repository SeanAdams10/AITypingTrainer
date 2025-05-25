import re

# Path to the test file
file_path = r"d:\OneDrive\Documents\SeanDev\AITypingTrainer\tests\models\test_session.py"

# Read the current content
with open(file_path, 'r') as f:
    content = f.read()

# Regular expression pattern to find all instances of Session(**data) or similar
pattern = r'Session\(\*\*([\w.()[\]{}\'\" ]+)\)'
replacement = r'Session.from_dict(\1)'

# Apply the replacement
updated_content = re.sub(pattern, replacement, content)

# Write the updated content back to the file
with open(file_path, 'w') as f:
    f.write(updated_content)

print("Replacements completed!")
