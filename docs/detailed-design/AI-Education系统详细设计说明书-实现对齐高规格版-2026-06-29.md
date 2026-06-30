# AI-Education 系统详细设计说明书（实现对齐高规格版）

生成时间：2026-06-29 13:42:25

## 1. 文档概述

### 1.1 编写目的
本文档用于在需求分析文档基础上，进一步明确 AI-Education 系统的模块设计、接口边界、数据库结构、关键流程、图件说明和当前实现差距。本文档以当前 FastAPI OpenAPI、真实 MySQL 数据库和已确认需求边界为依据，避免仅按需求文字或旧基线文档臆写。

### 1.2 编制依据
- 需求基准：D:\pythonFile\AI-Education2\docs\requirements\AI-Education需求分析文档-图件美化版-2026-06-28.docx
- 开发基线：D:\pythonFile\AI-Education2\docs\detailed-design\AI-Education系统详细设计说明书-开发基线版-2026-06-28.md
- 接口依据：当前 FastAPI `app.openapi()`，共 164 个 operation。
- 数据库依据：当前 MySQL `ai_education_design`，共 42 张表。
- 数据行数说明：本文出现的行数只代表本地演示与验证快照，不代表正式生产数据。

### 1.3 设计原则
系统设计坚持“课程底座先发布、学习证据可追溯、诊断服务不越界、学生路径由学生端执行、教师干预需审核、教师看板需授权过滤”的原则。所有 AI 生成结果在进入正式教学动作前，都必须保留人工确认或人工审核边界。

## 2. 总体架构设计

![图 1 AI-Education 运行架构与边界](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_1_system_architecture.png)
图 1 AI-Education 运行架构与边界

![图 2 需求模块与实现模块协同关系](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_2_module_collaboration.png)
图 2 需求模块与实现模块协同关系

![图 3 课程底座—学习证据—画像诊断—教学反馈数据闭环](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_3_data_closed_loop.png)
图 3 课程底座—学习证据—画像诊断—教学反馈数据闭环

![图 4 MySQL 数据库分域与表结构现状](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_4_database_domains.png)
图 4 MySQL 数据库分域与表结构现状

系统采用前后端分离架构，前端负责学生端、教师端和管理员端页面组织；后端以 FastAPI 暴露业务接口；智能服务提供诊断、5E 引导、资源推荐和行业情报能力；MySQL 保存课程底座、学习证据、画像、诊断、路径、作业、干预和教师行为事件。

模块协同关系不按历史 URL 前缀机械划分，而按业务主责划分。例如能力映射相关接口虽然挂在 `/api/course-digital-twin` 下，但在详细设计中主归属为行业情报与能力对接；资源学习事件作为学习行为证据支撑接口单列；LLM、OCR、日志和文件管理接口作为支撑能力单列。

## 3. 核心业务流程设计

![图 5 课程底座建设、资源绑定与能力映射发布流程](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_5_course_publish_flow.png)
图 5 课程底座建设、资源绑定与能力映射发布流程

![图 6 学生画像、诊断智能体与个性化路径协同流程](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_6_student_diagnosis_path.png)
图 6 学生画像、诊断智能体与个性化路径协同流程

![图 7 教师看板、诊断证据与干预任务包闭环](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_7_teacher_intervention_loop.png)
图 7 教师看板、诊断证据与干预任务包闭环

课程发布流程强调草稿与已发布底座隔离。课程结构、候选资源、岗位能力候选和能力映射在发布前均属于草稿或待审状态，下游学生端、诊断、路径和看板只能读取已发布结果。

学生画像与诊断路径流程强调职责边界。学生数字孪生维护画像状态；诊断智能体提供薄弱点、原因和证据等级；个性化路径由学生端生成和执行；教师端不替学生生成正式补学路径，而是通过干预任务包安排资源、作业、提醒和跟踪。

教师干预流程强调人工审核。诊断服务给出风险和建议动作，系统可生成干预草稿，但任务包必须经教师审核后下发。学生完成后，任务结果回流学生画像、教师看板和教师数字孪生。

## 4. 模块详细设计

