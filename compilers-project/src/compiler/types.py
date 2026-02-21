from __future__ import annotations

from dataclasses import dataclass


class Type:
    pass


@dataclass(frozen=True)
class PrimitiveType(Type):
    name: str

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class FunType(Type):
    params: list[Type]
    return_type: Type

    def __repr__(self) -> str:
        params = ", ".join([repr(p) for p in self.params])
        return f"({params}) => {self.return_type!r}"


Int = PrimitiveType("Int")
Bool = PrimitiveType("Bool")
Unit = PrimitiveType("Unit")