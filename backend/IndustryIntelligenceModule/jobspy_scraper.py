"""JobSpy scraper adapter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple


_WORKER_SCRIPT = """
import io
import json
import math
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, sys.argv[1])

from jobspy import scrape_jobs

sites = json.loads(sys.argv[2])
keyword = sys.argv[3]
country = sys.argv[4]
city = sys.argv[5]
limit = int(sys.argv[6])
fetch_desc = sys.argv[7] == 'true'
indeed_country = sys.argv[8]

location = country if city == '全国' else city
params = {
    'site_name': sites,
    'search_term': keyword,
    'location': location,
    'results_wanted': limit,
    'verbose': 0,
    'linkedin_fetch_description': fetch_desc,
}

if 'indeed' in sites and indeed_country:
    params['country_indeed'] = indeed_country

df = scrape_jobs(**params)


def safe_float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def format_k(value):
    if value is None:
        return None
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else str(rounded)


def format_salary(row):
    import re

    min_amount = safe_float(row.get('min_amount'))
    max_amount = safe_float(row.get('max_amount'))
    interval = str(row.get('interval') or '')

    if min_amount is not None or max_amount is not None:
        def to_k(value):
            if value is None:
                return None
            if interval == 'yearly':
                value = value / 12
            return value / 1000

        low = to_k(min_amount)
        high = to_k(max_amount)
        if low is not None and high is not None:
            return f"{format_k(low)}K-{format_k(high)}K"
        if low is not None:
            return f"{format_k(low)}K+"
        if high is not None:
            return f"{format_k(high)}K"

    desc = str(row.get('description') or '')
    patterns = [
        r'(\\d+\\.?\\d*)[Kk]\\s*[-~到]\\s*(\\d+\\.?\\d*)[Kk]',
        r'(\\d{4,6})\\s*[-~到]\\s*(\\d{4,6})\\s*[元/]',
        r'\\$\\s*(\\d[\\d,]*)\\s*[-–]\\s*\\$\\s*(\\d[\\d,]*)',
        r'(\\d+\\.?\\d*)[Kk]\\s*[-–]\\s*(\\d+\\.?\\d*)[Kk]',
    ]

    for pattern in patterns:
        match = re.search(pattern, desc, re.IGNORECASE)
        if not match:
            continue
        low_raw = match.group(1).replace(',', '')
        high_raw = match.group(2).replace(',', '')
        low = safe_float(low_raw)
        high = safe_float(high_raw)
        if low is None or high is None:
            continue
        if low > 1000:
            low = low / 1000
            high = high / 1000
        return f"{format_k(low)}K-{format_k(high)}K"

    return '面议'


def format_location(row, country_name):
    location = row.get('location')
    if location is None:
        return ''
    parts = [part.strip() for part in str(location).split(',')]
    city_parts = [part for part in parts if part not in (country_name, 'China', 'CN', 'USA', 'US', 'United States', '')]
    return city_parts[0] if city_parts else str(location)


def clean_string(value):
    if value is None:
        return ''
    text = str(value)
    return '' if text.lower() in ('none', 'nan') else text


jobs = []
for _, row in df.iterrows():
    jobs.append({
        'title': clean_string(row.get('title')),
        'company': clean_string(row.get('company')),
        'salary': format_salary(row),
        'location': format_location(row, country),
        'experience': '',
        'education': '',
        'description': clean_string(row.get('description')),
        'requirements': '',
        'source': clean_string(row.get('site')).capitalize(),
    })

