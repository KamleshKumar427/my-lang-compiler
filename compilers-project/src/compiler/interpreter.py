from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import compiler.ast as ast

Value = int | bool | None | Callable[[list["Value"]], "Value"]


class BreakSignal(Exception):
    def __init__(self, value: Value | None) -> None:
        self.value = value


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value: Value | None) -> None:
        self.value = value


@dataclass
class SymTab:
    parent: "SymTab | None" = None
    locals: dict[str, Value] = field(default_factory=dict)

    def define(self, name: str, value: Value) -> None:
        self.locals[name] = value

    def lookup(self, name: str) -> Value:
        if name in self.locals:
            return self.locals[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise Exception(f"Undefined variable: {name}")

    def assign(self, name: str, value: Value) -> None:
        if name in self.locals:
            self.locals[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise Exception(f"Undefined variable: {name}")


def _expect_arity(name: str, args: list[Value], arity: int) -> None:
    if len(args) != arity:
        raise Exception(f"{name}: expected {arity} arguments")


def _binary(name: str, fn: Callable[[Value, Value], Value]) -> Callable[[list[Value]], Value]:
    def op(args: list[Value]) -> Value:
        _expect_arity(name, args, 2)
        return fn(args[0], args[1])

    return op


def _unary(name: str, fn: Callable[[Value], Value]) -> Callable[[list[Value]], Value]:
    def op(args: list[Value]) -> Value:
        _expect_arity(name, args, 1)
        return fn(args[0])

    return op


def _div(a: Value, b: Value) -> Value:
    return int(a / b)  # type: ignore[operator]


def _rem(a: Value, b: Value) -> Value:
    return a - int(a / b) * b  # type: ignore[operator]


def create_global_symtab() -> SymTab:
    symtab = SymTab()

    symtab.define("+", _binary("+", lambda a, b: a + b))  # type: ignore[operator]
    symtab.define("-", _binary("-", lambda a, b: a - b))  # type: ignore[operator]
    symtab.define("*", _binary("*", lambda a, b: a * b))  # type: ignore[operator]
    symtab.define("/", _binary("/", _div))
    symtab.define("%", _binary("%", _rem))

    symtab.define("==", _binary("==", lambda a, b: a == b))
    symtab.define("!=", _binary("!=", lambda a, b: a != b))
    symtab.define("<", _binary("<", lambda a, b: a < b))  # type: ignore[operator]
    symtab.define("<=", _binary("<=", lambda a, b: a <= b))  # type: ignore[operator]
    symtab.define(">", _binary(">", lambda a, b: a > b))  # type: ignore[operator]
    symtab.define(">=", _binary(">=", lambda a, b: a >= b))  # type: ignore[operator]

    symtab.define("and", _binary("and", lambda a, b: bool(a) and bool(b)))
    symtab.define("or", _binary("or", lambda a, b: bool(a) or bool(b)))

    symtab.define("unary_-", _unary("unary_-", lambda a: -a))  # type: ignore[operator]
    symtab.define("unary_not", _unary("unary_not", lambda a: not a))

    def print_int(args: list[Value]) -> Value:
        _expect_arity("print_int", args, 1)
        print(args[0])
        return None

    def print_bool(args: list[Value]) -> Value:
        _expect_arity("print_bool", args, 1)
        print("true" if args[0] else "false")
        return None

    def read_int(args: list[Value]) -> Value:
        _expect_arity("read_int", args, 0)
        return int(input())

    symtab.define("print_int", print_int)
    symtab.define("print_bool", print_bool)
    symtab.define("read_int", read_int)

    return symtab


def interpret(node: ast.Expression | ast.Module, symtab: SymTab | None = None) -> Value:
    if symtab is None:
        symtab = create_global_symtab()

    if isinstance(node, ast.Module):
        def make_function(fn_def: ast.FunctionDef) -> Callable[[list[Value]], Value]:
            def _call(args: list[Value]) -> Value:
                _expect_arity(fn_def.name, args, len(fn_def.params))
                local = SymTab(symtab)
                for param, arg in zip(fn_def.params, args, strict=True):
                    local.define(param.name, arg)
                try:
                    return interpret(fn_def.body, local)
                except ReturnSignal as ret:
                    return ret.value
            return _call

        for fn in node.functions:
            symtab.define(fn.name, make_function(fn))

        top = SymTab(symtab)
        module_result: Value = None
        for expr in node.expressions:
            module_result = interpret(expr, top)
        return module_result

    if isinstance(node, ast.Literal):
        return node.value

    if isinstance(node, ast.Identifier):
        return symtab.lookup(node.name)

    if isinstance(node, ast.VarDeclaration):
        value = interpret(node.value, symtab)
        symtab.define(node.name, value)
        return None

    if isinstance(node, ast.BinaryOp):
        if node.op == "=":
            if not isinstance(node.left, ast.Identifier):
                raise Exception(f"{node.location}: expected identifier on left of '='")
            value = interpret(node.right, symtab)
            symtab.assign(node.left.name, value)
            return value
        if node.op == "and":
            left = interpret(node.left, symtab)
            if not left:
                return False
            right = interpret(node.right, symtab)
            return bool(right)
        if node.op == "or":
            left = interpret(node.left, symtab)
            if left:
                return True
            right = interpret(node.right, symtab)
            return bool(right)
        left = interpret(node.left, symtab)
        right = interpret(node.right, symtab)
        op = symtab.lookup(node.op)
        if not callable(op):
            raise Exception(f"{node.location}: operator '{node.op}' is not callable")
        return op([left, right])

    if isinstance(node, ast.UnaryOp):
        value = interpret(node.expr, symtab)
        op = symtab.lookup(f"unary_{node.op}")
        if not callable(op):
            raise Exception(f"{node.location}: operator '{node.op}' is not callable")
        return op([value])

    if isinstance(node, ast.If):
        condition = interpret(node.condition, symtab)
        if condition:
            return interpret(node.then_branch, symtab)
        if node.else_branch is None:
            return None
        return interpret(node.else_branch, symtab)

    if isinstance(node, ast.While):
        while interpret(node.condition, symtab):
            try:
                interpret(node.body, symtab)
            except ContinueSignal:
                continue
            except BreakSignal as br:
                return br.value
        return None

    if isinstance(node, ast.Call):
        callee = interpret(node.callee, symtab)
        if not callable(callee):
            raise Exception(f"{node.location}: callee is not callable")
        args = [interpret(arg, symtab) for arg in node.args]
        return callee(args)

    if isinstance(node, ast.Break):
        value = interpret(node.value, symtab) if node.value is not None else None
        raise BreakSignal(value)

    if isinstance(node, ast.Continue):
        raise ContinueSignal()

    if isinstance(node, ast.Return):
        value = interpret(node.value, symtab) if node.value is not None else None
        raise ReturnSignal(value)

    if isinstance(node, ast.Block):
        child = SymTab(symtab)
        block_result: Value = None
        for expr in node.expressions:
            block_result = interpret(expr, child)
        return block_result

    raise Exception(f"{node.location}: unknown expression")
