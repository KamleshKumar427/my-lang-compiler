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

    movq $0, %rax
    movq $0, %rdi
    movq $read_buf, %rsi
    movq $64, %rdx
    syscall
    cmpq $0, %rax
    jle .Lri_zero

    movq %rax, %rcx
    movq $read_buf, %rsi
    movq $0, %r9
    movq $1, %r8

.Lri_skip:
    cmpq $0, %rcx
    je .Lri_done
    movzbq (%rsi), %rax
    cmpb $32, %al
    je .Lri_adv
    cmpb $10, %al
    je .Lri_adv
    cmpb $9, %al
    je .Lri_adv
    cmpb $13, %al
    je .Lri_adv
    jmp .Lri_sign
.Lri_adv:
    incq %rsi
    decq %rcx
    jmp .Lri_skip

.Lri_sign:
    cmpb $45, %al
    jne .Lri_digits
    movq $-1, %r8
    incq %rsi
    decq %rcx

.Lri_digits:
    cmpq $0, %rcx
    je .Lri_done
    movzbq (%rsi), %rax
    cmpb $48, %al
    jl .Lri_done
    cmpb $57, %al
    jg .Lri_done
    imulq $10, %r9, %r9
    subb $48, %al
    movzbq %al, %rax
    addq %rax, %r9
    incq %rsi
    decq %rcx
    jmp .Lri_digits

.Lri_done:
    movq %r9, %rax
    cmpq $1, %r8
    je .Lri_ret
    negq %rax
.Lri_ret:
    movq %rbp, %rsp
    popq %rbp
    ret

.Lri_zero:
    movq $0, %rax
    movq %rbp, %rsp
    popq %rbp
    ret

.section .data
true_str:
    .asciz "true\n"
false_str:
    .asciz "false\n"

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