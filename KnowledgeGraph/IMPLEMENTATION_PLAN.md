# AI-Edu 知识图谱模块实施方案（Big Data 课程）
版本：v1.3  
日期：2026-04-22  
适用范围：`KnowledgeGraph`目录 + `data/course/big_data.json`替换链路 + 资源匹配 + 可选Neo4j落库

## 1. 目标与约束
### 1.1 核心目标
- 基于课程脚本文档自动生成高质量课程知识图谱。
- 图谱结构具备教学意义，可用于学习路径与资源匹配。
- 输出兼容系统原有消费格式，可平滑替换`data/course/big_data.json`。

### 1.2 协作与工程约束
- 默认仅改动`KnowledgeGraph/**`、`requirements.txt`、必要配置。
- 不主动侵入他人模块；涉及跨模块结构性改动前先请示。
- 代码模块化，支持后续“教师上传课程自动生成/增量维护图谱”迭代。

## 2. 知识图谱设计规范
### 2.1 三层教学实体定义
- `chapter`：课程中的语义化章节域，不允许“第X章”这类空泛名称。
- `topic`：章节下的主题单元，连接教学场景与具体概念。
- `concept`：最小教学知识点，要求可解释、可学习、可匹配资源。

关系：`course -> chapter -> topic -> concept`由`HAS_CHILD`表达层级；底层概念间关系独立存储。

### 2.2 关系类型
- `HAS_CHILD`：层级包含关系。
- `PREREQUISITE`：先修依赖（必须无环）。
- `RELATED_TO`：相关关系。
- `USES` / `APPLIES_TO` / `COMPARES_WITH` / `INCLUDES`：补充语义关系。

### 2.3 质量要求
- 概念命名必须有教学意义，过滤口语、碎片、抽象空词、讲稿噪声。
- `description`与`learning_objective`必须具体、可区分，禁止模板化套话。
- `keywords`必须去噪，过滤“本节课我们学习”“例如”等无效词。

## 3. 代码架构与模块职责
```text
KnowledgeGraph/src/
  pipeline.py                      # 阶段编排（0~7）
  course_profile.py                # 课程画像配置加载
  kg_text_rules.py                 # 文本规则与候选过滤
  ingestion/
    docx_loader.py                 # 脚本加载
    text_cleaner.py                # 清洗分段
  extraction/
    kggen_client.py                # kg-gen封装
    triple_postprocess.py          # 三元组规范化
  pedagogy/
    hierarchy_builder.py           # 教学层级构建
    relation_refiner.py            # 关系归一与去环
    quality_gate.py                # 质量门禁
  resource_match/
    utils.py                       # 匹配通用函数（分词、上下文、旧图谱映射）
    book_indexer.py                # PDF索引 + 文本资源匹配
    video_matcher.py               # 视频资源匹配（可选）
    web_resource_matcher.py        # 阶段6预留
```

## 4. 分阶段实施与验收
## 阶段0：工程骨架与运行自检（已完成）
实施内容：
- 初始化目录、配置、日志与阶段入口。
- 支持dry-run与旧图谱备份。

验收目标：
- `python KnowledgeGraph/scripts/run_pipeline.py --stage 0 --dry-run`成功。

## 阶段1：脚本文档解析与清洗（已完成）
实施内容：
- 解析`unstructured_script/*.docx`。
- 输出标准化语料（文档 + 分段）。

验收目标：
- 产出`scripts_cleaned.jsonl`和`scripts_cleaned_docs.json`。
- 文档解析成功率达标。

## 阶段2：三元组抽取与标准化（已完成）
实施内容：
- 集成`kg-gen`进行关系抽取。
- 去重、归一化，形成可构图三元组。

验收目标：
- 输出`triples_raw.jsonl`与`triples_normalized.jsonl`。
- 抽取结果可支持后续层级重构。

## 阶段3：教学化图谱重构与质量门禁（已完成）
实施内容：
- 基于通用规则 + `course_profile.yaml`做概念筛选与层级重建。
- 规范章节命名、关系类型、概念质量。
- 产出`concept_audit.json`追踪候选拒绝原因。

