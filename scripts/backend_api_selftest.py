from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=data, method=method.upper(), headers=headers)
        try:
            with self.opener.open(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if body:
                    try:
                        return resp.status, json.loads(body)
                    except json.JSONDecodeError:
                        return resp.status, body
                return resp.status, None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                return exc.code, json.loads(body) if body else None
            except json.JSONDecodeError:
                return exc.code, body
        except urllib.error.URLError as exc:
            return 0, {"error": str(exc)}


def run(base_url: str) -> int:
    results: list[CheckResult] = []
    c = ApiClient(base_url)
    db_path = Path("data/app.db")
    if not db_path.exists():
        print("Local DB not found: data/app.db")
        return 1

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        student_row = conn.execute(
            """
            SELECT u.user_id, u.login_id, u.password
            FROM users u
            JOIN twin_profile_nodes n ON n.username = u.username
            WHERE u.user_type='student' AND n.node_id LIKE '%Spark%'
            ORDER BY u.user_id
            LIMIT 1
            """
        ).fetchone()
        if not student_row:
            student_row = conn.execute(
                "SELECT user_id, login_id, password FROM users WHERE user_type='student' ORDER BY user_id LIMIT 1"
            ).fetchone()
        teacher_row = conn.execute(
            "SELECT user_id, login_id, password FROM users WHERE user_type='teacher' ORDER BY user_id LIMIT 1"
        ).fetchone()
    if not student_row or not teacher_row:
        print("Missing seed users in users table")
        return 1
    student_login_id = str(student_row["login_id"])
    student_user_id = str(student_row["user_id"])
    student_password = str(student_row["password"] or "")
    teacher_login_id = str(teacher_row["login_id"])
    teacher_user_id = str(teacher_row["user_id"])
    teacher_password = str(teacher_row["password"] or "")

    def _login(username: str, password: str, user_type: str, retries: int = 1) -> tuple[int, Any]:
        last_status, last_body = 0, None
        for attempt in range(retries):
            last_status, last_body = ApiClient(base_url).request(
                "POST",
                "/api/auth/login",
                {"username": username, "password": password, "user_type": user_type},
            )
            if last_status == 200:
                return last_status, last_body
            if attempt < retries - 1:
                time.sleep(1.0)
        return last_status, last_body

    def _login_with_client(client: ApiClient, username: str, password: str, user_type: str, retries: int = 1) -> tuple[int, Any]:
        last_status, last_body = 0, None
        for attempt in range(retries):
            last_status, last_body = client.request(
                "POST",
                "/api/auth/login",
                {"username": username, "password": password, "user_type": user_type},
            )
            if last_status == 200:
                return last_status, last_body
            if attempt < retries - 1:
                time.sleep(1.0)
        return last_status, last_body

    status, body = c.request("GET", "/openapi.json")
    results.append(
        CheckResult(
            name="openapi",
            ok=(status == 200),
            detail=f"status={status}",
        )
    )
    if status != 200:
        _print_results(results)
        print("\nBackend unreachable. Please start backend first, then rerun.")
        return 1

    # student login by login_id
    status, body = _login_with_client(c, student_login_id, student_password, "student", retries=3)
    user = body.get("user", {}) if isinstance(body, dict) else {}
    ok = status == 200 and str(user.get("user_id")) == student_user_id
    results.append(CheckResult("login_student_login_id", ok, f"status={status}, user_id={user.get('user_id')}"))

    status, body = c.request("GET", "/api/current-user")
    ok = status == 200 and isinstance(body, dict) and str(body.get("user_id")) == student_user_id
    results.append(CheckResult("current_user_after_student_login", ok, f"status={status}"))

    # student login by user_id
    status, body = _login(student_user_id, student_password, "student", retries=3)
    user = body.get("user", {}) if isinstance(body, dict) else {}
    ok = status == 200 and str(user.get("user_id")) == student_user_id
    results.append(CheckResult("login_student_user_id", ok, f"status={status}, identifier={student_user_id}, user_id={user.get('user_id')}"))

    # username login should be rejected in non-compatible mode
    status, _ = _login("__legacy_username_only__", student_password, "student", retries=1)
    results.append(CheckResult("login_student_username_rejected", status == 401, f"status={status}"))

    # teacher login by login_id/user_id
    for identifier, name in [(teacher_login_id, "teacher_login_id"), (teacher_user_id, "teacher_user_id")]:
        status, body = _login(identifier, teacher_password, "teacher", retries=3)
        user = body.get("user", {}) if isinstance(body, dict) else {}
        ok = status == 200 and str(user.get("user_id")) == teacher_user_id
        results.append(CheckResult(f"login_{name}", ok, f"status={status}, user_id={user.get('user_id')}"))
    status, _ = _login("__legacy_teacher_username_only__", teacher_password, "teacher", retries=1)
    results.append(CheckResult("login_teacher_username_rejected", status == 401, f"status={status}"))

    # student-course-profile by login_id/user_id
    for sid, label in [(student_login_id, "login_id"), (student_user_id, "user_id")]:
        status, body = c.request(
            "POST",
            "/api/digital-twin/student-course-profile",
            {"student_id": sid, "course_id": "Spark"},
        )
        count = body.get("course_node_count") if isinstance(body, dict) else None
        ok = status == 200 and isinstance(count, int)
        results.append(CheckResult(f"student_course_profile_{label}", ok, f"status={status}, course_node_count={count}"))

    # teacher external-sync by login_id/user_id
    for tid, label in [(teacher_login_id, "login_id"), (teacher_user_id, "user_id")]:
        status, body = c.request(
            "POST",
            f"/api/digital-twin/teacher-profile/{urllib.parse.quote(tid)}/external-sync",
            {"metrics": {"selftest_flag": True}},
        )
        resolved = body.get("teacher_username") if isinstance(body, dict) else None
        ok = status == 200 and resolved == "teacher"
        results.append(CheckResult(f"teacher_external_sync_{label}", ok, f"status={status}, teacher_username={resolved}"))

    _print_results(results)
    return 0 if all(item.ok for item in results) else 2


def _print_results(results: list[CheckResult]) -> None:
    print("Backend API Self-Test\n")
    for item in results:
        mark = "PASS" if item.ok else "FAIL"
        print(f"[{mark}] {item.name} - {item.detail}")
    passed = sum(1 for item in results if item.ok)
    print(f"\nSummary: {passed}/{len(results)} passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backend API self-test checklist")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
