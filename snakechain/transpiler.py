from __future__ import annotations

from typing import List

from jinja2 import Environment, StrictUndefined

from .ast import AssertStmt, AssignStmt, ContractSpec, IfStmt, Statement


_TEMPLATE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {{ contract.name }} {
{% for var in contract.state_vars %}    {{ var.type }} public {{ var.name }}{% if var.value %} = {{ var.value }}{% endif %};
{% endfor %}
{% for fn in contract.functions %}    function {{ fn.name }}({{ fn.parameters | join(', ') }}) {{ fn.visibility }} {
{{ render_statements(fn.body, 8) }}    }

{% endfor %}}
"""


def _render_expr(expr: str) -> str:
    return expr.replace("self.", "")


def _render_statement(stmt: Statement, indent: int) -> List[str]:
    pad = " " * indent
    if isinstance(stmt, AssertStmt):
        return [f"{pad}require({_render_expr(stmt.expr)}, 'assert failed');"]
    if isinstance(stmt, AssignStmt):
        return [f"{pad}{_render_expr(stmt.target)} = {_render_expr(stmt.expr)};"]
    if isinstance(stmt, IfStmt):
        lines = [f"{pad}if ({_render_expr(stmt.condition)}) {{"]
        for inner in stmt.body:
            lines.extend(_render_statement(inner, indent + 4))
        lines.append(f"{pad}}}")
        if stmt.orelse:
            lines.append(f"{pad}else {{")
            for inner in stmt.orelse:
                lines.extend(_render_statement(inner, indent + 4))
            lines.append(f"{pad}}}")
        return lines
    raise TypeError(f"Unsupported statement {stmt}")


def render_statements(body: List[Statement], indent: int) -> str:
    lines: List[str] = []
    for stmt in body:
        lines.extend(_render_statement(stmt, indent))
    return "\n".join(lines) + ("\n" if lines else "")


def _format_params(params):
    return [f"{param.type} {param.name}" for param in params]


def transpile(contract: ContractSpec) -> str:
    env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.globals["render_statements"] = render_statements
    env.filters["join"] = lambda items, sep: sep.join(map(str, items))
    template = env.from_string(_TEMPLATE)
    rendered = template.render(contract=contract)
    return rendered


class SolidityTranspiler:
    def transpile(self, contract: ContractSpec) -> str:
        return transpile(contract)
