"""LLM-backed job skill extraction."""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import JSONDecodeError
from typing import Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI

from IndustryIntelligenceModule.settings import settings
from tools.llm_logger import get_llm_logger


StatusCallback = Optional[Callable[[str, str, Dict], None]]


class SkillAnalyzer:
    """Extract skills and structured job fields from job descriptions."""

    SKILL_ALIASES = {
        "python3": "Python",
        "py": "Python",
        "java 8": "Java",
        "java8": "Java",
        "sql server": "SQL Server",
        "mysql": "MySQL",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mongo": "MongoDB",
        "mongodb": "MongoDB",
        "power bi": "Power BI",
        "powerbi": "Power BI",
        "tableau desktop": "Tableau",
        "scikit learn": "Scikit-learn",
        "sklearn": "Scikit-learn",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "apache spark": "Spark",
        "apache flink": "Flink",
        "hive sql": "Hive",
        "k8s": "Kubernetes",
        "huggingface": "Hugging Face",
        "hugging face": "Hugging Face",
        "lang chain": "LangChain",
        "llama index": "LlamaIndex",
        "click house": "ClickHouse",
        "dbt": "dbt",
    }

    SEARCH_TERM_PRIORS = {
        "大数据分析": ["Big Data Analyst", "Data Analyst", "Data Analytics", "Business Intelligence Analyst"],
        "数据分析": ["Data Analyst", "Data Analytics", "Business Intelligence Analyst"],
        "数据分析师": ["Data Analyst", "Business Intelligence Analyst", "Analytics Specialist"],
        "大数据": ["Big Data", "Data Engineer", "Big Data Engineer", "Data Platform"],
        "数据开发": ["Data Engineer", "Big Data Engineer", "ETL Developer"],
        "数据仓库": ["Data Warehouse", "Data Warehouse Engineer", "ETL Developer"],
        "商业分析": ["Business Analyst", "Business Intelligence Analyst", "Data Analyst"],
        "算法工程师": ["Algorithm Engineer", "Machine Learning Engineer", "AI Engineer"],
        "机器学习": ["Machine Learning Engineer", "Machine Learning", "AI Engineer"],
        "人工智能": ["AI Engineer", "Machine Learning Engineer", "LLM Engineer"],
        "产品经理": ["Product Manager"],
        "运营": ["Operations", "Operations Specialist", "Growth Operations"],
    }

    NON_JOB_PATTERNS = [
        "培训", "招生", "课程", "实训", "训练营", "特训营", "就业班", "公开课", "试听",
        "学员", "讲师", "招生老师", "培训机构", "咨询报名"
    ]

    def _looks_like_non_job_listing(self, title: str, text: str) -> bool:
        combined = f"{title or ''} {text or ''}".lower()
        return any(token in combined for token in self.NON_JOB_PATTERNS)

    def _has_substantive_description(self, text: str) -> bool:
        compact = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(compact) < 20:
            return False
        if compact in {"暂无职位描述", "暂无描述", "职位描述", "暂无任职要求摘要"}:
            return False
        return True

    def __init__(self):
        self.model = settings.MODEL_NAME
        self.llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.1,
            base_url=settings.BASE_URL,
            api_key=settings.API_KEY,
        )
        self.max_workers = max(1, min(int(os.getenv("INDUSTRY_ANALYZE_WORKERS", "3")), 4))

    def _parse_json(self, content: str) -> dict:
        content = (content or "").strip()
        if content.startswith("```json"):
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif content.startswith("```"):
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                content = content[start : end + 1]
        return json.loads(content)

    def _normalize_skill_name(self, skill: str) -> str:
        if not skill:
            return ""
        cleaned = re.sub(r"\s+", " ", str(skill).strip()).strip(" ,;/|")
        alias_key = cleaned.lower()
        if alias_key in self.SKILL_ALIASES:
            return self.SKILL_ALIASES[alias_key]
        if re.fullmatch(r"[A-Za-z0-9 .+#-]+", cleaned):
            uppercase_words = {"sql", "etl", "bi", "nlp", "cv", "llm"}
            exact_words = {"dbt": "dbt"}
            normalized_words = []
            for word in cleaned.split(" "):
                lowered = word.lower()
                if lowered in uppercase_words:
                    normalized_words.append(word.upper())
                elif lowered in exact_words:
                    normalized_words.append(exact_words[lowered])
                elif lowered in {"tensorflow", "pytorch"}:
                    normalized_words.append(word[0].upper() + word[1:].lower())
                else:
                    normalized_words.append(word[0].upper() + word[1:] if word else word)
            cleaned = " ".join(normalized_words)
        return self.SKILL_ALIASES.get(cleaned.lower(), cleaned)

    def _normalize_skills(self, skills: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for skill in skills or []:
            item = self._normalize_skill_name(skill)
            if not item:
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(item)
        return normalized

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"[\n\r]+|(?<=[。！；;.!?])", text or "")
        return [part.strip() for part in parts if part and part.strip()]

    def _trim_evidence(self, text: str, max_len: int = 120) -> str:
        compact = re.sub(r"\s+", " ", text or "").strip()
        if len(compact) <= max_len:
            return compact
        return compact[: max_len - 3].rstrip() + "..."

    def _find_evidence_snippet(self, skill: str, text: str) -> str:
        normalized_skill = self._normalize_skill_name(skill)
        candidates = [normalized_skill]
        for alias, canonical in self.SKILL_ALIASES.items():
            if canonical == normalized_skill:
                candidates.append(alias)
        sentences = self._split_sentences(text)
        for candidate in candidates:
            for sentence in sentences:
                if re.search(r"[\u4e00-\u9fff]", candidate):
                    if candidate in sentence:
                        return self._trim_evidence(sentence)
                else:
                    pattern = r"(?<![A-Za-z0-9])" + re.escape(candidate) + r"(?![A-Za-z0-9])"
                    if re.search(pattern, sentence, re.IGNORECASE):
                        return self._trim_evidence(sentence)
        return self._trim_evidence(text)

    def _normalize_skill_evidence(self, items: List[Dict], text: str) -> List[Dict[str, str]]:
        normalized_items = []
        seen = set()
        for item in items or []:
            if isinstance(item, dict):
                raw_name = item.get("name") or item.get("skill") or ""
                raw_evidence = item.get("evidence") or item.get("snippet") or ""
            else:
                raw_name = str(item)
                raw_evidence = ""
            name = self._normalize_skill_name(raw_name)
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            evidence = self._trim_evidence(raw_evidence) or self._find_evidence_snippet(name, text)
            normalized_items.append({"name": name, "evidence": evidence})
            seen.add(key)
        return normalized_items

    def _build_skill_evidence(self, skills: List[str], text: str) -> List[Dict[str, str]]:
        return [{"name": skill, "evidence": self._find_evidence_snippet(skill, text)} for skill in self._normalize_skills(skills)]

    def _normalize_search_terms(self, terms: List[str], max_terms: int = 6) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for term in terms or []:
            cleaned = re.sub(r"\s+", " ", str(term or "").strip())
            cleaned = cleaned.strip(" ,;/|")
            if len(cleaned) < 2:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
            if len(normalized) >= max_terms:
                break
        return normalized

    def _fallback_search_terms(self, keyword: str) -> List[str]:
        compact = re.sub(r"\s+", "", str(keyword or "").lower())
        if not compact:
            return []

        matched: List[str] = []
        for base, variants in self.SEARCH_TERM_PRIORS.items():
            base_key = re.sub(r"\s+", "", base.lower())
            if compact == base_key or compact in base_key or base_key in compact:
                matched.extend(variants)

        if not matched:
            for base, variants in self.SEARCH_TERM_PRIORS.items():
                fragments = [part for part in re.split(r"[\s/,+，、]+", base.lower()) if part]
                if any(fragment and fragment in compact for fragment in fragments):
                    matched.extend(variants)

        return self._normalize_search_terms(matched)

    def _llm_domestic_terms(self, keyword: str) -> List[str]:
        prompt = f'''你是中文招聘搜索词优化助手。请把岗位关键词扩展成适合中国招聘网站检索的中文搜索词。

原始关键词：{keyword}

请严格返回 JSON：
{{
  "primary": "最核心的中文岗位搜索词",
  "variants": ["4到6个适合招聘网站搜索的中文近义词或扩展词"]
}}

要求：
1. 只返回中文搜索词，不要英文。
2. 优先使用招聘网站里常见的岗位名称，不要口语化表达。
3. 词组要简洁，适合 Boss、智联、拉勾、LinkedIn 中文岗位检索。
4. 总共最多返回 6 个搜索词。'''
        result = self._request_json(prompt)
        terms = [result.get("primary", "")]
        terms.extend(result.get("variants", []) or [])
        return self._normalize_search_terms(terms)

    def _llm_search_terms(self, keyword: str, country: str) -> List[str]:
        prompt = f'''你是招聘搜索词优化助手。请把中文岗位关键词改写成适合 {country} 招聘网站检索的英文搜索词。

原始关键词：{keyword}

请严格返回 JSON：
{{
  "primary": "最核心的英文岗位搜索词",
  "variants": ["3到5个适合招聘网站搜索的英文近义词或扩展词"]
}}

要求：
1. 只返回英文搜索词，不要中文。
2. 优先使用招聘网站里常见的岗位名称，而不是生硬直译。
3. 词组要简洁，适合 Indeed/LinkedIn 直接搜索。
4. 总共最多返回 6 个搜索词。'''
        result = self._request_json(prompt)
        terms = [result.get("primary", "")]
        terms.extend(result.get("variants", []) or [])
        return self._normalize_search_terms(terms)

    def generate_search_terms(self, keyword: str, country: str = "中国") -> List[str]:
        base_keyword = re.sub(r"\s+", " ", str(keyword or "").strip())
        if not base_keyword:
            return []

        if country == "中国":
            try:
                llm_terms = self._llm_domestic_terms(base_keyword)
            except Exception:
                llm_terms = []
            merged = self._normalize_search_terms([base_keyword] + llm_terms)
            return merged or [base_keyword]

        if not re.search(r"[\u4e00-\u9fff]", base_keyword):
            return [base_keyword]

        fallback_terms = self._fallback_search_terms(base_keyword)
        try:
            llm_terms = self._llm_search_terms(base_keyword, country)
        except Exception:
            llm_terms = []

        merged = self._normalize_search_terms([base_keyword] + llm_terms + fallback_terms)
        return merged or fallback_terms or [base_keyword]

    def _request_json(self, prompt: str) -> dict:
        response = self.llm.invoke([
            ("system", "你是专业的招聘文本信息抽取助手，只返回合法 JSON，不要输出额外解释。"),
            ("human", prompt),
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
        get_llm_logger().log_llm_call(
            messages=[
                {"role": "system", "content": "你是专业的招聘文本信息抽取助手，只返回合法 JSON，不要输出额外解释。"},
                {"role": "user", "content": prompt},
            ],
            response=response,
            model=self.model or "",
            module="IndustryIntelligenceModule.analyzer",
            metadata={"function": "enrich_job"},
            username="industry_intelligence",
        )
        return self._parse_json(content)

    def enrich_job(self, job: Dict) -> Dict:
        title = job.get("title") or ""
        description = f"{job.get('description') or ''} {job.get('requirements') or ''}".strip()

        if self._looks_like_non_job_listing(title, description):
            job["skills"] = []
            job["skill_evidence"] = []
            job["requirements"] = ""
            job.setdefault("salary", "面议")
            return job

        if not self._has_substantive_description(description):
            job["skills"] = []
            job["skill_evidence"] = []
            job.setdefault("salary", "面议")
            return job

        prompt = f"""请仔细阅读下面的职位描述全文，并提取结构化信息。

职位标题：{title}

职位描述全文：
{description[:4000]}

请严格返回如下 JSON，不要输出任何额外说明：
{{
  \"skills\": [\"只保留职位中明确提到的技术技能、工具、框架、编程语言\"],
  \"skill_evidence\": [
    {{\"name\": \"技能名\", \"evidence\": \"必须来自原文的短句或片段\"}}
  ],
  \"salary\": \"提取到的薪资范围，提取不到则返回 面议\",
  \"experience\": \"提取到的经验要求，提取不到返回空字符串\",
  \"education\": \"提取到的学历要求，提取不到返回空字符串\",
  \"requirements\": \"用 2-3 句概括岗位核心任职要求\"
}}

注意：
1. skills 只保留硬技能，不包含沟通能力等软技能。
2. evidence 必须直接来自原文，不要编造。
3. experience 和 education 只能按原文提取，不要猜测。
4. 技能命名尽量标准化。
"""

        try:
            result = self._request_json(prompt)
            skill_evidence = self._normalize_skill_evidence(result.get("skill_evidence", []), description)
            if skill_evidence:
                job["skill_evidence"] = skill_evidence
                job["skills"] = [item["name"] for item in skill_evidence]
            else:
                job["skills"] = self._normalize_skills(result.get("skills", []))
                job["skill_evidence"] = self._build_skill_evidence(job["skills"], description)
            job["salary"] = result.get("salary") or job.get("salary") or "面议"
            job["experience"] = result.get("experience") or job.get("experience", "")
            job["education"] = result.get("education") or job.get("education", "")
            if not job.get("requirements"):
                job["requirements"] = result.get("requirements", "")
        except (JSONDecodeError, ValueError, KeyError, TypeError):
            job["skills"] = []
            job["skill_evidence"] = []
            job.setdefault("salary", "面议")
        except Exception:
            job["skills"] = []
            job["skill_evidence"] = []
            job.setdefault("salary", "面议")
        return job

    def batch_extract(self, jobs: List[Dict], status_callback: StatusCallback = None) -> List[Dict]:
        if not jobs:
            return []

        indexed_results = [None] * len(jobs)
        total = len(jobs)
        completed = 0

        with ThreadPoolExecutor(max_workers=min(self.max_workers, total)) as executor:
            future_map = {executor.submit(self.enrich_job, dict(job)): index for index, job in enumerate(jobs)}
            for future in as_completed(future_map):
                index = future_map[future]
                indexed_results[index] = future.result()
                completed += 1
                if status_callback:
                    current_job = indexed_results[index] or jobs[index]
                    status_callback(
                        "analyzing",
                        f"正在解析第 {completed}/{total} 条职位：{current_job.get('title', '未知岗位')}",
                        {
                            "step": 3,
                            "current": completed,
                            "total": total,
                            "title": current_job.get("title", "未知岗位"),
                        },
                    )

        return indexed_results


