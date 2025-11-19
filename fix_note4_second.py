# Read the file
with open('app.py', 'r') as f:
    lines = f.readlines()

# Find the second occurrence to insert after (around line 280)
insert_after = -1
for i, line in enumerate(lines):
    if "return ' '.join(selected_words)" in line and i > 275 and i < 285:
        insert_after = i
        break

if insert_after > 0:
    # Insert the new code
    new_code = '''            
            # For NORMAL sentences (has prior punctuation, sentence_start > 0)
            # with moderate length, extract from BEGINNING of sentence
            # This handles cases like "He pointed me to the American Journal of Psychiatry."
            if sentence_start > 0 and len(current_sentence) < 100:
                # Normal sentence with endnote at end - take from beginning
                words = current_sentence.split()
                if len(words) >= self.word_count:
                    selected_words = words[:self.word_count]  # FIRST words of sentence
                else:
                    selected_words = words
                
                # Clean any punctuation
                if selected_words:
                    selected_words[-1] = re.sub(r'[.,;:!?"\'"]+$', '', selected_words[-1])
                
                return ' '.join(selected_words)
'''
    lines.insert(insert_after + 1, new_code)
    
    # Write back
    with open('app.py', 'w') as f:
        f.writelines(lines)
    
    print("Fixed! Inserted second normal sentence handling after line", insert_after)
else:
    print("Could not find second insertion point")
