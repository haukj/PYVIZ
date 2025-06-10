import os
import sys
import tempfile
from pathlib import Path

# Ensure repository root is on the import path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from parser import parse_file

def test_parse_file_edges():
    code = """
def a():
    b()

def b():
    pass
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sample.py"
        path.write_text(code)
        nodes, edges, groups = parse_file(path)
    names = sorted(n.name for n in nodes)
    assert names == ["a", "b"]
    assert any(e.caller == "a" and e.callee == "b" for e in edges)
