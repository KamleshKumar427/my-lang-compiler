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
        elif isinstance(insn, ir.LoadParam):
            add_var(insn.dest)
        elif isinstance(insn, ir.Return):
            add_var(insn.value)

    return [v for v in vars_set if v.name.startswith("x")]


def generate_assembly(functions: dict[str, list[ir.Instruction]]) -> str:
    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)

    emit(".extern print_int")
    emit(".extern print_bool")
    emit(".extern read_int")
    emit("")
    emit(".section .text")
    emit("")

    for func_name, instructions in functions.items():
        local_map = Locals(variables=get_all_ir_variables(instructions))
        ret_label = f".L{func_name}_ret"

        def label_ref(label: ir.Label) -> str:
            return f".L{func_name}_{label.name}"

        def arg_ref(v: ir.IRVar) -> str:
            if local_map.has(v):
                return local_map.get_ref(v)
            if v.name == "unit":
                return "$0"
            return f"{v.name}(%rip)"

        def load_value(v: ir.IRVar, reg: str) -> None:
            if local_map.has(v):
                emit(f"movq {local_map.get_ref(v)}, {reg}")
            elif v.name == "unit":
                emit(f"movq $0, {reg}")
            else:
                emit(f"leaq {v.name}(%rip), {reg}")

        emit(f".global {func_name}")
        emit(f".type {func_name}, @function")
        emit("")
        emit(f"{func_name}:")
        emit("pushq %rbp")
        emit("movq %rsp, %rbp")
        if local_map.stack_used() > 0:
            emit(f"subq ${local_map.stack_used()}, %rsp")

        for insn in instructions:
            emit(f"# {insn}")
            if isinstance(insn, ir.Label):
                emit("")
                emit(f"{label_ref(insn)}:")
            elif isinstance(insn, ir.LoadIntConst):
                if -2**31 <= insn.value < 2**31:
                    emit(f"movq ${insn.value}, {local_map.get_ref(insn.dest)}")
                else:
                    emit(f"movabsq ${insn.value}, %rax")
                    emit(f"movq %rax, {local_map.get_ref(insn.dest)}")
            elif isinstance(insn, ir.LoadBoolConst):
                value = 1 if insn.value else 0
                emit(f"movq ${value}, {local_map.get_ref(insn.dest)}")
            elif isinstance(insn, ir.Copy):
                load_value(insn.source, "%rax")
                emit(f"movq %rax, {local_map.get_ref(insn.dest)}")
            elif isinstance(insn, ir.LoadParam):
                regs = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]
                if insn.index >= len(regs):
                    raise Exception("Too many arguments for call")
                emit(f"movq {regs[insn.index]}, {local_map.get_ref(insn.dest)}")
            elif isinstance(insn, ir.Jump):
                emit(f"jmp {label_ref(insn.label)}")
            elif isinstance(insn, ir.CondJump):
                emit(f"cmpq $0, {local_map.get_ref(insn.cond)}")
                emit(f"jne {label_ref(insn.then_label)}")
                emit(f"jmp {label_ref(insn.else_label)}")
            elif isinstance(insn, ir.Return):
                load_value(insn.value, "%rax")
                emit(f"jmp {ret_label}")
            elif isinstance(insn, ir.Call):
                if insn.fun.name in all_intrinsics:
                    arg_refs = [arg_ref(a) for a in insn.args]
                    all_intrinsics[insn.fun.name](
                        IntrinsicArgs(arg_refs=arg_refs, result_register="%rax", emit=emit)
                    )
                    emit(f"movq %rax, {local_map.get_ref(insn.dest)}")
                    continue

                regs = ["%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"]
                if len(insn.args) > len(regs):
                    raise Exception("Too many arguments for call")
                for reg, arg in zip(regs, insn.args, strict=False):
                    load_value(arg, reg)
                if local_map.has(insn.fun):
                    emit(f"movq {local_map.get_ref(insn.fun)}, %rax")
                    emit("callq *%rax")
                else:
                    emit(f"callq {insn.fun.name}")
                emit(f"movq %rax, {local_map.get_ref(insn.dest)}")

        emit("movq $0, %rax")
        emit(f"{ret_label}:")
        emit("movq %rbp, %rsp")
        emit("popq %rbp")
        emit("ret")
        emit("")

    return "\n".join(lines) + "\n"