验收目标：
- 产出`big_data_kg.canonical.json`、`quality_report.json`、`concept_audit.json`。
- 通过关键硬门禁（章节语义、关键词去噪、无效概念清零等）。

## 阶段4：资源匹配（文本必达 + 视频可选）（已完成）
实施内容：
- 文本资源匹配：
  - 对`data/Book/*.pdf`抽取文本建立索引。
  - 根据概念名称、描述、目标、关键词、topic/chapter上下文匹配最相关PDF。
  - 利用历史图谱`data/course/big_data.json`作为弱监督提示。
  - 低置信度触发可追踪回退策略，确保覆盖。
- 视频资源匹配：
  - 使用`data/Video/video_urls.json` + 历史图谱映射做可选匹配。
  - 无高置信度候选时允许留空。
- 更新`quality_report.json`中的资源覆盖率指标。

验收目标：
- 每个`concept`至少1个文本资源（100%覆盖）。
- 输出视频匹配率统计。
- 产出：
  - `KnowledgeGraph/data/intermediate/book_index.json`
  - `KnowledgeGraph/data/output/resource_match_report.json`
  - `KnowledgeGraph/data/output/stage4_summary.json`
  - `KnowledgeGraph/data/output/stage4_run_report.json`

## 阶段5：兼容导出与系统替换（待实施）
实施内容：
- 从canonical导出legacy结构，生成`big_data_kg.legacy.json`。
- 替换`data/course/big_data.json`并联调接口消费链路。

验收目标：
- 后端接口可无代码侵入消费新图谱。

## 阶段6：外部网络资源增强（可选，待实施）
实施内容：
- 可选抓取并融合外部文本/视频资源（白名单站点）。

验收目标：
- 开关关闭不影响主流程，开启后资源可追溯。

## 阶段7：Neo4j落库（可选，待实施）
实施内容：
- 导出Cypher或直写Neo4j（节点、关系、资源）。

验收目标：
- 节点关系数量与canonical一致，可完成核心查询。

## 5. 阶段4后的当前产物与指标口径
`quality_report.json`至少维护以下关键指标：
- `concept_text_resource_coverage`
- `video_match_rate`
- `duplicate_name_rate`
- `chapter_name_issue_count`
- `keyword_noise_count`
- `invalid_concept_count`
- `prerequisite_cycle_detected`

## 6. 配置与依赖
### 6.1 环境变量
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `NEO4J_URI`
- `NEO4_USER`
- `NEO4J_PASSWORD`

### 6.2 依赖策略
- 新增依赖必须写入`requirements.txt`。
- 资源匹配当前复用已存在依赖（如`PyMuPDF`）完成PDF索引。

## 7. 可复用性设计说明
- 规则与阈值外置到`course_profile.yaml`，便于课程迁移。
- 资源匹配与图谱构建解耦，后续可替换更强检索器（向量召回/重排）。
- 阶段化编排支持“先验收再进入下一阶段”的协作流程。
## Stage4 Video Matching V2 (2026-04-22)
### Goal
- Remove legacy-video dependency on `data/course/big_data.json`.
- Match only from `video_urls + subtitle/transcript text + concept semantics`.
- Keep video matching optional while improving coverage and traceability.

### Flow
1. Transcript collection: subtitle-first (`m3u8`/`vtt`/`srt`), ASR fallback (`faster-whisper`).
2. Transcript indexing: cleaning, chunking, keyword extraction, sparse vectorization.
3. Concept retrieval: query expansion, coarse recall (`BM25 + keyword`), rerank (`semantic + keyword coverage + hierarchy consistency`).
4. Confidence gate: `matched` / `needs_review` / `unmatched`.
5. Reporting: full trace report with candidate list, score breakdown, evidence snippet and timestamp.

### Score Formula
- `total_score = 0.45 * semantic + 0.35 * keyword_coverage + 0.20 * hierarchy_consistency`

### New Outputs
- `KnowledgeGraph/data/intermediate/video_transcripts/*.json`
- `KnowledgeGraph/data/output/video_match_report.json`
- `KnowledgeGraph/data/output/resource_match_report.json` (aggregated stage4 view)

### Stage4 Quality Metrics
- `video_transcript_coverage`
- `video_match_rate`
- `avg_video_match_score`
