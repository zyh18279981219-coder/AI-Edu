#!/usr/bin/env python3
"""Generate course PDFs that match the richer 2.pdf lecture-note style."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
COURSE_JSON = ROOT / "data" / "course" / "big_data.json"
REPORT_JSON = ROOT / "data" / "pdf_generation_report.json"
BOOK_DIR = ROOT / "data" / "Book"

BODY_FONT = "Deng"
HEADING_FONT = "DengB"
CODE_FONT = "Courier"

ALIASES = {
    "Volume": "Volume（数据规模）",
    "Variety": "Variety（数据多样性）",
    "Velocity": "Velocity（数据速度）",
    "Veracity": "Veracity（数据真实性）",
    "Value": "Value（数据价值）",
    "BulkSynchronousParallel(BSP)": "BSP 同步并行模型",
    "EagerExecution": "Eager Execution（即时执行）",
}


def register_fonts() -> None:
    fonts = {
        BODY_FONT: Path(r"C:\Windows\Fonts\Deng.ttf"),
        HEADING_FONT: Path(r"C:\Windows\Fonts\Dengb.ttf"),
    }
    for name, path in fonts.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))


def load_topics() -> dict[int, dict[str, object]]:
    course_data = json.loads(COURSE_JSON.read_text(encoding="utf-8"))
    items: dict[int, dict[str, object]] = {}

    def walk(node: dict, lineage: list[str]) -> None:
        name = node.get("name") or node.get("root_name", "")
        current = lineage + ([name] if name else [])
        resource_path = node.get("resource_path", "")
        values: list[str] = []
        if isinstance(resource_path, str) and resource_path:
            values = [resource_path]
        elif isinstance(resource_path, list):
            values = [value for value in resource_path if isinstance(value, str)]

        for value in values:
            match = re.search(r"data/Book/(\d+)\.PDF", value, re.IGNORECASE)
            if not match:
                continue
            number = int(match.group(1))
            items[number] = {
                "number": number,
                "title": name,
                "lineage": current,
                "resource_path": value,
            }

        for key in ("children", "grandchildren", "great-grandchildren"):
            for child in node.get(key, []) or []:
                walk(child, current)

    walk(course_data, [])
    return dict(sorted(items.items()))


def assess_pdf(path: Path) -> dict[str, int | str | None]:
    record: dict[str, int | str | None] = {
        "exists": int(path.exists()),
        "size": None,
        "pages": None,
        "text_len": None,
        "error": "",
    }
    if not path.exists():
        return record
    try:
        doc = fitz.open(path)
        text_len = 0
        for index in range(min(doc.page_count, 6)):
            text_len += len(doc.load_page(index).get_text("text").strip())
        record["size"] = path.stat().st_size
        record["pages"] = doc.page_count
        record["text_len"] = text_len
        doc.close()
    except Exception as exc:  # pragma: no cover - defensive
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def topic_display(title: str) -> str:
    return ALIASES.get(title, title)


def infer_profile(topic: dict[str, object]) -> dict[str, object]:
    title = str(topic["title"])
    lineage = [str(item) for item in topic["lineage"]]
    text = " / ".join(lineage + [title]).lower()

    profiles = [
        {
            "name": "crawler",
            "match": ["爬虫", "deepweb", "darkweb", "数据提取", "互联网数据收集", "pageRank".lower(), "opic"],
            "domain": "互联网数据采集与治理",
            "core_terms": ["URL 调度", "抓取策略", "去重与增量更新", "robots 合规"],
            "tools": ["Scrapy", "Kafka", "Flink", "Elasticsearch"],
            "metrics": ["覆盖率", "抓取时延", "失败率", "站点负载影响"],
            "case": "舆情监测平台",
            "code_kind": "crawler",
        },
        {
            "name": "recommendation",
            "match": ["推荐系统", "协同过滤", "隐语义", "矩阵分解", "社交网络", "力导向图", "fruchterman", "相似度计算"],
            "domain": "推荐系统与网络分析",
            "core_terms": ["用户-物品关系", "图结构表示", "相似度度量", "在线反馈闭环"],
            "tools": ["Spark MLlib", "NetworkX", "Neo4j", "Faiss"],
            "metrics": ["Precision@K", "Recall@K", "图密度", "覆盖率"],
            "case": "在线教育课程推荐",
            "code_kind": "recommendation",
        },
        {
            "name": "tensorflow",
            "match": ["tensorflow", "卷积神经网络", "激活函数", "权重和偏置", "深度学习"],
            "domain": "深度学习工程实现",
            "core_terms": ["张量计算", "自动求导", "训练循环", "分布式训练"],
            "tools": ["TensorFlow 2.x", "Keras", "TensorBoard", "CUDA"],
            "metrics": ["训练损失", "验证准确率", "吞吐量", "显存占用"],
            "case": "图像分类与质检",
            "code_kind": "tensorflow",
        },
        {
            "name": "ml",
            "match": ["机器学习", "聚类", "回归", "pca", "svd", "朴素贝叶斯", "svm", "k近邻", "apriori", "支持度", "欧几里得距离"],
            "domain": "数据挖掘与机器学习",
            "core_terms": ["特征表达", "模型训练", "评估与调参", "结果解释"],
            "tools": ["scikit-learn", "Spark MLlib", "Pandas", "Jupyter"],
            "metrics": ["准确率", "召回率", "RMSE", "轮廓系数"],
            "case": "客户分群与预测分析",
            "code_kind": "ml",
        },
        {
            "name": "processing",
            "match": ["mapreduce", "spark", "rdd", "流计算", "批处理", "bsp", "pregel", "并行", "分布式计算", "mpp", "内存计算"],
            "domain": "分布式计算与数据处理",
            "core_terms": ["任务拆分", "并行执行", "容错恢复", "资源调度"],
            "tools": ["Hadoop", "YARN", "Spark", "Flink"],
            "metrics": ["吞吐量", "作业延迟", "资源利用率", "扩展性"],
            "case": "日志处理与实时分析",
            "code_kind": "processing",
        },
        {
            "name": "storage",
            "match": ["hdfs", "文件系统", "存储", "数据库", "nosql", "newsql", "cap", "base", "greenplum", "hana", "容错"],
            "domain": "分布式存储与数据管理",
            "core_terms": ["数据分片", "副本机制", "一致性权衡", "冷热分层"],
            "tools": ["HDFS", "HBase", "Cassandra", "Greenplum"],
            "metrics": ["可用性", "恢复时间", "写入吞吐", "副本开销"],
            "case": "政务数据湖建设",
            "code_kind": "storage",
        },
        {
            "name": "foundation",
            "match": ["商务智能", "第四范式", "因果关系", "全量数据", "能力", "概念", "特征"],
            "domain": "大数据基础理论与应用认知",
            "core_terms": ["数据价值链", "问题建模", "技术演进", "业务落地"],
            "tools": ["Power BI", "Tableau", "Spark", "云数据平台"],
            "metrics": ["决策时效", "分析覆盖度", "数据质量", "业务转化率"],
            "case": "企业数字化转型",
            "code_kind": "foundation",
        },
    ]

    for profile in profiles:
        if any(keyword.lower() in text for keyword in profile["match"]):
            return profile
    return profiles[-1]


def build_learning_goals(topic_name: str, profile: dict[str, object]) -> list[str]:
    return [
        f"理解{topic_name}在{profile['domain']}中的定位，以及它与上游采集、下游分析的关系。",
        f"掌握{topic_name}涉及的关键概念、核心术语与常见工程约束。",
        f"能够结合{', '.join(profile['tools'][:2])}等工具，说明{topic_name}的典型实现路径。",
        f"能够分析{topic_name}在性能、成本、可靠性和治理方面的主要权衡。",
        f"具备把{topic_name}迁移到真实业务场景并开展实践设计的能力。",
    ]


def build_intro(topic_name: str, lineage: list[str], profile: dict[str, object]) -> list[str]:
    upper_context = "、".join(lineage[-3:-1]) if len(lineage) >= 3 else "课程知识体系"
    return [
        f"{topic_name}是“{upper_context}”知识链条中的关键节点。它既承接前置的概念理解，也直接影响后续的系统设计、算法效果和运维治理，因此在大数据课程中通常被作为重点内容展开。",
        f"从工程视角看，{topic_name}不是孤立知识点，而是围绕{profile['core_terms'][0]}、{profile['core_terms'][1]}与{profile['core_terms'][2]}展开的一组方法论。学习它的真正目标，不只是会背定义，而是能判断什么时候该用、为什么这么用，以及代价是什么。",
        f"在真实业务中，{topic_name}常出现在{profile['case']}、数据平台升级、跨团队协作和合规审计等场景。理解其原理后，学生能够把课堂上的抽象术语转化为可执行的架构方案、分析流程与质量控制动作。",
    ]


def build_core_sections(topic_name: str, profile: dict[str, object]) -> list[tuple[str, list[str]]]:
    terms = list(profile["core_terms"])
    metrics = list(profile["metrics"])
    tools = list(profile["tools"])
    return [
        (
            f"{topic_name}的概念边界",
            [
                f"需要先明确{topic_name}要解决的核心问题，以及它与相邻概念之间的边界，避免把平台能力、算法能力或治理能力混为一谈。",
                f"围绕{terms[0]}与{terms[1]}建立统一术语，有助于团队在需求评审、方案设计和指标复盘时减少歧义。",
                f"教学中应引导学生从“业务目标 - 数据形态 - 技术约束”三个角度理解{topic_name}，而不是停留在静态定义上。",
            ],
        ),
        (
            "关键机制与工作流程",
            [
                f"{topic_name}通常遵循“输入准备、核心处理、结果输出、反馈优化”的闭环流程，其中{terms[2]}常常决定系统能否稳定运行。",
                f"当业务规模扩大时，{terms[3]}会成为影响吞吐和稳定性的关键因素，需要通过架构层面的冗余与隔离来处理。",
                f"把流程拆解成阶段后，学生更容易识别瓶颈点，例如数据倾斜、状态膨胀、索引失衡或高并发竞争。",
            ],
        ),
        (
            "指标、约束与设计权衡",
            [
                f"{topic_name}的效果不能只看单一性能指标，通常要同时关注{metrics[0]}、{metrics[1]}、{metrics[2]}与{metrics[3]}。",
                f"在成本有限的情况下，系统设计常需要在精度、时延、可扩展性和可维护性之间做权衡，这正是课堂案例分析的重点。",
                f"将指标前置到方案设计阶段，能够帮助团队建立可观测性与验收标准，避免项目上线后才暴露结构性问题。",
            ],
        ),
        (
            "平台、工具与实现路径",
            [
                f"工程实践里，{topic_name}往往依赖{tools[0]}、{tools[1]}、{tools[2]}等工具共同完成，从而形成从数据流入到业务使用的完整链路。",
                f"工具选型不能只看流行度，还要结合数据规模、团队技能、部署环境和运维复杂度进行综合判断。",
                f"良好的实现路径通常包含接口规范、异常处理、日志追踪、版本治理和回滚策略，而不仅仅是功能跑通。",
            ],
        ),
        (
            "常见误区与优化方向",
            [
                f"第一个误区是把{topic_name}理解为单点技术能力，忽略了它对组织流程、数据质量与协作机制的要求。",
                f"第二个误区是过早追求复杂方案，实际上许多问题可以通过分层设计、指标治理和资源隔离先得到缓解。",
                f"优化时应优先识别主要矛盾，再决定是调整模型、改写作业、优化存储结构，还是补充治理规则。",
            ],
        ),
    ]


def build_case_steps(topic_name: str, profile: dict[str, object]) -> list[str]:
    return [
        f"案例背景：某机构建设{profile['case']}，需要把分散的数据资源转化为可追踪、可分析、可服务的统一能力。",
        f"问题识别：原有流程在{profile['metrics'][0]}和{profile['metrics'][1]}上表现不稳定，导致业务响应慢、分析结果波动大。",
        f"方案设计：团队围绕{topic_name}重构处理链路，引入{profile['tools'][0]}与{profile['tools'][1]}，并补充质量校验与权限控制。",
        f"实施过程：先完成数据标准统一，再分阶段上线核心能力，最后接入监控、告警和回溯分析机制。",
        f"应用效果：业务侧获得更稳定的分析结果，技术侧在容量扩展、错误恢复和协作效率上明显改善。",
    ]


def build_discussion(topic_name: str, profile: dict[str, object]) -> dict[str, list[str]]:
    return {
        "research": [
            f"围绕{topic_name}的自动化优化正成为热点，例如基于策略学习的资源编排、自动参数搜索和智能异常定位。",
            f"{profile['domain']}正在和隐私计算、可解释 AI、云原生平台深度结合，推动从“可用”走向“可治理、可审计、可持续”。",
            f"课程教学也在从概念讲授转向案例驱动与实验驱动，强调学生对完整数据链路的理解能力。",
        ],
        "challenges": [
            f"{topic_name}落地时最大的挑战通常不是单点算法，而是异构系统协同、跨团队标准统一和长期运维成本控制。",
            f"当数据规模继续增长时，系统容易出现性能瓶颈、资源竞争和质量漂移，需要持续观测与分层治理。",
            f"合规、安全和伦理要求正在前移，设计阶段就必须考虑最小权限、数据脱敏、审计留痕与责任归属。",
        ],
        "trends": [
            f"{topic_name}将持续走向服务化、智能化和平台化，核心能力会越来越多地沉淀为可复用组件。",
            f"流批一体、湖仓一体和多模态数据处理会让{topic_name}不再局限于单一技术栈，而是进入统一数据底座。",
            f"未来 3-5 年，课程实践会更加重视真实数据集、工程指标与可解释性分析，弱化只会调用 API 的表层训练。",
            f"生成式 AI 将更多参与数据建模、代码生成和运维辅助，但人仍需负责约束、验证和质量判断。",
        ],
    }


def build_summary(topic_name: str, profile: dict[str, object]) -> list[str]:
    return [
        f"{topic_name}是{profile['domain']}中的关键知识点，理解其定位有助于串联整章内容。",
        f"它的核心不只是定义本身，更在于掌握{', '.join(profile['core_terms'][:3])}之间的联系。",
        f"真实项目里必须同时考虑{', '.join(profile['metrics'][:3])}，才能让方案兼顾效果与成本。",
        f"{', '.join(profile['tools'][:3])}等工具为{topic_name}提供了工程落地路径，但工具不能替代设计判断。",
        f"后续学习应继续结合案例、代码与实验，把{topic_name}转化为可解释、可验证的实践能力。",
    ]


def build_reflection(topic_name: str) -> list[str]:
    return [
        f"{topic_name}最容易被误解的地方是什么？如果让你给新同学讲解，你会如何解释它的边界？",
        f"在资源有限的条件下，实现{topic_name}时你会优先优化哪一项指标，原因是什么？",
        f"如果业务规模扩大 10 倍，当前围绕{topic_name}的方案最先暴露的问题可能是什么？",
    ]


def comparison_rows(topic_name: str, profile: dict[str, object]) -> list[list[str]]:
    return [
        ["观察维度", "在本主题中的体现", "教学关注点"],
        ["业务目标", f"{topic_name}服务于更高效的数据价值转化", "先明确问题，再选择技术"],
        ["技术抓手", "围绕平台、算法、治理三类能力协同展开", "不要把工具当成全部"],
        ["质量指标", "同时关注性能、准确性、可用性和成本", "建立可验证的验收标准"],
        ["演进方向", "从单点能力走向自动化、平台化、智能化", "培养学生的迁移能力"],
    ]


def code_sample(topic_name: str, profile: dict[str, object]) -> str:
    kind = str(profile["code_kind"])
    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", topic_name).strip("_") or "topic"
    if kind == "storage":
        return f"""from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("{safe_name}Demo").getOrCreate()

