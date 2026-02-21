from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from compiler.__main__ import call_compiler


def _load_test_cases() -> list[tuple[str, str, list[str], list[str]]]:
    base = Path(__file__).resolve().parents[1] / "test_programs"
    if not base.exists():
        return []
    cases: list[tuple[str, str, list[str], list[str]]] = []
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        content = path.read_text().splitlines()
        current: list[str] = []
        groups: list[list[str]] = []
        for line in content:
            if line.strip() == "---":
                groups.append(current)
                current = []
            else:
                current.append(line)
        groups.append(current)

        for idx, lines in enumerate(groups):
            inputs: list[str] = []
            outputs: list[str] = []
            program_lines: list[str] = []
            for line in lines:
                if line.startswith("input "):
                    inputs.append(line[len("input ") :])
                elif line.startswith("prints "):
                    outputs.append(line[len("prints ") :])
                else:
                    program_lines.append(line)
            program = "\n".join(program_lines)
            name = f"{path.stem}_{idx}"
            cases.append((name, program, inputs, outputs))
    return cases


def _run_case(program: str, inputs: list[str], outputs: list[str]) -> None:
    exe_bytes = call_compiler(program, "(test)")
    with tempfile.TemporaryDirectory() as tmp:
        exe_path = Path(tmp) / "program"
        exe_path.write_bytes(exe_bytes)
        os.chmod(exe_path, 0o755)
        input_data = "\n".join(inputs)
        if input_data:
            input_data += "\n"
        result = subprocess.run(
            [str(exe_path)],
            input=input_data,
            text=True,
            capture_output=True,
            check=True,
        )
        stdout_lines = result.stdout.splitlines()
        assert stdout_lines == outputs


for name, program, inputs, outputs in _load_test_cases():
    def _make_test(p: str, i: list[str], o: list[str]) -> Callable[[], None]:
        def _test() -> None:
            _run_case(p, i, o)

        return _test

    globals()[f"test_{name}"] = _make_test(program, inputs, outputs)
