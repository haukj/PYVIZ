# parser.py
"""
Parserer en Python-fil og returnerer en liste av NodeInfo-objekter
samt en liste av EdgeInfo-objekter (funksjonskall).
"""
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

@dataclass
class NodeInfo:
    name: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

@dataclass
class EdgeInfo:
    caller: str  # source-funksjon
    callee: str  # target-funksjon

@dataclass
class GroupInfo:
    name: str
    children: list[NodeInfo] = field(default_factory=list)
    connections: list[EdgeInfo] = field(default_factory=list)  # Added connections attribute

def parse_file(
    py_path: Path,
    parse_classes: bool = True,
    parse_functions: bool = True,
    verbose: bool = False,
) -> tuple[list[NodeInfo], list[EdgeInfo], list[GroupInfo]]:
    try:
        source = py_path.read_text(encoding="utf8")
        tree = ast.parse(source)
    except (FileNotFoundError, SyntaxError) as e:
        with open("error_log.txt", "a") as log_file:
            log_file.write(f"Error parsing file {py_path}: {e}\n")
        return [], [], []

    funcs: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    groups: list[GroupInfo] = []

    class Visitor(ast.NodeVisitor):
        """Collect function definitions, call edges and classes."""

        def __init__(self):
            super().__init__()
            self.func_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef):
            if not parse_functions:
                return
            inputs = [arg.arg for arg in node.args.args]
            returns: set[str] = set()

            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value:
                    if isinstance(child.value, ast.Name):
                        returns.add(child.value.id)

            funcs[node.name] = NodeInfo(name=node.name, inputs=inputs, outputs=list(returns))

            self.func_stack.append(node.name)
            self.generic_visit(node)
            self.func_stack.pop()

        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Name) and self.func_stack:
                edges.append(EdgeInfo(caller=self.func_stack[-1], callee=node.func.id))
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef):
            if not parse_classes:
                return
            group = GroupInfo(name=node.name)
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    group.children.append(funcs.get(child.name, NodeInfo(name=child.name)))
            groups.append(group)

    Visitor().visit(tree)

    # Debugging logs
    if verbose:
        print(f"Parsed nodes: {funcs}")
        print(f"Parsed edges: {edges}")
        print(f"Parsed groups: {groups}")

    return list(funcs.values()), edges, groups
