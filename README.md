# HY Compilers – Spring 2026 Project (Python)

A compiler for the course project language, implemented in Python. The compiler is packaged as a Docker image that exposes a TCP server (port 3000) used by the course Test Gadget.

## What it does
Pipeline:
- Tokenizer (lexer)
- Parser (builds AST)
- Type checker
- IR generation
- x86_64 Linux code generation (assembly / executable)
