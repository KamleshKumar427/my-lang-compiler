from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int


@dataclass(frozen=True)
class Token:
    loc: SourceLocation
    type: str
    text: str


def _advance_position(text: str, line: int, column: int) -> tuple[int, int]:
    if "\n" not in text:
        return line, column + len(text)
    lines = text.split("\n")
    line += len(lines) - 1
    column = len(lines[-1]) + 1
    return line, column


def tokenize(source_code: str) -> list[Token]:
    whitespace_re = re.compile(r"[ \t\r\n]+")
    comment_slash_re = re.compile(r"//[^\n]*")
    comment_hash_re = re.compile(r"#[^\n]*")
    identifier_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    int_re = re.compile(r"[0-9]+")
    operator_re = re.compile(r"==|!=|<=|>=|[+\-*/%]|=|[<>]")
    punctuation_re = re.compile(r"[(){};,]")

    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1

    while i < len(source_code):
        chunk = source_code[i:]

        m = whitespace_re.match(chunk)
        if m is not None:
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = comment_slash_re.match(chunk)
        if m is not None:
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = comment_hash_re.match(chunk)
        if m is not None:
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = identifier_re.match(chunk)
        if m is not None:
            tokens.append(Token(SourceLocation(line, column), "identifier", m.group(0)))
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = int_re.match(chunk)
        if m is not None:
            tokens.append(Token(SourceLocation(line, column), "int_literal", m.group(0)))
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = operator_re.match(chunk)
        if m is not None:
            tokens.append(Token(SourceLocation(line, column), "operator", m.group(0)))
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        m = punctuation_re.match(chunk)
        if m is not None:
            tokens.append(Token(SourceLocation(line, column), "punctuation", m.group(0)))
            line, column = _advance_position(m.group(0), line, column)
            i += m.end()
            continue

        snippet = chunk[:10].replace("\n", "\\n")
        raise Exception(f"Unexpected character at {line}:{column}: '{snippet}'")

    return tokens
