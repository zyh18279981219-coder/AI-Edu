"""Service layer for industry intelligence."""

from __future__ import annotations

import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

from IndustryIntelligenceModule.analyzer import SkillAnalyzer
from IndustryIntelligenceModule.jobspy_scraper import JobSpyScraper
from IndustryIntelligenceModule.relevance import KeywordRelevanceFilter


COUNTRY_OPTIONS = {
    "中国": {
        "jobspy_location": "China",
        "indeed_country": "China",
        "cities": ["全国", "北京", "上海", "深圳", "杭州", "广州"],
    },
    "美国": {
        "jobspy_location": "United States",
        "indeed_country": "USA",
        "cities": ["全国", "New York, NY", "San Francisco, CA", "Seattle, WA", "Austin, TX"],
    },
    "新加坡": {
        "jobspy_location": "Singapore",
        "indeed_country": "Singapore",
        "cities": ["全国", "Singapore"],
    },
}
CITY_OPTIONS = COUNTRY_OPTIONS["中国"]["cities"]
SOURCE_OPTIONS = ["linkedin", "indeed"]
PARALLEL_COUNTRIES = ["中国", "美国", "新加坡"]
StatusCallback = Optional[Callable[[str, str, Dict], None]]

EXPERIENCE_BUCKETS = ["不限", "1年以下", "1-3年", "3-5年", "5-10年", "10年以上"]
EDUCATION_BUCKETS = ["不限", "大专及以上", "本科及以上", "硕士及以上", "博士及以上"]