print(json.dumps(jobs, ensure_ascii=False))
"""

COUNTRY_CONFIG = {
    "中国": {"jobspy_location": "China", "indeed_country": "China"},
    "美国": {"jobspy_location": "United States", "indeed_country": "USA"},
    "新加坡": {"jobspy_location": "Singapore", "indeed_country": "Singapore"},
}


class JobSpyScraper:
    """Run JobSpy in subprocesses and merge normalized results."""

    def __init__(self, sites: List[str] | None = None, fetch_linkedin_desc: bool = True):
        self.sites = sites or ["linkedin", "indeed"]
        self.fetch_linkedin_desc = fetch_linkedin_desc
        self.jobspy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "JobSpy"))
        self.linkedin_timeout = int(os.getenv("INDUSTRY_LINKEDIN_TIMEOUT", "60"))
        self.indeed_timeout = int(os.getenv("INDUSTRY_INDEED_TIMEOUT", "45"))
        self.keyword_workers = max(1, min(int(os.getenv("INDUSTRY_KEYWORD_WORKERS", "3")), 4))

    def _sanitize_sites(self, country: str) -> tuple[List[str], List[str]]:
        sites = list(self.sites)
        warnings: List[str] = []
        if country not in COUNTRY_CONFIG:
            raise RuntimeError(f"当前暂不支持国家/地区: {country}")
        if "glassdoor" in sites:
            sites = [site for site in sites if site != "glassdoor"]
            warnings.append("已自动移除 Glassdoor：当前地区不支持该数据源。")
        return sites, warnings

    def _site_strategy(self, site: str, country: str, city: str, limit: int) -> Tuple[int, bool, int, List[str]]:
        warnings: List[str] = []
        effective_limit = limit
        fetch_desc = self.fetch_linkedin_desc
        timeout = self.linkedin_timeout if site == "linkedin" else self.indeed_timeout

        if site == "linkedin" and city == "全国":
            if effective_limit > 35:
                effective_limit = 35
                warnings.append(f"LinkedIn 全国搜索已自动限制为 {effective_limit} 条，以提升返回速度。")

        if site == "linkedin":
            timeout = min(timeout, 60) if not fetch_desc else max(timeout, 90)

        return effective_limit, fetch_desc, timeout, warnings

    def _summarize_error(self, site: str, error_text: str) -> str:
        compact = " ".join(str(error_text or "").split())
        lowered = compact.lower()
        if "cannot convert float nan to integer" in lowered or "nan" in lowered:
            return f"{site}: 数据格式异常，已跳过"
        if "ssl" in lowered or "ssleoferror" in lowered or "unexpected_eof_while_reading" in lowered:
            return f"{site}: 网络连接不稳定，已跳过"
        if "timed out" in lowered or "timeout" in lowered:
            return f"{site}: 抓取超时，已跳过"
        if "max retries exceeded" in lowered:
            return f"{site}: 请求重试失败，已跳过"
        return f"{site}: 抓取失败，已跳过"

    def _run_single_site(self, site: str, keyword: str, country: str, city: str, limit: int) -> Tuple[List[Dict], List[str]]:
        effective_limit, fetch_desc, timeout, warnings = self._site_strategy(site, country, city, limit)
        country_config = COUNTRY_CONFIG.get(country, COUNTRY_CONFIG["中国"])
        country_location = country_config["jobspy_location"]
        indeed_country = country_config["indeed_country"] if site == "indeed" else ""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(_WORKER_SCRIPT)
            script_path = handle.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    script_path,
                    self.jobspy_path,
                    json.dumps([site], ensure_ascii=False),
                    keyword,
                    country_location,
                    city,
                    str(effective_limit),
                    "true" if fetch_desc else "false",
                    indeed_country,
                ],
                capture_output=True,
                timeout=timeout,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            if result.returncode != 0:
                raise RuntimeError(stderr or stdout or f"{site} 返回异常")
            last_line = stdout.strip().splitlines()[-1] if stdout.strip() else "[]"
            return json.loads(last_line), warnings
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)

    def _dedupe_jobs(self, jobs: List[Dict]) -> List[Dict]:
        deduped = []
        seen = set()
        for job in jobs:
            key = (
                (job.get("source") or "").strip().lower(),
                (job.get("title") or "").strip().lower(),
                (job.get("company") or "").strip().lower(),
                (job.get("location") or "").strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(job)
        return deduped

    def _normalize_keywords(self, keyword: str | List[str]) -> List[str]:
        if isinstance(keyword, str):
            items = [keyword]
        else:
            items = list(keyword or [])

        normalized: List[str] = []
        seen = set()
        for item in items:
            cleaned = " ".join(str(item or "").split()).strip(" ,;/|")
            if len(cleaned) < 2:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _keyword_limit(self, index: int, base_limit: int) -> int:
        if index == 0:
            return base_limit
        return max(8, min(25, max(base_limit // 2, 10)))

    def _search_single_keyword(self, keyword: str, country: str, city: str, limit: int) -> List[Dict]:
        sites, warnings = self._sanitize_sites(country)
        if not sites:
            raise RuntimeError("当前没有可用数据源，请至少选择 linkedin 或 indeed。")

        all_jobs: List[Dict] = []
        errors: List[str] = []
        combined_warnings = list(warnings)
        max_workers = min(len(sites), 2)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self._run_single_site, site, keyword, country, city, limit): site for site in sites}
            for future in as_completed(future_map):
                site = future_map[future]
                try:
                    site_jobs, site_warnings = future.result()
                    all_jobs.extend(site_jobs)
                    combined_warnings.extend(site_warnings)
                except subprocess.TimeoutExpired:
                    errors.append(f"{site}: 抓取超时，已跳过")
                except Exception as exc:
                    errors.append(self._summarize_error(site, str(exc)))

        if not all_jobs and errors:
            raise RuntimeError("；".join(errors))

        jobs = self._dedupe_jobs(all_jobs)
        if errors:
            combined_warnings.append("部分数据源抓取失败：" + "；".join(errors))
        combined_warnings = [item for item in dict.fromkeys(combined_warnings) if item]
        if combined_warnings:
            warning_text = "；".join(combined_warnings)
            for job in jobs:
                job["source_warning"] = warning_text
        for job in jobs:
            job["search_keyword"] = keyword
        return jobs

    def search_jobs(self, keyword: str | List[str], country: str = "中国", city: str = "全国", limit: int = 20) -> List[Dict]:
        keywords = self._normalize_keywords(keyword)
        if not keywords:
            return []

        all_jobs: List[Dict] = []
        errors: List[str] = []
        worker_count = min(len(keywords[:6]), self.keyword_workers)

        with ThreadPoolExecutor(max_workers=max(1, worker_count)) as executor:
            future_map = {}
            for index, term in enumerate(keywords[:6]):
                term_limit = self._keyword_limit(index, limit)
                future = executor.submit(self._search_single_keyword, term, country, city, term_limit)
                future_map[future] = term

            for future in as_completed(future_map):
                term = future_map[future]
                try:
                    all_jobs.extend(future.result())
                except Exception as exc:
                    errors.append(f"{term}: {exc}")

        if not all_jobs and errors:
            raise RuntimeError("；".join(errors))

        jobs = self._dedupe_jobs(all_jobs)
        if errors:
            warning_text = "部分搜索词抓取失败：" + "；".join(errors)
            for job in jobs:
                existing = job.get("source_warning", "")
                job["source_warning"] = f"{existing}；{warning_text}".strip("；") if existing else warning_text
        return jobs




