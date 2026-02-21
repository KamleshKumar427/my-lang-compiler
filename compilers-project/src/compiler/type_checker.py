from __future__ import annotations

from dataclasses import dataclass, field

import compiler.ast as ast
from compiler.types import Bool, FunType, Int, Type, Unit


@dataclass
class SymTab:
    parent: "SymTab | None" = None
    locals: dict[str, Type] = field(default_factory=dict)

    def define(self, name: str, value: Type) -> None:
        self.locals[name] = value

    def lookup(self, name: str) -> Type:
        if name in self.locals:
            return self.locals[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise Exception(f"Undefined variable: {name}")

    def assign(self, name: str, value: Type) -> None:
        if name in self.locals:
            self.locals[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise Exception(f"Undefined variable: {name}")


def create_global_symtab() -> SymTab:
    symtab = SymTab()

    symtab.define("+", FunType([Int, Int], Int))
    symtab.define("-", FunType([Int, Int], Int))
    symtab.define("*", FunType([Int, Int], Int))
    symtab.define("/", FunType([Int, Int], Int))
    symtab.define("%", FunType([Int, Int], Int))

    symtab.define("<", FunType([Int, Int], Bool))
    symtab.define("<=", FunType([Int, Int], Bool))
    symtab.define(">", FunType([Int, Int], Bool))
    symtab.define(">=", FunType([Int, Int], Bool))

    symtab.define("and", FunType([Bool, Bool], Bool))
    symtab.define("or", FunType([Bool, Bool], Bool))

    symtab.define("unary_-", FunType([Int], Int))
    symtab.define("unary_not", FunType([Bool], Bool))

    symtab.define("print_int", FunType([Int], Unit))
    symtab.define("print_bool", FunType([Bool], Unit))
    symtab.define("read_int", FunType([], Int))

    return symtab


def _expect_type(actual: Type, expected: Type, node: ast.Expression) -> None:
    if actual != expected:
        raise Exception(f"{node.location}: expected {expected}, got {actual}")


def _expect_fun_type(t: Type, node: ast.Expression) -> FunType:
    if not isinstance(t, FunType):
        raise Exception(f"{node.location}: expected function type")
    return t


def typecheck(node: ast.Expression, symtab: SymTab | None = None) -> Type:
    if symtab is None:
        symtab = create_global_symtab()

    def check(n: ast.Expression, env: SymTab) -> Type:
        if isinstance(n, ast.Literal):
            if isinstance(n.value, bool):
                n.type = Bool
                return Bool
            if isinstance(n.value, int):
                n.type = Int
                return Int
            n.type = Unit
            return Unit

        if isinstance(n, ast.Identifier):
            t = env.lookup(n.name)
            n.type = t
            return t

        if isinstance(n, ast.VarDeclaration):
            value_type = check(n.value, env)
            if n.declared_type is not None:
                _expect_type(value_type, n.declared_type, n)
                env.define(n.name, n.declared_type)
            else:
                env.define(n.name, value_type)
            n.type = Unit
            return Unit

        if isinstance(n, ast.BinaryOp):
            if n.op == "=":
                if not isinstance(n.left, ast.Identifier):
                    raise Exception(f"{n.location}: expected identifier on left of '='")
                left_type = env.lookup(n.left.name)
                n.left.type = left_type
                right_type = check(n.right, env)
                _expect_type(right_type, left_type, n)
                n.type = left_type
                return left_type

            left_type = check(n.left, env)
            right_type = check(n.right, env)

            if n.op in ["==", "!="]:
                if left_type != right_type:
                    raise Exception(f"{n.location}: expected matching types")
                n.type = Bool
                return Bool

            op_type = _expect_fun_type(env.lookup(n.op), n)
            if len(op_type.params) != 2:
                raise Exception(f"{n.location}: expected binary operator")
            _expect_type(left_type, op_type.params[0], n.left)
            _expect_type(right_type, op_type.params[1], n.right)
            n.type = op_type.return_type
            return op_type.return_type

        if isinstance(n, ast.UnaryOp):
            expr_type = check(n.expr, env)
            op_type = _expect_fun_type(env.lookup(f"unary_{n.op}"), n)
            if len(op_type.params) != 1:
                raise Exception(f"{n.location}: expected unary operator")
            _expect_type(expr_type, op_type.params[0], n.expr)
            n.type = op_type.return_type
            return op_type.return_type

        if isinstance(n, ast.If):
            cond_type = check(n.condition, env)
            _expect_type(cond_type, Bool, n.condition)
            then_type = check(n.then_branch, env)
            if n.else_branch is None:
                _expect_type(then_type, Unit, n.then_branch)
                n.type = Unit
                return Unit
            else_type = check(n.else_branch, env)
            _expect_type(then_type, else_type, n)
            n.type = then_type
            return then_type

        if isinstance(n, ast.While):
            cond_type = check(n.condition, env)
            _expect_type(cond_type, Bool, n.condition)
            body_type = check(n.body, env)
            _expect_type(body_type, Unit, n.body)
            n.type = Unit
            return Unit

        if isinstance(n, ast.Call):
            callee_type = check(n.callee, env)
            fun_type = _expect_fun_type(callee_type, n.callee)
            if len(fun_type.params) != len(n.args):
                raise Exception(f"{n.location}: expected {len(fun_type.params)} arguments")
            for arg, expected in zip(n.args, fun_type.params, strict=True):
                arg_type = check(arg, env)
                _expect_type(arg_type, expected, arg)
            n.type = fun_type.return_type
            return fun_type.return_type

        if isinstance(n, ast.Block):
            child = SymTab(env)
            result_type: Type = Unit
            for expr in n.expressions:
                result_type = check(expr, child)
            n.type = result_type
            return result_type

        raise Exception(f"{n.location}: unknown expression")

    return check(node, symtab)