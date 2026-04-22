# 知识图谱模块（KnowledgeGraph）
本模块用于将课程脚本文档自动生成教学知识图谱，并逐阶段完成质量治理、资源匹配与系统替换。当前已实现到`stage 4`（文本资源强制匹配 + 视频资源可选匹配）。

## 已实现阶段
1. `stage 0`：目录与配置检查、运行环境自检、可选旧图谱备份。  
2. `stage 1`：DOCX脚本解析、文本清洗、标准化分段。  
3. `stage 2`：基于`kg-gen`与回退策略抽取并标准化三元组。  
4. `stage 3`：教学层级重构（course/chapter/topic/concept）、关系精修、质量门禁。  
5. `stage 4`：学习资源匹配（每个`concept`至少1个文本资源，视频可选）。

## 目录说明（核心）
```text
KnowledgeGraph/
  config/
    course_profile.yaml
  data/
    intermediate/
      scripts_cleaned.jsonl
      triples_raw.jsonl
      triples_normalized.jsonl
      book_index.json
    output/
      big_data_kg.canonical.json
      quality_report.json
      concept_audit.json
      resource_match_report.json
      stage*_summary.json
      stage*_run_report.json
  src/
    pipeline.py
    course_profile.py
    kg_text_rules.py
    extraction/
    pedagogy/
    resource_match/
      book_indexer.py
      video_matcher.py
      web_resource_matcher.py
  scripts/
    run_pipeline.py
```

## 快速运行
在项目根目录执行：

```powershell
python KnowledgeGraph/scripts/run_pipeline.py --stage 0 --dry-run
python KnowledgeGraph/scripts/run_pipeline.py --stage 1
python KnowledgeGraph/scripts/run_pipeline.py --stage 2
python KnowledgeGraph/scripts/run_pipeline.py --stage 3
python KnowledgeGraph/scripts/run_pipeline.py --stage 4
```

仅检查阶段4前置条件（不落盘匹配结果）：

```powershell
python KnowledgeGraph/scripts/run_pipeline.py --stage 4 --dry-run
```

## 阶段4资源匹配规则
- 文本资源（必达）：
  - 输入：`data/Book/*.pdf`
  - 方式：抽取PDF前若干页文本建立索引，结合`concept`名称/描述/目标/关键词/上下文（topic/chapter）做语义重叠匹配。
  - 弱监督：复用`data/course/big_data.json`中的历史叶子节点资源映射作为提示信号。
  - 保底：当置信度过低时启用可追踪回退策略，确保`concept`文本覆盖率100%。
- 视频资源（可选）：
  - 输入：`data/Video/video_urls.json`
  - 方式：基于历史图谱映射 + 语义相似度匹配；不满足阈值可不匹配。
  - 支持多个知识点复用同一视频。

## 阶段4输出文件
- `KnowledgeGraph/data/output/big_data_kg.canonical.json`（已写入资源匹配结果）
- `KnowledgeGraph/data/intermediate/book_index.json`
- `KnowledgeGraph/data/output/resource_match_report.json`
- `KnowledgeGraph/data/output/stage4_summary.json`
- `KnowledgeGraph/data/output/stage4_run_report.json`
- `KnowledgeGraph/data/output/quality_report.json`（更新`concept_text_resource_coverage`与`video_match_rate`）

## canonical中资源字段约定
`concept`节点新增：

```json
{
  "resources": [
    {
      "resource_id": "text_book_001",
      "resource_type": "text",
      "title": "示例标题",
      "path": "data/Book/1.pdf",
      "score": 0.23,
      "match_method": "token_overlap",
      "provider": "local_book"
    },
    {
      "resource_id": "video_003",
      "resource_type": "video",
      "title": "示例视频",
      "url": "http://...m3u8",
      "score": 0.91,
      "match_method": "legacy_semantic",
      "provider": "local_video_urls"
    }
  ],
  "resource_refs": [
    "data/Book/1.pdf",
    "http://...m3u8"
  ]
}
```

## 当前验收基线（阶段4）
- `concept_text_resource_coverage_100pct = true`
- `video_match_rate_reported = true`
- 资源匹配过程与样本可在`resource_match_report.json`追溯。

## 后续阶段
- `stage 5`：兼容导出（替换`data/course/big_data.json`）与系统落库同步。  
- `stage 6`（可选）：外部网络资源扩展（CSDN/B站/YouTube等）。  
- `stage 7`（可选）：Neo4j图数据库落库与查询脚本。  
## Stage4 视频匹配 V2（2026-04-22）
- 视频匹配不再依赖 `data/course/big_data.json` 的历史视频映射。
- 阶段4视频链路改为：字幕优先抓取（m3u8/vtt/srt） -> ASR回退转写（faster-whisper） -> 视频文本索引化。
- 匹配流程改为：查询扩展 -> 粗召回（BM25 + 关键词）-> 精排（语义相似 + 关键词覆盖 + 层级一致性）。
- 精排权重默认：`0.45 semantic + 0.35 keyword + 0.20 hierarchy`。
- 每个 concept 输出高/中/低置信度决策：
- `matched`：高置信度，写入 canonical 的 `resources`。
- `needs_review`：中置信度，保留候选到报告，等待人工复核。
- `unmatched`：低置信度，留空不强行匹配。

### Stage4 视频输出（新增）
- `KnowledgeGraph/data/output/video_match_report.json`
- `KnowledgeGraph/data/intermediate/video_transcripts/*.json`
- `KnowledgeGraph/data/output/resource_match_report.json`（仍保留聚合视图）

### quality_report 指标（更新）
- `video_transcript_coverage`
- `video_match_rate`
- `avg_video_match_score`
## Stage4 Video Matching V2 (2026-04-22)
- Video matching no longer depends on legacy mappings from `data/course/big_data.json`.
- Stage4 video flow is now: subtitle-first extraction (`m3u8`/`vtt`/`srt`) -> ASR fallback (`faster-whisper`) -> transcript indexing.
- Matching flow: query expansion -> coarse recall (`BM25` + keyword overlap) -> rerank (semantic + keyword coverage + hierarchy consistency).
- Default rerank weights: `0.45 semantic + 0.35 keyword + 0.20 hierarchy`.
- Confidence routing:
- `matched`: high confidence, write video resource into canonical graph.
- `needs_review`: medium confidence, keep candidates in report for manual review.
- `unmatched`: low confidence, keep empty and do not force assignment.

### New Outputs
- `KnowledgeGraph/data/output/video_match_report.json`
- `KnowledgeGraph/data/intermediate/video_transcripts/*.json`

### Quality Metrics (Stage4)
- `video_transcript_coverage`
- `video_match_rate`
- `avg_video_match_score`
