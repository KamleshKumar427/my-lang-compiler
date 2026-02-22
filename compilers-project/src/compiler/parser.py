from __future__ import annotations

from compiler.tokenizer import SourceLocation, Token
import compiler.ast as ast
import compiler.types as types


left_associative_binary_operators: list[list[str]] = [
    ["or"],
    ["and"],
    ["==", "!="],
    ["<", "<=", ">", ">="],
    ["+", "-"],
    ["*", "/", "%"],
]


def parse(tokens: list[Token]) -> ast.Module:
    pos = 0
    end_loc = tokens[-1].loc if tokens else SourceLocation(1, 1)
    reserved_idents = {
        "and",
        "break",
        "continue",
        "do",
        "else",
        "fun",
        "if",
        "or",
        "return",
        "then",
        "var",
        "while",
    }

    def peek() -> Token:
        if pos < len(tokens):
            return tokens[pos]
        return Token(end_loc, "end", "")

    def consume(expected: str | list[str] | None = None) -> Token:
        nonlocal pos
        token = peek()
        if isinstance(expected, str) and token.text != expected:
            raise Exception(f'{token.loc}: expected "{expected}"')
        if isinstance(expected, list) and token.text not in expected:
            comma_separated = ", ".join([f'"{e}"' for e in expected])
            raise Exception(f"{token.loc}: expected one of: {comma_separated}")
        pos += 1
        return token

    def starts_expression(token: Token) -> bool:
        if token.text in ["if", "while", "{", "("]:
            return True
        if token.type == "int_literal":
            return True
        if token.type == "identifier" and token.text not in reserved_idents:
            return True
        if token.text in ["true", "false"]:
            return True
        return False

    def parse_expression(allow_var: bool) -> ast.Expression:
        if allow_var and peek().text == "var":
            return parse_var_declaration()
        return parse_assignment()

    def parse_var_declaration() -> ast.Expression:
        var_token = consume("var")
        name_token = peek()
        if name_token.type != "identifier":
            raise Exception(f"{name_token.loc}: expected an identifier")
        name_token = consume()
        declared_type: types.Type | None = None
        if peek().text == ":":
            consume(":")
            declared_type = parse_type()
        consume("=")
        value = parse_expression(False)
        return ast.VarDeclaration(var_token.loc, name_token.text, value, declared_type)

    def parse_assignment() -> ast.Expression:
        left = parse_left_associative(0)
        if peek().text == "=":
            op_token = consume("=")
            right = parse_assignment()
            return ast.BinaryOp(op_token.loc, left, op_token.text, right)
        return left

    def parse_left_associative(level: int) -> ast.Expression:
        if level == len(left_associative_binary_operators):
            return parse_unary()
        left = parse_left_associative(level + 1)
        while peek().text in left_associative_binary_operators[level]:
            op_token = consume()
            right = parse_left_associative(level + 1)
            left = ast.BinaryOp(op_token.loc, left, op_token.text, right)
        return left

    def parse_unary() -> ast.Expression:
        if peek().text in ["-", "not"]:
            op_token = consume()
            expr = parse_unary()
            return ast.UnaryOp(op_token.loc, op_token.text, expr)
        return parse_postfix()

    def parse_postfix() -> ast.Expression:
        expr = parse_primary()
        while peek().text == "(":
            consume("(")
            args: list[ast.Expression] = []
            if peek().text != ")":
                args.append(parse_expression(False))
                while peek().text == ",":
                    consume(",")
                    args.append(parse_expression(False))
            consume(")")
            expr = ast.Call(expr.location, expr, args)
        return expr

    def parse_primary() -> ast.Expression:
        token = peek()
        if token.text == "return":
            return parse_return()
        if token.text == "break":
            return parse_break()
        if token.text == "continue":
            return parse_continue()
        if token.text == "if":
            return parse_if()
        if token.text == "while":
            return parse_while()
        if token.text == "{":
            return parse_block()
        if token.text == "(":
            return parse_parenthesized()
        if token.type == "int_literal":
            token = consume()
            return ast.Literal(token.loc, int(token.text))
        if token.type == "identifier":
            if token.text == "true":
                consume()
                return ast.Literal(token.loc, True)
            if token.text == "false":
                consume()
                return ast.Literal(token.loc, False)
            if token.text in reserved_idents:
                raise Exception(f"{token.loc}: expected expression")
            token = consume()
            return ast.Identifier(token.loc, token.text)
        raise Exception(f"{token.loc}: expected expression")

    def parse_type() -> types.Type:
        token = peek()
        if token.text == "(":
            consume("(")
            params: list[types.Type] = []
            if peek().text != ")":
                params.append(parse_type())
                while peek().text == ",":
                    consume(",")
                    params.append(parse_type())
            consume(")")
            consume("=>")
            ret = parse_type()
            return types.FunType(params, ret)
        if token.text == "Int":
            consume()
            return types.Int
        if token.text == "Bool":
            consume()
            return types.Bool
        if token.text == "Unit":
            consume()
            return types.Unit
        raise Exception(f"{token.loc}: expected type")

    def parse_parenthesized() -> ast.Expression:
        consume("(")
        expr = parse_expression(False)
        consume(")")
        return expr

    def parse_if() -> ast.Expression:
        if_token = consume("if")
        condition = parse_expression(False)
        consume("then")
        then_branch = parse_expression(False)
        else_branch: ast.Expression | None = None
        if peek().text == "else":
            consume("else")
            else_branch = parse_expression(False)
        return ast.If(if_token.loc, condition, then_branch, else_branch)

    def parse_while() -> ast.Expression:
        while_token = consume("while")
        condition = parse_expression(False)
        consume("do")
        body = parse_expression(False)
        return ast.While(while_token.loc, condition, body)

    def parse_return() -> ast.Expression:
        token = consume("return")
        value: ast.Expression | None = None
        if starts_expression(peek()):
            value = parse_expression(False)
        return ast.Return(token.loc, value)

    def parse_break() -> ast.Expression:
        token = consume("break")
        value: ast.Expression | None = None
        if starts_expression(peek()):
            value = parse_expression(False)
        return ast.Break(token.loc, value)

    def parse_continue() -> ast.Expression:
        token = consume("continue")
        return ast.Continue(token.loc)

    def parse_block() -> ast.Expression:
        lbrace = consume("{")
        expressions: list[ast.Expression] = []
        if peek().text == "}":
            consume("}")
            expressions.append(ast.Literal(lbrace.loc, None))
            return ast.Block(lbrace.loc, expressions)
        while True:
            expressions.append(parse_expression(True))
            if peek().text == ";":
                semi = consume(";")
                if peek().text == "}":
                    consume("}")
                    expressions.append(ast.Literal(semi.loc, None))
                    return ast.Block(lbrace.loc, expressions)
                continue
            if peek().text == "}":
                consume("}")
                return ast.Block(lbrace.loc, expressions)
            if tokens[pos - 1].text == "}":
                continue
            raise Exception(f"{peek().loc}: expected '{{' or '}}'")

    def parse_function_def() -> ast.FunctionDef:
        fun_token = consume("fun")
        name_token = peek()
        if name_token.type != "identifier":
            raise Exception(f"{name_token.loc}: expected an identifier")
        name_token = consume()
        if name_token.text in reserved_idents:
            raise Exception(f"{name_token.loc}: expected an identifier")
        consume("(")
        params: list[ast.FunctionParam] = []
        if peek().text != ")":
            while True:
                param_name = peek()
                if param_name.type != "identifier":
                    raise Exception(f"{param_name.loc}: expected an identifier")
                param_name = consume()
                consume(":")
                param_type = parse_type()
                params.append(ast.FunctionParam(param_name.text, param_type))
                if peek().text == ",":
                    consume(",")
                    continue
                break
        consume(")")
        consume(":")
        ret_type = parse_type()
        body = parse_block()
        return ast.FunctionDef(fun_token.loc, name_token.text, params, ret_type, body)

    def parse_module() -> ast.Module:
        if peek().type == "end":
            raise Exception(f"{peek().loc}: expected expression")
        module_loc = peek().loc
        functions: list[ast.FunctionDef] = []
        expressions: list[ast.Expression] = []
        while True:
            if peek().type == "end":
                break
            if peek().text == "fun":
                functions.append(parse_function_def())
                continue
            expressions.append(parse_expression(True))
            if peek().text == ";":
                semi = consume(";")
                if peek().type == "end":
                    expressions.append(ast.Literal(semi.loc, None))
                    break
                continue
            if peek().type == "end":
                break
            if tokens[pos - 1].text == "}":
                continue
            if peek().text == "fun" and tokens[pos - 1].text == "}":
                continue
            raise Exception(f"{peek().loc}: expected ';' or end of input")
        return ast.Module(module_loc, functions, expressions)

    result = parse_module()
    if peek().type != "end":
        raise Exception(f"{peek().loc}: unexpected input")
    return result
