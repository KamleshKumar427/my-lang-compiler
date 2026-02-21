import pytest

import compiler.types as types
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import typecheck


def tc(source: str) -> types.Type:
    return typecheck(parse(tokenize(source)))


def test_typecheck_literals_and_ops() -> None:
    assert tc("1 + 2") is types.Int
    assert tc("true and false") is types.Bool


def test_typecheck_if_and_while() -> None:
    assert tc("if true then 1 else 2") is types.Int
    assert tc("while true do { }") is types.Unit


def test_typecheck_vars_and_assignment() -> None:
    assert tc("{ var x = 1; x }") is types.Int
    assert tc("{ var x: Int = 1; x }") is types.Int
    with pytest.raises(Exception):
        tc("{ var x: Bool = 1; x }")
    with pytest.raises(Exception):
        tc("{ var x = 1; x = true }")


def test_typecheck_calls_and_fun_types() -> None:
    assert tc("print_int(1)") is types.Unit
    assert tc("{ var f: (Int) => Unit = print_int; f(123) }") is types.Unit
    with pytest.raises(Exception):
        tc("print_int(true)")


def test_typecheck_errors() -> None:
    with pytest.raises(Exception):
        tc("1 == true")
    with pytest.raises(Exception):
        tc("if true then 1")