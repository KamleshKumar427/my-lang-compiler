from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar

import compiler.ir as ir

State = TypeVar("State")

UNINITIALIZED = -1
PREDEFINED = -2


@dataclass(frozen=True)
class FlowGraph:
    instructions: list[ir.Instruction]
    succs: dict[int, set[int]]
    preds: dict[int, set[int]]
    label_to_index: dict[str, int]

    def instruction(self, index: int) -> ir.Instruction:
        return self.instructions[index]


def build_flowgraph(instructions: list[ir.Instruction]) -> FlowGraph:
    label_to_index: dict[str, int] = {}
    for i, insn in enumerate(instructions):
        if isinstance(insn, ir.Label):
            label_to_index[insn.name] = i

    succs: dict[int, set[int]] = {i: set() for i in range(len(instructions))}
    for i, insn in enumerate(instructions):
        if isinstance(insn, ir.Jump):
            target = label_to_index[insn.label.name]
            succs[i].add(target)
        elif isinstance(insn, ir.CondJump):
            succs[i].add(label_to_index[insn.then_label.name])
            succs[i].add(label_to_index[insn.else_label.name])
        else:
            if i + 1 < len(instructions):
                succs[i].add(i + 1)

    preds: dict[int, set[int]] = {i: set() for i in range(len(instructions))}
    for i, nexts in succs.items():
        for j in nexts:
            preds[j].add(i)

    return FlowGraph(instructions=instructions, succs=succs, preds=preds, label_to_index=label_to_index)


def flowgraph_to_dot(graph: FlowGraph) -> str:
    lines: list[str] = ["digraph flowgraph {"]
    for i, insn in enumerate(graph.instructions):
        label = f"{i}: {insn}".replace("\"", "\\\"")
        lines.append(f'  n{i} [label="{label}"];')
    for i, nexts in graph.succs.items():
        for j in nexts:
            lines.append(f"  n{i} -> n{j};")
    lines.append("}")
    return "\n".join(lines)


def forward_dataflow(
    graph: FlowGraph,
    initial_in0: State,
    initial_state: Callable[[], State],
    transfer: Callable[[State, ir.Instruction, int], State],
    merge: Callable[[Iterable[State]], State],
) -> tuple[dict[int, State], dict[int, State]]:
    n = len(graph.instructions)
    in_states: dict[int, State] = {i: initial_state() for i in range(n)}
    out_states: dict[int, State] = {i: initial_state() for i in range(n)}
    if n == 0:
        return in_states, out_states

    in_states[0] = initial_in0
    out_states[0] = transfer(initial_in0, graph.instructions[0], 0)

    work = deque(range(1, n))
    while work:
        i = work.popleft()
        pred_states = [out_states[p] for p in graph.preds.get(i, set())]
        new_in = merge(pred_states) if pred_states else initial_state()
        new_out = transfer(new_in, graph.instructions[i], i)
        if new_in != in_states[i] or new_out != out_states[i]:
            in_states[i] = new_in
            out_states[i] = new_out
            for s in graph.succs.get(i, set()):
                work.append(s)

    return in_states, out_states


def backward_dataflow(
    graph: FlowGraph,
    initial_out_last: State,
    initial_state: Callable[[], State],
    transfer: Callable[[State, ir.Instruction, int], State],
    merge: Callable[[Iterable[State]], State],
) -> tuple[dict[int, State], dict[int, State]]:
    n = len(graph.instructions)
    in_states: dict[int, State] = {i: initial_state() for i in range(n)}
    out_states: dict[int, State] = {i: initial_state() for i in range(n)}
    if n == 0:
        return in_states, out_states

    out_states[n - 1] = initial_out_last
    in_states[n - 1] = transfer(initial_out_last, graph.instructions[n - 1], n - 1)

    work = deque(range(0, n - 1))
    while work:
        i = work.popleft()
        succ_states = [in_states[s] for s in graph.succs.get(i, set())]
        new_out = merge(succ_states) if succ_states else initial_state()
        new_in = transfer(new_out, graph.instructions[i], i)
        if new_in != in_states[i] or new_out != out_states[i]:
            in_states[i] = new_in
            out_states[i] = new_out
            for p in graph.preds.get(i, set()):
                work.append(p)

    return in_states, out_states


def _instruction_uses_defs(insn: ir.Instruction) -> tuple[set[ir.IRVar], set[ir.IRVar]]:
    uses: set[ir.IRVar] = set()
    defs: set[ir.IRVar] = set()

    if isinstance(insn, ir.LoadBoolConst):
        defs.add(insn.dest)
    elif isinstance(insn, ir.LoadIntConst):
        defs.add(insn.dest)
    elif isinstance(insn, ir.Copy):
        uses.add(insn.source)
        defs.add(insn.dest)
    elif isinstance(insn, ir.Call):
        uses.add(insn.fun)
        uses.update(insn.args)
        defs.add(insn.dest)
    elif isinstance(insn, ir.CondJump):
        uses.add(insn.cond)

    return uses, defs


def reaching_definitions(
    instructions: list[ir.Instruction],
) -> tuple[dict[int, dict[ir.IRVar, set[int]]], dict[int, dict[ir.IRVar, set[int]]]]:
    graph = build_flowgraph(instructions)

    all_vars: set[ir.IRVar] = set()
    for insn in instructions:
        uses, defs = _instruction_uses_defs(insn)
        all_vars.update(uses)
        all_vars.update(defs)

    def empty_state() -> dict[ir.IRVar, set[int]]:
        return {v: set() for v in all_vars}

    initial_in0: dict[ir.IRVar, set[int]] = {}
    for v in all_vars:
        if v.name.startswith("x"):
            initial_in0[v] = {UNINITIALIZED}
        else:
            initial_in0[v] = {PREDEFINED}

    def transfer(s: dict[ir.IRVar, set[int]], insn: ir.Instruction, index: int) -> dict[ir.IRVar, set[int]]:
        _, defs = _instruction_uses_defs(insn)
        out = {v: set(defs_set) for v, defs_set in s.items()}
        for v in defs:
            out[v] = {index}
        return out

    def merge(states: Iterable[dict[ir.IRVar, set[int]]]) -> dict[ir.IRVar, set[int]]:
        merged = empty_state()
        for st in states:
            for v, defs_set in st.items():
                merged[v].update(defs_set)
        return merged

    return forward_dataflow(graph, initial_in0, empty_state, transfer, merge)


def live_variables(
    instructions: list[ir.Instruction],
) -> tuple[dict[int, set[ir.IRVar]], dict[int, set[ir.IRVar]]]:
    graph = build_flowgraph(instructions)

    def empty_state() -> set[ir.IRVar]:
        return set()

    def transfer(out_state: set[ir.IRVar], insn: ir.Instruction, index: int) -> set[ir.IRVar]:
        uses, defs = _instruction_uses_defs(insn)
        return (out_state - defs) | uses

    def merge(states: Iterable[set[ir.IRVar]]) -> set[ir.IRVar]:
        merged: set[ir.IRVar] = set()
        for st in states:
            merged |= st
        return merged

    return backward_dataflow(graph, set(), empty_state, transfer, merge)