| 章节 | 模块 | 职责边界 | 接口数 | 相关表 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| 3.1 | 课程数字孪生与课程资源 | 维护课程底座、资源候选、发布版本和课程运行评估；下游只读已发布课程底座。 | 11 | courses、course_metadata、course_nodes、course_node_relations、resources、resource_learning_events | 基础实现，部分表为空：course_node_relations |
| 3.2 | 学生学习空间 | 承载学生学习入口，展示课程、资源、作业、路径和画像摘要，并回传学习行为。 | 9 | sessions、user_activity_log、user_states、resource_learning_events、learning_plans | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.3 | 在线测验 | 围绕知识点生成/发布/提交测验，测验结果作为叶子知识点强证据。 | 7 | quiz_attempts | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.4 | 学生数字孪生 | 维护学生画像状态、掌握度、章节实践能力、风险和能力达成；不直接解释根因或生成路径。 | 7 | twin_profiles、twin_profile_nodes、twin_history、resource_learning_events、homework_assignment_knowledge_points | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.5 | 诊断智能体 | 解释薄弱原因、证据等级和建议动作；证据不足时只提示补证，不强行诊断。 | 3 | diagnosis_reports、diagnosis_corrections、twin_profile_nodes、quiz_attempts、homework_submissions | 基础实现，部分表为空：diagnosis_corrections |
| 3.6 | 个性化学习路径 | 基于画像和诊断生成路径版本；正式节点必须来自已发布课程图谱。 | 7 | learning_plans、learning_plan_nodes、learning_path_node_status | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.7 | 5E 教学智能体 | 提供 5E 阶段化学习引导和 EES 有效度，作为过程性辅助证据。 | 6 | events、user_interaction、fivee_effectiveness_records | 基础实现，部分表为空：events、user_interaction、fivee_effectiveness_records |
| 3.8 | 作业与实践评测 | 支持四类作业、提交、批改、教师终审和证据回流；覆盖知识点必须教师确认。 | 19 | homework_assignments、homework_submissions、homework_assignment_knowledge_points、homework_grading_events | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.9 | 教师智能干预任务包 | 读取诊断结果生成线上任务包草稿，教师审核后下发，学生完成后回流。 | 16 | intervention_packages、intervention_package_items、intervention_package_student_records、teacher_intervention_events | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.10 | 教师看板与教师数字孪生 | 展示班级学情、风险和教师六维画像；AI 建议必须教师手动触发。 | 13 | teaching_interaction_events、teaching_research_events、homework_grading_events、teacher_intervention_events、user_activity_log、llm_logs | 已有接口和本地数据，需继续按页面和权限验收 |
| 3.11 | 教学互动 | 人工教学沟通和教研记录层；教师行为稳定回流教师数字孪生。 | 23 | teaching_announcements、teaching_discussion_topics、teaching_discussion_posts、teaching_research_records、teaching_interaction_events、teaching_research_events | 基础实现，部分表为空：teaching_announcements、teaching_discussion_topics、teaching_discussion_posts、teaching_research_records |
| 3.12 | 行业情报与能力对接 | 检索岗位、提取能力候选，教师确认后交课程数字孪生发布。 | 14 | career_positions、career_abilities、course_ability_mappings | 已有接口和本地数据，需继续按页面和权限验收 |

### 3.1 课程数字孪生与课程资源

维护课程底座、资源候选、发布版本和课程运行评估；下游只读已发布课程底座。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 11 个 operation |
| 数据表 | courses(8行)、course_metadata(8行)、course_nodes(282行)、course_node_relations(0行)、resources(290行)、resource_learning_events(22行) |
| 关键边界 | 只发布课程底座、资源绑定和能力支撑关系；下游只读已发布版本。 |
| 待验收点 | 课程底座发布态过滤需要继续代码级验收，下游不得读取未发布草稿节点、候选资源和候选能力映射。；资源自动检索质量、RAG 入库和资源审核体验仍需按真实页面闭环。 |

### 3.2 学生学习空间

承载学生学习入口，展示课程、资源、作业、路径和画像摘要，并回传学习行为。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 9 个 operation |
| 数据表 | sessions(64行)、user_activity_log(4行)、user_states(2行)、resource_learning_events(22行)、learning_plans(11行) |
| 关键边界 | 组织学生学习入口和学习行为记录，不重新计算画像或诊断。 |
| 待验收点 | 需核对首页、课程资源、作业、测验、画像摘要和路径任务是否形成统一学生工作台。；学生端不得暴露教师审核过程、证据权重调整和后台备注。 |

### 3.3 在线测验

围绕知识点生成/发布/提交测验，测验结果作为叶子知识点强证据。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 7 个 operation |
| 数据表 | quiz_attempts(26行) |
| 关键边界 | 提供已发布知识点测验和作答记录，是知识点强证据来源。 |
| 待验收点 | 测验定义、发布和作答接口已存在，但题目版本、知识点绑定和异常测验排除规则需要补字段级说明。；测验结果回流画像、诊断和教师看板的触发时机需要代码级验收。 |

### 3.4 学生数字孪生

