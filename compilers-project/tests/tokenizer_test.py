from compiler.tokenizer import Token, SourceLocation, tokenize


def tok_texts(source: str) -> list[str]:
    return [t.text for t in tokenize(source)]


def test_tokenizer_basics() -> None:
    assert tok_texts("if  3\nwhile") == ["if", "3", "while"]
    assert tok_texts("a<=b") == ["a", "<=", "b"]
    assert tok_texts("x=1+2*3") == ["x", "=", "1", "+", "2", "*", "3"]
    assert tok_texts("print_int(123);") == ["print_int", "(", "123", ")", ";"]
    assert tok_texts("a//c\nb") == ["a", "b"]
    assert tok_texts("a#c\nb") == ["a", "b"]


def test_token_locations_and_types() -> None:
    tokens = tokenize("abc")
    assert tokens == [Token(SourceLocation(1, 1), "identifier", "abc")]

    tokens = tokenize("a\nb")
    assert tokens[1].loc == SourceLocation(2, 1)

    tokens = tokenize("x=10")
    assert [t.type for t in tokens] == ["identifier", "operator", "int_literal"]