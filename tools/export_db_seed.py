from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


def export_sqlite_dump(db_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        with output_path.open("w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
    finally:
        conn.close()


def import_sqlite_dump(seed_path: Path, db_path: Path, backup: bool = True) -> None:
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed SQL not found: {seed_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if backup and db_path.exists():
        backup_path = db_path.with_suffix(db_path.suffix + ".bak")
        shutil.copy2(db_path, backup_path)

    # Reset DB and sidecar files for deterministic import.
    for path in [db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")]:
        if path.exists():
            path.unlink()

    sql_text = seed_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(sql_text)
        conn.commit()
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export/import SQLite database seed SQL")
    parser.add_argument(
        "--mode",
        choices=["export", "import", "export-homework"],
        required=True,
        help="export: dump DB to SQL; import: restore DB from SQL; export-homework: export homework JSON to SQLite tables",
    )
    parser.add_argument(
        "--db",
        default="data/app.db",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--out",
        default="release/init_seed.sql",
        help="For export: output SQL path; for import: input SQL path",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="When importing, do not backup existing DB",
    )
    parser.add_argument(
        "--homework-store",
        default="data/homework/homework_store.json",
        help="Path to homework JSON store (used by export-homework mode)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = _resolve_path(args.db)
    out_path = _resolve_path(args.out)

    if args.mode == "export":
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        export_sqlite_dump(db_path, out_path)
        print(f"Exported seed SQL to: {out_path}")
        return

    if args.mode == "export-homework":
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from HomeworkModule.exporter import export_homework_json_to_sqlite

        result = export_homework_json_to_sqlite(
            homework_store_path=_resolve_path(args.homework_store),
            sqlite_db_path=db_path,
        )
        print(f"Exported homework data to SQLite: {db_path}")
        print(result)
        return

    import_sqlite_dump(out_path, db_path, backup=not args.no_backup)
    print(f"Imported seed SQL from: {out_path} -> {db_path}")


if __name__ == "__main__":
    main()
