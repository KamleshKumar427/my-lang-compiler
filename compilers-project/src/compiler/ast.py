from __future__ import annotations

from dataclasses import dataclass, field

from compiler.tokenizer import SourceLocation
from compiler.types import Type, Unit

Location = SourceLocation


@dataclass
class Expression:
    location: Location
    type: Type = field(kw_only=True, default=Unit)


@dataclass
class Literal(Expression):
    value: int | bool | None


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    op: str
    expr: Expression


@dataclass
class If(Expression):
    condition: Expression
    then_branch: Expression
    else_branch: Expression | None


@dataclass
class While(Expression):
    condition: Expression
    body: Expression


@dataclass
class Call(Expression):
    callee: Expression
    args: list[Expression]


@dataclass
class Break(Expression):
    value: Expression | None = None


@dataclass
class Continue(Expression):
    pass


@dataclass
class Return(Expression):
    value: Expression | None


@dataclass
class Block(Expression):
    expressions: list[Expression]


@dataclass
class VarDeclaration(Expression):
    name: str
    value: Expression
    declared_type: Type | None = None


@dataclass
class FunctionParam:
    name: str
    type: Type


@dataclass
class FunctionDef:
    location: Location
    name: str
    params: list[FunctionParam]
    return_type: Type
    body: Expression


@dataclass
class Module:
    location: Location
    functions: list[FunctionDef]
    expressions: list[Expression]
