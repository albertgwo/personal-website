# Fix v14_clean.nb Evaluation Order Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce errors from 986 to <50 by fixing cell evaluation order and conditional pattern matching issues.

**Architecture:** The root cause is that conditional function definitions (μo, NYield) use pattern guards like `pH_ /; pH < SGRpHLowBnd` but `SGRpHLowBnd` is still symbolic when the function is called. We'll (1) verify the issue, (2) identify all affected functions, (3) apply fixes, (4) validate.

**Tech Stack:** Mathematica .nb file parsing, Python scripts, MCP tools via subagents

---

## Root Cause Analysis Summary

From investigation:
- 986 errors persist after re-evaluation (timestamps confirm fresh errors)
- 228 errors explicitly contain `$Failed`
- `timeGrowthCease` returns `$Failed` because `μo[pH]` and `NYield[pH]` pattern guards fail
- Pattern guards use symbolic variables (`SGRpHLowBnd`, etc.) that aren't numeric when called

**The cascade:**
```
SGRpHLowBnd (symbolic) → μo[pH] pattern match fails → μo[4.5] unevaluated
→ NDSolve gets non-numeric → $Failed → 222 NDSolve errors → 986 total
```

---

### Task 1: Verify Pattern Guard Issue with Live Test

**Files:**
- None (verification only)

**Step 1: Create test script**

Run in bash:
```bash
cat > /tmp/test_pattern_guard.wl << 'EOF'
(* Test if pattern guards with symbolic bounds fail *)
ClearAll[testFunc, lowerBound];
testFunc[x_ /; x < lowerBound] := "below";
testFunc[x_ /; x >= lowerBound] := "above";
Print["With symbolic lowerBound: testFunc[5] = ", testFunc[5]];
lowerBound = 3;
Print["With numeric lowerBound=3: testFunc[5] = ", testFunc[5]];
EOF
```

**Step 2: Run test**

Run: `wolframscript -file /tmp/test_pattern_guard.wl`

Expected output:
```
With symbolic lowerBound: testFunc[5] = testFunc[5]   (* UNEVALUATED - this is the bug *)
With numeric lowerBound=3: testFunc[5] = above
```

**Step 3: Document in beads**

Run: `bd comments mathematica-migration-7hf add "CONFIRMED: Pattern guards with symbolic bounds return unevaluated. This is the root cause of all 986 errors."`

---

### Task 2: Locate All Conditional Function Definitions

**Files:**
- Create: `conditional_functions.txt`

**Step 1: Find all pattern guard conditions**

Run:
```bash
grep -n '/;' v14_clean.nb | grep -E '(LowBnd|HighBnd|pHLow|pHHigh)' > conditional_functions.txt
```

**Step 2: Identify the key functions**

Known affected functions (from dependency chain):
- `μo[pH_]` - lines ~1572-1587
- `NYield[pH_]` - lines ~1745-1760

Run:
```bash
grep -n '"\[Mu\]o".*"/;"' v14_clean.nb | head -10 >> conditional_functions.txt
grep -n '"NYield".*"/;"' v14_clean.nb | head -10 >> conditional_functions.txt
cat conditional_functions.txt
```

**Step 3: Commit**

Run: `git add conditional_functions.txt && git commit -m "data: identify conditional function definitions with pattern guards"`

---

### Task 3: Check Bound Variable Computation Order

**Files:**
- None (verification)

**Step 1: Find where bound variables are computed**

Run:
```bash
echo "=== SGRpHLowBnd ===" && grep -n 'SGRpHLowBnd.*=' v14_clean.nb | head -5
echo "=== SGRpHHighBnd ===" && grep -n 'SGRpHHighBnd.*=' v14_clean.nb | head -5
echo "=== YieldpHLowBnd ===" && grep -n 'YieldpHLowBnd.*=' v14_clean.nb | head -5
echo "=== YieldpHHighBnd ===" && grep -n 'YieldpHHighBnd.*=' v14_clean.nb | head -5
```

**Step 2: Compare with conditional definition locations**

The key question: Are bounds computed BEFORE conditional functions are DEFINED?

Expected: Bounds at lines ~1560-1570, conditional μo at lines ~1572-1587
If bounds come AFTER → that's a bug

**Step 3: Document findings**

Run: `bd comments mathematica-migration-7hf add "Cell order analysis: [document findings here]"`

---

### Task 4: Create Fix Strategy - Add ?NumericQ Guards

**Files:**
- Modify: `v14_clean.nb`

**Step 1: Identify exact lines to modify**

The pattern `pH_ /; pH < SGRpHLowBnd` should become `pH_?NumericQ /; pH < SGRpHLowBnd`

Find exact RowBox patterns:
```bash
grep -n '"pH_".*"/;"' v14_clean.nb | head -20
```

**Step 2: Create fix script**

```bash
cat > fix_pattern_guards.py << 'EOF'
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
EOF
chmod +x fix_pattern_guards.py
```

**Step 3: Review before applying**

Run: `grep -c '"pH_".*"/;"' v14_clean.nb`

Expected: Should show count of patterns to fix

---

### Task 5: Apply Fix and Verify Syntax