维护学生画像状态、掌握度、章节实践能力、风险和能力达成；不直接解释根因或生成路径。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 7 个 operation |
| 数据表 | twin_profiles(6行)、twin_profile_nodes(41行)、twin_history(71行)、resource_learning_events(22行)、homework_assignment_knowledge_points(4行) |
| 关键边界 | 维护学生画像状态，不解释根因，不生成路径。 |
| 待验收点 | 能力达成等级需要确认只读取教师确认并发布后的职业能力映射。；证据下钻、快照追溯和学生/教师视图差异仍需前端验收。 |

### 3.5 诊断智能体

解释薄弱原因、证据等级和建议动作；证据不足时只提示补证，不强行诊断。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 3 个 operation |
| 数据表 | diagnosis_reports(6行)、diagnosis_corrections(0行)、twin_profile_nodes(41行)、quiz_attempts(26行)、homework_submissions(16行) |
| 关键边界 | 提供薄弱点、原因、证据等级和建议动作，不直接下发任务。 |
| 待验收点 | 诊断修正表当前为空，人工修正闭环需要补演示数据和页面入口。；证据不足分支必须阻止强诊断进入正式路径或强干预。 |

### 3.6 个性化学习路径

基于画像和诊断生成路径版本；正式节点必须来自已发布课程图谱。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 7 个 operation |
| 数据表 | learning_plans(11行)、learning_plan_nodes(26行)、learning_path_node_status(4行) |
| 关键边界 | 学生端生成和执行路径，正式节点来自已发布课程图谱。 |
| 待验收点 | 路径生成应由学生端触发和执行，教师端只进行干预；`username` 参数接口需做角色约束。；路径版本的触发源、诊断依据、失效原因和回滚字段仍需补强。 |

### 3.7 5E 教学智能体

提供 5E 阶段化学习引导和 EES 有效度，作为过程性辅助证据。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 6 个 operation |
| 数据表 | events(0行)、user_interaction(0行)、fivee_effectiveness_records(0行) |
| 关键边界 | 提供阶段化学习引导和过程性辅助证据。 |
| 待验收点 | 5E 事件、交互统计和有效性记录当前为空，属于结构已建未产品化。；5E 证据只能作为过程性辅助证据，不能替代测验和作业。 |

### 3.8 作业与实践评测

支持四类作业、提交、批改、教师终审和证据回流；覆盖知识点必须教师确认。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 19 个 operation |
| 数据表 | homework_assignments(10行)、homework_submissions(16行)、homework_assignment_knowledge_points(4行)、homework_grading_events(3行) |
| 关键边界 | 作业覆盖知识点经教师确认后才影响叶子知识点画像。 |
| 待验收点 | 作业覆盖知识点必须只在 `confirmed_by_teacher=1` 后影响叶子知识点画像。；代码题稳定性、权限控制和状态流转需要继续专项验证。 |

### 3.9 教师智能干预任务包

读取诊断结果生成线上任务包草稿，教师审核后下发，学生完成后回流。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 16 个 operation |
| 数据表 | intervention_packages(6行)、intervention_package_items(32行)、intervention_package_student_records(6行)、teacher_intervention_events(14行) |
| 关键边界 | 教师审核后下发干预任务，学生完成后回流。 |
| 待验收点 | 干预任务完成结果回流画像、路径和看板的闭环需要继续验收。；`teacher/diagnose` 应调用统一诊断服务，避免形成第二套诊断口径。 |

### 3.10 教师看板与教师数字孪生

展示班级学情、风险和教师六维画像；AI 建议必须教师手动触发。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 13 个 operation |
| 数据表 | teaching_interaction_events(11行)、teaching_research_events(3行)、homework_grading_events(3行)、teacher_intervention_events(14行)、user_activity_log(4行)、llm_logs(28行) |
| 关键边界 | 查看授权范围内学情和教师行为画像，AI 建议需手动触发。 |
| 待验收点 | 所有看板接口必须按教师-学生或课程授权范围过滤。；AI 建议只能教师手动触发，不得写成系统自动替教师决策。 |

### 3.11 教学互动

人工教学沟通和教研记录层；教师行为稳定回流教师数字孪生。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 23 个 operation |
| 数据表 | teaching_announcements(0行)、teaching_discussion_topics(0行)、teaching_discussion_posts(0行)、teaching_research_records(0行)、teaching_interaction_events(11行)、teaching_research_events(3行) |
| 关键边界 | 人工沟通和教研记录层，行为事件回流教师数字孪生。 |
| 待验收点 | 公告、讨论、教研记录表当前多为空，需要补演示数据和前端验收。；互动证据进入学生画像时需要保留来源、时间、课程节点和任务类型。 |

### 3.12 行业情报与能力对接

检索岗位、提取能力候选，教师确认后交课程数字孪生发布。

