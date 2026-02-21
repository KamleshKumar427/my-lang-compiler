import compiler.ast as ast
from compiler.interpreter import SymTab, create_global_symtab, interpret
from compiler.parser import parse
from compiler.tokenizer import tokenize


def eval_source(source: str, symtab: SymTab | None = None) -> object:
    if symtab is None:
        symtab = create_global_symtab()
    return interpret(parse(tokenize(source)), symtab)


def test_interpreter_basics() -> None:
    assert eval_source("2 + 3") == 5


def test_blocks_and_shadowing() -> None:
    assert eval_source("{ var x = 1; { var x = 2; x }; x }") == 1


def test_assignment_and_while() -> None:
    source = "{ var x = 0; while x < 3 do { x = x + 1; }; x }"
    assert eval_source(source) == 3


def test_short_circuit_or() -> None:
    source = "{ var rhs = false; true or { rhs = true; true }; rhs }"
    assert eval_source(source) is False


def test_call_with_custom_function() -> None:
    symtab = create_global_symtab()
    symtab.define("f", lambda args: args[0] + 1)  # type: ignore[operator]
    assert eval_source("f(10)", symtab) == 11