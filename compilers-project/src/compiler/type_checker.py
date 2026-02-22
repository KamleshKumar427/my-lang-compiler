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


@dataclass
class LoopContext:
    break_type: Type | None = None


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


def typecheck(node: ast.Expression | ast.Module, symtab: SymTab | None = None) -> Type:
    if symtab is None:
        symtab = create_global_symtab()

    def check(
        n: ast.Expression,
        env: SymTab,
        loop: LoopContext | None,
        return_type: Type | None,
    ) -> Type:
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
            value_type = check(n.value, env, loop, return_type)
            if n.name in env.locals:
                raise Exception(f"{n.location}: variable already declared: {n.name}")
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
                right_type = check(n.right, env, loop, return_type)
                _expect_type(right_type, left_type, n)
                n.type = left_type
                return left_type

            left_type = check(n.left, env, loop, return_type)
            right_type = check(n.right, env, loop, return_type)

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
            expr_type = check(n.expr, env, loop, return_type)
            op_type = _expect_fun_type(env.lookup(f"unary_{n.op}"), n)
            if len(op_type.params) != 1:
                raise Exception(f"{n.location}: expected unary operator")
            _expect_type(expr_type, op_type.params[0], n.expr)
            n.type = op_type.return_type
            return op_type.return_type

        if isinstance(n, ast.If):
            cond_type = check(n.condition, env, loop, return_type)
            _expect_type(cond_type, Bool, n.condition)
            then_type = check(n.then_branch, env, loop, return_type)
            if n.else_branch is None:
                n.type = Unit
                return Unit
            else_type = check(n.else_branch, env, loop, return_type)
            _expect_type(then_type, else_type, n)
            n.type = then_type
            return then_type

        if isinstance(n, ast.While):
            cond_type = check(n.condition, env, loop, return_type)
            _expect_type(cond_type, Bool, n.condition)
            loop_ctx = LoopContext()
            body_type = check(n.body, env, loop_ctx, return_type)
            _expect_type(body_type, Unit, n.body)
            n.type = loop_ctx.break_type if loop_ctx.break_type is not None else Unit
            return n.type

        if isinstance(n, ast.Call):
            callee_type = check(n.callee, env, loop, return_type)
            fun_type = _expect_fun_type(callee_type, n.callee)
            if len(fun_type.params) != len(n.args):
                raise Exception(f"{n.location}: expected {len(fun_type.params)} arguments")
            for arg, expected in zip(n.args, fun_type.params, strict=True):
                arg_type = check(arg, env, loop, return_type)
                _expect_type(arg_type, expected, arg)
            n.type = fun_type.return_type
            return fun_type.return_type

        if isinstance(n, ast.Break):
            if loop is None:
                raise Exception(f"{n.location}: break outside loop")
            if n.value is None:
                value_type = Unit
            else:
                value_type = check(n.value, env, loop, return_type)
            if loop.break_type is None:
                loop.break_type = value_type
            else:
                _expect_type(value_type, loop.break_type, n)
            n.type = Unit
            return Unit

        if isinstance(n, ast.Continue):
            if loop is None:
                raise Exception(f"{n.location}: continue outside loop")
            n.type = Unit
            return Unit

        if isinstance(n, ast.Return):
            if return_type is None:
                raise Exception(f"{n.location}: return outside function")
            if n.value is None:
                _expect_type(Unit, return_type, n)
                n.type = Unit
                return Unit
            value_type = check(n.value, env, loop, return_type)
            _expect_type(value_type, return_type, n)
            n.type = Unit
            return Unit

        if isinstance(n, ast.Block):
            child = SymTab(env)
            result_type: Type = Unit
            for expr in n.expressions:
                result_type = check(expr, child, loop, return_type)
            n.type = result_type
            return result_type

        raise Exception(f"{n.location}: unknown expression")

    if isinstance(node, ast.Module):
        seen: set[str] = set()
        for fn in node.functions:
            if fn.name in seen:
                raise Exception(f"{fn.location}: function already declared: {fn.name}")
            if fn.name == "main" or fn.name in symtab.locals:
                raise Exception(f"{fn.location}: function name reserved: {fn.name}")
            seen.add(fn.name)
            symtab.define(
                fn.name,
                FunType([p.type for p in fn.params], fn.return_type),
            )

        for fn in node.functions:
            fn_env = SymTab(symtab)
            param_names: set[str] = set()
            for param in fn.params:
                if param.name in param_names:
                    raise Exception(f"{fn.location}: duplicate parameter: {param.name}")
                param_names.add(param.name)
                fn_env.define(param.name, param.type)
            check(fn.body, fn_env, None, fn.return_type)

        top_env = SymTab(symtab)
        result: Type = Unit
        for expr in node.expressions:
            result = check(expr, top_env, None, None)
        return result

    return check(node, symtab, None, None)
