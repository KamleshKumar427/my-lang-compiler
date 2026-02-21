from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


RUNTIME_ASM = r'''
.section .text
.global _start
.global print_int
.global print_bool
.global read_int

_start:
    callq main
    movq %rax, %rdi
    movq $60, %rax
    syscall

print_int:
    pushq %rbp
    movq %rsp, %rbp
    subq $32, %rsp

    movabsq $0x8000000000000000, %r11
    cmpq %r11, %rdi
    jne .Lpi_start
    movq $minint_str, %rsi
    movq $20, %rdx
    movq $1, %rax
    movq $1, %rdi
    syscall
    jmp .Lpi_done

.Lpi_start:
    movq %rdi, %rax
    movq $0, %rcx
    leaq -1(%rbp), %rsi

    movq $0, %r8
    cmpq $0, %rax
    jge .Lpi_positive
    negq %rax
    movq $1, %r8
.Lpi_positive:
    cmpq $0, %rax
    jne .Lpi_loop
    movb $48, (%rsi)
    decq %rsi
    incq %rcx
    jmp .Lpi_after_digits

.Lpi_loop:
    movq $10, %r10
.Lpi_digit:
    cqto
    idivq %r10
    addb $48, %dl
    movb %dl, (%rsi)
    decq %rsi
    incq %rcx
    cmpq $0, %rax
    jne .Lpi_digit

.Lpi_after_digits:
    cmpq $0, %r8
    je .Lpi_no_sign
    movb $45, (%rsi)
    decq %rsi
    incq %rcx
.Lpi_no_sign:
    leaq 1(%rsi), %rsi
    movq $1, %rax
    movq $1, %rdi
    movq %rcx, %rdx
    syscall

    movb $10, -32(%rbp)
    movq $1, %rax
    movq $1, %rdi
    leaq -32(%rbp), %rsi
    movq $1, %rdx
    syscall

.Lpi_done:
    movq %rbp, %rsp
    popq %rbp
    movq $0, %rax
    ret

print_bool:
    pushq %rbp
    movq %rsp, %rbp

    cmpq $0, %rdi
    jne .Lpb_true
    movq $false_str, %rsi
    movq $6, %rdx
    jmp .Lpb_print
.Lpb_true:
    movq $true_str, %rsi
    movq $5, %rdx
.Lpb_print:
    movq $1, %rax
    movq $1, %rdi
    syscall

    movq %rbp, %rsp
    popq %rbp
    movq $0, %rax
    ret

read_int:
    pushq %rbp
    movq %rsp, %rbp
    movq $0, %r9
    movq $1, %r8

.Lri_skip:
    movq $0, %rax
    movq $0, %rdi
    leaq read_buf(%rip), %rsi
    movq $1, %rdx
    syscall
    cmpq $1, %rax
    jne .Lri_eof
    movzbq read_buf(%rip), %rcx
    cmpb $32, %cl
    je .Lri_skip
    cmpb $10, %cl
    je .Lri_skip
    cmpb $9, %cl
    je .Lri_skip
    cmpb $13, %cl
    je .Lri_skip
    cmpb $45, %cl
    jne .Lri_digit_loop
    movq $-1, %r8

.Lri_read_after_sign:
    movq $0, %rax
    movq $0, %rdi
    leaq read_buf(%rip), %rsi
    movq $1, %rdx
    syscall
    cmpq $1, %rax
    jne .Lri_eof
    movzbq read_buf(%rip), %rcx

.Lri_digit_loop:
    cmpb $48, %cl
    jl .Lri_done
    cmpb $57, %cl
    jg .Lri_done
    imulq $10, %r9, %r9
    subb $48, %cl
    movzbq %cl, %rax
    addq %rax, %r9
    movq $0, %rax
    movq $0, %rdi
    leaq read_buf(%rip), %rsi
    movq $1, %rdx
    syscall
    cmpq $1, %rax
    jne .Lri_done
    movzbq read_buf(%rip), %rcx
    jmp .Lri_digit_loop

.Lri_done:
    movq %r9, %rax
    cmpq $1, %r8
    je .Lri_ret
    negq %rax
.Lri_ret:
    movq %rbp, %rsp
    popq %rbp
    ret

.Lri_eof:
    movq $0, %rax
    movq %rbp, %rsp
    popq %rbp
    ret

.section .data
true_str:
    .asciz "true\n"
false_str:
    .asciz "false\n"
minint_str:
    .asciz "-9223372036854775808\n"

.section .bss
read_buf:
    .skip 64
'''


def assemble_and_get_executable(code: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        asm_path = tmp_path / "program.s"
        obj_path = tmp_path / "program.o"
        exe_path = tmp_path / "program"

        asm_path.write_text(code + "\n" + RUNTIME_ASM)

        subprocess.run(["as", "-o", str(obj_path), str(asm_path)], check=True)
        subprocess.run(["ld", "-o", str(exe_path), str(obj_path)], check=True)

        return exe_path.read_bytes()