| 设计项 | 当前说明 |
| --- | --- |
| 接口覆盖 | 14 个 operation |
| 数据表 | career_positions(1行)、career_abilities(1行)、course_ability_mappings(1行) |
| 关键边界 | 生成岗位和能力候选，不负责发布课程底座。 |
| 待验收点 | 3.12 产生岗位/能力候选，3.1 完成审核发布，设计中需避免职责混写。；职业能力映射只允许使用教师确认发布后的叶子知识点关系。 |

## 5. 接口设计

接口章节以当前 FastAPI OpenAPI 为准。正式接口说明后续还应继续补请求字段、响应字段、权限角色和错误码；本版重点解决接口覆盖、模块归属和支撑接口分组。

![图 8 FastAPI 接口分组统计](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_8_api_classification.png)
图 8 FastAPI 接口分组统计

### 5.1 课程数字孪生与课程资源

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/course-digital-twin/courses | List Course Digital Twin Courses |  | 200,422 |
| POST | /api/course-digital-twin/initial-graph | Generate Course Digital Twin Initial Graph | application/json | 200,422 |
| POST | /api/course-digital-twin/publish | Publish Course Digital Twin | application/json | 200,422 |
| POST | /api/course-digital-twin/resource-candidates/bind | Bind Course Digital Twin Resource Candidates | application/json | 200,422 |
| POST | /api/course-digital-twin/resource-review | Review Course Digital Twin Resource | application/json | 200,422 |
| POST | /api/course-digital-twin/structure | Upsert Course Digital Twin Structure | application/json | 200,422 |
| GET | /api/course-digital-twin/{course_id} | Get Course Digital Twin Summary |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/resources | List Course Digital Twin Resources |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/runtime-evaluation | Evaluate Course Digital Twin Runtime |  | 200,422 |
| GET | /api/knowledge-graph | Get Knowledge Graph |  | 200,422 |
| POST | /api/upload | Upload Files | multipart/form-data | 200,422 |

### 5.2 学生学习空间

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/graph-visualization | Get Graph Visualization |  | 200,422 |
| GET | /api/learning-nodes | Get Learning Nodes |  | 200,422 |
| GET | /api/learning-plans | Get Learning Plans |  | 200,422 |
| GET | /api/learning-progress | Get Learning Progress |  | 200,422 |
| GET | /api/learning-streak | Get Learning Streak |  | 200,422 |
| POST | /api/node/resources | Get Node Resources | application/json | 200,422 |
| GET | /api/notifications/recent | Get Recent Notifications |  | 200,422 |
| POST | /api/pdf/select | Select Pdf | application/json | 200,422 |
| GET | /api/pdf/{path} | Get Pdf |  | 200,422 |

### 5.3 在线测验

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/quiz/answer | Answer Quiz | application/json | 200,422 |
| POST | /api/quiz/complete | Complete Quiz | application/json | 200,422 |
| GET | /api/quiz/definitions | List Quiz Definitions |  | 200,422 |
| POST | /api/quiz/definitions | Save Quiz Definition | application/json | 200,422 |
| POST | /api/quiz/definitions/{definition_id}/publish | Publish Quiz Definition | application/json | 200,422 |
| POST | /api/quiz/start | Start Quiz | application/json | 200,422 |
| POST | /api/quiz/summary | Generate Quiz Summary | application/json | 200,422 |

### 5.4 学生数字孪生

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/digital-twin/collect/{username} | Collect Data |  | 200,422 |
| GET | /api/digital-twin/profile/{username} | Get Profile |  | 200,422 |
| POST | /api/digital-twin/quiz-score | Update Quiz Score | application/json | 200,422 |
| POST | /api/digital-twin/student-course-profile | Get Student Course Profile | application/json | 200,422 |
| GET | /api/digital-twin/student-profile/{username} | Get Student Profile Summary |  | 200,422 |
| GET | /api/homework/twin/my-results | Get My Results For Twin |  | 200,422 |
| GET | /api/homework/twin/student-results | Get Student Results For Twin |  | 200,422 |

### 5.5 诊断智能体

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/digital-twin/diagnosis-corrections | List Diagnosis Corrections |  | 200,422 |
| POST | /api/digital-twin/diagnosis-corrections | Record Diagnosis Correction | application/json | 200,422 |
| POST | /api/digital-twin/diagnosis/{username} | Generate Student Diagnosis | application/json | 200,422 |

### 5.6 个性化学习路径

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/digital-twin/path/generate/{username} | Generate Path | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/current | Get Current Path |  | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node-status/{node_id} | Update Path Node Status | application/json | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node/{node_id} | Update Node Mastery | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/versions | List Path Versions |  | 200,422 |
| POST | /api/learning-plan | Create Learning Plan | application/json | 200,422 |
| POST | /api/learning-plan/from-quiz | Create Learning Plan From Quiz | application/json | 200,422 |

