# tests/test_symbol_dependency.py
"""Tests for symbol dependency graph builder."""

import pytest
import json
from pathlib import Path


class TestSymbolExtraction:
    """Test extracting symbols from Mathematica expressions."""

    def test_simple_assignment_extracts_symbol(self):
        """x = 5 should extract symbol 'x' with no dependencies."""
        from symbol_dependency import extract_definition

        expr = 'RowBox[{"x", "=", "5"}]'
        result = extract_definition(expr)

        assert result["symbol"] == "x"
        assert result["depends_on"] == []

    def test_assignment_with_dependency(self):
        """y = x + 1 should extract 'y' depending on 'x'."""
        from symbol_dependency import extract_definition

        expr = 'RowBox[{"y", "=", RowBox[{"x", "+", "1"}]}]'
        result = extract_definition(expr)

        assert result["symbol"] == "y"
        assert "x" in result["depends_on"]

    def test_function_definition(self):
        """f[x_] := x^2 should extract function 'f'."""
        from symbol_dependency import extract_definition

        expr = 'RowBox[{"f", "[", RowBox[{"x_"}], "]", ":=", SuperscriptBox["x", "2"]}]'
        result = extract_definition(expr)

        assert result["symbol"] == "f"
        assert result["type"] == "function"

    def test_chained_assignment(self):
        """a = b = c should extract both assignments."""
        from symbol_dependency import extract_definitions

        expr = 'RowBox[{"a", "=", RowBox[{"b", "=", "c"}]}]'
        results = extract_definitions(expr)

        assert len(results) == 2
        symbols = [r["symbol"] for r in results]
        assert "a" in symbols
        assert "b" in symbols


class TestDependencyGraph:
    """Test building and querying the dependency graph."""

    def test_find_undefined_symbols(self):
        """Graph should identify symbols used but never defined."""
        from symbol_dependency import DependencyGraph

        graph = DependencyGraph()
        graph.add_definition("y", cell=1, depends_on=["x"])
        # x is never defined

        undefined = graph.find_undefined()
        assert "x" in undefined

    def test_trace_to_root(self):
        """Should trace dependency chain back to root."""
        from symbol_dependency import DependencyGraph

        graph = DependencyGraph()
        graph.add_definition("a", cell=1, depends_on=[])
        graph.add_definition("b", cell=2, depends_on=["a"])
        graph.add_definition("c", cell=3, depends_on=["b"])

        chain = graph.trace_to_root("c")
        assert chain == ["c", "b", "a"]

    def test_cascade_impact_count(self):
        """Should count how many symbols depend on a given symbol."""
        from symbol_dependency import DependencyGraph

        graph = DependencyGraph()
        graph.add_definition("root", cell=1, depends_on=[])
        graph.add_definition("a", cell=2, depends_on=["root"])
        graph.add_definition("b", cell=3, depends_on=["root"])
        graph.add_definition("c", cell=4, depends_on=["a"])

        impact = graph.count_dependents("root")
        assert impact == 3  # a, b, c all depend on root


class TestNotebookParsing:
    """Test parsing actual notebook files."""

    def test_parse_color_scheme_cell(self):
        """Should correctly parse the color scheme definitions in cell 6."""
        from symbol_dependency import parse_notebook_symbols

        # Use the actual notebook
        nb_path = Path("v14_clean.nb")
        if not nb_path.exists():
            pytest.skip("v14_clean.nb not available")

        symbols = parse_notebook_symbols(nb_path, cell_range=(1, 10))

        # txc should be defined before axc, bxc, fgc, tkc
        txc_cell = symbols.get("txc", {}).get("cell")
        axc_cell = symbols.get("axc", {}).get("cell")

        assert txc_cell is not None, "txc should be defined"
        assert axc_cell is not None, "axc should be defined"
        assert txc_cell < axc_cell, "txc should be defined before axc"
