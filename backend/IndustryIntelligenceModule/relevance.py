"""Keyword relevance scoring."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


class KeywordRelevanceFilter:
    """Rule-based keyword relevance scorer with non-job suppression."""

    NON_JOB_PATTERNS = [
        "培训", "招生", "课程", "实训", "训练营", "特训营", "就业班", "公开课", "试听",
        "学员", "讲师", "招生老师", "培训机构", "咨询报名"
    ]

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip()).lower()

    def _tokenize_keyword(self, keyword: str) -> List[str]:
        keyword = self._normalize(keyword)
        if not keyword:
            return []
        tokens = [keyword]
        parts = [part for part in re.split(r"[\s/,+，、]+", keyword) if part]
        for part in parts:
            if part not in tokens:
                tokens.append(part)
        return tokens

    def _looks_like_non_job_listing(self, job: Dict) -> bool:
        combined = self._normalize(
            f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}"
        )
        return any(token in combined for token in self.NON_JOB_PATTERNS)

    def score_job(self, job: Dict, keyword: str) -> Tuple[int, List[str]]:
        if self._looks_like_non_job_listing(job):
            return -50, ["疑似培训/招生/课程信息，已降权"]

        tokens = self._tokenize_keyword(keyword)
        if not tokens:
            return 0, []

        title = self._normalize(job.get("title", ""))
        description = self._normalize(job.get("description", ""))
        requirements = self._normalize(job.get("requirements", ""))
        company = self._normalize(job.get("company", ""))

        score = 0
        reasons: List[str] = []

        for token in tokens:
            if token in title:
                score += 8
                reasons.append(f"标题命中: {token}")
            elif any(part and part in title for part in token.split() if len(part) >= 2):
                score += 4
                reasons.append(f"标题部分命中: {token}")

            if token in description:
                score += 3
                reasons.append(f"描述命中: {token}")
            if token in requirements:
                score += 2
                reasons.append(f"要求命中: {token}")
            if token in company:
                score += 1
                reasons.append(f"公司字段命中: {token}")

        unique_reasons: List[str] = []
        seen = set()
        for reason in reasons:
            if reason in seen:
                continue
            seen.add(reason)
            unique_reasons.append(reason)

        return score, unique_reasons

    def rank_jobs(self, jobs: List[Dict], keyword: str) -> List[Dict]:
        ranked: List[Dict] = []
        for job in jobs:
            score, reasons = self.score_job(job, keyword)
            enriched = dict(job)
            enriched["relevance_score"] = score
            enriched["relevance_reasons"] = reasons
            ranked.append(enriched)

        ranked.sort(
            key=lambda item: (
                item.get("relevance_score", 0),
                len(item.get("description", "") or ""),
                len(item.get("title", "") or ""),
            ),
            reverse=True,
        )
        return ranked
