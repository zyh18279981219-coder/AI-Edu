from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document as load_docx
from docx.document import Document as DocxDocument


class DocxLoader:
    """Load and parse DOCX scripts under KnowledgeGraph/unstructured_script."""

    def __init__(self, scripts_dir: str | Path, logger=None) -> None:
        self.scripts_dir = Path(scripts_dir)
        self.logger = logger

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _parse_lesson_info(file_stem: str) -> tuple[int | None, int | None, str]:
        match = re.search(r"(\d+)\s*-\s*(\d+)", file_stem)
        if not match:
            return None, None, file_stem.strip()

        lesson_no = int(match.group(1))
        section_no = int(match.group(2))
        topic = file_stem[match.end() :].strip(" _-")
        if not topic:
            topic = file_stem.strip()
        return lesson_no, section_no, topic

    @staticmethod
    def _extract_paragraphs(doc: DocxDocument) -> list[str]:
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return paragraphs

    @staticmethod
    def _extract_table_text(doc: DocxDocument) -> list[str]:
        table_texts: list[str] = []
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    table_texts.append(" | ".join(cells))
        return table_texts

    def _parse_file(self, file_path: Path, index: int) -> dict[str, Any]:
        lesson_no, section_no, topic = self._parse_lesson_info(file_path.stem)

        doc = load_docx(file_path)
        paragraphs = self._extract_paragraphs(doc)
        table_rows = self._extract_table_text(doc)
        all_blocks = paragraphs + table_rows
        raw_text = "\n".join(all_blocks).strip()

        title = topic
        if paragraphs:
            first_line = paragraphs[0].strip()
            if 4 <= len(first_line) <= 80:
                title = first_line

        return {
            "doc_id": f"doc_{index:03d}",
            "source_file": file_path.name,
            "source_path": str(file_path),
            "title": title,
            "lesson_no": lesson_no,
            "section_no": section_no,
            "topic": topic,
            "paragraph_count": len(paragraphs),
            "table_row_count": len(table_rows),
            "char_count": len(raw_text),
            "raw_text": raw_text,
        }

    def load(self) -> dict[str, Any]:
        files = sorted(self.scripts_dir.glob("*.docx"))
        documents: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        if not files:
            self._log("warning", "No DOCX files found under: %s", self.scripts_dir)

        for idx, file_path in enumerate(files, start=1):
            try:
                doc = self._parse_file(file_path, idx)
                documents.append(doc)
            except Exception as exc:  # pragma: no cover
                errors.append({"source_file": file_path.name, "error": str(exc)})
                self._log("warning", "Failed to parse DOCX: %s (%s)", file_path.name, exc)

        stats = {
            "total_files": len(files),
            "parsed_files": len(documents),
            "failed_files": len(errors),
            "success_rate": round(
                (len(documents) / len(files) * 100.0), 2
            )
            if files
            else 0.0,
        }
        self._log(
            "info",
            "DOCX parsing finished. total=%s parsed=%s failed=%s success_rate=%s%%",
            stats["total_files"],
            stats["parsed_files"],
            stats["failed_files"],
            stats["success_rate"],
        )
        return {"documents": documents, "errors": errors, "stats": stats}
