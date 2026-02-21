from __future__ import annotations

from dataclasses import dataclass

from compiler.tokenizer import SourceLocation

Location = SourceLocation


@dataclass(frozen=True)
class Expression:
    location: Location


@dataclass(frozen=True)
class Literal(Expression):
    value: int | bool | None


@dataclass(frozen=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True)
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass(frozen=True)
class UnaryOp(Expression):
    op: str
    expr: Expression


@dataclass(frozen=True)
class If(Expression):
    condition: Expression
    then_branch: Expression
    else_branch: Expression | None


@dataclass(frozen=True)
class While(Expression):
    condition: Expression
    body: Expression


@dataclass(frozen=True)
class Call(Expression):
    callee: Expression
    args: list[Expression]


@dataclass(frozen=True)
class Block(Expression):
    expressions: list[Expression]


@dataclass(frozen=True)
class VarDeclaration(Expression):
    name: str
    value: Expression