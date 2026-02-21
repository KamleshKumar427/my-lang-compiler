import pytest

import compiler.ast as ast
import compiler.types as types
from compiler.parser import parse
from compiler.tokenizer import SourceLocation, tokenize


def shape_type(t: types.Type | None) -> object:
    if t is None:
        return None
    if t is types.Int:
        return "Int"
    if t is types.Bool:
        return "Bool"
    if t is types.Unit:
        return "Unit"
    if isinstance(t, types.FunType):
        return ("fun", [shape_type(p) for p in t.params], shape_type(t.return_type))
    raise AssertionError("unknown type")


def shape(expr: ast.Expression) -> object:
    if isinstance(expr, ast.Literal):
        return ("lit", expr.value)
    if isinstance(expr, ast.Identifier):
        return ("id", expr.name)
    if isinstance(expr, ast.BinaryOp):
        return ("bin", expr.op, shape(expr.left), shape(expr.right))
    if isinstance(expr, ast.UnaryOp):
        return ("un", expr.op, shape(expr.expr))
    if isinstance(expr, ast.If):
        return (
            "if",
            shape(expr.condition),
            shape(expr.then_branch),
            None if expr.else_branch is None else shape(expr.else_branch),
        )
    if isinstance(expr, ast.While):
        return ("while", shape(expr.condition), shape(expr.body))
    if isinstance(expr, ast.Call):
        return ("call", shape(expr.callee), [shape(a) for a in expr.args])
    if isinstance(expr, ast.Block):
        return ("block", [shape(e) for e in expr.expressions])
    if isinstance(expr, ast.VarDeclaration):
        return ("var", expr.name, shape_type(expr.declared_type), shape(expr.value))
    raise AssertionError("unknown node type")


def parse_shape(source: str) -> object:
    return shape(parse(tokenize(source)))


def test_precedence_and_associativity() -> None:
    assert parse_shape("a + b * c") == (
        "bin",
        "+",
        ("id", "a"),
        ("bin", "*", ("id", "b"), ("id", "c")),
    )
    assert parse_shape("(a + b) * c") == (
        "bin",
        "*",
        ("bin", "+", ("id", "a"), ("id", "b")),
        ("id", "c"),
    )
    assert parse_shape("1 - 2 + 3") == (
        "bin",
        "+",
        ("bin", "-", ("lit", 1), ("lit", 2)),
        ("lit", 3),
    )
    assert parse_shape("a = b = c") == (
        "bin",
        "=",
        ("id", "a"),
        ("bin", "=", ("id", "b"), ("id", "c")),
    )


def test_if_and_calls() -> None:
    assert parse_shape("if a then b else c") == (
        "if",
        ("id", "a"),
        ("id", "b"),
        ("id", "c"),
    )
    assert parse_shape("if a then b") == ("if", ("id", "a"), ("id", "b"), None)
    assert parse_shape("1 + if true then 2 else 3") == (
        "bin",
        "+",
        ("lit", 1),
        ("if", ("lit", True), ("lit", 2), ("lit", 3)),
    )
    assert parse_shape("f(x, y + 1)") == (
        "call",
        ("id", "f"),
        [("id", "x"), ("bin", "+", ("id", "y"), ("lit", 1))],
    )


def test_unary_and_while() -> None:
    assert parse_shape("not not x") == ("un", "not", ("un", "not", ("id", "x")))
    assert parse_shape("-x * 2") == (
        "bin",
        "*",
        ("un", "-", ("id", "x")),
        ("lit", 2),
    )
    assert parse_shape("while a do b") == ("while", ("id", "a"), ("id", "b"))


def test_blocks_and_var() -> None:
    assert parse_shape("{ a; }") == ("block", [("id", "a"), ("lit", None)])
    assert parse_shape("{ { a } { b } }") == (
        "block",
        [("block", [("id", "a")]), ("block", [("id", "b")])],
    )
    assert parse_shape("{ var x = 1; x }") == (
        "block",
        [("var", "x", None, ("lit", 1)), ("id", "x")],
    )
    assert parse_shape("{ var f: (Int) => Unit = print_int; f(123) }") == (
        "block",
        [
            (
                "var",
                "f",
                ("fun", ["Int"], "Unit"),
                ("id", "print_int"),
            ),
            ("call", ("id", "f"), [("lit", 123)]),
        ],
    )


def test_top_level_sequences() -> None:
    assert parse_shape("a; b") == ("block", [("id", "a"), ("id", "b")])
    assert parse_shape("a;") == ("block", [("id", "a"), ("lit", None)])


def test_locations() -> None:
    expr = parse(tokenize("abc"))
    assert expr.location == SourceLocation(1, 1)


def test_errors() -> None:
    with pytest.raises(Exception):
        parse(tokenize(""))
    with pytest.raises(Exception):
        parse(tokenize("a b"))
    with pytest.raises(Exception):
        parse(tokenize("{ a b }"))
    with pytest.raises(Exception):
        parse(tokenize("if true then var x = 1 else 2"))
