import ast
from pathlib import Path

ENGINE = Path(__file__).parents[1] / "engine"


def _imported_roots(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_engine_never_imports_streamlit():
    for path in ENGINE.glob("*.py"):
        roots = set(_imported_roots(ast.parse(path.read_text(encoding="utf-8"))))
        assert "streamlit" not in roots, f"{path.name} importeert streamlit"
