from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class SymTab(Generic[T]):
    parent: "SymTab[T] | None" = None
    locals: dict[str, T] = field(default_factory=dict)

    def add_local(self, name: str, value: T) -> None:
        self.locals[name] = value

    def require(self, name: str) -> T:
        if name in self.locals:
            return self.locals[name]
        if self.parent is not None:
            return self.parent.require(name)
        raise Exception(f"Undefined variable: {name}")

    def set_existing(self, name: str, value: T) -> None:
        if name in self.locals:
            self.locals[name] = value
            return
        if self.parent is not None:
            self.parent.set_existing(name, value)
            return
        raise Exception(f"Undefined variable: {name}")