from __future__ import annotations

from typing import List

from lark import Lark, Transformer, v_args
from lark.indenter import Indenter

from .ast import AssertStmt, AssignStmt, ContractSpec, Function, IfStmt, Parameter, StateVar


type_map = {
    "string": "string",
    "uint256": "uint256",
    "address": "address",
    "bool": "bool",
}


class SnakechainIndenter(Indenter):
    NL_type = "NEWLINE"
    OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
    CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
    INDENT_type = "INDENT"
    DEDENT_type = "DEDENT"
    tab_len = 4


grammar = r"""
    ?start: contract

    contract: "contract" NAME ":" NEWLINE INDENT contract_body DEDENT -> contract
    contract_body: contract_item+
    contract_item: state_var | function

    state_var: NAME type_decl? state_value? NEWLINE -> state_var
    state_value: "=" expr
    type_decl: ":" type_expr

    function: "def" NAME "(" [parameters] ")" ":" NEWLINE INDENT func_body DEDENT -> function
    parameters: param ("," param)*
    param: NAME ":" type_expr -> param

    func_body: func_stmt+
    ?func_stmt: assert_stmt | assign_stmt | if_stmt

    assert_stmt: "assert" expr NEWLINE -> assert_stmt
    assign_stmt: assign_target "=" expr NEWLINE -> assign_stmt
    assign_target: dotted | indexed | NAME

    if_stmt: "if" expr ":" NEWLINE INDENT func_body DEDENT else_block? -> if_stmt
    else_block: "else" ":" NEWLINE INDENT func_body DEDENT -> else_block

    ?expr: or_expr
    ?or_expr: and_expr ("or" and_expr)*
    ?and_expr: not_expr ("and" not_expr)*
    ?not_expr: "not" not_expr   -> not_expr
             | comparison
    ?comparison: arith (COMP_OP arith)+ -> comparison
               | arith
    COMP_OP: "=="|"!="|">="|"<="|">"|"<"
    ?arith: term ((PLUS|MINUS) term)*
    ?term: factor (("*"|"/") factor)*
    ?factor: atom
          | "-" factor -> neg
    ?atom: NAME -> name
         | dotted
         | indexed
         | NUMBER -> number
         | STRING -> string
         | "True" -> true
         | "False" -> false
         | "msg" "." "sender" -> msg_sender
         | "msg" "." "value" -> msg_value
         | "(" expr ")"

    dotted: NAME "." NAME -> dotted
    indexed: (dotted|NAME) "[" expr "]" -> indexed

    type_expr: BASE_TYPE -> base_type
             | MAPPING_TYPE -> mapping_type

    BASE_TYPE: /(address|string|uint256|bool)/
    MAPPING_TYPE: /mapping\s*\[\s*(address|string|uint256|bool)\s*,\s*(address|string|uint256|bool)\s*\]/

    PLUS: "+"
    MINUS: "-"

    NAME: /(?!contract\b)(?!def\b)(?!assert\b)(?!msg\b)(?!sender\b)(?!value\b)(?!mapping\b)(?!address\b)(?!string\b)(?!uint256\b)(?!bool\b)[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /[0-9]+/
    STRING: /"(\\.|[^"\\])*"/ | /'(\\.|[^'\\])*'/

    %import common.WS_INLINE
    %declare INDENT DEDENT
    NEWLINE: /\r?\n[ \t]*/
    %ignore WS_INLINE
"""


