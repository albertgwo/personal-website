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
    """Parse notebook and extract all symbol definitions."""
    raise NotImplementedError("TODO: implement")


if __name__ == "__main__":
    import sys
    print("symbol_dependency.py - not yet implemented")
    sys.exit(1)
