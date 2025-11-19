# Fix the regex pattern more simply
with open('app.py', 'r') as f:
    content = f.read()

# Replace the problematic regex pattern with a simpler version
import re
content = re.sub(
    r"selected_words\[-1\] = re\.sub\(r'\[.*?\]\+'\+'\$', '', selected_words\[-1\]\)",
    "selected_words[-1] = re.sub(r'[.,;:!?\"\\'\\'\"]+$', '', selected_words[-1])",
    content
)

with open('app.py', 'w') as f:
    f.write(content)

print("Fixed regex patterns with simpler version")
