import os
import re

results_path = r'c:\Users\basto\OneDrive\Documents\IMPORTANT\project\test_results.txt'

try:
    with open(results_path, 'rb') as f:
        content = f.read().decode('utf-16', errors='ignore')
    
    # Split by ======================================================================
    sections = re.split(r'={70,}', content)
    
    print(f"Total sections found: {len(sections)}")
    
    for section in sections:
        if "FAIL:" in section or "ERROR:" in section:
            # Extract just the first few lines of the section to see the test name and error
            lines = section.strip().split('\n')
            print("-" * 40)
            print("\n".join(lines[:10])) # Print first 10 lines of the failure
            print("...")
            print("\n".join(lines[-5:])) # Print last 5 lines of the failure

except Exception as e:
    print(f"Error reading file: {e}")
