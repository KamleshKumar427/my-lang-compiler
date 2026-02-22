import compiler.ast as ast
from compiler.ir_generator import generate_ir
from compiler.parser import parse
from compiler.tokenizer import tokenize
from compiler.type_checker import create_global_symtab, typecheck


def test_ir_smoke() -> None:
    module = parse(tokenize("1 + 2 * 3"))
    typecheck(module)
    reserved = set(create_global_symtab().locals.keys())
    functions = generate_ir(reserved, module)
    ins = functions["main"]
    assert len(ins) > 0
    assert any(type(i).__name__ == "Call" for i in ins)
