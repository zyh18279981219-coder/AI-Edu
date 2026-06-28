from __future__ import annotations

import argparse
import getpass
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MYSQL_BIN = Path(r"D:\develop\mysql-8.0.31-winx64\bin")
APP_LOCAL_USER = "ai_education_design"
APP_LOCAL_PASSWORD = "ai_education_design"


def load_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def mysql_exe(name: str) -> str:
    candidate = MYSQL_BIN / f"{name}.exe"
    return str(candidate if candidate.exists() else name)


def write_client_cnf(path: Path, *, host: str, port: int, user: str, password: str) -> None:
    path.write_text(
        "[client]\n"
        f"host={host}\n"
        f"port={port}\n"
        f"user={user}\n"
        f"password={password}\n"
        "default-character-set=utf8mb4\n",
        encoding="utf-8",
    )


def run(cmd: list[str], *, stdin_path: Path | None = None, stdout_path: Path | None = None) -> None:
    stdin = stdin_path.open("rb") if stdin_path else None
    stdout = stdout_path.open("wb") if stdout_path else None
    try:
        proc = subprocess.run(cmd, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, cwd=PROJECT_ROOT)
    finally:
        if stdin:
            stdin.close()
        if stdout:
            stdout.close()
    if proc.returncode != 0:
        message = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(message.strip() or f"Command failed: {' '.join(cmd)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clone remote ai_education MySQL database into a local MySQL database.")
    parser.add_argument("--local-host", default=os.getenv("LOCAL_DB_HOST", "127.0.0.1"))
    parser.add_argument("--local-port", type=int, default=int(os.getenv("LOCAL_DB_PORT", "3306")))
    parser.add_argument("--local-user", default=os.getenv("LOCAL_DB_USER", "root"))
    parser.add_argument("--local-password", default=os.getenv("LOCAL_DB_PASSWORD"))
    parser.add_argument("--local-db", default=os.getenv("LOCAL_DB_NAME", "ai_education_design"))
    parser.add_argument("--write-env-local", action="store_true", help="Write .env.local.mysql for manual switching.")
    args = parser.parse_args()

    if args.local_host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to clone into a non-local host. Use a local MySQL instance for design work.")

    env = load_env(PROJECT_ROOT / ".env")
    remote_required = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [key for key in remote_required if not env.get(key)]
    if missing:
        raise SystemExit(f"Missing remote DB settings in .env: {', '.join(missing)}")

    local_password = args.local_password
    if local_password is None:
        local_password = getpass.getpass(f"Password for local MySQL user {args.local_user}: ")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "output" / f"local_clone_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    remote_cnf = out_dir / "remote.cnf"
    local_cnf = out_dir / "local.cnf"
    dump_path = out_dir / f"{env['DB_NAME']}_remote_full_{stamp}.sql"

    try:
        write_client_cnf(
            remote_cnf,
            host=env["DB_HOST"],
            port=int(env["DB_PORT"]),
            user=env["DB_USER"],
            password=env["DB_PASSWORD"],
        )
        write_client_cnf(
            local_cnf,
            host=args.local_host,
            port=args.local_port,
            user=args.local_user,
            password=local_password,
        )

        run(
            [
                mysql_exe("mysqldump"),
                f"--defaults-extra-file={remote_cnf}",
                "--single-transaction",
                "--quick",
                "--skip-lock-tables",
                "--no-tablespaces",
                "--set-gtid-purged=OFF",
                "--default-character-set=utf8mb4",
                env["DB_NAME"],
            ],
            stdout_path=dump_path,
        )
        run(
            [
                mysql_exe("mysql"),
                f"--defaults-extra-file={local_cnf}",
                "-e",
                f"DROP DATABASE IF EXISTS `{args.local_db}`; "
                f"CREATE DATABASE `{args.local_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            ]
        )
        run([mysql_exe("mysql"), f"--defaults-extra-file={local_cnf}", args.local_db], stdin_path=dump_path)
        run(
            [
                mysql_exe("mysql"),
                f"--defaults-extra-file={local_cnf}",
                "-e",
                f"CREATE USER IF NOT EXISTS '{APP_LOCAL_USER}'@'127.0.0.1' IDENTIFIED BY '{APP_LOCAL_PASSWORD}'; "
                f"CREATE USER IF NOT EXISTS '{APP_LOCAL_USER}'@'localhost' IDENTIFIED BY '{APP_LOCAL_PASSWORD}'; "
                f"ALTER USER '{APP_LOCAL_USER}'@'127.0.0.1' IDENTIFIED BY '{APP_LOCAL_PASSWORD}'; "
                f"ALTER USER '{APP_LOCAL_USER}'@'localhost' IDENTIFIED BY '{APP_LOCAL_PASSWORD}'; "
                f"GRANT ALL PRIVILEGES ON `{args.local_db}`.* TO '{APP_LOCAL_USER}'@'127.0.0.1'; "
                f"GRANT ALL PRIVILEGES ON `{args.local_db}`.* TO '{APP_LOCAL_USER}'@'localhost'; "
                "FLUSH PRIVILEGES;",
            ]
        )

        if args.write_env_local:
            (PROJECT_ROOT / ".env.local.mysql").write_text(
                "DB_TYPE=mysql\n"
                f"DB_HOST={args.local_host}\n"
                f"DB_PORT={args.local_port}\n"
                f"DB_USER={APP_LOCAL_USER}\n"
                f"DB_PASSWORD={APP_LOCAL_PASSWORD}\n"
                f"DB_NAME={args.local_db}\n"
                "DB_CHARSET=utf8mb4\n"
                "DB_AUTO_MIGRATE=0\n",
                encoding="utf-8",
            )
    finally:
        for path in (remote_cnf, local_cnf):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    print(f"Local clone created: {args.local_host}:{args.local_port}/{args.local_db}")
    print(f"Remote dump saved: {dump_path}")
    if args.write_env_local:
        print("Local env saved: .env.local.mysql")


if __name__ == "__main__":
    main()
