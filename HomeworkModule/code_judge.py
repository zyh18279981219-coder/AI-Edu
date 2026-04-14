from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Set


def _collect_top_imports(code: str) -> Set[str]:
    modules: Set[str] = set()
    try:
        tree = ast.parse(code)
    except Exception:
        return modules
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _missing_modules(code: str) -> List[str]:
    missing: List[str] = []
    for module in sorted(_collect_top_imports(code)):
        if module in {"__future__"}:
            continue
        try:
            spec = importlib.util.find_spec(module)
        except Exception:
            spec = None
        if spec is None:
            missing.append(module)
    return missing


def run_python_code_judge(code: str, test_cases: List[Dict[str, Any]], timeout_seconds: int = 3) -> Dict[str, Any]:
    if not str(code or "").strip():
        return {
            "passed": 0,
            "total": len(test_cases),
            "pass_rate": 0.0,
            "details": [
                {"case": i + 1, "ok": False, "error": "empty_code"}
                for i in range(len(test_cases))
            ],
        }

    missing = _missing_modules(code)
    if missing:
        details = []
        for idx, case in enumerate(test_cases):
            details.append(
                {
                    "case": idx + 1,
                    "ok": False,
                    "input": str(case.get("input", "")),
                    "expected": str(case.get("expected", case.get("output", ""))).strip(),
                    "actual": "",
                    "stderr": f"评测环境缺少依赖: {', '.join(missing)}",
                    "return_code": -2,
                    "error": "missing_dependency",
                }
            )
        return {
            "passed": 0,
            "total": len(test_cases),
            "pass_rate": 0.0,
            "details": details,
            "missing_modules": missing,
        }

    passed = 0
    details: List[Dict[str, Any]] = []
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=True, encoding="utf-8") as fp:
        fp.write(code)
        fp.flush()

        for idx, case in enumerate(test_cases):
            case_input = str(case.get("input", ""))
            expected = str(case.get("expected", case.get("output", ""))).strip()
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", fp.name],
                    input=case_input,
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                )
                actual = (proc.stdout or "").strip()
                stderr = (proc.stderr or "").strip()
                ok = proc.returncode == 0 and actual == expected
                if ok:
                    passed += 1
                details.append(
                    {
                        "case": idx + 1,
                        "ok": ok,
                        "input": case_input,
                        "expected": expected,
                        "actual": actual,
                        "stderr": stderr,
                        "return_code": proc.returncode,
                    }
                )
            except subprocess.TimeoutExpired:
                details.append(
                    {
                        "case": idx + 1,
                        "ok": False,
                        "input": case_input,
                        "expected": expected,
                        "actual": "",
                        "stderr": f"timeout>{timeout_seconds}s",
                        "return_code": -1,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                details.append(
                    {
                        "case": idx + 1,
                        "ok": False,
                        "input": case_input,
                        "expected": expected,
                        "actual": "",
                        "stderr": str(exc),
                        "return_code": -3,
                        "error": "sandbox_error",
                    }
                )

    total = len(test_cases)
    pass_rate = (passed / total) if total else 0.0
    return {
        "passed": passed,
        "total": total,
        "pass_rate": pass_rate,
        "details": details,
    }