@v_args(inline=True)
class TreeToAST(Transformer):
    def contract(self, *parts):
        name_token = next(p for p in parts if hasattr(p, "type") and p.type == "NAME")
        body = next((p for p in parts if hasattr(p, "children")), None)
        list_body = body.children if body else next((p for p in parts if isinstance(p, list)), [])
        state_vars: List[StateVar] = []
        functions: List[Function] = []
        for item in list_body:
            if isinstance(item, StateVar):
                state_vars.append(item)
            elif isinstance(item, Function):
                functions.append(item)
        return ContractSpec(name_token.value, state_vars, functions)

    def contract_body(self, *items):
        return list(items)

    def contract_item(self, item):
        return item

    def state_var(self, name, *parts):
        declared_type = None
        init_value = None
        for part in parts:
            if hasattr(part, "type"):
                continue
            if declared_type is None and self._is_supported_type(part):
                declared_type = part
                continue
            if init_value is None:
                init_value = part
        inferred = self._infer_type(init_value)
        final_type = declared_type or inferred
        if not self._is_supported_type(final_type):
            raise ValueError(f"Unsupported state variable type for {name.value}: {final_type}")
        value_literal = init_value if init_value is not None else self._default_value(final_type)
        return StateVar(name.value, final_type, value_literal)

    def state_value(self, *tokens):
        return tokens[-1]

    def type_decl(self, *tokens):
        return tokens[-1]

    def base_type(self, token):
        return token.value

    def mapping_type(self, token):
        return token.value

    def function(self, *parts):
        name_token = next(p for p in parts if hasattr(p, "type") and p.type == "NAME")
        params_list = next((p for p in parts if isinstance(p, list) and p and isinstance(p[0], Parameter)), [])
        body_list = next((p for p in parts if isinstance(p, list) and (not p or isinstance(p[0], (AssertStmt, AssignStmt, IfStmt)))), [])
        return Function(name_token.value, params_list, body_list)

    def parameters(self, *params):
        return list(params)

    def param(self, name, type_token):
        t = type_token
        if not self._is_supported_type(t):
            raise ValueError(f"Unsupported parameter type {t}")
        return Parameter(name.value, t)

    def func_body(self, *stmts):
        return list(stmts)

    def assert_stmt(self, *parts):
        expr = next(p for p in parts if not hasattr(p, "type"))
        return AssertStmt(expr)

    def assign_stmt(self, target, *parts):
        expr = next((p for p in reversed(parts) if not hasattr(p, "type")), None)
        if expr is None:
            raise ValueError("Assignment missing expression")
        return AssignStmt(target, expr)

    def assign_target(self, target):
        return target

    def if_stmt(self, condition, body, else_block=None):
        orelse: List = []
        if else_block is not None:
            orelse = else_block
        return IfStmt(condition, body, orelse)

    def else_block(self, body):
        return body

    def dotted(self, left, right):
        return f"{left.value}.{right.value}"

    def indexed(self, base, index):
        base_expr = base if isinstance(base, str) else base.value
        return f"{base_expr}[{index}]"

    def name(self, token):
        return token.value

    def number(self, token):
        return token.value

    def string(self, token):
        return token.value

    def true(self):
        return "true"

    def false(self):
        return "false"

    def msg_sender(self):
        return "msg.sender"

    def msg_value(self):
        return "msg.value"

    def neg(self, value):
        return f"-{value}"

    def comparison(self, left, *rest):
        expr = left
        for op, right in zip(rest[::2], rest[1::2]):
            expr = f"{expr} {self._op_to_str(op)} {right}"
        return expr

    def not_expr(self, value):
        return f"!({value})"

    def or_expr(self, left, *rest):
        expr = left
        for item in rest:
            expr = f"{expr} || {item}"
        return expr

    def and_expr(self, left, *rest):
        expr = left
        for item in rest:
            expr = f"{expr} && {item}"
        return expr

    def arith(self, left, *rest):
        expr = left
        for op, right in zip(rest[::2], rest[1::2]):
            expr = f"{expr} {self._op_to_str(op)} {right}"
        return expr

    def term(self, left, *rest):
        expr = left
        for op, right in zip(rest[::2], rest[1::2]):
            expr = f"{expr} {self._op_to_str(op)} {right}"
        return expr

    def comp_op(self, *tokens):
        if not tokens:
            return ""
        token = tokens[-1]
        if hasattr(token, "value"):
            return token.value
        if hasattr(token, "data") and getattr(token, "children", None):
            return self._op_to_str(token.children[-1])
        return str(token)

    def _op_to_str(self, op):
        return op if isinstance(op, str) else getattr(op, "value", str(op))

    def _infer_type(self, value):
        if value is None:
            return None
        if isinstance(value, str) and value.startswith(("\"", "'")):
            return "string"
        if isinstance(value, str) and value.isdigit():
            return "uint256"
        if isinstance(value, str) and value in {"true", "false"}:
            return "bool"
        return None

    def _default_value(self, var_type: str) -> str:
        if var_type.startswith("mapping["):
            return ""
        if var_type == "string":
            return '""'
        if var_type == "bool":
            return "false"
        return "0"

    def _is_supported_type(self, value: str | None) -> bool:
        if value is None:
            return False
        if value in type_map:
            return True
        return value.startswith("mapping[") and value.endswith("]")


class DSLParser:
    def __init__(self):
        self._lark = Lark(
            grammar,
            parser="lalr",
            lexer="basic",
            postlex=SnakechainIndenter(),
            start="start",
        )

    def parse(self, source: str) -> ContractSpec:
        tree = self._lark.parse(source)
        ast = TreeToAST().transform(tree)
        return ast

    def parse_file(self, path: str) -> ContractSpec:
        with open(path, "r", encoding="utf-8") as f:
            return self.parse(f.read())
