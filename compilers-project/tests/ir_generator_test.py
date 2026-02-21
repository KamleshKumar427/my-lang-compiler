import compiler.ast as ast
from compiler.ir_generator import generate_ir
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import create_global_symtab, typecheck


def test_ir_smoke() -> None:
    expr = parse(tokenize("1 + 2 * 3"))
    typecheck(expr)
    reserved = set(create_global_symtab().locals.keys())
    ins = generate_ir(reserved, expr)
    assert len(ins) > 0
    assert any(type(i).__name__ == "Call" for i in ins)