### 5.7 5E 教学智能体

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/5e/chat/history | Get Conversation History | application/json | 200,422 |
| GET | /api/5e/chat/history/{user_id}/{lesson_id} | Conversation History |  | 200,422 |
| POST | /api/5e/chat/message | Receive Chat Content | application/json | 200,422 |
| POST | /api/5e/course/id-by-name | Api Get Course Id By Name | application/json | 200,422 |
| GET | /api/5e/effectiveness/summary | Effectiveness Summary |  | 200,422 |
| GET | /api/5e/ping | Ping |  | 200 |

### 5.8 作业与实践评测

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/homework/ai/generate-draft | Ai Generate Draft | application/json | 200,422 |
| POST | /api/homework/ai/generate-questions | Ai Generate Questions | application/json | 200,422 |
| GET | /api/homework/assignments | List Assignments |  | 200,422 |
| POST | /api/homework/assignments | Publish Assignment | application/json | 200,422 |
| POST | /api/homework/assignments/seed-oj-smoke | Seed Oj Smoke Assignment |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id} | Get Assignment |  | 200,422 |
| PUT | /api/homework/assignments/{assignment_id} | Update Assignment | application/json | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/close | Close Assignment Status |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id}/coverage | Get Assignment Coverage |  | 200,422 |
| PUT | /api/homework/assignments/{assignment_id}/coverage | Update Assignment Coverage | application/json | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/publish | Publish Assignment Status |  | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/reopen | Reopen Assignment Status |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id}/submissions | List Assignment Submissions |  | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/submissions | Submit Assignment | application/json | 200,422 |
| GET | /api/homework/course-nodes | List Course Nodes |  | 200,422 |
| GET | /api/homework/my-submissions | List My Submissions |  | 200,422 |
| GET | /api/homework/submissions/{submission_id} | Get Submission Detail |  | 200,422 |
| POST | /api/homework/submissions/{submission_id}/ai-grade | Ai Grade Submission | application/json | 200,422 |
| POST | /api/homework/submissions/{submission_id}/final-grade | Finalize Grade | application/json | 200,422 |

### 5.9 教师智能干预任务包

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/intervention/student/packages | List Student Packages |  | 200,422 |
| GET | /api/intervention/student/packages/{package_id} | Get Student Package Detail |  | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/answers | Student Save Answer | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/decision | Student Decide Package | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/progress | Student Update Package Progress | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/tasks | Student Update Structured Task | application/json | 200,422 |
| POST | /api/intervention/teacher/diagnose | Diagnose Students | application/json | 200,422 |
| POST | /api/intervention/teacher/generate-draft | Generate Intervention Draft | application/json | 200,422 |
| GET | /api/intervention/teacher/packages | List Teacher Packages |  | 200,422 |
| GET | /api/intervention/teacher/packages/{package_id} | Get Teacher Package Detail |  | 200,422 |
| PUT | /api/intervention/teacher/packages/{package_id} | Update Teacher Package | application/json | 200,422 |
| POST | /api/intervention/teacher/packages/{package_id}/grade | Grade Teacher Package Question | application/json | 200,422 |
| POST | /api/intervention/teacher/packages/{package_id}/push | Push Teacher Package |  | 200,422 |
| GET | /api/intervention/teacher/progress | List Teacher Progress |  | 200,422 |
| GET | /api/intervention/teacher/students-overview | Get Teacher Students Overview |  | 200,422 |
| GET | /api/intervention/teacher/task-reference-options | List Teacher Task Reference Options |  | 200,422 |

### 5.10 教师看板与教师数字孪生

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/dashboard/class-overview | Get Class Overview |  | 200,422 |
| GET | /api/dashboard/node/{node_id}/ranking | Get Node Ranking |  | 200,422 |
| GET | /api/dashboard/student/{username} | Get Student Detail |  | 200,422 |
| GET | /api/dashboard/student/{username}/trend | Get Student Trend |  | 200,422 |
| GET | /api/dashboard/teacher-twin | Get Teacher Twin |  | 200,422 |
| POST | /api/dashboard/teacher-twin/ai-suggestions | Generate Teacher Twin Ai Suggestions |  | 200,422 |
| GET | /api/dashboard/teacher-twin/drilldown | Get Teacher Twin Drilldown |  | 200,422 |
| POST | /api/digital-twin/teacher-events/grading | Record Teacher Grading Event | application/json | 200,422 |
| POST | /api/digital-twin/teacher-events/interaction | Record Teacher Interaction Event | application/json | 200,422 |
| POST | /api/digital-twin/teacher-events/research | Record Teacher Research Event | application/json | 200,422 |
| GET | /api/digital-twin/teacher-profile/{teacher_username} | Get Teacher Profile Summary |  | 200,422 |
| POST | /api/digital-twin/teacher-profile/{teacher_username}/external-sync | Sync Teacher External Metrics | application/json | 200,422 |
| GET | /api/heatmap | Get Heatmap |  | 200,422 |

