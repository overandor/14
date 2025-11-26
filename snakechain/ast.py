from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class StateVar:
    name: str
    type: str
    value: str


@dataclass
class Parameter:
    name: str
    type: str

    def __str__(self) -> str:
        return f"{self.type} {self.name}"


@dataclass
class Statement:
    pass


@dataclass
class AssertStmt(Statement):
    expr: str


@dataclass
class AssignStmt(Statement):
    target: str
    expr: str


@dataclass
class IfStmt(Statement):
    condition: str
    body: List[Statement] = field(default_factory=list)
    orelse: List[Statement] = field(default_factory=list)


@dataclass
class Function:
    name: str
    parameters: List[Parameter]
    body: List[Statement]
    visibility: str = "public"


@dataclass
class ContractSpec:
    name: str
    state_vars: List[StateVar]
    functions: List[Function]
