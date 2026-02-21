from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class IntrinsicArgs:
    arg_refs: list[str]
    result_register: str
    emit: Callable[[str], None]


def _binary_arith(op: str) -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        a, b = args.arg_refs
        args.emit(f"movq {a}, {args.result_register}")
        args.emit(f"{op} {b}, {args.result_register}")

    return emit_intrinsic


def _binary_div() -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        a, b = args.arg_refs
        args.emit(f"movq {a}, %rax")
        args.emit("cqto")
        args.emit(f"idivq {b}")
        if args.result_register != "%rax":
            args.emit(f"movq %rax, {args.result_register}")

    return emit_intrinsic


def _binary_rem() -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        a, b = args.arg_refs
        args.emit(f"movq {a}, %rax")
        args.emit("cqto")
        args.emit(f"idivq {b}")
        if args.result_register != "%rdx":
            args.emit(f"movq %rdx, {args.result_register}")

    return emit_intrinsic


def _compare(setcc: str) -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        a, b = args.arg_refs
        args.emit(f"movq {a}, %rax")
        args.emit(f"cmpq {b}, %rax")
        args.emit(f"{setcc} %al")
        args.emit("movzbq %al, %rax")
        if args.result_register != "%rax":
            args.emit(f"movq %rax, {args.result_register}")

    return emit_intrinsic


def _unary_neg() -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        (a,) = args.arg_refs
        args.emit(f"movq {a}, {args.result_register}")
        args.emit(f"negq {args.result_register}")

    return emit_intrinsic


def _unary_not() -> Callable[[IntrinsicArgs], None]:
    def emit_intrinsic(args: IntrinsicArgs) -> None:
        (a,) = args.arg_refs
        args.emit(f"movq {a}, %rax")
        args.emit("cmpq $0, %rax")
        args.emit("sete %al")
        args.emit("movzbq %al, %rax")
        if args.result_register != "%rax":
            args.emit(f"movq %rax, {args.result_register}")

    return emit_intrinsic


all_intrinsics: dict[str, Callable[[IntrinsicArgs], None]] = {
    "+": _binary_arith("addq"),
    "-": _binary_arith("subq"),
    "*": _binary_arith("imulq"),
    "/": _binary_div(),
    "%": _binary_rem(),
    "<": _compare("setl"),
    "<=": _compare("setle"),
    ">": _compare("setg"),
    ">=": _compare("setge"),
    "==": _compare("sete"),
    "!=": _compare("setne"),
    "unary_-": _unary_neg(),
    "unary_not": _unary_not(),
}