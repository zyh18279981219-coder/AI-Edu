from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from KnowledgeGraph.src.course_profile import CourseProfile
from KnowledgeGraph.src.extraction.kggen_client import KGGenClient
from KnowledgeGraph.src.extraction.triple_postprocess import TriplePostProcessor
from KnowledgeGraph.src.ingestion.docx_loader import DocxLoader
from KnowledgeGraph.src.ingestion.text_cleaner import TextCleaner
from KnowledgeGraph.src.kg_config import KGConfig
from KnowledgeGraph.src.logging_utils import setup_kg_logger
from KnowledgeGraph.src.pedagogy.hierarchy_builder import HierarchyBuilder
from KnowledgeGraph.src.pedagogy.quality_gate import QualityGate
from KnowledgeGraph.src.pedagogy.relation_refiner import RelationRefiner
from KnowledgeGraph.src.resource_match.book_indexer import BookIndexer
from KnowledgeGraph.src.resource_match.settings import ResourceMatchSettings
from KnowledgeGraph.src.resource_match.video_matcher import VideoMatcher


class KGPipeline:
    def __init__(self, config: KGConfig | None = None) -> None:
        self.config = config or KGConfig.from_env()
        self.logger = setup_kg_logger(log_file=self.config.output_dir / "pipeline.log")

    def backup_course_graph(self) -> Path | None:
        source_path = self.config.project_root / "data" / "course" / "big_data.json"
        if not source_path.exists():
            self.logger.warning("Skip backup: source file not found: %s", source_path)
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = self.config.backup_dir / f"big_data.backup.{timestamp}.json"
        shutil.copy2(source_path, target_path)
        self.logger.info("Backup created: %s", target_path)
        return target_path

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=False))
                file.write("\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not path.exists():
            return records

        with path.open("r", encoding="utf-8") as file:
            for line in file:
                payload = line.strip()
                if not payload:
                    continue
                records.append(json.loads(payload))
        return records

    def _base_checks(self) -> dict[str, bool]:
        return {
            "scripts_dir_exists": self.config.scripts_dir.exists(),
            "output_dir_exists": self.config.output_dir.exists(),
            "intermediate_dir_exists": self.config.intermediate_dir.exists(),
            "backup_dir_exists": self.config.backup_dir.exists(),
        }

    def run_stage0(self, dry_run: bool = False) -> dict[str, Any]:
        self.config.ensure_directories()

        report: dict[str, Any] = {
            "stage": "stage_0",
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "checks": self._base_checks(),
            "config": self.config.masked_dict(),
            "notes": [
                "Stage 0 only initializes module skeleton and runtime config.",
                "No graph extraction or resource matching is executed in this stage.",
            ],
        }

        report_name = "stage0_dry_run_report.json" if dry_run else "stage0_run_report.json"
        report_path = self.config.output_dir / report_name
        self._write_json(report_path, report)
        self.logger.info("Pipeline report saved: %s", report_path)
        return report | {"report_path": str(report_path)}

    def run_stage1(self, dry_run: bool = False) -> dict[str, Any]:
        self.config.ensure_directories()
        checks = self._base_checks()
        discovered_files = sorted(self.config.scripts_dir.glob("*.docx"))

        if dry_run:
            report: dict[str, Any] = {
                "stage": "stage_1",
                "dry_run": True,
                "timestamp": datetime.now().isoformat(),
                "status": "ok",
                "checks": checks,
                "document_discovery": {
                    "total_docx": len(discovered_files),
                    "sample_files": [path.name for path in discovered_files[:5]],
                },
                "notes": [
                    "Stage 1 dry-run only checks script availability and output paths.",
                    "No parsing output file is generated in dry-run mode.",
                ],
            }
            report_path = self.config.output_dir / "stage1_dry_run_report.json"
            self._write_json(report_path, report)
            self.logger.info("Pipeline report saved: %s", report_path)
            return report | {"report_path": str(report_path)}

        loader = DocxLoader(self.config.scripts_dir, logger=self.logger)
        load_result = loader.load()

        cleaner = TextCleaner(
            logger=self.logger,
            course_profile=CourseProfile.from_path(self.config.course_profile_path),
        )
        cleaned_result = cleaner.clean(load_result["documents"])

        jsonl_path = self.config.intermediate_dir / "scripts_cleaned.jsonl"
        docs_path = self.config.intermediate_dir / "scripts_cleaned_docs.json"
        stage1_summary_path = self.config.output_dir / "stage1_summary.json"

        self._write_jsonl(jsonl_path, cleaned_result["segments"])
        self._write_json(docs_path, {"documents": cleaned_result["documents"]})

        summary: dict[str, Any] = {
            "stage": "stage_1",
            "timestamp": datetime.now().isoformat(),
            "loader_stats": load_result["stats"],
            "clean_stats": cleaned_result["stats"],
            "output_files": {
                "scripts_cleaned_jsonl": str(jsonl_path),
                "scripts_cleaned_docs_json": str(docs_path),
            },
            "acceptance": {
                "doc_parse_success_rate": load_result["stats"]["success_rate"],
                "doc_parse_success_rate_target": 100.0,
                "all_docs_parsed": load_result["stats"]["failed_files"] == 0,
                "scripts_cleaned_generated": jsonl_path.exists(),
                "segment_count_positive": cleaned_result["stats"]["segment_count"] > 0,
            },
        }
        self._write_json(stage1_summary_path, summary)

        report: dict[str, Any] = {
            "stage": "stage_1",
            "dry_run": False,
            "timestamp": datetime.now().isoformat(),
            "status": "ok" if summary["acceptance"]["scripts_cleaned_generated"] else "failed",
            "checks": checks,
            "summary_file": str(stage1_summary_path),
            "acceptance": summary["acceptance"],
            "loader_stats": load_result["stats"],
            "clean_stats": cleaned_result["stats"],
        }
        report_path = self.config.output_dir / "stage1_run_report.json"
        self._write_json(report_path, report)
        self.logger.info("Pipeline report saved: %s", report_path)
        return report | {"report_path": str(report_path)}

    def run_stage2(
        self,
        dry_run: bool = False,
        kggen_doc_limit: int = 5,
        max_chars_per_doc: int = 1200,
    ) -> dict[str, Any]:
        self.config.ensure_directories()
        checks = self._base_checks()

        stage1_docs_path = self.config.intermediate_dir / "scripts_cleaned_docs.json"
        if not stage1_docs_path.exists():
            self.logger.info("Stage1 output missing, running stage1 first.")
            self.run_stage1(dry_run=False)

        if dry_run:
            report: dict[str, Any] = {
                "stage": "stage_2",
                "dry_run": True,
                "timestamp": datetime.now().isoformat(),
                "status": "ok",
                "checks": checks
                | {
                    "stage1_docs_exists": stage1_docs_path.exists(),
                    "kggen_repo_exists": (self.config.third_party_dir / "kg-gen").exists(),
                },
                "params": {
                    "kggen_doc_limit": kggen_doc_limit,
                    "max_chars_per_doc": max_chars_per_doc,
                },
                "notes": [
                    "Stage 2 dry-run checks prerequisites only.",
                    "No triple extraction is executed in dry-run mode.",
                ],
            }
            report_path = self.config.output_dir / "stage2_dry_run_report.json"
            self._write_json(report_path, report)
            self.logger.info("Pipeline report saved: %s", report_path)
            return report | {"report_path": str(report_path)}

        payload = json.loads(stage1_docs_path.read_text(encoding="utf-8"))
        cleaned_docs = payload.get("documents", [])
        if not isinstance(cleaned_docs, list):
            cleaned_docs = []

        kg_client = KGGenClient(
            model=self.config.llm_model,
            api_key=self.config.llm_api_key,
            api_base=self.config.llm_base_url,
            logger=self.logger,
            kggen_doc_limit=kggen_doc_limit,
            max_chars_per_doc=max_chars_per_doc,
        )
        extraction_result = kg_client.extract(cleaned_docs)

        raw_path = self.config.intermediate_dir / "triples_raw.jsonl"
        raw_doc_stats_path = self.config.output_dir / "stage2_doc_stats.json"
        self._write_jsonl(raw_path, extraction_result["triples"])
        self._write_json(
            raw_doc_stats_path,
            {"doc_stats": extraction_result["doc_stats"], "errors": extraction_result["errors"]},
        )

        post_processor = TriplePostProcessor()
        normalized_result = post_processor.normalize(extraction_result["triples"])
        normalized_path = self.config.intermediate_dir / "triples_normalized.jsonl"
        self._write_jsonl(normalized_path, normalized_result["triples"])

        summary: dict[str, Any] = {
            "stage": "stage_2",
            "timestamp": datetime.now().isoformat(),
            "extraction_stats": extraction_result["stats"],
            "normalized_stats": normalized_result["stats"],
            "params": {
                "kggen_doc_limit": kggen_doc_limit,
                "max_chars_per_doc": max_chars_per_doc,
            },
            "output_files": {
                "triples_raw_jsonl": str(raw_path),
                "triples_normalized_jsonl": str(normalized_path),
                "doc_stats_json": str(raw_doc_stats_path),
            },
            "acceptance": {
                "all_docs_have_triples": extraction_result["stats"]["docs_with_triples"]
                == extraction_result["stats"]["total_docs"],
                "kggen_invoked": extraction_result["stats"]["kggen_attempted_docs"] > 0,
                "kggen_success_docs_positive": extraction_result["stats"]["kggen_success_docs"] > 0,
                "triples_raw_generated": raw_path.exists(),
                "triples_normalized_generated": normalized_path.exists(),
                "relation_count_gt_entity_count": normalized_result["stats"][
                    "relation_count_gt_entity_count"
                ],
            },
        }
        summary_path = self.config.output_dir / "stage2_summary.json"
        self._write_json(summary_path, summary)

        report: dict[str, Any] = {
            "stage": "stage_2",
            "dry_run": False,
            "timestamp": datetime.now().isoformat(),
            "status": "ok"
            if summary["acceptance"]["triples_raw_generated"]
            and summary["acceptance"]["kggen_invoked"]
            and normalized_result["stats"]["normalized_triple_count"] > 0
            else "failed",
            "checks": checks,
            "summary_file": str(summary_path),
            "acceptance": summary["acceptance"],
            "extraction_stats": extraction_result["stats"],
            "normalized_stats": normalized_result["stats"],
            "params": summary["params"],
        }
        report_path = self.config.output_dir / "stage2_run_report.json"
        self._write_json(report_path, report)
        self.logger.info("Pipeline report saved: %s", report_path)
        return report | {"report_path": str(report_path)}

    def run_stage3(self, dry_run: bool = False) -> dict[str, Any]:
        self.config.ensure_directories()
        checks = self._base_checks()

        stage1_docs_path = self.config.intermediate_dir / "scripts_cleaned_docs.json"
        triples_path = self.config.intermediate_dir / "triples_normalized.jsonl"
        output_canonical_path = self.config.output_dir / "big_data_kg.canonical.json"
        quality_report_path = self.config.output_dir / "quality_report.json"
        concept_audit_path = self.config.output_dir / "concept_audit.json"

        if dry_run:
            report: dict[str, Any] = {
                "stage": "stage_3",
                "dry_run": True,
                "timestamp": datetime.now().isoformat(),
                "status": "ok",
                "checks": checks
                | {
                    "stage1_docs_exists": stage1_docs_path.exists(),
                    "stage2_triples_exists": triples_path.exists(),
                    "course_profile_exists": self.config.course_profile_path.exists(),
                },
                "notes": [
                    "Stage 3 dry-run checks prerequisites only.",
                    "No hierarchy build or quality evaluation is executed in dry-run mode.",
                ],
            }
            report_path = self.config.output_dir / "stage3_dry_run_report.json"
            self._write_json(report_path, report)
            self.logger.info("Pipeline report saved: %s", report_path)
            return report | {"report_path": str(report_path)}

        if not stage1_docs_path.exists():
            self.logger.info("Stage1 output missing, running stage1 first.")
            self.run_stage1(dry_run=False)
        if not triples_path.exists():
            self.logger.info("Stage2 output missing, running stage2 first.")
            self.run_stage2(dry_run=False)

        stage1_docs_payload = json.loads(stage1_docs_path.read_text(encoding="utf-8"))
        documents = stage1_docs_payload.get("documents", [])
        if not isinstance(documents, list):
            documents = []
        triples = self._read_jsonl(triples_path)

        builder = HierarchyBuilder(
            logger=self.logger,
            profile_path=self.config.course_profile_path,
        )
        hierarchy_result = builder.build(
            triples=triples,
            documents=documents,
            course_id="course_big_data",
            course_name="大数据分析",
        )

        refiner = RelationRefiner(logger=self.logger)
        refined_result = refiner.refine(hierarchy_result["graph"])

        quality_gate = QualityGate(
            logger=self.logger,
            profile_path=self.config.course_profile_path,
            course_profile=builder.course_profile,
        )
        quality_result = quality_gate.evaluate(
            refined_result["graph"],
            model_config={
                "llm_model": self.config.llm_model,
                "llm_base_url": self.config.llm_base_url,
            },
        )

        self._write_json(output_canonical_path, refined_result["graph"])
        self._write_json(concept_audit_path, hierarchy_result["concept_audit"])
        quality_report = {
            "stage": "stage_3",
            "timestamp": datetime.now().isoformat(),
            "passed": quality_result["passed"],
            "acceptance": quality_result["acceptance"],
            "metrics": quality_result["metrics"],
        }
        self._write_json(quality_report_path, quality_report)

        acceptance = {
            "canonical_generated": output_canonical_path.exists(),
            **quality_result["acceptance"],
        }

        summary: dict[str, Any] = {
            "stage": "stage_3",
            "timestamp": datetime.now().isoformat(),
            "builder_stats": hierarchy_result["stats"],
            "relation_refine_stats": refined_result["stats"],
            "quality": quality_result,
            "output_files": {
                "canonical_graph_json": str(output_canonical_path),
                "quality_report_json": str(quality_report_path),
                "concept_audit_json": str(concept_audit_path),
            },
            "acceptance": acceptance,
        }
        summary_path = self.config.output_dir / "stage3_summary.json"
        self._write_json(summary_path, summary)

        report: dict[str, Any] = {
            "stage": "stage_3",
            "dry_run": False,
            "timestamp": datetime.now().isoformat(),
            "status": "ok" if all(acceptance.values()) else "failed",
            "checks": checks
            | {
                "stage1_docs_exists": stage1_docs_path.exists(),
                "stage2_triples_exists": triples_path.exists(),
                "course_profile_exists": self.config.course_profile_path.exists(),
            },
            "summary_file": str(summary_path),
            "acceptance": acceptance,
            "builder_stats": hierarchy_result["stats"],
            "relation_refine_stats": refined_result["stats"],
            "quality_passed": quality_result["passed"],
        }
        report_path = self.config.output_dir / "stage3_run_report.json"
        self._write_json(report_path, report)
        self.logger.info("Pipeline report saved: %s", report_path)
        return report | {"report_path": str(report_path)}

    def run_stage4(self, dry_run: bool = False) -> dict[str, Any]:
        self.config.ensure_directories()
        checks = self._base_checks()

        canonical_path = self.config.output_dir / "big_data_kg.canonical.json"
        quality_report_path = self.config.output_dir / "quality_report.json"
        resource_report_path = self.config.output_dir / "resource_match_report.json"
        video_match_report_path = self.config.output_dir / "video_match_report.json"
        summary_path = self.config.output_dir / "stage4_summary.json"
        book_index_path = self.config.intermediate_dir / "book_index.json"
        video_transcript_dir = self.config.intermediate_dir / "video_transcripts"
        resource_match_config_path = self.config.config_dir / "resource_match.yaml"

        legacy_graph_path = self.config.project_root / "data" / "course" / "big_data.json"
        book_dir = self.config.project_root / "data" / "Book"
        video_urls_path = self.config.project_root / "data" / "Video" / "video_urls.json"

        pdf_files = sorted(book_dir.glob("*.pdf")) if book_dir.exists() else []
        stage4_checks = checks | {
            "stage3_canonical_exists": canonical_path.exists(),
            "book_dir_exists": book_dir.exists(),
            "book_pdf_count_positive": len(pdf_files) > 0,
            "video_urls_exists": video_urls_path.exists(),
            "legacy_graph_exists": legacy_graph_path.exists(),
            "resource_match_config_exists": resource_match_config_path.exists(),
        }

        if dry_run:
            report: dict[str, Any] = {
                "stage": "stage_4",
                "dry_run": True,
                "timestamp": datetime.now().isoformat(),
                "status": "ok",
                "checks": stage4_checks,
                "resource_inputs": {
                    "book_dir": str(book_dir),
                    "book_pdf_count": len(pdf_files),
                    "video_urls_path": str(video_urls_path),
                    "legacy_graph_path": str(legacy_graph_path),
                    "resource_match_config_path": str(resource_match_config_path),
                    "video_transcript_dir": str(video_transcript_dir),
                    "video_match_report_path": str(video_match_report_path),
                },
                "notes": [
                    "Stage 4 dry-run checks text/video resource matching prerequisites only.",
                    "No canonical graph update or resource assignment is executed.",
                ],
            }
            report_path = self.config.output_dir / "stage4_dry_run_report.json"
            self._write_json(report_path, report)
            self.logger.info("Pipeline report saved: %s", report_path)
            return report | {"report_path": str(report_path)}

        if not canonical_path.exists():
            self.logger.info("Stage3 canonical graph missing, running stage3 first.")
            self.run_stage3(dry_run=False)

        canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))

        book_indexer = BookIndexer(book_dir=book_dir, logger=self.logger)
        book_result = book_indexer.match(
            graph=canonical_payload,
            legacy_graph_path=legacy_graph_path if legacy_graph_path.exists() else None,
        )
        graph_with_books = book_result["graph"]
        self._write_json(book_index_path, book_result.get("book_index", {}))

        video_matcher = VideoMatcher(
            video_url_path=video_urls_path,
            logger=self.logger,
            settings_path=resource_match_config_path,
            transcript_cache_dir=video_transcript_dir,
        )
        video_result = video_matcher.match(
            graph=graph_with_books,
        )
        enriched_graph = video_result["graph"]
        resource_settings = ResourceMatchSettings.from_path(resource_match_config_path)

        meta = dict(enriched_graph.get("meta", {}) or {})
        resource_meta = dict(meta.get("resource_match", {}) or {})
        resource_meta["book"] = book_result.get("stats", {})
        resource_meta["video"] = video_result.get("stats", {})
        meta["resource_match"] = resource_meta
        enriched_graph["meta"] = meta
        self._write_json(canonical_path, enriched_graph)

        video_match_report = {
            "stage": "stage_4_video_match",
            "timestamp": datetime.now().isoformat(),
            "video_stats": video_result.get("stats", {}),
            "index_stats": video_result.get("index_stats", {}),
            "matches": video_result.get("matches", []),
            "video_transcripts_sample": video_result.get("transcripts", [])[:100],
            "output_files": {
                "video_transcript_dir": str(video_transcript_dir),
                "canonical_graph_json": str(canonical_path),
            },
        }
        self._write_json(video_match_report_path, video_match_report)

        resource_report = {
            "stage": "stage_4",
            "timestamp": datetime.now().isoformat(),
            "book_stats": book_result.get("stats", {}),
            "video_stats": video_result.get("stats", {}),
            "book_match_records_sample": book_result.get("matches", [])[:200],
            "video_match_records_sample": video_result.get("matches", [])[:200],
            "video_transcript_records_sample": video_result.get("transcripts", [])[:80],
            "output_files": {
                "canonical_graph_json": str(canonical_path),
                "book_index_json": str(book_index_path),
                "video_match_report_json": str(video_match_report_path),
                "video_transcript_dir": str(video_transcript_dir),
            },
        }
        self._write_json(resource_report_path, resource_report)

        quality_payload: dict[str, Any] = {}
        if quality_report_path.exists():
            try:
                quality_payload = json.loads(quality_report_path.read_text(encoding="utf-8"))
            except Exception:
                quality_payload = {}
        if not isinstance(quality_payload, dict):
            quality_payload = {}

        quality_metrics = dict(quality_payload.get("metrics", {}) or {})
        quality_metrics["concept_text_resource_coverage"] = book_result.get("stats", {}).get(
            "text_coverage_pct", 0.0
        )
        quality_metrics["video_match_rate"] = video_result.get("stats", {}).get(
            "video_match_rate_pct", 0.0
        )
        quality_metrics["video_transcript_coverage"] = video_result.get("stats", {}).get(
            "transcript_coverage_pct", 0.0
        )
        quality_metrics["avg_video_match_score"] = video_result.get("stats", {}).get(
            "avg_video_match_score", 0.0
        )

        quality_acceptance = dict(quality_payload.get("acceptance", {}) or {})
        target_video_match_rate = float(resource_settings.video.quality_targets.match_rate_pct)
        target_video_transcript_coverage = float(
            resource_settings.video.quality_targets.transcript_coverage_pct
        )
        quality_acceptance["concept_text_resource_coverage_100pct"] = (
            quality_metrics["concept_text_resource_coverage"] >= 99.99
        )
        quality_acceptance["video_match_rate_ge_target"] = (
            quality_metrics["video_match_rate"] >= target_video_match_rate
        )
        quality_acceptance["video_transcript_coverage_ge_target"] = (
            quality_metrics["video_transcript_coverage"] >= target_video_transcript_coverage
        )
        quality_acceptance["video_match_rate_reported"] = True
        quality_acceptance["video_transcript_coverage_reported"] = True
        quality_acceptance["avg_video_match_score_reported"] = True

        quality_payload["stage"] = "stage_4"
        quality_payload["timestamp"] = datetime.now().isoformat()
        quality_payload["metrics"] = quality_metrics
        quality_payload["acceptance"] = quality_acceptance
        quality_payload["passed"] = all(bool(flag) for flag in quality_acceptance.values())
        self._write_json(quality_report_path, quality_payload)

        acceptance = {
            "canonical_resource_enriched": canonical_path.exists(),
            "concept_text_resource_coverage_100pct": quality_acceptance[
                "concept_text_resource_coverage_100pct"
            ],
            "video_match_rate_ge_target": quality_acceptance["video_match_rate_ge_target"],
            "video_transcript_coverage_ge_target": quality_acceptance[
                "video_transcript_coverage_ge_target"
            ],
            "avg_video_match_score_reported": quality_acceptance["avg_video_match_score_reported"],
            "video_match_report_generated": video_match_report_path.exists(),
            "resource_match_report_generated": resource_report_path.exists(),
        }
        summary: dict[str, Any] = {
            "stage": "stage_4",
            "timestamp": datetime.now().isoformat(),
            "book_stats": book_result.get("stats", {}),
            "video_stats": video_result.get("stats", {}),
            "output_files": {
                "canonical_graph_json": str(canonical_path),
                "book_index_json": str(book_index_path),
                "resource_match_report_json": str(resource_report_path),
                "video_match_report_json": str(video_match_report_path),
                "quality_report_json": str(quality_report_path),
                "video_transcript_dir": str(video_transcript_dir),
            },
            "quality_targets": {
                "video_match_rate_pct": target_video_match_rate,
                "video_transcript_coverage_pct": target_video_transcript_coverage,
            },
            "acceptance": acceptance,
        }
        self._write_json(summary_path, summary)

        report: dict[str, Any] = {
            "stage": "stage_4",
            "dry_run": False,
            "timestamp": datetime.now().isoformat(),
            "status": "ok" if all(acceptance.values()) else "failed",
            "checks": stage4_checks,
            "summary_file": str(summary_path),
            "acceptance": acceptance,
            "book_stats": book_result.get("stats", {}),
            "video_stats": video_result.get("stats", {}),
        }
        report_path = self.config.output_dir / "stage4_run_report.json"
        self._write_json(report_path, report)
        self.logger.info("Pipeline report saved: %s", report_path)
        return report | {"report_path": str(report_path)}

    def run(
        self,
        stage: int = 0,
        dry_run: bool = False,
        kggen_doc_limit: int = 5,
        max_chars_per_doc: int = 1200,
    ) -> dict[str, Any]:
        if stage == 0:
            return self.run_stage0(dry_run=dry_run)
        if stage == 1:
            return self.run_stage1(dry_run=dry_run)
        if stage == 2:
            return self.run_stage2(
                dry_run=dry_run,
                kggen_doc_limit=kggen_doc_limit,
                max_chars_per_doc=max_chars_per_doc,
            )
        if stage == 3:
            return self.run_stage3(dry_run=dry_run)
        if stage == 4:
            return self.run_stage4(dry_run=dry_run)
        raise ValueError(f"Unsupported stage: {stage}")
