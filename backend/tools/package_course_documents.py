"""Package tracked course PDFs for a Linux deployment without touching code or 5E."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "backend/data/Book"], cwd=PROJECT_ROOT
    ).decode("utf-8").split("\0")
    paths = [Path(name) for name in tracked if name and Path(name).suffix.lower() == ".pdf"]
    if not paths:
        raise SystemExit("No tracked course PDFs found")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = PROJECT_ROOT / "tmp" / ("course_documents_" + stamp)
    out.mkdir(parents=True, exist_ok=False)
    archive = out / "course_documents.tar.gz"
    manifest = []
    names = {p.as_posix() for p in paths}
    with tarfile.open(archive, "w:gz") as bundle:
        for relative in sorted(paths):
            source = PROJECT_ROOT / relative
            if not source.is_file():
                raise FileNotFoundError(source)
            if source.read_bytes()[:5] != b"%PDF-":
                raise ValueError(f"Invalid PDF header: {relative}")
            entry = {"path": relative.as_posix(), "bytes": source.stat().st_size,
                     "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            bundle.add(source, arcname=entry["path"], recursive=False)
            # Historical DB rows use .PDF. Add aliases in the archive itself;
            # Windows cannot store both spellings, while Linux can.
            alias = relative.with_suffix(".PDF").as_posix()
            if alias not in names:
                link = tarfile.TarInfo(alias)
                link.type = tarfile.LNKTYPE
                link.linkname = entry["path"]
                link.mode = 0o644
                bundle.addfile(link)
                entry["linux_alias"] = alias
            manifest.append(entry)
    summary = {"file_count": len(manifest), "linux_alias_count": sum("linux_alias" in e for e in manifest),
               "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": manifest}
    (out / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.txt").write_text(
        "Course documents only. No application code, database configuration or 5E files.\n"
        "Copy course_documents.tar.gz to /tmp on the application server. Verify the project directory first.\n"
        "For the confirmed deployment at /root/workdir/AI-Edu, add missing files without replacing existing files:\n"
        "tar --extract --gzip --file=/tmp/course_documents.tar.gz --directory=/root/workdir/AI-Edu --skip-old-files\n"
        "If the backend is containerized, copy into its persistent mount instead of its ephemeral filesystem.\n"
        "Then verify /api/pdf/data/Book/1.PDF returns application/pdf, not the SPA HTML or a 404.\n"
        "An unavailable backend or a missing /api reverse proxy must be repaired separately.\n",
        encoding="utf-8",
    )
    print(json.dumps({"archive": str(archive), "pdf_count": len(manifest),
                      "linux_alias_count": summary["linux_alias_count"], "archive_bytes": archive.stat().st_size}))


if __name__ == "__main__":
    main()