### 5.11 教学互动

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/teaching-interaction/analytics | Get Interaction Analytics |  | 200,422 |
| GET | /api/teaching-interaction/announcements | List Announcements |  | 200,422 |
| POST | /api/teaching-interaction/announcements | Create Announcement | application/json | 200,422 |
| GET | /api/teaching-interaction/announcements/public | List Public Announcements |  | 200,422 |
| DELETE | /api/teaching-interaction/announcements/{announcement_id} | Delete Announcement |  | 200,422 |
| PUT | /api/teaching-interaction/announcements/{announcement_id} | Update Announcement | application/json | 200,422 |
| GET | /api/teaching-interaction/context-options | Get Context Options |  | 200,422 |
| POST | /api/teaching-interaction/posts | Create Post | application/json | 200,422 |
| DELETE | /api/teaching-interaction/posts/{post_id} | Delete Post |  | 200,422 |
| PUT | /api/teaching-interaction/posts/{post_id} | Update Post | application/json | 200,422 |
| DELETE | /api/teaching-interaction/posts/{post_id}/student | Delete Student Post |  | 200,422 |
| PUT | /api/teaching-interaction/posts/{post_id}/student | Update Student Post | application/json | 200,422 |
| GET | /api/teaching-interaction/topics | List Topics |  | 200,422 |
| POST | /api/teaching-interaction/topics | Create Topic | application/json | 200,422 |
| GET | /api/teaching-interaction/topics/public | List Public Topics |  | 200,422 |
| DELETE | /api/teaching-interaction/topics/{topic_id} | Delete Topic |  | 200,422 |
| PUT | /api/teaching-interaction/topics/{topic_id} | Update Topic | application/json | 200,422 |
| POST | /api/teaching-interaction/topics/{topic_id}/student-question | Create Student Question |  | 200,422 |
| GET | /api/teaching-research/context-options | Get Context Options |  | 200,422 |
| GET | /api/teaching-research/records | List Research Records |  | 200,422 |
| POST | /api/teaching-research/records | Create Research Record | application/json | 200,422 |
| DELETE | /api/teaching-research/records/{record_id} | Delete Research Record |  | 200,422 |
| PUT | /api/teaching-research/records/{record_id} | Update Research Record | application/json | 200,422 |

### 5.12 行业情报与能力对接

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/course-digital-twin/abilities/import | Import Course Digital Twin Abilities | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings | Upsert Course Digital Twin Ability Mappings | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings/candidates/generate | Generate Course Digital Twin Ability Mapping Candidates | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings/review | Review Course Digital Twin Ability Mappings | application/json | 200,422 |
| POST | /api/course-digital-twin/positions | Upsert Course Digital Twin Position | application/json | 200,422 |
| GET | /api/course-digital-twin/{course_id}/abilities | List Course Digital Twin Abilities |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/ability-mappings | List Course Digital Twin Ability Mappings |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/positions | List Course Digital Twin Positions |  | 200,422 |
| POST | /api/industry-intelligence/analyze | Analyze | application/json | 200,422 |
| GET | /api/industry-intelligence/current | Get Current Task |  | 200,422 |
| POST | /api/industry-intelligence/reanalyze | Reanalyze | application/json | 200,422 |
| GET | /api/industry-intelligence/status | Get Status |  | 200 |
| GET | /api/industry-intelligence/tasks/{task_id} | Get Task |  | 200,422 |
| POST | /api/industry-intelligence/tasks/{task_id}/cancel | Cancel Task |  | 200,422 |

### 5.13 LLM、OCR 与日志支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/chat | Chat | application/json | 200,422 |
| GET | /api/health/llm | Llm Health Check |  | 200,422 |
| GET | /api/languages | Get Languages |  | 200 |
| POST | /api/llm-log | Log Llm Call | application/json | 200,422 |
| GET | /api/llm-logs | Get Llm Logs |  | 200 |
| POST | /api/ocr/extract | Extract Text From Image | multipart/form-data | 200,422 |
| POST | /api/summary | Generate Summary | application/json | 200,422 |

### 5.14 前端页面与历史兼容接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | / | Root |  | 200 |
| GET | /admin.html | Get Admin Page |  | 200 |
| GET | /teacher.html | Get Teacher Page |  | 200 |
| GET | /{full_path} | Frontend Spa |  | 200,422 |

### 5.15 学习行为证据支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/resource-learning/events | Record Resource Learning Event | application/json | 200,422 |
| GET | /api/resource-learning/summary | Get Resource Learning Summary |  | 200,422 |

