#!/usr/bin/env python3
"""Fix pattern guards by adding ?NumericQ to prevent symbolic matching."""
import re
import sys
from pathlib import Path

def fix_pattern_guards(content: str) -> tuple[str, int]:
    """Add ?NumericQ to bare pH_ parameters in conditional patterns.

    Transforms: pH_ /; pH < SGRpHLowBnd
    To:         pH_?NumericQ /; pH < SGRpHLowBnd
    """
    count = 0

    # Pattern: "pH_" followed by pattern guard (not already having ?NumericQ)
    # In RowBox format: "pH_", "/;"
    pattern = r'("pH_")(,\s*"/;")'

    def replacer(m):
        nonlocal count
        # Check if already has ?NumericQ
        if '?NumericQ' in m.group(0):
            return m.group(0)
        count += 1
        return '"pH_?NumericQ"' + m.group(2)

    fixed = re.sub(pattern, replacer, content)
    return fixed, count

if __name__ == "__main__":
    nb_path = Path("v14_clean.nb")
    content = nb_path.read_text(encoding='utf-8')
    fixed, count = fix_pattern_guards(content)

    if count > 0:
        backup = nb_path.with_suffix('.nb.pre-numericq-fix')
        nb_path.rename(backup)
        nb_path.write_text(fixed, encoding='utf-8')
        print(f"Fixed {count} pattern guards. Backup: {backup}")
    else:
        print("No fixes needed or pattern not found")
