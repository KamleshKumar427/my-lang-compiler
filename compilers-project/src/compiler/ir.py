from __future__ import annotations

from dataclasses import dataclass
import dataclasses
from typing import Any

from compiler.tokenizer import SourceLocation

Location = SourceLocation


@dataclass(frozen=True)
class IRVar:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Instruction:
    location: Location

    def __str__(self) -> str:
        def format_value(v: Any) -> str:
            if isinstance(v, list):
                return f'[{", ".join(format_value(e) for e in v)}]'
            return str(v)

        args = ", ".join(
            format_value(getattr(self, field.name))
            for field in dataclasses.fields(self)
            if field.name != "location"
        )
        return f"{type(self).__name__}({args})"


@dataclass(frozen=True)
class LoadBoolConst(Instruction):
    value: bool
    dest: IRVar


@dataclass(frozen=True)
class LoadIntConst(Instruction):
    value: int
    dest: IRVar


@dataclass(frozen=True)
class Copy(Instruction):
    source: IRVar
    dest: IRVar


@dataclass(frozen=True)
class Call(Instruction):
    fun: IRVar
    args: list[IRVar]
    dest: IRVar


@dataclass(frozen=True)
class Jump(Instruction):
    label: "Label"


@dataclass(frozen=True)
class CondJump(Instruction):
    cond: IRVar
    then_label: "Label"
    else_label: "Label"


@dataclass(frozen=True)
class Label(Instruction):
    name: str

    def __str__(self) -> str:
        return self.name