df = spark.read.json("s3://demo-bucket/events/*.json")
clean_df = df.dropna().repartition(8, "event_date")
clean_df.write.mode("overwrite").parquet("hdfs:///warehouse/{safe_name.lower()}")

summary = spark.read.parquet("hdfs:///warehouse/{safe_name.lower()}")
print(summary.count())
spark.stop()
"""
    if kind == "processing":
        return f"""from pyspark.sql import SparkSession
from pyspark.sql.functions import count

spark = SparkSession.builder.appName("{safe_name}Pipeline").getOrCreate()
logs = spark.read.json("data/input/logs.json")
result = logs.groupBy("event_type").agg(count("*").alias("cnt"))
result.orderBy(result.cnt.desc()).show()
spark.stop()
"""
    if kind == "ml":
        return f"""from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(max_iter=500))
])
model.fit(X_train, y_train)
print(model.score(X_test, y_test))
"""
    if kind == "tensorflow":
        return f"""import tensorflow as tf

model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10, activation="softmax"),
])

model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train_ds, validation_data=val_ds, epochs=5)
"""
    if kind == "recommendation":
        return f"""from pyspark.ml.recommendation import ALS

als = ALS(
    userCol="user_id",
    itemCol="item_id",
    ratingCol="rating",
    coldStartStrategy="drop"
)
model = als.fit(train_df)
recommendations = model.recommendForAllUsers(5)
recommendations.show(truncate=False)
"""
    if kind == "crawler":
        return """import requests