class IndustryIntelligenceService:
    """Collect, analyze, and serialize industry intelligence data."""

    def __init__(self):
        self.relevance_filter = KeywordRelevanceFilter()
        self.analyzer = SkillAnalyzer()

    def _collect_single_region(
        self,
        keyword: str,
        country: str,
        city: str,
        job_limit: int,
        relevance_threshold: int,
        sources: List[str],
        fetch_desc: bool,
        status_callback: StatusCallback = None,
        allow_status_updates: bool = True,
    ) -> Dict:
        target_total = max(job_limit * len(sources), job_limit)
        fetch_step = max(target_total, job_limit * 2)
        max_fetch_limit = max(
            target_total,
            int(os.getenv("INDUSTRY_MAX_FETCH_LIMIT", str(max(120, target_total * 4)))),
        )

        search_terms = self.analyzer.generate_search_terms(keyword, country)
        scoring_terms = list(search_terms)
        if keyword and keyword not in scoring_terms:
            scoring_terms.append(keyword)
        scoring_keyword = " / ".join(scoring_terms)

        scraper = JobSpyScraper(sites=sources, fetch_linkedin_desc=fetch_desc)
        current_limit = min(max_fetch_limit, max(fetch_step, target_total))
        final_raw_jobs: List[Dict] = []
        final_ranked_jobs: List[Dict] = []
        selected_jobs: List[Dict] = []
        stagnant_rounds = 0
        previous_raw_count = -1
        previous_selected_count = -1
        rounds = 0

        while True:
            rounds += 1
            if status_callback and allow_status_updates:
                status_callback(
                    "collecting",
                    f"[{country}] 第 {rounds} 轮抓取中，当前抓取上限 {current_limit} 条，搜索词：{', '.join(search_terms)}",
                    {
                        "step": 1,
                        "round": rounds,
                        "fetch_limit": current_limit,
                        "target_total": target_total,
                        "search_terms": search_terms,
                        "country": country,
                    },
                )

            raw_jobs = scraper.search_jobs(search_terms, country, city, current_limit)
            ranked_jobs = self.relevance_filter.rank_jobs(raw_jobs, scoring_keyword)
            kept_jobs = [job for job in ranked_jobs if job.get("relevance_score", 0) >= relevance_threshold]
            selected_jobs = kept_jobs[:target_total]
            for job in selected_jobs:
                job["market_country"] = country
            final_raw_jobs = raw_jobs
            final_ranked_jobs = ranked_jobs

            if status_callback and allow_status_updates:
                status_callback(
                    "filtering",
                    (
                        f"[{country}] 第 {rounds} 轮抓取到 {len(raw_jobs)} 条原始职位，"
                        f"其中 {len(kept_jobs)} 条达到相关性阈值 {relevance_threshold}。"
                    ),
                    {
                        "step": 2,
                        "round": rounds,
                        "raw_count": len(raw_jobs),
                        "threshold_kept_count": len(kept_jobs),
                        "target_total": target_total,
                        "fetch_limit": current_limit,
                        "search_terms": search_terms,
                        "country": country,
                    },
                )

            if len(selected_jobs) >= target_total:
                break
            if current_limit >= max_fetch_limit:
                break

            if len(raw_jobs) <= previous_raw_count and len(selected_jobs) <= previous_selected_count:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            if stagnant_rounds >= 1:
                break

            previous_raw_count = len(raw_jobs)
            previous_selected_count = len(selected_jobs)
            current_limit = min(max_fetch_limit, current_limit + fetch_step)

        source_counts = Counter(job.get("source", "Unknown") for job in final_raw_jobs)
        warnings = sorted({job.get("source_warning", "").strip() for job in final_raw_jobs if job.get("source_warning")})
        threshold_kept_count = sum(1 for job in final_ranked_jobs if job.get("relevance_score", 0) >= relevance_threshold)
        selected_count = len(selected_jobs)

        relevance_summary = {
            "input_count": len(final_raw_jobs),
            "requested_count": target_total,
            "threshold": relevance_threshold,
            "threshold_kept_count": threshold_kept_count,
            "selected_count": selected_count,
            "dropped_count": max(0, len(final_ranked_jobs) - selected_count),
            "backfilled_count": 0,
            "strict_threshold": True,
            "fetch_rounds": rounds,
            "final_fetch_limit": current_limit,
            "max_fetch_limit": max_fetch_limit,
            "completed_target": selected_count >= target_total,
            "country": country,
            "city": city,
            "search_terms": search_terms,
        }

        if selected_count < target_total:
            warnings.append(
                f"[{country}] 已按严格阈值 {relevance_threshold} 筛选，并自动扩大抓取范围；达到最大抓取上限后仍仅找到 {selected_count} 条符合条件的职位。"
            )

        return {
            "jobs": selected_jobs,
            "raw_count": len(final_raw_jobs),
            "source_counts": dict(source_counts),
            "relevance_summary": relevance_summary,
            "warnings": warnings,
        }

    def collect_jobs(
        self,
        keyword: str,
        country: str,
        city: str,
        job_limit: int,
        relevance_threshold: int,
        sources: List[str],
        fetch_desc: bool,
        status_callback: StatusCallback = None,
        include_global: bool = False,
    ) -> Dict:
        if not include_global:
            return self._collect_single_region(
                keyword=keyword,
                country=country,
                city=city,
                job_limit=job_limit,
                relevance_threshold=relevance_threshold,
                sources=sources,
                fetch_desc=fetch_desc,
                status_callback=status_callback,
                allow_status_updates=True,
            )

        countries = list(PARALLEL_COUNTRIES)
        if status_callback:
            status_callback(
                "collecting",
                "已开启国内+海外并行抓取，正在同时处理中国、美国、新加坡。",
                {"step": 1, "countries": countries, "parallel": True},
            )

        collected_results: List[Dict] = []
        errors: List[str] = []
        with ThreadPoolExecutor(max_workers=min(len(countries), 3)) as executor:
            future_map = {
                executor.submit(
                    self._collect_single_region,
                    keyword,
                    region,
                    "全国",
                    job_limit,
                    relevance_threshold,
                    sources,
                    fetch_desc,
                    None,
                    False,
                ): region
                for region in countries
            }
            for future in as_completed(future_map):
                region = future_map[future]
                try:
                    collected_results.append(future.result())
                except Exception as exc:
                    errors.append(f"[{region}] {exc}")

        combined_jobs: List[Dict] = []
        combined_source_counts = Counter()
        warnings: List[str] = []
        search_terms_map: Dict[str, List[str]] = {}
        total_raw_count = 0
        total_requested = 0
        total_threshold_kept = 0
        total_selected = 0
        max_rounds = 0
        max_fetch_limit = 0

        for result in collected_results:
            combined_jobs.extend(result.get("jobs", []))
            combined_source_counts.update(result.get("source_counts", {}))
            total_raw_count += int(result.get("raw_count", 0) or 0)
            warnings.extend(result.get("warnings", []))
            summary = result.get("relevance_summary", {})
            total_requested += int(summary.get("requested_count", 0) or 0)
            total_threshold_kept += int(summary.get("threshold_kept_count", 0) or 0)
            total_selected += int(summary.get("selected_count", 0) or 0)
            max_rounds = max(max_rounds, int(summary.get("fetch_rounds", 0) or 0))
            max_fetch_limit = max(max_fetch_limit, int(summary.get("final_fetch_limit", 0) or 0))
            if summary.get("country"):
                search_terms_map[summary["country"]] = list(summary.get("search_terms", []) or [])

        warnings = [item for item in dict.fromkeys(warnings) if item]
        if errors:
            warnings.append("部分地区抓取失败，系统已自动使用可用地区结果继续分析。")

        combined_summary = {
            "input_count": total_raw_count,
            "requested_count": total_requested,
            "threshold": relevance_threshold,
            "threshold_kept_count": total_threshold_kept,
            "selected_count": total_selected,
            "dropped_count": max(0, total_raw_count - total_selected),
            "backfilled_count": 0,
            "strict_threshold": True,
            "fetch_rounds": max_rounds,
            "final_fetch_limit": max_fetch_limit,
            "max_fetch_limit": max_fetch_limit,
            "completed_target": total_selected >= total_requested and total_requested > 0,
            "country": "国内+海外",
            "city": "全国",
            "search_terms": [f"{name}: {', '.join(terms)}" for name, terms in search_terms_map.items() if terms],
            "parallel": True,
            "included_countries": countries,
        }

        return {
            "jobs": combined_jobs,
            "raw_count": total_raw_count,
            "source_counts": dict(combined_source_counts),
            "relevance_summary": combined_summary,
            "warnings": warnings,
        }

    def analyze_jobs(self, jobs: List[Dict], status_callback: StatusCallback = None) -> List[Dict]:
        if not jobs:
            return []
        return self.analyzer.batch_extract(jobs, status_callback=status_callback)

    def run_full_analysis(
        self,
        keyword: str,
        country: str,
        city: str,
        job_limit: int,
        relevance_threshold: int,
        sources: List[str],
        fetch_desc: bool,
        status_callback: StatusCallback = None,
        include_global: bool = False,
    ) -> Dict:
        collected = self.collect_jobs(
            keyword=keyword,
            country=country,
            city=city,
            job_limit=job_limit,
            relevance_threshold=relevance_threshold,
            sources=sources,
            fetch_desc=fetch_desc,
            status_callback=status_callback,
            include_global=include_global,
        )

        if status_callback:
            total = len(collected["jobs"])
            status_callback(
                "analyzing",
                f"正在用 LLM 解析 {total} 条职位的技能与要求...",
                {"step": 3, "current": 0, "total": total},
            )

        analyzed_jobs = self.analyze_jobs(collected["jobs"], status_callback=status_callback)

        if status_callback:
            status_callback("rendering", "正在整理图表和统计摘要...", {"step": 4})

        return self.build_payload(
            analyzed_jobs,
            raw_count=collected["raw_count"],
            source_counts=collected["source_counts"],
            relevance_summary=collected["relevance_summary"],
            warnings=collected["warnings"],
        )

    def build_payload(self, jobs: List[Dict], raw_count: int | None = None, source_counts: Dict[str, int] | None = None, relevance_summary: Dict | None = None, warnings: List[str] | None = None) -> Dict:
        normalized_jobs = [self._normalize_job(job) for job in list(jobs or [])]
        all_skills = [skill for job in normalized_jobs for skill in job.get("skills", [])]
        skill_counter = Counter(all_skills)
        job_counter = Counter(job.get("title", "未知岗位") for job in normalized_jobs if job.get("title"))
        experience_counter = self._ordered_counter(job.get("experience", "") for job in normalized_jobs if job.get("experience") in EXPERIENCE_BUCKETS)
        education_counter = self._ordered_counter(job.get("education", "") for job in normalized_jobs if job.get("education") in EDUCATION_BUCKETS)

        summary = {
            "total_jobs": len(normalized_jobs),
            "total_skills": len(skill_counter),
            "avg_skills_per_job": round(len(all_skills) / len(normalized_jobs), 1) if normalized_jobs else 0,
            "top_skill": skill_counter.most_common(1)[0][0] if skill_counter else None,
            "top_skill_count": skill_counter.most_common(1)[0][1] if skill_counter else 0,
            "top_job": job_counter.most_common(1)[0][0] if job_counter else None,
            "top_job_count": job_counter.most_common(1)[0][1] if job_counter else 0,
        }

        return {
            "jobs": normalized_jobs,
            "metrics": {
                "jobs_total": len(normalized_jobs),
                "jobs_analyzed": sum(1 for job in normalized_jobs if job.get("skills")),
                "skills_total": len(skill_counter),
                "sources_total": len({job.get("source", "") for job in normalized_jobs if job.get("source")}),
            },
            "summary": summary,
            "raw_count": raw_count if raw_count is not None else len(normalized_jobs),
            "source_counts": source_counts or {},
            "relevance_summary": relevance_summary or {},
            "relevance_message": self._build_relevance_message(relevance_summary or {}),
            "warnings": warnings or [],
            "charts": {
                "skill_ranking": self._counter_rows(skill_counter, top_n=15),
                "job_distribution": self._counter_rows(job_counter, top_n=10),
                "experience_distribution": self._bucket_rows(experience_counter, EXPERIENCE_BUCKETS),
                "education_distribution": self._bucket_rows(education_counter, EDUCATION_BUCKETS),
                "skill_heatmap": self._build_heatmap(normalized_jobs),
            },
        }

    def _normalize_job(self, job: Dict) -> Dict:
        normalized = dict(job)
        normalized["skills"] = list(job.get("skills") or [])
        normalized["skill_evidence"] = list(job.get("skill_evidence") or [])
        normalized["relevance_reasons"] = list(job.get("relevance_reasons") or [])
        normalized["title"] = job.get("title", "")
        normalized["company"] = job.get("company", "")
        normalized["salary"] = job.get("salary", "面议")
        normalized["experience"] = self._normalize_experience(job.get("experience", ""))
        normalized["education"] = self._normalize_education(job.get("education", ""))
        normalized["location"] = job.get("location", "")
        normalized["source"] = job.get("source", "")
        normalized["requirements"] = job.get("requirements", "")
        normalized["description"] = job.get("description", "")
        normalized["relevance_score"] = int(job.get("relevance_score", 0) or 0)
        normalized["market_country"] = job.get("market_country", "")

        has_substantive_text = bool(str(normalized["description"] or "").strip()) or bool(str(normalized["requirements"] or "").strip())
        if not has_substantive_text:
            normalized["skills"] = []
            normalized["skill_evidence"] = []

        return normalized

    def _normalize_experience(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return "不限"
        compact = value.lower().replace("年以上", "年").replace("年及以上", "年").replace("以上经验", "年经验").replace("工作经验", "经验").replace("years", "year")
        compact = compact.replace("1 year", "1年").replace("2 year", "2年").replace("3 year", "3年")
        compact = re.sub(r"\s+", "", compact)
        if any(token in compact for token in ["不限", "应届", "校招", "实习", "无经验", "经验不限", "无要求"]):
            return "不限"
        if any(token in compact for token in ["年龄", "岁", "专业", "本科", "硕士", "博士", "学历"]):
            return "不限"
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-~到至]\s*(\d+(?:\.\d+)?)\s*年", compact)
        if range_match:
            return self._experience_bucket_from_range(float(range_match.group(1)), float(range_match.group(2)))
        plus_match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:经验)?(?:以上)?", compact)
        if plus_match:
            return self._experience_bucket_from_min(float(plus_match.group(1)))
        month_match = re.search(r"(\d+)\s*(个月|月)", compact)
        if month_match:
            return "1年以下" if int(month_match.group(1)) < 12 else "1-3年"
        return "不限"

    def _experience_bucket_from_range(self, start: float, end: float) -> str:
        if end < 1:
            return "1年以下"
        if start < 1 and end <= 3:
            return "1年以下"
        if end <= 3:
            return "1-3年"
        if end <= 5:
            return "3-5年" if start >= 3 else "1-3年"
        if end <= 10:
            return "5-10年" if start >= 5 else "3-5年"
        return "10年以上"

    def _experience_bucket_from_min(self, year: float) -> str:
        if year < 1:
            return "1年以下"
        if year < 3:
            return "1-3年"
        if year < 5:
            return "3-5年"
        if year < 10:
            return "5-10年"
        return "10年以上"

    def _normalize_education(self, text: str) -> str:
        value = str(text or "").strip()
        if not value:
            return "不限"
        compact = re.sub(r"\s+", "", value.lower().replace("学历要求", "").replace("学历", ""))
        if any(token in compact for token in ["不限", "无要求", "无学历要求", "学历不限"]):
            return "不限"
        if any(token in compact for token in ["博士后", "phd", "doctorate", "博士研究生", "博士"]):
            return "博士及以上"
        if any(token in compact for token in ["硕士", "研究生", "master", "mba", "ma", "ms"]):
            return "硕士及以上"
        if any(token in compact for token in ["本科", "学士", "bachelor", "大学本科", "统招本科", "全日制本科"]):
            return "本科及以上"
        if any(token in compact for token in ["大专", "专科", "高职", "college", "juniorcollege"]):
            return "大专及以上"
        if any(token in compact for token in ["专业", "计算机", "软件工程", "数学", "统计", "信息", "自动化", "电子", "通信"]):
            return "不限"
        return "不限"

    def _ordered_counter(self, values) -> Counter:
        return Counter(list(values))

    def _counter_rows(self, counter: Counter, top_n: int | None = None) -> List[Dict]:
        rows = [{"name": name, "value": value} for name, value in counter.most_common(top_n)]
        return [row for row in rows if row["name"]]

    def _bucket_rows(self, counter: Counter, buckets: List[str]) -> List[Dict]:
        return [{"name": bucket, "value": counter.get(bucket, 0)} for bucket in buckets if counter.get(bucket, 0)]

    def _normalize_job_title(self, title: str) -> str:
        """Fuzzy-merge similar job titles into a canonical short form."""
        t = re.sub(r"\s+", "", (title or "").strip().lower())
        if not t:
            return "其他"
        # Strip common prefixes/suffixes that fragment titles
        t = re.sub(r"^(senior|sr\.?|junior|jr\.?|lead|staff|principal|intern|实习|高级|资深|首席|中级|初级)", "", t)
        t = re.sub(r"(工程师|专员|专家|顾问|经理|主管|总监|助理|实习生)$", "", t)
        t = t.strip(" -—·/")
        # Map to canonical categories by keyword matching
        mappings = [
            ("数据分析", "数据分析"),
            ("dataanaly", "数据分析"),
            ("businessintelligence", "BI分析"),
            ("bi分析", "BI分析"),
            ("商业分析", "商业分析"),
            ("businessanaly", "商业分析"),
            ("数据开发", "数据开发"),
            ("大数据", "大数据开发"),
            ("bigdata", "大数据开发"),
            ("dataengineer", "数据开发"),
            ("数据仓库", "数仓开发"),
            ("数仓", "数仓开发"),
            ("datawarehouse", "数仓开发"),
            ("etl", "ETL开发"),
            ("算法", "算法"),
            ("algorithm", "算法"),
            ("机器学习", "机器学习"),
            ("machinelearning", "机器学习"),
            ("深度学习", "深度学习"),
            ("deeplearning", "深度学习"),
            ("人工智能", "AI"),
            ("ai", "AI"),
            ("nlp", "NLP"),
            ("自然语言", "NLP"),
            ("cv", "计算机视觉"),
            ("computervision", "计算机视觉"),
            ("大模型", "大模型"),
            ("llm", "大模型"),
            ("数据挖掘", "数据挖掘"),
            ("datamining", "数据挖掘"),
            ("数据科学", "数据科学"),
            ("datascien", "数据科学"),
            ("产品", "产品经理"),
            ("product", "产品经理"),
            ("运营", "运营"),
            ("operation", "运营"),
            ("后端", "后端开发"),
            ("backend", "后端开发"),
            ("前端", "前端开发"),
            ("frontend", "前端开发"),
            ("全栈", "全栈开发"),
            ("fullstack", "全栈开发"),
            ("测试", "测试"),
            ("qa", "测试"),
            ("test", "测试"),
            ("devops", "DevOps"),
            ("运维", "运维"),
            ("sre", "SRE"),
            ("安全", "安全"),
            ("security", "安全"),
        ]
        for keyword, category in mappings:
            if keyword in t:
                return category
        return title.strip() or "其他"

    def _build_heatmap(self, jobs: List[Dict], top_n_skills: int = 15, top_n_jobs: int = 8) -> Dict:
        skill_counter = Counter()
        job_counter = Counter()
        pairs = Counter()
        for job in jobs:
            title = self._normalize_job_title(job.get("title", ""))
            job_counter[title] += 1
            for skill in job.get("skills", []):
                skill_counter[skill] += 1
                pairs[(title, skill)] += 1
        top_skills = [name for name, _ in skill_counter.most_common(top_n_skills)]
        top_jobs = [name for name, _ in job_counter.most_common(top_n_jobs)]
        matrix = []
        for job_index, job_name in enumerate(top_jobs):
            for skill_index, skill_name in enumerate(top_skills):
                value = pairs.get((job_name, skill_name), 0)
                if value:
                    matrix.append([skill_index, job_index, value])
        return {"skills": top_skills, "jobs": top_jobs, "matrix": matrix}

    def _build_relevance_message(self, relevance_summary: Dict) -> str:
        if not relevance_summary:
            return ""
        requested = int(relevance_summary.get("requested_count", 0) or 0)
        threshold = int(relevance_summary.get("threshold", 0) or 0)
        threshold_kept = int(relevance_summary.get("threshold_kept_count", 0) or 0)
        selected_count = int(relevance_summary.get("selected_count", 0) or 0)
        rounds = int(relevance_summary.get("fetch_rounds", 1) or 1)
        final_fetch_limit = int(relevance_summary.get("final_fetch_limit", 0) or 0)
        completed_target = bool(relevance_summary.get("completed_target", False))
        country = relevance_summary.get("country", "")
        city = relevance_summary.get("city", "")
        search_terms = relevance_summary.get("search_terms", []) or []
        location_text = f"{country}-{city}" if country and city else city or country
        search_text = f"，搜索词：{' | '.join(search_terms)}" if search_terms else ""
        if completed_target:
            return f"当前已按严格相关性阈值 {threshold} 筛选，在 {location_text} 共抓取 {rounds} 轮、最终抓取上限扩展到 {final_fetch_limit} 条，并保留 {selected_count}/{requested} 条高相关职位{search_text}。"
        return f"当前已按严格相关性阈值 {threshold} 筛选，并在 {location_text} 自动扩大抓取范围；共抓取 {rounds} 轮后，仅找到 {threshold_kept} 条符合条件的职位，因此当前展示 {selected_count} 条{search_text}。"

