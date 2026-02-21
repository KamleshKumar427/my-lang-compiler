from __future__ import annotations

from dataclasses import dataclass

from compiler import ir
from compiler.intrinsics import IntrinsicArgs, all_intrinsics


@dataclass
class Locals:
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        self._var_to_location = {}
        offset = 0
        for var in variables:
            offset += 8
            self._var_to_location[var] = f"-{offset}(%rbp)"
        self._stack_used = ((offset + 15) // 16) * 16

    def get_ref(self, v: ir.IRVar) -> str:
        return self._var_to_location[v]

    def has(self, v: ir.IRVar) -> bool:
        return v in self._var_to_location

    def stack_used(self) -> int:
        return self._stack_used


def get_all_ir_variables(instructions: list[ir.Instruction]) -> list[ir.IRVar]:
    vars_set: set[ir.IRVar] = set()

    def add_var(v: ir.IRVar) -> None:
        vars_set.add(v)

    for insn in instructions:
        if isinstance(insn, ir.LoadBoolConst):
            add_var(insn.dest)
        elif isinstance(insn, ir.LoadIntConst):
            add_var(insn.dest)
        elif isinstance(insn, ir.Copy):
            add_var(insn.source)
            add_var(insn.dest)
        elif isinstance(insn, ir.Call):
            add_var(insn.fun)
            for a in insn.args:
                add_var(a)
            add_var(insn.dest)
        elif isinstance(insn, ir.CondJump):
            add_var(insn.cond)

    return [v for v in vars_set if v.name.startswith("x")]


def generate_assembly(instructions: list[ir.Instruction]) -> str:
    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)

    locals = Locals(variables=get_all_ir_variables(instructions))

    emit(".extern print_int")
    emit(".extern print_bool")
    emit(".extern read_int")
    emit(".global main")
    emit(".type main, @function")
    emit("")
    emit(".section .text")
    emit("")
    emit("main:")
    emit("pushq %rbp")
    emit("movq %rsp, %rbp")
    if locals.stack_used() > 0:
        emit(f"subq ${locals.stack_used()}, %rsp")

    for insn in instructions:
        emit(f"# {insn}")
        if isinstance(insn, ir.Label):
            emit("")
            emit(f".L{insn.name}:")
        elif isinstance(insn, ir.LoadIntConst):
            if -2**31 <= insn.value < 2**31:
                emit(f"movq ${insn.value}, {locals.get_ref(insn.dest)}")
            else:
                emit(f"movabsq ${insn.value}, %rax")
                emit(f"movq %rax, {locals.get_ref(insn.dest)}")
        elif isinstance(insn, ir.LoadBoolConst):
            value = 1 if insn.value else 0
            emit(f"movq ${value}, {locals.get_ref(insn.dest)}")
        elif isinstance(insn, ir.Copy):
            if locals.has(insn.source):
                emit(f"movq {locals.get_ref(insn.source)}, %rax")
            else:
                emit(f"leaq {insn.source.name}(%rip), %rax")
            emit(f"movq %rax, {locals.get_ref(insn.dest)}")
        elif isinstance(insn, ir.Jump):
            emit(f"jmp .L{insn.label.name}")
        elif isinstance(insn, ir.CondJump):
            emit(f"cmpq $0, {locals.get_ref(insn.cond)}")
            emit(f"jne .L{insn.then_label.name}")
            emit(f"jmp .L{insn.else_label.name}")
        elif isinstance(insn, ir.Call):
            if insn.fun.name in all_intrinsics:
                arg_refs = [locals.get_ref(a) for a in insn.args]
                all_intrinsics[insn.fun.name](
                    IntrinsicArgs(arg_refs=arg_refs, result_register="%rax", emit=emit)
                )
                emit(f"movq %rax, {locals.get_ref(insn.dest)}")
                continue

            regs = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]
            if len(insn.args) > len(regs):
                raise Exception("Too many arguments for call")
            for reg, arg in zip(regs, insn.args, strict=False):
                if locals.has(arg):
                    emit(f"movq {locals.get_ref(arg)}, {reg}")
                else:
                    emit(f"leaq {arg.name}(%rip), {reg}")
            if locals.has(insn.fun):
                emit(f"movq {locals.get_ref(insn.fun)}, %rax")
                emit("callq *%rax")
            else:
                emit(f"callq {insn.fun.name}")
            emit(f"movq %rax, {locals.get_ref(insn.dest)}")

    emit("")
    emit("movq %rbp, %rsp")
    emit("popq %rbp")
    emit("ret")

    return "\n".join(lines) + "\n"