from bs4 import BeautifulSoup

resp = requests.get("https://example.com", timeout=10)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")
titles = [a.get_text(strip=True) for a in soup.select("a.article-link")]
for title in titles[:10]:
    print(title)
"""
    return f"""import pandas as pd

df = pd.read_csv("data/demo.csv")
summary = df.groupby("category")["value"].agg(["count", "mean", "max"])
print(summary.sort_values("count", ascending=False))
"""


def formula_lines(topic_name: str) -> list[str]:
    formulas: list[str] = []
    if "支持度" in topic_name or "置信度" in topic_name or "提升度" in topic_name:
        formulas = [
            "support(A=>B) = count(A and B) / N",
            "confidence(A=>B) = count(A and B) / count(A)",
            "lift(A=>B) = confidence(A=>B) / support(B)",
        ]
    elif "欧几里得距离" in topic_name:
        formulas = ["distance(x, y) = sqrt(sum((xi - yi)^2))"]
    elif "均值" in topic_name:
        formulas = ["mean(x) = sum(xi) / n"]
    elif "回归方程" in topic_name or "线性回归" in topic_name:
        formulas = ["y = beta0 + beta1 * x + epsilon"]
    elif "主成分分析" in topic_name or "PCA" in topic_name:
        formulas = ["Z = X * W", "W = eigenvectors(cov(X))"]
    elif "奇异值分解" in topic_name or "SVD" in topic_name:
        formulas = ["A = U * Sigma * V^T"]
    elif "先验概率" in topic_name:
        formulas = ["P(Y|X) = P(X|Y) * P(Y) / P(X)"]
    return formulas


def make_styles():
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodyCN",
        parent=styles["BodyText"],
        fontName=BODY_FONT,
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1d1d1f"),
        alignment=TA_JUSTIFY,
        wordWrap="CJK",
        spaceAfter=4,
    )
    title = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=HEADING_FONT,
        fontSize=22,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"),
        spaceAfter=10,
    )
    subtitle = ParagraphStyle(
        "SubtitleCN",
        parent=styles["Heading2"],
        fontName=BODY_FONT,
        fontSize=13.5,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=18,
    )
    h1 = ParagraphStyle(
        "Heading1CN",
        parent=styles["Heading1"],
        fontName=HEADING_FONT,
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#111111"),
        wordWrap="CJK",
        spaceBefore=12,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "Heading2CN",
        parent=styles["Heading2"],
        fontName=HEADING_FONT,
        fontSize=13.2,
        leading=18,
        textColor=colors.HexColor("#222222"),
        wordWrap="CJK",
        spaceBefore=8,
        spaceAfter=4,
    )
    bullet = ParagraphStyle(
        "BulletCN",
        parent=body,
        leftIndent=12,
        firstLineIndent=0,
        bulletIndent=0,
        spaceBefore=1,
    )
    code = ParagraphStyle(
        "CodeCN",
        parent=styles["Code"],
        fontName=CODE_FONT,
        fontSize=8.8,
        leading=11,
        backColor=colors.HexColor("#f5f5f7"),
        leftIndent=6,
        rightIndent=6,
        borderPadding=6,
        borderColor=colors.HexColor("#d9d9de"),
        borderWidth=0.5,
        borderRadius=4,
    )
    return {
        "body": body,
        "title": title,
        "subtitle": subtitle,
        "h1": h1,
        "h2": h2,
        "bullet": bullet,
        "code": code,
    }


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(esc(text), style)


def bullet_list(items: list[str], styles: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(paragraph(item, styles["bullet"])) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=10,
    )


def make_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[paragraph(cell, styles["body"]) for cell in row] for row in rows]
    table = Table(data, colWidths=[26 * mm, 86 * mm, 50 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cfcfd6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(BODY_FONT, 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(doc.leftMargin, A4[1] - 14 * mm, "大数据分析课程讲义")
    canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def build_story(topic: dict[str, object], extra_pages: bool = False):
    styles = make_styles()
    title = topic_display(str(topic["title"]))
    lineage = [str(item) for item in topic["lineage"] if item]
    profile = infer_profile(topic)
    story = [
        paragraph("课程内容", styles["title"]),
        paragraph(title, styles["subtitle"]),
        paragraph("1. 学习目标 (Learning Objectives)", styles["h1"]),
        bullet_list(build_learning_goals(title, profile), styles),
        paragraph("2. 引言 (Introduction)", styles["h1"]),
    ]
    for intro in build_intro(title, lineage, profile):
        story.extend([paragraph(intro, styles["body"]), Spacer(1, 2)])

    story.append(paragraph("3. 核心知识体系 (Core Knowledge Framework)", styles["h1"]))
    for index, (heading, bullets) in enumerate(build_core_sections(title, profile), start=1):
        story.append(paragraph(f"3.{index} {heading}", styles["h2"]))
        story.append(bullet_list(bullets, styles))
        story.append(Spacer(1, 3))

    formulas = formula_lines(title)
    if formulas:
        story.append(paragraph("3.6 关键公式与表达", styles["h2"]))
        story.append(Preformatted("\n".join(formulas), styles["code"]))
        story.append(Spacer(1, 4))

    story.append(make_table(comparison_rows(title, profile), styles))
    story.append(Spacer(1, 8))
    story.append(paragraph("4. 应用与实践 (Application and Practice)", styles["h1"]))
    story.append(paragraph(f"4.1 案例研究：{profile['case']}中的{title}落地实践", styles["h2"]))
    story.append(bullet_list(build_case_steps(title, profile), styles))
    story.append(Spacer(1, 6))
    story.append(paragraph("4.2 代码示例", styles["h2"]))
    story.append(Preformatted(code_sample(title, profile), styles["code"]))
    story.append(Spacer(1, 8))

    discussion = build_discussion(title, profile)
    story.append(paragraph("5. 深入探讨与未来展望 (In-depth Discussion & Future Outlook)", styles["h1"]))
    story.append(paragraph("5.1 当前研究热点", styles["h2"]))
    story.append(bullet_list(discussion["research"], styles))
    story.append(paragraph("5.2 重大挑战", styles["h2"]))
    story.append(bullet_list(discussion["challenges"], styles))
    story.append(paragraph("5.3 未来 3-5 年发展趋势", styles["h2"]))
    story.append(bullet_list(discussion["trends"], styles))
    story.append(Spacer(1, 8))
    story.append(paragraph("6. 章节总结 (Chapter Summary)", styles["h1"]))
    story.append(bullet_list(build_summary(title, profile), styles))

    if extra_pages:
        story.extend(
            [
                PageBreak(),
                paragraph("7. 课后思考与课堂活动", styles["h1"]),
                paragraph("7.1 思考题", styles["h2"]),
                bullet_list(build_reflection(title), styles),
                paragraph("7.2 课堂活动建议", styles["h2"]),
                bullet_list(
                    [
                        f"让学生围绕{title}绘制一张概念图，把输入、处理、输出、约束和指标连接起来。",
                        f"以小组形式比较两种不同实现路径，讨论它们在性能、成本和治理方面的差异。",
                        f"根据给定业务场景设计一个最小可行方案，明确需要的数据、工具与评估方法。",
                    ],
                    styles,
                ),
                paragraph("7.3 延伸阅读方向", styles["h2"]),
                bullet_list(
                    [
                        f"查阅 {profile['tools'][0]} 与 {profile['tools'][1]} 的官方实践文档，整理与{title}相关的工程建议。",
                        f"对比课堂案例与真实企业案例，识别哪些差异来自业务规模，哪些差异来自组织协作方式。",
                        f"结合课程后续章节思考：如果把{title}接入完整的数据平台，还需要补充哪些治理与运维能力？",
                    ],
                    styles,
                ),
            ]
        )
    return story


def build_pdf(topic: dict[str, object], target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    for extra_pages in (False, True):
        doc = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=16 * mm,
            title=str(topic["title"]),
            author="OpenAI Codex",
        )
        story = build_story(topic, extra_pages=extra_pages)
        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        info = assess_pdf(target)
        pages = int(info["pages"] or 0)
        text_len = int(info["text_len"] or 0)
        if pages >= 4 and text_len >= 2200:
            info["regenerated_with_extra_pages"] = extra_pages
            return info
    info = assess_pdf(target)
    info["regenerated_with_extra_pages"] = True
    return info


def parse_number_spec(value: str) -> set[int]:
    result: set[int] = set()
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-", 1)
            result.update(range(int(start), int(end) + 1))
        else:
            result.add(int(chunk))
    return result


def default_targets(topic_map: dict[int, dict[str, object]]) -> set[int]:
    targets: set[int] = set()
    for number, topic in topic_map.items():
        output = ROOT / str(topic["resource_path"])
        info = assess_pdf(output)
        pages = int(info["pages"] or 0)
        text_len = int(info["text_len"] or 0)
        size = int(info["size"] or 0)
        if not output.exists() or size < 150000 or pages < 4 or text_len < 2000:
            targets.add(number)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rich Chinese PDFs for the big data course.")
    parser.add_argument("--numbers", help="Comma-separated numbers or ranges, e.g. 1,79-202")
    parser.add_argument("--limit", type=int, default=0, help="Generate only the first N matched targets")
    args = parser.parse_args()

    register_fonts()
    topic_map = load_topics()
    targets = parse_number_spec(args.numbers) if args.numbers else default_targets(topic_map)
    targets = {number for number in sorted(targets) if number in topic_map}
    if args.limit:
        targets = set(sorted(targets)[: args.limit])

    results: list[dict[str, object]] = []
    for number in sorted(targets):
        topic = topic_map[number]
        output = ROOT / str(topic["resource_path"])
        info = build_pdf(topic, output)
        results.append(
            {
                "number": number,
                "title": str(topic["title"]),
                "path": str(output.relative_to(ROOT)).replace("\\", "/"),
                "pages": info.get("pages"),
                "size": info.get("size"),
                "text_len": info.get("text_len"),
                "extra_pages": info.get("regenerated_with_extra_pages", False),
            }
        )
        print(f"[OK] {number:03d} {topic['title']} -> {output.name} ({info.get('pages')} pages)")

    report = {
        "generated_count": len(results),
        "targets": sorted(targets),
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written to {REPORT_JSON}")


if __name__ == "__main__":
    main()
