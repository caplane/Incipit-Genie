#!/usr/bin/env python3
"""
Demonstration of the 2-7 word count feature
Shows how different word counts affect incipit extraction
"""

from app import SmartIncipitExtractor

# Test with a quote from your Epilogue
test_cases = [
    ("many psychiatrists now view as a landmark in the treatment of clinical depression", 80),
    ("The very fact that serious and conscientious men could differ so emphatically", 75),
    ("Over four decades, he experienced outpatient psychoanalytic therapy and multiple hospitalizations", 85),
]

print("📊 WORD COUNT FEATURE DEMONSTRATION")
print("=" * 60)
print()
print("Showing how different word counts affect incipit extraction:")
print()

for text, pos in test_cases:
    print(f"Original text: \"{text}\"")
    print("-" * 40)
    
    for word_count in [2, 3, 4, 5, 6, 7]:
        extractor = SmartIncipitExtractor(word_count=word_count)
        incipit = extractor.extract_incipit_at_position(text, pos)
        print(f"  {word_count} words: \"{incipit}\"")
    
    print()

print("💡 RECOMMENDATIONS:")
print("  • 2-3 words: Best for simple citations")
print("  • 4-5 words: Good balance of context and brevity")
print("  • 6-7 words: Maximum context for complex citations")
print()
print("✅ Users can now choose based on their publisher's requirements!")
