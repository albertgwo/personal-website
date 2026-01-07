#!/usr/bin/env python3
"""Fix timeGrowthCeaseAnchorPoints to filter $Failed entries before Interpolation.

The problem: Table generates {pH, timeGrowthCease[pH, sMin]} for pH 3.5 to 9.5,
but for pH outside the viable growth niche, timeGrowthCease returns $Failed.
Interpolation then fails on these $Failed entries.

The fix: Wrap the Table result in Select[..., FreeQ[#, $Failed] &] to filter
out entries containing $Failed before passing to Interpolation.
"""

import re
from pathlib import Path


def fix_anchor_points(content: str) -> tuple[str, int]:
    """Wrap timeGrowthCeaseAnchorPoints Table in Select to filter $Failed.

    Before:
        timeGrowthCeaseAnchorPoints = Table[{pH, timeGrowthCease[pH, sMin]}, {pH, 3.5, 9.5, 0.1}];

    After:
        timeGrowthCeaseAnchorPoints = Select[Table[{pH, timeGrowthCease[pH, sMin]}, {pH, 3.5, 9.5, 0.1}], FreeQ[#, $Failed] &];
    """
    count = 0

    # Pattern: timeGrowthCeaseAnchorPoints = Table[...] but NOT already wrapped in Select
    # In RowBox format, we need to find the pattern and wrap it

    # Look for the pattern: "timeGrowthCeaseAnchorPoints", "=", ... "Table", "["
    # We'll find and modify the RowBox structure

    # The fix is to change:
    #   RowBox[{"timeGrowthCeaseAnchorPoints", "=", ..., RowBox[{"Table", "[", ...}]
    # To:
    #   RowBox[{"timeGrowthCeaseAnchorPoints", "=", ..., RowBox[{"Select", "[", RowBox[{"Table", "[", ...}], ",", " ", RowBox[{"FreeQ", "[", RowBox[{"#", ",", " ", "$Failed"}], "]"}], " ", "&"}]}]

    # This is complex in RowBox format. Let's use a targeted regex that finds
    # the Table expression and wraps it.

    # Find: RowBox[{"Table", "[", ... (the timeGrowthCeaseAnchorPoints Table)
    # The context tells us it's after "timeGrowthCeaseAnchorPoints", "=",

    # Match the full line from timeGrowthCeaseAnchorPoints= to the closing of Table
    # Pattern to find the Table[...] RowBox and its contents

    # Simpler approach: Find the specific RowBox structure and modify it
    # The Table expression ends with "}"}], "]"}]}]

    # Let's find the pattern and replace just the Table RowBox with Select[Table[...], FreeQ[#, $Failed] &]

    old_pattern = r'(RowBox\[\{"Table", "\[",\s*RowBox\[\{\s*RowBox\[\{"\{",\s*RowBox\[\{"pH", ",",\s*RowBox\[\{"timeGrowthCease", "\[",\s*RowBox\[\{"pH", ",", " ", "sMin"\}], "\]"\}]\}], "\}"\}], ",", " ",\s*RowBox\[\{"\{",\s*RowBox\[\{"pH", ",", " ", "3\.5", ",", " ", "9\.5", ",", " ", "0\.1"\}],\s*"\}"\}]\}], "\]"\}])'

    def replacer(m):
        nonlocal count
        table_rowbox = m.group(1)
        # Wrap in Select[..., FreeQ[#, $Failed] &]
        wrapped = f'RowBox[{{"Select", "[", {table_rowbox}, ",", " ", RowBox[{{"FreeQ", "[", RowBox[{{"#", ",", " ", "$Failed"}}], "]"}}], " ", "&"}}], "]"}}]'
        count += 1
        return wrapped

    # Try the complex pattern first
    fixed = re.sub(old_pattern, replacer, content)

    if count == 0:
        # Simpler approach - find and replace the string pattern directly
        # Look for the specific text pattern in the notebook

        # The pattern in the .nb file looks like:
        # RowBox[{"timeGrowthCeaseAnchorPoints", "=", "\[IndentingNewLine]",
        #    RowBox[{"Table", "[", ...

        # We can insert Select[ after the = and FreeQ filter after the Table
        lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Look for timeGrowthCeaseAnchorPoints=
            if 'timeGrowthCeaseAnchorPoints", "="' in line and i + 1 < len(lines) and '"Table"' in lines[i+1]:
                # Found the assignment, need to wrap the Table in Select
                # Insert Select[ after the assignment
                new_lines.append(line)
                # Look ahead for the Table line and modify it
                j = i + 1
                while j < len(lines) and '"Table"' not in lines[j]:
                    new_lines.append(lines[j])
                    j += 1

                if j < len(lines):
                    table_line = lines[j]
                    # Change RowBox[{"Table" to RowBox[{"Select", "[", RowBox[{"Table"
                    modified = table_line.replace(
                        'RowBox[{"Table", "[",',
                        'RowBox[{"Select", "[", RowBox[{"Table", "[",'
                    )
                    new_lines.append(modified)
                    count += 1

                    # Now find the end of the Table expression and add the filter
                    # The Table ends with "]"}]}]
                    k = j + 1
                    depth = 1
                    while k < len(lines):
                        new_lines.append(lines[k])
                        # Count brackets to find end
                        if '"Table"' in lines[k]:
                            depth += 1
                        if '"]"}]}]' in lines[k] and depth > 0:
                            depth -= 1
                            if depth == 0:
                                # This is the end of Table, add the filter
                                # But we need to be more careful about where exactly
                                break
                        k += 1
                    i = k
            else:
                new_lines.append(line)
            i += 1

        if count > 0:
            fixed = '\n'.join(new_lines)

    return fixed, count


