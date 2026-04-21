from __future__ import annotations

import base64
from dataclasses import dataclass
import os
from typing import Any, Dict, List

import httpx
from tools.runtime_config import load_runtime_config


@dataclass
class SandboxLimits:
    cpu_limit_ns: int = 10_000_000_000
    memory_limit_bytes: int = 512 * 1024 * 1024
    proc_limit: int = 256
    output_max_bytes: int = 2 * 1024 * 1024


class SandboxService:
    """Encapsulates Go-Judge request construction and execution."""

    def __init__(self) -> None:
        runtime_config = load_runtime_config()
        oj_config = runtime_config.get("oj", {}) if isinstance(runtime_config.get("oj"), dict) else {}
        default_url = str(oj_config.get("run_url", "http://192.168.31.128:5050/run"))
        default_timeout = float(oj_config.get("timeout_seconds", 15) or 15)
        self.java_bin = str(oj_config.get("java_bin", "/usr/local/jdk/jdk-25/bin/java"))

        self.base_url = os.environ.get("GO_JUDGE_URL", default_url)
        self.timeout_seconds = float(os.environ.get("GO_JUDGE_TIMEOUT_SECONDS", str(default_timeout)))
        self.limits = SandboxLimits()

    def judge_code(
        self,
        *,
        code: str,
        language: str,
        test_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        normalized_language = self._normalize_language(language)
        details: List[Dict[str, Any]] = []
        earned_score = 0.0
        total_score = 0.0
        passed = 0

        for idx, case in enumerate(test_cases):
            weight = float(case.get("weight", 0) or 0)
            if weight < 0:
                weight = 0.0
            total_score += weight

            case_input = str(case.get("input", ""))
            expected = str(case.get("expected", case.get("output", "")))
            is_file_io = bool(case.get("is_file_io", False))

            run_result = self._run_single_case(
                code=code,
                language=normalized_language,
                case_input=case_input,
                is_file_io=is_file_io,
            )

            actual = str(run_result.get("stdout", ""))
            stderr = str(run_result.get("stderr", ""))
            ok = bool(run_result.get("ok", False)) and self._normalize_output(actual) == self._normalize_output(expected)
            got_score = weight if ok else 0.0
            if ok:
                passed += 1
                earned_score += got_score

            details.append(
                {
                    "case": idx + 1,
                    "ok": ok,
                    "status": run_result.get("status", "Wrong Answer"),
                    "input": case_input,
                    "expected": expected,
                    "actual": actual,
                    "stderr": stderr,
                    "weight": round(weight, 2),
                    "score": round(got_score, 2),
                    "is_file_io": is_file_io,
                    "exit_code": run_result.get("exit_code", 0),
                    "time_ms": run_result.get("time_ms", 0),
                    "memory_kb": run_result.get("memory_kb", 0),
                }
            )

        score_rate = (earned_score / total_score) if total_score > 0 else 0.0
        return {
            "language": normalized_language,
            "passed": passed,
            "total": len(test_cases),
            "earned_score": round(earned_score, 2),
            "total_score": round(total_score, 2),
            "score_rate": score_rate,
            "details": details,
        }

    def _run_single_case(
        self,
        *,
        code: str,
        language: str,
        case_input: str,
        is_file_io: bool,
    ) -> Dict[str, Any]:
        request_payload = self._build_run_request(
            code=code,
            language=language,
            case_input=case_input,
            is_file_io=is_file_io,
        )
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(self.base_url, json=request_payload)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "status": "Sandbox Error",
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -3,
                "time_ms": 0,
                "memory_kb": 0,
            }

        parsed = self._extract_case_result(resp.json())
        status = str(parsed.get("status", "Unknown"))
        exit_code = int(parsed.get("exitStatus", parsed.get("exit_code", 0)) or 0)
        time_ns = int(parsed.get("time", parsed.get("time_ns", 0)) or 0)
        memory_bytes = int(parsed.get("memory", parsed.get("memory_bytes", 0)) or 0)
        files = parsed.get("files", {}) if isinstance(parsed.get("files"), dict) else {}
        stdout = str(files.get("stdout", parsed.get("stdout", "")))
        stderr = str(files.get("stderr", parsed.get("stderr", "")))

        ok = status in {"Accepted", "Success"} and exit_code == 0
        return {
            "ok": ok,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "time_ms": round(time_ns / 1_000_000),
            "memory_kb": round(memory_bytes / 1024),
        }

    def _build_run_request(
        self,
        *,
        code: str,
        language: str,
        case_input: str,
        is_file_io: bool,
    ) -> Dict[str, Any]:
        code_b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
        case_input_b64 = base64.b64encode(case_input.encode("utf-8")).decode("ascii")

        stdin_file = {"content": "" if is_file_io else case_input}
        io_files = [
            stdin_file,
            {"name": "stdout", "max": self.limits.output_max_bytes},
            {"name": "stderr", "max": self.limits.output_max_bytes},
        ]

        common_env = [
            "PATH=/usr/bin:/bin",
            f"CODE_B64={code_b64}",
            f"CASE_INPUT_B64={case_input_b64}",
        ]

        file_io_script = ""
        if is_file_io:
            file_io_script = "printf '%s' \"$CASE_INPUT_B64\" | base64 -d > input.txt; "

        if language == "python":
            script = (
                f"{file_io_script}"
                "printf '%s' \"$CODE_B64\" | base64 -d > main.py; "
                "python3 main.py"
            )
            run_cmd = {
                "args": ["/bin/sh", "-c", script],
                "env": common_env,
                "files": io_files,
                "cpuLimit": self.limits.cpu_limit_ns,
                "memoryLimit": self.limits.memory_limit_bytes,
                "procLimit": self.limits.proc_limit,
            }
            return {"cmd": [run_cmd]}

        if language == "cpp":
            script = (
                f"{file_io_script}"
                "printf '%s' \"$CODE_B64\" | base64 -d > main.cpp; "
                "g++ main.cpp -O2 -std=c++17 -o main && ./main"
            )
            run_cmd = {
                "args": ["/bin/sh", "-c", script],
                "env": common_env,
                "files": io_files,
                "cpuLimit": self.limits.cpu_limit_ns,
                "memoryLimit": self.limits.memory_limit_bytes,
                "procLimit": self.limits.proc_limit,
            }
            return {"cmd": [run_cmd]}

        # java: source-file mode using configured java binary
        java_cmd: Dict[str, Any] = {
            "args": [
                os.environ.get("GO_JUDGE_JAVA_BIN", self.java_bin),
                "-Xms16m",
                "-Xmx64m",
                "Main.java",
            ],
            "env": ["PATH=/usr/bin:/bin"],
            "files": io_files,
            "cpuLimit": self.limits.cpu_limit_ns,
            "memoryLimit": max(self.limits.memory_limit_bytes, 512 * 1024 * 1024),
            "procLimit": max(self.limits.proc_limit, 256),
            "copyIn": {
                "Main.java": {
                    "content": code,
                }
            },
            "copyOut": ["stdout", "stderr"],
        }
        if is_file_io:
            java_cmd["copyIn"]["input.txt"] = {"content": case_input}
        return {"cmd": [java_cmd]}

    def _extract_case_result(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list) and payload.get("data"):
                return self._extract_case_result(payload["data"][0])
            if isinstance(payload.get("result"), list) and payload.get("result"):
                return self._extract_case_result(payload["result"][0])
            if isinstance(payload.get("runResults"), list) and payload.get("runResults"):
                return self._extract_case_result(payload["runResults"][-1])
            return payload

        if isinstance(payload, list) and payload:
            return self._extract_case_result(payload[0])
        return {}

    def _normalize_language(self, language: str) -> str:
        raw = str(language or "python").strip().lower()
        aliases = {
            "py": "python",
            "python": "python",
            "python3": "python",
            "c++": "cpp",
            "cpp": "cpp",
            "cc": "cpp",
            "java": "java",
        }
        return aliases.get(raw, "python")

    def _normalize_output(self, value: str) -> str:
        return str(value or "").replace("\r\n", "\n").strip()