### 5.16 用户、权限与会话

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/auth/login | Login Json | application/json | 200,422 |
| POST | /api/change-password | Change Password | application/json | 200,422 |
| GET | /api/current-user | Get Current User Info |  | 200,422 |
| POST | /api/logout | Logout |  | 200,422 |
| POST | /api/register | Register User | application/json | 200,422 |
| GET | /api/students | Get Students |  | 200,422 |
| GET | /api/teachers | Get Teachers |  | 200 |
| POST | /api/update-profile | Update Profile | application/json | 200,422 |
| POST | /login/admin | Login Admin | application/x-www-form-urlencoded | 200,422 |
| POST | /login/student | Login Student | application/x-www-form-urlencoded | 200,422 |
| POST | /login/teacher | Login Teacher | application/x-www-form-urlencoded | 200,422 |

### 5.17 资源文件与课程运行支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/clear-course-cache | Clear Course Cache |  | 200,422 |
| POST | /api/delete-resource | Delete Resource | application/json | 200,422 |
| GET | /api/recycle-bin | Get Recycle Bin |  | 200,422 |
| POST | /api/restore-resource | Restore Resource | application/json | 200,422 |

### 5.18 通用/历史接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/learning-activity | Log Learning Activity | application/json | 200,422 |

## 6. 数据库设计

当前数据库为 `ai_education_design`，共 42 张表。表结构来自 `SHOW FULL COLUMNS` 与 `SHOW INDEX`，正式数据库设计还应继续补充 `SHOW CREATE TABLE` 或 `information_schema.KEY_COLUMN_USAGE`，以区分普通索引、唯一约束和真实外键。

| 表名 | 当前行数 | 字段数 | 归属/消费模块 | 数据状态 |
| --- | --- | --- | --- | --- |
| career_abilities | 1 | 9 | 行业情报与能力对接、课程数字孪生与课程资源 | 已有本地数据 |
| career_positions | 1 | 10 | 行业情报与能力对接、课程数字孪生与课程资源 | 已有本地数据 |
| course_ability_mappings | 1 | 13 | 行业情报与能力对接、课程数字孪生与课程资源、学生数字孪生 | 已有本地数据 |
| course_metadata | 8 | 5 | 课程数字孪生与课程资源 | 已有本地数据 |
| course_node_relations | 0 | 6 | 课程数字孪生与课程资源 | 结构已建未产品化 |
| course_nodes | 282 | 10 | 课程数字孪生与课程资源 | 已有本地数据 |
| courses | 8 | 12 | 课程数字孪生与课程资源 | 已有本地数据 |
| diagnosis_corrections | 0 | 14 | 诊断智能体 | 结构已建未产品化 |
| diagnosis_reports | 6 | 11 | 诊断智能体 | 已有本地数据 |
| events | 0 | 7 | 5E 教学智能体 | 结构已建未产品化 |
| fivee_effectiveness_records | 0 | 18 | 5E 教学智能体 | 结构已建未产品化 |
| homework_assignment_knowledge_points | 4 | 14 | 学生数字孪生、作业与实践评测、诊断智能体 | 已有本地数据 |
| homework_assignments | 10 | 20 | 作业与实践评测 | 已有本地数据 |
| homework_grading_events | 3 | 12 | 作业与实践评测、教师看板与教师数字孪生 | 已有本地数据 |
| homework_submissions | 16 | 14 | 诊断智能体、作业与实践评测、学生数字孪生 | 已有本地数据 |
| intervention_package_items | 32 | 14 | 教师智能干预任务包 | 已有本地数据 |
| intervention_package_student_records | 6 | 13 | 教师智能干预任务包 | 已有本地数据 |
| intervention_packages | 6 | 16 | 教师智能干预任务包 | 已有本地数据 |
| learning_path_node_status | 4 | 17 | 个性化学习路径 | 已有本地数据 |
| learning_plan_nodes | 26 | 11 | 个性化学习路径 | 已有本地数据 |
| learning_plans | 11 | 11 | 学生学习空间、个性化学习路径 | 已有本地数据 |
| llm_logs | 28 | 8 | 教师看板与教师数字孪生、LLM、OCR 与日志支撑接口 | 已有本地数据 |
| quiz_attempts | 26 | 10 | 在线测验、诊断智能体、学生数字孪生、教师看板与教师数字孪生 | 已有本地数据 |
| resource_learning_events | 22 | 14 | 课程数字孪生与课程资源、学生学习空间、学生数字孪生、学习行为证据支撑接口 | 已有本地数据 |
| resources | 290 | 17 | 课程数字孪生与课程资源 | 已有本地数据 |
| sessions | 64 | 10 | 学生学习空间 | 已有本地数据 |
| teacher_intervention_events | 14 | 10 | 教师智能干预任务包、教师看板与教师数字孪生 | 已有本地数据 |
| teacher_student_links | 6 | 5 | 通用/支撑表 | 已有本地数据 |
| teaching_announcements | 0 | 10 | 教学互动 | 结构已建未产品化 |
| teaching_discussion_posts | 0 | 9 | 教学互动 | 结构已建未产品化 |
| teaching_discussion_topics | 0 | 11 | 教学互动 | 结构已建未产品化 |
| teaching_interaction_events | 11 | 11 | 教师看板与教师数字孪生、教学互动 | 已有本地数据 |
| teaching_research_events | 3 | 7 | 教师看板与教师数字孪生、教学互动 | 已有本地数据 |
| teaching_research_records | 0 | 11 | 教学互动 | 结构已建未产品化 |
| twin_history | 71 | 8 | 学生数字孪生 | 已有本地数据 |
| twin_profile_nodes | 41 | 12 | 学生数字孪生、诊断智能体 | 已有本地数据 |
| twin_profiles | 6 | 7 | 学生数字孪生 | 已有本地数据 |
| user_activity_log | 4 | 7 | 学生学习空间、教师看板与教师数字孪生、用户、权限与会话 | 已有本地数据 |
| user_interaction | 0 | 12 | 5E 教学智能体 | 结构已建未产品化 |
| user_profiles | 0 | 9 | 通用/支撑表 | 结构已建未产品化 |
| user_states | 2 | 4 | 学生学习空间 | 已有本地数据 |
| users | 8 | 10 | 通用/支撑表 | 已有本地数据 |