def apply_simple_fix(content: str) -> tuple[str, int]:
    """Apply a simpler fix - modify the pH range to stay within viable niche.

    Change: {pH, 3.5, 9.5, 0.1}
    To:     {pH, SGRpHLowBnd, SGRpHHighBnd, 0.1}

    This is safer because it uses the actual computed bounds.
    """
    count = 0

    # Find the pattern in the Table iterator for timeGrowthCeaseAnchorPoints
    # The context is: Table[{pH, timeGrowthCease[pH, sMin]}, {pH, 3.5, 9.5, 0.1}]

    # We need to change "3.5" to "SGRpHLowBnd" and "9.5" to "SGRpHHighBnd"
    # But only in the context of timeGrowthCease Table

    # Look for the specific pattern in RowBox format
    pattern = r'("pH", ",", " ", ")("3\.5")(, ",", " ", ")("9\.5")(, ",", " ", "0\.1")'

    # Find all matches and only replace ones near timeGrowthCease
    lines = content.split('\n')
    new_lines = []
    in_timegrowthcease_context = False

    for i, line in enumerate(lines):
        if 'timeGrowthCeaseAnchorPoints' in line:
            in_timegrowthcease_context = True

        if in_timegrowthcease_context and '"3.5"' in line and '"9.5"' in line:
            # This is likely the iterator line
            modified = line.replace('"3.5"', '"SGRpHLowBnd"').replace('"9.5"', '"SGRpHHighBnd"')
            new_lines.append(modified)
            count += 1
            in_timegrowthcease_context = False
        else:
            new_lines.append(line)
            # Reset context after a few lines
            if in_timegrowthcease_context and i > 0 and 'timeGrowthCeaseAnchorPoints' not in lines[i-1]:
                # Check if we're past the Table definition
                if '";"}]' in line:
                    in_timegrowthcease_context = False

    return '\n'.join(new_lines), count


if __name__ == "__main__":
    nb_path = Path("v14_clean.nb")

    print("Reading notebook...")
    content = nb_path.read_text(encoding='utf-8')

    print("\nApplying fix: Change pH range from 3.5-9.5 to SGRpHLowBnd-SGRpHHighBnd...")
    fixed, count = apply_simple_fix(content)

    if count > 0:
        # Create backup
        backup = nb_path.with_suffix('.nb.pre-anchorpoints-fix')
        print(f"Creating backup: {backup}")
        nb_path.rename(backup)

        # Write fixed content
        nb_path.write_text(fixed, encoding='utf-8')
        print(f"\nFixed {count} occurrences.")
        print("The Table iterator now uses SGRpHLowBnd and SGRpHHighBnd instead of 3.5 and 9.5")
        print("\nUser must re-evaluate the notebook in Mathematica.")
    else:
        print("No fixes applied. Pattern may have changed or already fixed.")
        print("\nManual fix instructions:")
        print("In Mathematica, find the line:")
        print("  Table[{pH, timeGrowthCease[pH, sMin]}, {pH, 3.5, 9.5, 0.1}]")
        print("And change it to:")
        print("  Table[{pH, timeGrowthCease[pH, sMin]}, {pH, SGRpHLowBnd, SGRpHHighBnd, 0.1}]")
