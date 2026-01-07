# symbol_dependency.py
"""
Mathematica Symbol Dependency Graph Builder

Parses .nb files to extract symbol definitions and their dependencies.
Used for debugging cascading errors in notebook evaluation.

Usage:
    python symbol_dependency.py v14_clean.nb --roots
    python symbol_dependency.py v14_clean.nb --trace timeGrowthCease
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from pathlib import Path
import re
import json


# Common Mathematica builtins that should not be treated as user-defined dependencies
BUILTINS = {
    # Literals
    'True', 'False', 'Null', 'None', 'Automatic', 'All', 'Infinity',
    'Pi', 'E', 'I',
    # Math
    'Sin', 'Cos', 'Tan', 'Exp', 'Log', 'Sqrt', 'Abs', 'Power',
    'Plus', 'Times', 'Divide', 'Subtract',
    # List operations
    'List', 'Table', 'Map', 'Apply', 'Select', 'Cases', 'Range',
    'Part', 'First', 'Last', 'Rest', 'Most', 'Length', 'Flatten',
    # Control
    'If', 'Which', 'Switch', 'Do', 'For', 'While',
    'Module', 'Block', 'With', 'Function',
    # Graphics
    'Graphics', 'Graphics3D', 'Plot', 'Plot3D', 'Show',
    'RGBColor', 'Hue', 'GrayLevel', 'Opacity',
    'Point', 'Line', 'Polygon', 'Circle', 'Disk', 'Text',
    # Solving
    'NDSolve', 'DSolve', 'Solve', 'FindRoot', 'FindMinimum', 'FindMaximum',
    # I/O
    'Print', 'Export', 'Import', 'Clear', 'Remove',
}


def extract_definition(expr: str) -> dict:
    """Extract a single symbol definition from a RowBox expression.

    Handles patterns like:
    - RowBox[{"x", "=", "5"}]
    - RowBox[{"f", "[", "x_", "]", ":=", ...}]
    """
    # Match simple assignment: symbol = value
    simple_match = re.search(r'RowBox\[\{"(\w+)",\s*"=",', expr)
    if simple_match:
        symbol = simple_match.group(1)

        # Extract RHS to find dependencies
        rhs_start = expr.find('"=",') + 4
        rhs = expr[rhs_start:]

        # Find all potential symbol references (words not in quotes as operators)
        # Exclude common builtins and numeric literals
        candidates = re.findall(r'"(\w+)"', rhs)
        # Filter out numeric literals and operators
        deps = set(c for c in candidates if not c.isdigit()) - BUILTINS - {symbol}

        return {
            "symbol": symbol,
            "depends_on": list(deps),
            "type": "variable"
        }

    # Match function definition: f[x_] := ...
    func_match = re.search(r'RowBox\[\{"(\w+)",\s*"\[",.*?":="', expr)
    if func_match:
        symbol = func_match.group(1)
        return {
            "symbol": symbol,
            "depends_on": [],
            "type": "function"
        }

    return {"symbol": None, "depends_on": [], "type": None}


def extract_definitions(expr: str) -> List[dict]:
    """Extract all symbol definitions from an expression (handles chained assignments)."""
    raise NotImplementedError("TODO: implement")


@dataclass
class DependencyGraph:
    """Tracks symbol definitions and their dependencies."""

    definitions: Dict[str, dict] = field(default_factory=dict)
    _undefined: Set[str] = field(default_factory=set)

    def add_definition(self, symbol: str, cell: int, depends_on: List[str]) -> None:
        """Record a symbol definition."""
        self.definitions[symbol] = {
            "cell": cell,
            "depends_on": [d for d in depends_on if d not in BUILTINS],
        }

    def find_undefined(self) -> Set[str]:
        """Find symbols used but never defined."""
        all_deps = set()
        for info in self.definitions.values():
            all_deps.update(info["depends_on"])

        defined = set(self.definitions.keys())
        self._undefined = all_deps - defined - BUILTINS
        return self._undefined

    def trace_to_root(self, symbol: str) -> List[str]:
        """Trace dependency chain back to root."""
        chain = [symbol]
        visited = {symbol}

        current = symbol
        while current in self.definitions:
            deps = self.definitions[current]["depends_on"]
            if not deps:
                break
            # Follow first dependency
            next_sym = deps[0]
            if next_sym in visited:
                chain.append(f"{next_sym} (CIRCULAR)")
                break
            chain.append(next_sym)
            visited.add(next_sym)
            current = next_sym

        return chain

    def count_dependents(self, symbol: str) -> int:
        """Count how many symbols depend on this one (direct + transitive)."""
        dependents = set()

        def find_dependents(sym: str):
            for name, info in self.definitions.items():
                if sym in info["depends_on"] and name not in dependents:
                    dependents.add(name)
                    find_dependents(name)

        find_dependents(symbol)
        return len(dependents)


def parse_notebook_symbols(path: Path, cell_range: tuple = None) -> Dict[str, dict]:
    """Parse notebook and extract all symbol definitions.

    Args:
        path: Path to .nb file
        cell_range: Optional (start, end) to limit parsing to specific Input cells

    Returns:
        Dict mapping symbol names to their definition info including:
        - cell: The Input cell number (1-indexed)
        - depends_on: List of symbols this one depends on
        - type: "variable" or "function"
        - line: Line number in the file where the definition appears
    """
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
        lines = content.split('\n')

    symbols = {}

    # Build a mapping from character position to line number
    def pos_to_line(pos: int) -> int:
        return content[:pos].count('\n') + 1

    # First, identify all Input cells and their ranges
    # An Input cell is Cell[BoxData[...], "Input", ...]
    input_cells = []  # List of (cell_idx, start_pos, end_pos)
    cell_idx = 0

    # Find all Cell[BoxData patterns
    cell_pattern = re.compile(r'Cell\[BoxData\[')
    for cell_match in cell_pattern.finditer(content):
        cell_start = cell_match.start()

        # Find the end of this cell by bracket matching
        depth = 2  # We're past Cell[ and BoxData[
        pos = cell_match.end()
        while pos < len(content) and depth > 0:
            c = content[pos]
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
            pos += 1

        cell_end = pos

        # Check if this is an Input cell
        cell_content = content[cell_start:cell_end]
        if '"Input"' in cell_content:
            cell_idx += 1

            # Check cell_range filter
            if cell_range:
                start, end = cell_range
                if cell_idx < start or cell_idx > end:
                    continue

            input_cells.append((cell_idx, cell_start, cell_end))

    # Collect all definitions with their positions for proper ordering
    all_definitions = []

    # Now extract symbol definitions from each Input cell
    for cell_num, cell_start, cell_end in input_cells:
        cell_content = content[cell_start:cell_end]

        # Find variable assignments: RowBox[{"symbol", ... "=", ...}]
        # where "=" is not ":="
        rowbox_pattern = re.compile(r'RowBox\[\{"([a-zA-Z_][a-zA-Z0-9_]*)",')

        for m in rowbox_pattern.finditer(cell_content):
            sym = m.group(1)
            rowbox_start = m.start()

            # Find the matching ] for this RowBox
            depth = 1
            pos = m.end()
            while pos < len(cell_content) and depth > 0:
                c = cell_content[pos]
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                pos += 1
                if pos - rowbox_start > 1000:  # Safety limit
                    break

            rowbox_content = cell_content[rowbox_start:pos]

            # Check if this is an assignment (has "=" but not ":=")
            is_assignment = '"="' in rowbox_content and '":="' not in rowbox_content
            is_delayed = '":="' in rowbox_content

            if is_assignment and sym not in BUILTINS:
                # Extract dependencies from the RHS
                # Find what comes after "="
                eq_idx = rowbox_content.find('"="')
                deps = []
                if eq_idx != -1:
                    rhs = rowbox_content[eq_idx + 3:]
                    # Find symbol references in RHS
                    for dep_match in re.finditer(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', rhs):
                        dep = dep_match.group(1)
                        if (dep not in BUILTINS and dep != sym and
                            dep not in deps and not dep.isdigit()):
                            deps.append(dep)

                # Store position in file for ordering
                abs_pos = cell_start + rowbox_start
                all_definitions.append({
                    "symbol": sym,
                    "pos": abs_pos,
                    "depends_on": deps[:10],
                    "type": "variable",
                    "line": pos_to_line(abs_pos)
                })

            elif is_delayed and sym not in BUILTINS:
                # Function definition
                abs_pos = cell_start + rowbox_start
                all_definitions.append({
                    "symbol": sym,
                    "pos": abs_pos,
                    "depends_on": [],
                    "type": "function",
                    "line": pos_to_line(abs_pos)
                })

    # Sort by position and assign cell numbers based on definition order
    all_definitions.sort(key=lambda x: x["pos"])

    # Assign sequential "cell" numbers based on definition order
    # This ensures txc (defined first) has a lower cell number than axc (defined later)
    for idx, defn in enumerate(all_definitions, 1):
        sym = defn["symbol"]
        if sym not in symbols:  # Keep first definition only
            symbols[sym] = {
                "cell": idx,  # Sequential number based on definition order
                "depends_on": defn["depends_on"],
                "type": defn["type"],
                "line": defn["line"]
            }

    return symbols


if __name__ == "__main__":
    import sys
    print("symbol_dependency.py - not yet implemented")
    sys.exit(1)
