# Fix all regex patterns with quotes properly
with open('app.py', 'r') as f:
    lines = f.readlines()

# Fix all occurrences of the problematic regex pattern
for i, line in enumerate(lines):
    if "re.sub(r'[.,;:!?" in line and "selected_words[-1]" in line:
        # Replace with correct pattern
        lines[i] = "                    selected_words[-1] = re.sub(r'[.,;:!?\"\\'\"]+'+'$', '', selected_words[-1])\n"

# Write back
with open('app.py', 'w') as f:
    f.writelines(lines)

print("Fixed all regex patterns")