**Files:**
- Modify: `v14_clean.nb`

**Step 1: Create backup**

Run: `cp v14_clean.nb v14_clean.nb.backup-pre-numericq`

**Step 2: Apply fix**

Run: `python fix_pattern_guards.py`

Expected: "Fixed N pattern guards. Backup: v14_clean.nb.pre-numericq-fix"

**Step 3: Verify fix was applied**

Run: `grep -c 'NumericQ' v14_clean.nb`

Expected: Should show count > 0

**Step 4: Commit**

Run: `git add v14_clean.nb fix_pattern_guards.py && git commit -m "fix: add ?NumericQ guards to conditional function definitions"`

---

### Task 6: Request User Re-evaluation

**Files:**
- None (user action)

**Step 1: Instruct user**

> **USER ACTION REQUIRED:**
>
> 1. Open `v14_clean.nb` in Mathematica
> 2. Go to **Evaluation → Quit Kernel → Local** (clean slate)
> 3. Go to **Evaluation → Evaluate Notebook** (Cmd+Shift+Enter)
> 4. Wait for completion (5-15 minutes)
> 5. **Save the notebook** (Cmd+S)
> 6. Return and say "evaluation complete"

**Step 2: Wait for confirmation**

---

### Task 7: Count Errors After Fix

**Files:**
- Modify: `error_analysis.json`

**Step 1: Parse errors using subagent**

Use Task subagent (NEVER direct MCP call):
```python
Task(subagent_type="general-purpose", prompt="""
Parse v14_clean.nb to count current errors:
1. Use mcp__plugin_mathematica-mcp_mathematica__parse_notebook
2. Use mcp__plugin_mathematica-mcp_mathematica__get_errors
3. Report: total count, breakdown by category
""")
```

**Step 2: Update error_analysis.json**

Add new entry:
```json
{
  "progress": {
    ...
    "after_numericq_fix": "[NEW_COUNT]"
  }
}
```

**Step 3: Calculate improvement**

```bash
echo "Improvement: 986 → [NEW_COUNT] = $((986 - NEW_COUNT)) fewer errors ($((100 * (986 - NEW_COUNT) / 986))% reduction)"
```

---

### Task 8: If Errors Remain - Investigate Remaining Issues

**Files:**
- None (investigation)

**Step 1: If error count > 50, identify remaining root causes**

Use subagent:
```python
Task(subagent_type="general-purpose", prompt="""
Analyze remaining errors in v14_clean.nb:
1. Get first 10 error messages
2. Look for patterns in what's still failing
3. Check if there are other conditional functions we missed
4. Report findings
""")
```

**Step 2: Document in beads**

Run: `bd comments mathematica-migration-7hf add "Post-fix analysis: [findings]"`

---

### Task 9: Alternative Fix - Ensure Bounds Are Computed First

**Files:**
- Modify: `v14_clean.nb` (if Task 4-7 didn't work)

**Step 1: Find InitializationCell settings**

Run: `grep -n 'InitializationCell' v14_clean.nb | head -10`

**Step 2: Mark bound computation cells as initialization**

The cells computing `SGRpHLowBnd`, `YieldpHLowBnd`, etc. should have:
```mathematica
InitializationCell -> True
```

This ensures they run first on Evaluate Notebook.

**Step 3: Apply fix manually in Mathematica**

> **USER ACTION:**
> 1. Select cells that compute `SGRpHLowBnd`, `SGRpHHighBnd`, etc.
> 2. Right-click → Cell Properties → Initialization Cell
> 3. Save and re-evaluate

---

### Task 10: Final Validation and Session Close

**Files:**
- None (validation + git)

**Step 1: Verify error count acceptable**

Target: < 50 errors (ideally 0)

**Step 2: Close beads issues if resolved**

Run:
```bash
bd list --status=open
# If errors < 50:
bd close mathematica-migration-7hf --reason="Errors reduced from 986 to [N] by adding ?NumericQ guards"
```

**Step 3: Final commit and push**

Run:
```bash
git status
git add .
bd sync
git commit -m "fix: resolve v14_clean.nb errors - reduced from 986 to [N]"
git push
```

---

## Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Error count | < 50 (ideally 0) | `mcp__parse_notebook` + `get_errors` |
| Pattern guards fixed | All conditional pH_ patterns | `grep 'NumericQ' v14_clean.nb` |
| Beads tracked | All discoveries | `bd list` shows activity |
| Git committed | All changes | `git status` shows clean |

---

## Rollback Procedure

If fix causes MORE errors:
```bash
cp v14_clean.nb.backup-pre-numericq v14_clean.nb
git checkout -- v14_clean.nb
```

---

## Key Insight

The error cascade is NOT from missing definitions - it's from **pattern match failure due to symbolic bounds**. When Mathematica evaluates `pH < SGRpHLowBnd` and `SGRpHLowBnd` is a symbol (not a number), the comparison returns unevaluated (symbolic), so the pattern guard `/;` condition is neither True nor False, and the function returns unevaluated. Adding `?NumericQ` ensures the function is only called with numeric arguments, giving the bounds time to be computed.
