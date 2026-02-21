from __future__ import annotations

import compiler.ast as ast
from compiler import ir
from compiler.symtab import SymTab
from compiler.types import Bool, Int


def generate_ir(reserved_names: set[str], root_expr: ast.Expression) -> list[ir.Instruction]:
    var_unit = ir.IRVar("unit")

    next_var_id = 0
    next_label_id = 0

    def new_var() -> ir.IRVar:
        nonlocal next_var_id
        while True:
            name = f"x{next_var_id}"
            next_var_id += 1
            if name not in reserved_names:
                return ir.IRVar(name)

    def new_label() -> ir.Label:
        nonlocal next_label_id
        name = f"L{next_label_id}"
        next_label_id += 1
        return ir.Label(root_expr.location, name)

    ins: list[ir.Instruction] = []

    def visit(st: SymTab[ir.IRVar], expr: ast.Expression) -> ir.IRVar:
        loc = expr.location

        if isinstance(expr, ast.Literal):
            if isinstance(expr.value, bool):
                var = new_var()
                ins.append(ir.LoadBoolConst(loc, expr.value, var))
                return var
            if isinstance(expr.value, int):
                var = new_var()
                ins.append(ir.LoadIntConst(loc, expr.value, var))
                return var
            if expr.value is None:
                return var_unit
            raise Exception(f"{loc}: unsupported literal: {type(expr.value)}")

        if isinstance(expr, ast.Identifier):
            return st.require(expr.name)

        if isinstance(expr, ast.VarDeclaration):
            var_value = visit(st, expr.value)
            var_slot = new_var()
            st.add_local(expr.name, var_slot)
            ins.append(ir.Copy(loc, var_value, var_slot))
            return var_unit

        if isinstance(expr, ast.BinaryOp):
            if expr.op == "=":
                if not isinstance(expr.left, ast.Identifier):
                    raise Exception(f"{loc}: expected identifier on left of '='")
                var_target = st.require(expr.left.name)
                var_value = visit(st, expr.right)
                ins.append(ir.Copy(loc, var_value, var_target))
                return var_value

            if expr.op in ["and", "or"]:
                l_left_true = new_label()
                l_left_false = new_label()
                l_end = new_label()
                var_result = new_var()

                var_left = visit(st, expr.left)
                ins.append(ir.CondJump(loc, var_left, l_left_true, l_left_false))

                if expr.op == "and":
                    ins.append(l_left_true)
                    var_right = visit(st, expr.right)
                    ins.append(ir.Copy(loc, var_right, var_result))
                    ins.append(ir.Jump(loc, l_end))

                    ins.append(l_left_false)
                    ins.append(ir.LoadBoolConst(loc, False, var_result))
                    ins.append(ir.Jump(loc, l_end))
                else:
                    ins.append(l_left_true)
                    ins.append(ir.LoadBoolConst(loc, True, var_result))
                    ins.append(ir.Jump(loc, l_end))

                    ins.append(l_left_false)
                    var_right = visit(st, expr.right)
                    ins.append(ir.Copy(loc, var_right, var_result))
                    ins.append(ir.Jump(loc, l_end))

                ins.append(l_end)
                return var_result

            var_op = st.require(expr.op)
            var_left = visit(st, expr.left)
            var_right = visit(st, expr.right)
            var_result = new_var()
            ins.append(ir.Call(loc, var_op, [var_left, var_right], var_result))
            return var_result

        if isinstance(expr, ast.UnaryOp):
            var_op = st.require(f"unary_{expr.op}")
            var_value = visit(st, expr.expr)
            var_result = new_var()
            ins.append(ir.Call(loc, var_op, [var_value], var_result))
            return var_result

        if isinstance(expr, ast.If):
            l_then = new_label()
            l_else = new_label()
            l_end = new_label()
            var_result = new_var()

            var_cond = visit(st, expr.condition)
            if expr.else_branch is None:
                ins.append(ir.CondJump(loc, var_cond, l_then, l_end))
                ins.append(l_then)
                visit(st, expr.then_branch)
                ins.append(ir.Jump(loc, l_end))
                ins.append(l_end)
                return var_unit

            ins.append(ir.CondJump(loc, var_cond, l_then, l_else))
            ins.append(l_then)
            var_then = visit(st, expr.then_branch)
            ins.append(ir.Copy(loc, var_then, var_result))
            ins.append(ir.Jump(loc, l_end))

            ins.append(l_else)
            var_else = visit(st, expr.else_branch)
            ins.append(ir.Copy(loc, var_else, var_result))
            ins.append(ir.Jump(loc, l_end))

            ins.append(l_end)
            return var_result

        if isinstance(expr, ast.While):
            l_cond = new_label()
            l_body = new_label()
            l_end = new_label()

            ins.append(ir.Jump(loc, l_cond))
            ins.append(l_cond)
            var_cond = visit(st, expr.condition)
            ins.append(ir.CondJump(loc, var_cond, l_body, l_end))

            ins.append(l_body)
            visit(st, expr.body)
            ins.append(ir.Jump(loc, l_cond))

            ins.append(l_end)
            return var_unit

        if isinstance(expr, ast.Call):
            var_fun = visit(st, expr.callee)
            args = [visit(st, arg) for arg in expr.args]
            var_result = new_var()
            ins.append(ir.Call(loc, var_fun, args, var_result))
            return var_result

        if isinstance(expr, ast.Block):
            child = SymTab(st)
            result = var_unit
            for e in expr.expressions:
                result = visit(child, e)
            return result

        raise Exception(f"{loc}: unknown expression")

    root_symtab = SymTab[ir.IRVar](parent=None)
    for name in reserved_names:
        root_symtab.add_local(name, ir.IRVar(name))

    var_final_result = visit(root_symtab, root_expr)

    if root_expr.type == Int:
        var_print = root_symtab.require("print_int")
        var_result = new_var()
        ins.append(ir.Call(root_expr.location, var_print, [var_final_result], var_result))
    elif root_expr.type == Bool:
        var_print = root_symtab.require("print_bool")
        var_result = new_var()
        ins.append(ir.Call(root_expr.location, var_print, [var_final_result], var_result))

    return ins