## 7. 需求实现差距与验收路线

![图 9 需求—实现差距与后续验收路线](D:/pythonFile/AI-Education2/docs/detailed-design/high-spec/figures/fig_9_gap_roadmap.png)
图 9 需求—实现差距与后续验收路线

当前系统已经具备主链路接口和数据库结构，但“有接口、有表、有本地数据”不等于业务边界已经闭环。后续验收必须重点检查发布态过滤、教师确认、学生/教师视图隔离、教师授权范围和证据回流。

| 模块 | 主要差距与验收点 |
| --- | --- |
| 课程数字孪生与课程资源 | 课程底座发布态过滤需要继续代码级验收，下游不得读取未发布草稿节点、候选资源和候选能力映射。；资源自动检索质量、RAG 入库和资源审核体验仍需按真实页面闭环。 |
| 学生学习空间 | 需核对首页、课程资源、作业、测验、画像摘要和路径任务是否形成统一学生工作台。；学生端不得暴露教师审核过程、证据权重调整和后台备注。 |
| 在线测验 | 测验定义、发布和作答接口已存在，但题目版本、知识点绑定和异常测验排除规则需要补字段级说明。；测验结果回流画像、诊断和教师看板的触发时机需要代码级验收。 |
| 学生数字孪生 | 能力达成等级需要确认只读取教师确认并发布后的职业能力映射。；证据下钻、快照追溯和学生/教师视图差异仍需前端验收。 |
| 诊断智能体 | 诊断修正表当前为空，人工修正闭环需要补演示数据和页面入口。；证据不足分支必须阻止强诊断进入正式路径或强干预。 |
| 个性化学习路径 | 路径生成应由学生端触发和执行，教师端只进行干预；`username` 参数接口需做角色约束。；路径版本的触发源、诊断依据、失效原因和回滚字段仍需补强。 |
| 5E 教学智能体 | 5E 事件、交互统计和有效性记录当前为空，属于结构已建未产品化。；5E 证据只能作为过程性辅助证据，不能替代测验和作业。 |
| 作业与实践评测 | 作业覆盖知识点必须只在 `confirmed_by_teacher=1` 后影响叶子知识点画像。；代码题稳定性、权限控制和状态流转需要继续专项验证。 |
| 教师智能干预任务包 | 干预任务完成结果回流画像、路径和看板的闭环需要继续验收。；`teacher/diagnose` 应调用统一诊断服务，避免形成第二套诊断口径。 |
| 教师看板与教师数字孪生 | 所有看板接口必须按教师-学生或课程授权范围过滤。；AI 建议只能教师手动触发，不得写成系统自动替教师决策。 |
| 教学互动 | 公告、讨论、教研记录表当前多为空，需要补演示数据和前端验收。；互动证据进入学生画像时需要保留来源、时间、课程节点和任务类型。 |
| 行业情报与能力对接 | 3.12 产生岗位/能力候选，3.1 完成审核发布，设计中需避免职责混写。；职业能力映射只允许使用教师确认发布后的叶子知识点关系。 |

