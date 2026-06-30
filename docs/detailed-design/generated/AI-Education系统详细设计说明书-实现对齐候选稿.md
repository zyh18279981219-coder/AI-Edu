# AI-Education 系统详细设计说明书（实现对齐候选稿）

生成时间：2026-06-29 13:21:14

## 1. 编制依据

- 需求基准：`D:\pythonFile\AI-Education2\docs\requirements\AI-Education需求分析文档-图件美化版-2026-06-28.docx`
- 现有详细设计底稿：`D:\pythonFile\AI-Education2\docs\detailed-design\AI-Education系统详细设计说明书-开发基线版-2026-06-28.md`
- 接口依据：当前 `backend/app.py` 运行时 `app.openapi()`。
- 数据库依据：当前 MySQL `ai_education_design` 的 `SHOW TABLES`、`SHOW FULL COLUMNS`、`SHOW INDEX`。
- 本文为候选稿，不直接覆盖正式 Word；正式交付前应再做人工审阅、排版和需求逐条审计。

## 2. 当前实现总览

当前 FastAPI 共暴露 `164` 个接口操作，当前 MySQL 数据库共有 `42` 张业务/支撑表。数据库行数只代表本地演示与验证快照，不能等同于正式生产数据量。

系统主链路已经覆盖课程数字孪生、在线测验、学生数字孪生、诊断、个性化路径、作业、教师干预、教师看板、教学互动和行业情报等模块。其中部分模块仍处于基础实现或结构已建状态，尤其是 5E 有效性、教学互动内容数据、教研记录、部分教师画像事件仍需要继续产品化。

## 3. 模块职责边界

学生端负责查看画像、触发诊断结果消费和生成/执行个性化学习路径；教师端负责课程建设、资源与能力映射审核、作业发布、看板查看和干预任务下发。诊断智能体是计算与解释服务，向学生数字孪生、个性化路径和教师看板提供薄弱点、证据等级和建议动作；它不直接替代学生端路径生成，也不直接替代教师端干预。

课程数字孪生发布课程底座、资源绑定和能力支撑关系；下游模块读取已发布课程底座。作业覆盖知识点、职业能力映射、干预任务包下发等关键动作必须保留教师确认边界。

需要注意，本文的接口归类采用“业务主责 + 支撑接口 + 交叉引用”的方式。部分接口由于历史路由命名仍挂在 `/api/digital-twin` 或 `/api/course-digital-twin` 下，但设计文档按真实业务边界归类。

## 4. 模块-接口-数据表映射

| 章节 | 模块 | 职责边界 | 接口数 | 主要接口 | 相关表(行数) | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | 课程数字孪生与课程资源 | 维护课程底座、资源候选、发布版本和课程运行评估；下游只读已发布课程底座。 | 11 | `GET /api/course-digital-twin/courses`<br>`POST /api/course-digital-twin/initial-graph`<br>`POST /api/course-digital-twin/publish`<br>`POST /api/course-digital-twin/resource-candidates/bind`<br>`POST /api/course-digital-twin/resource-review`<br>`POST /api/course-digital-twin/structure`<br>`GET /api/course-digital-twin/{course_id}`<br>`GET /api/course-digital-twin/{course_id}/resources`<br>`GET /api/course-digital-twin/{course_id}/runtime-evaluation`<br>`GET /api/knowledge-graph`<br>`POST /api/upload` | `courses`(8)<br>`course_metadata`(8)<br>`course_nodes`(282)<br>`course_node_relations`(0)<br>`resources`(290)<br>`resource_learning_events`(22) | 基础实现，部分数据表为空：course_node_relations |
| 3.2 | 学生学习空间 | 承载学生学习入口，展示课程、资源、作业、路径和画像摘要，并回传学习行为。 | 9 | `GET /api/graph-visualization`<br>`GET /api/learning-nodes`<br>`GET /api/learning-plans`<br>`GET /api/learning-progress`<br>`GET /api/learning-streak`<br>`POST /api/node/resources`<br>`GET /api/notifications/recent`<br>`POST /api/pdf/select`<br>`GET /api/pdf/{path}` | `sessions`(64)<br>`user_activity_log`(4)<br>`user_states`(2)<br>`resource_learning_events`(22)<br>`learning_plans`(11) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.3 | 在线测验 | 围绕知识点生成/发布/提交测验，测验结果作为叶子知识点强证据。 | 7 | `POST /api/quiz/answer`<br>`POST /api/quiz/complete`<br>`GET /api/quiz/definitions`<br>`POST /api/quiz/definitions`<br>`POST /api/quiz/definitions/{definition_id}/publish`<br>`POST /api/quiz/start`<br>`POST /api/quiz/summary` | `quiz_attempts`(26) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.4 | 学生数字孪生 | 维护学生画像状态、掌握度、章节实践能力、风险和能力达成；不直接解释根因或生成路径。 | 7 | `POST /api/digital-twin/collect/{username}`<br>`GET /api/digital-twin/profile/{username}`<br>`POST /api/digital-twin/quiz-score`<br>`POST /api/digital-twin/student-course-profile`<br>`GET /api/digital-twin/student-profile/{username}`<br>`GET /api/homework/twin/my-results`<br>`GET /api/homework/twin/student-results` | `twin_profiles`(6)<br>`twin_profile_nodes`(41)<br>`twin_history`(71)<br>`resource_learning_events`(22)<br>`homework_assignment_knowledge_points`(4) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.5 | 诊断智能体 | 解释薄弱原因、证据等级和建议动作；证据不足时只提示补证，不强行诊断。 | 3 | `GET /api/digital-twin/diagnosis-corrections`<br>`POST /api/digital-twin/diagnosis-corrections`<br>`POST /api/digital-twin/diagnosis/{username}` | `diagnosis_reports`(6)<br>`diagnosis_corrections`(0)<br>`twin_profile_nodes`(41)<br>`quiz_attempts`(26)<br>`homework_submissions`(16) | 基础实现，部分数据表为空：diagnosis_corrections |
| 3.6 | 个性化学习路径 | 基于画像和诊断生成路径版本；正式节点必须来自已发布课程图谱。 | 7 | `POST /api/digital-twin/path/generate/{username}`<br>`GET /api/digital-twin/path/{username}/current`<br>`PATCH /api/digital-twin/path/{username}/node-status/{node_id}`<br>`PATCH /api/digital-twin/path/{username}/node/{node_id}`<br>`GET /api/digital-twin/path/{username}/versions`<br>`POST /api/learning-plan`<br>`POST /api/learning-plan/from-quiz` | `learning_plans`(11)<br>`learning_plan_nodes`(26)<br>`learning_path_node_status`(4) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.7 | 5E 教学智能体 | 提供 5E 阶段化学习引导和 EES 有效度，作为过程性辅助证据。 | 6 | `POST /api/5e/chat/history`<br>`GET /api/5e/chat/history/{user_id}/{lesson_id}`<br>`POST /api/5e/chat/message`<br>`POST /api/5e/course/id-by-name`<br>`GET /api/5e/effectiveness/summary`<br>`GET /api/5e/ping` | `events`(0)<br>`user_interaction`(0)<br>`fivee_effectiveness_records`(0) | 接口存在，核心事件表为空，属于结构已建未产品化 |
| 3.8 | 作业与实践评测 | 支持四类作业、提交、批改、教师终审和证据回流；覆盖知识点必须教师确认。 | 19 | `POST /api/homework/ai/generate-draft`<br>`POST /api/homework/ai/generate-questions`<br>`GET /api/homework/assignments`<br>`POST /api/homework/assignments`<br>`POST /api/homework/assignments/seed-oj-smoke`<br>`GET /api/homework/assignments/{assignment_id}`<br>`PUT /api/homework/assignments/{assignment_id}`<br>`POST /api/homework/assignments/{assignment_id}/close`<br>`GET /api/homework/assignments/{assignment_id}/coverage`<br>`PUT /api/homework/assignments/{assignment_id}/coverage`<br>`POST /api/homework/assignments/{assignment_id}/publish`<br>`POST /api/homework/assignments/{assignment_id}/reopen`<br>`GET /api/homework/assignments/{assignment_id}/submissions`<br>`POST /api/homework/assignments/{assignment_id}/submissions`<br>`GET /api/homework/course-nodes`<br>`GET /api/homework/my-submissions`<br>`GET /api/homework/submissions/{submission_id}`<br>`POST /api/homework/submissions/{submission_id}/ai-grade`<br>`POST /api/homework/submissions/{submission_id}/final-grade` | `homework_assignments`(10)<br>`homework_submissions`(16)<br>`homework_assignment_knowledge_points`(4)<br>`homework_grading_events`(3) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.9 | 教师智能干预任务包 | 读取诊断结果生成线上任务包草稿，教师审核后下发，学生完成后回流。 | 16 | `GET /api/intervention/student/packages`<br>`GET /api/intervention/student/packages/{package_id}`<br>`POST /api/intervention/student/packages/{package_id}/answers`<br>`POST /api/intervention/student/packages/{package_id}/decision`<br>`POST /api/intervention/student/packages/{package_id}/progress`<br>`POST /api/intervention/student/packages/{package_id}/tasks`<br>`POST /api/intervention/teacher/diagnose`<br>`POST /api/intervention/teacher/generate-draft`<br>`GET /api/intervention/teacher/packages`<br>`GET /api/intervention/teacher/packages/{package_id}`<br>`PUT /api/intervention/teacher/packages/{package_id}`<br>`POST /api/intervention/teacher/packages/{package_id}/grade`<br>`POST /api/intervention/teacher/packages/{package_id}/push`<br>`GET /api/intervention/teacher/progress`<br>`GET /api/intervention/teacher/students-overview`<br>`GET /api/intervention/teacher/task-reference-options` | `intervention_packages`(6)<br>`intervention_package_items`(32)<br>`intervention_package_student_records`(6)<br>`teacher_intervention_events`(14) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.10 | 教师看板与教师数字孪生 | 展示班级学情、风险和教师六维画像；AI 建议必须教师手动触发。 | 13 | `GET /api/dashboard/class-overview`<br>`GET /api/dashboard/node/{node_id}/ranking`<br>`GET /api/dashboard/student/{username}`<br>`GET /api/dashboard/student/{username}/trend`<br>`GET /api/dashboard/teacher-twin`<br>`POST /api/dashboard/teacher-twin/ai-suggestions`<br>`GET /api/dashboard/teacher-twin/drilldown`<br>`POST /api/digital-twin/teacher-events/grading`<br>`POST /api/digital-twin/teacher-events/interaction`<br>`POST /api/digital-twin/teacher-events/research`<br>`GET /api/digital-twin/teacher-profile/{teacher_username}`<br>`POST /api/digital-twin/teacher-profile/{teacher_username}/external-sync`<br>`GET /api/heatmap` | `teaching_interaction_events`(11)<br>`teaching_research_events`(3)<br>`homework_grading_events`(3)<br>`teacher_intervention_events`(14)<br>`user_activity_log`(4)<br>`llm_logs`(28) | 已有接口和本地数据，仍需按页面与业务流验收 |
| 3.11 | 教学互动 | 人工教学沟通和教研记录层；教师行为稳定回流教师数字孪生。 | 23 | `GET /api/teaching-interaction/analytics`<br>`GET /api/teaching-interaction/announcements`<br>`POST /api/teaching-interaction/announcements`<br>`GET /api/teaching-interaction/announcements/public`<br>`DELETE /api/teaching-interaction/announcements/{announcement_id}`<br>`PUT /api/teaching-interaction/announcements/{announcement_id}`<br>`GET /api/teaching-interaction/context-options`<br>`POST /api/teaching-interaction/posts`<br>`DELETE /api/teaching-interaction/posts/{post_id}`<br>`PUT /api/teaching-interaction/posts/{post_id}`<br>`DELETE /api/teaching-interaction/posts/{post_id}/student`<br>`PUT /api/teaching-interaction/posts/{post_id}/student`<br>`GET /api/teaching-interaction/topics`<br>`POST /api/teaching-interaction/topics`<br>`GET /api/teaching-interaction/topics/public`<br>`DELETE /api/teaching-interaction/topics/{topic_id}`<br>`PUT /api/teaching-interaction/topics/{topic_id}`<br>`POST /api/teaching-interaction/topics/{topic_id}/student-question`<br>`GET /api/teaching-research/context-options`<br>`GET /api/teaching-research/records`<br>`POST /api/teaching-research/records`<br>`DELETE /api/teaching-research/records/{record_id}`<br>`PUT /api/teaching-research/records/{record_id}` | `teaching_announcements`(0)<br>`teaching_discussion_topics`(0)<br>`teaching_discussion_posts`(0)<br>`teaching_research_records`(0)<br>`teaching_interaction_events`(11)<br>`teaching_research_events`(3) | 基础实现，部分数据表为空：teaching_announcements、teaching_discussion_topics、teaching_discussion_posts、teaching_research_records |
| 3.12 | 行业情报与能力对接 | 检索岗位、提取能力候选，教师确认后交课程数字孪生发布。 | 14 | `POST /api/course-digital-twin/abilities/import`<br>`POST /api/course-digital-twin/ability-mappings`<br>`POST /api/course-digital-twin/ability-mappings/candidates/generate`<br>`POST /api/course-digital-twin/ability-mappings/review`<br>`POST /api/course-digital-twin/positions`<br>`GET /api/course-digital-twin/{course_id}/abilities`<br>`GET /api/course-digital-twin/{course_id}/ability-mappings`<br>`GET /api/course-digital-twin/{course_id}/positions`<br>`POST /api/industry-intelligence/analyze`<br>`GET /api/industry-intelligence/current`<br>`POST /api/industry-intelligence/reanalyze`<br>`GET /api/industry-intelligence/status`<br>`GET /api/industry-intelligence/tasks/{task_id}`<br>`POST /api/industry-intelligence/tasks/{task_id}/cancel` | `career_positions`(1)<br>`career_abilities`(1)<br>`course_ability_mappings`(1) | 已有接口和本地数据，仍需按页面与业务流验收 |

## 5. 数据库设计基线

当前库名：`ai_education_design`。当前表数量：`42`。

| 表名 | 当前行数 | 字段数 | 主责/主用途 | 关联或消费模块 | 用途说明 | 数据状态 |
| --- | --- | --- | --- | --- | --- | --- |
| career_abilities | 1 | 9 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源 | 职业能力候选。 | 已有本地数据 |
| career_positions | 1 | 10 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源 | 课程目标岗位配置。 | 已有本地数据 |
| course_ability_mappings | 1 | 13 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源、学生数字孪生 | 职业能力与叶子知识点支撑关系。 | 已有本地数据 |
| course_metadata | 8 | 5 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程扩展结构数据。 | 已有本地数据 |
| course_node_relations | 0 | 6 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程节点关系扩展表。 | 结构已建未产品化 |
| course_nodes | 282 | 10 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程章节、小节、叶子知识点节点。 | 已有本地数据 |
| courses | 8 | 12 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程数字孪生课程主表。 | 已有本地数据 |
| diagnosis_corrections | 0 | 14 | 诊断智能体 | 诊断智能体 | 诊断人工修正记录。 | 结构已建未产品化 |
| diagnosis_reports | 6 | 11 | 诊断智能体 | 诊断智能体 | 诊断报告。 | 已有本地数据 |
| events | 0 | 7 | 5E 教学智能体底层事件 | 5E 教学智能体 | 5E 底层事件记录。 | 结构已建未产品化 |
| fivee_effectiveness_records | 0 | 18 | 5E 教学智能体有效性记录 | 5E 教学智能体 | 5E 引导有效性记录。 | 结构已建未产品化 |
| homework_assignment_knowledge_points | 4 | 14 | 作业与实践评测 | 学生数字孪生、作业与实践评测、诊断智能体 | 作业覆盖知识点确认表。 | 已有本地数据 |
| homework_assignments | 10 | 20 | 作业与实践评测 | 作业与实践评测 | 作业主表。 | 已有本地数据 |
| homework_grading_events | 3 | 12 | 教师看板与教师数字孪生证据事件 | 作业与实践评测、教师看板与教师数字孪生 | 作业批改行为事件。 | 已有本地数据 |
| homework_submissions | 16 | 14 | 作业与实践评测 | 诊断智能体、作业与实践评测、学生数字孪生 | 作业提交与评分结果。 | 已有本地数据 |
| intervention_package_items | 32 | 14 | 教师智能干预任务包 | 教师智能干预任务包 | 干预任务包任务项。 | 已有本地数据 |
| intervention_package_student_records | 6 | 13 | 教师智能干预任务包 | 教师智能干预任务包 | 学生干预任务包执行记录。 | 已有本地数据 |
| intervention_packages | 6 | 16 | 教师智能干预任务包 | 教师智能干预任务包 | 教师干预任务包主表。 | 已有本地数据 |
| learning_path_node_status | 4 | 17 | 个性化学习路径 | 个性化学习路径 | 路径节点执行状态。 | 已有本地数据 |
| learning_plan_nodes | 26 | 11 | 个性化学习路径 | 个性化学习路径 | 学习计划/路径节点与载荷。 | 已有本地数据 |
| learning_plans | 11 | 11 | 学生学习空间、个性化学习路径 | 学生学习空间、个性化学习路径 | 学习计划和个性化路径版本主表。 | 已有本地数据 |
| llm_logs | 28 | 8 | LLM、OCR 与日志支撑接口 | 教师看板与教师数字孪生、LLM、OCR 与日志支撑接口 | 大模型调用日志。 | 已有本地数据 |
| quiz_attempts | 26 | 10 | 在线测验、诊断智能体 | 在线测验、诊断智能体、学生数字孪生、教师看板与教师数字孪生 | 在线测验作答记录。 | 已有本地数据 |
| resource_learning_events | 22 | 14 | 课程数字孪生与课程资源、学生学习空间、学生数字孪生 | 课程数字孪生与课程资源、学生学习空间、学生数字孪生、学习行为证据支撑接口 | 资源学习事件表。 | 已有本地数据 |
| resources | 290 | 17 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程资源和外部资源绑定表。 | 已有本地数据 |
| sessions | 64 | 10 | 学生学习空间 | 学生学习空间 | 登录会话与学习上下文。 | 已有本地数据 |
| teacher_intervention_events | 14 | 10 | 教师看板与教师数字孪生证据事件 | 教师智能干预任务包、教师看板与教师数字孪生 | 教师干预事件。 | 已有本地数据 |
| teacher_student_links | 6 | 5 | 通用/支撑表 | 通用/支撑表 | 教师与学生关系。 | 已有本地数据 |
| teaching_announcements | 0 | 10 | 教学互动 | 教学互动 | 教学公告。 | 结构已建未产品化 |
| teaching_discussion_posts | 0 | 9 | 教学互动 | 教学互动 | 教学讨论回复。 | 结构已建未产品化 |
| teaching_discussion_topics | 0 | 11 | 教学互动 | 教学互动 | 教学讨论主题。 | 结构已建未产品化 |
| teaching_interaction_events | 11 | 11 | 教师看板与教师数字孪生证据事件 | 教师看板与教师数字孪生、教学互动 | 教学互动事件。 | 已有本地数据 |
| teaching_research_events | 3 | 7 | 教师看板与教师数字孪生证据事件 | 教师看板与教师数字孪生、教学互动 | 教研行为事件。 | 已有本地数据 |
| teaching_research_records | 0 | 11 | 教学互动 | 教学互动 | 教研记录。 | 结构已建未产品化 |
| twin_history | 71 | 8 | 学生数字孪生 | 学生数字孪生 | 学生画像历史快照。 | 已有本地数据 |
| twin_profile_nodes | 41 | 12 | 学生数字孪生、诊断智能体 | 学生数字孪生、诊断智能体 | 学生知识点画像节点。 | 已有本地数据 |
| twin_profiles | 6 | 7 | 学生数字孪生 | 学生数字孪生 | 学生数字孪生总画像。 | 已有本地数据 |
| user_activity_log | 4 | 7 | 通用活动支撑 | 学生学习空间、教师看板与教师数字孪生、用户、权限与会话 | 用户活动日志。 | 已有本地数据 |
| user_interaction | 0 | 12 | 5E 教学智能体交互统计 | 5E 教学智能体 | 5E 或学习交互统计记录。 | 结构已建未产品化 |
| user_profiles | 0 | 9 | 通用/支撑表 | 通用/支撑表 | 用户扩展资料。 | 结构已建未产品化 |
| user_states | 2 | 4 | 学生学习空间 | 学生学习空间 | 运行态键值状态。 | 已有本地数据 |
| users | 8 | 10 | 通用/支撑表 | 通用/支撑表 | 用户主表，保存学生、教师、管理员账号及登录标识。 | 已有本地数据 |

### 5.1 外键与一致性说明

本候选稿的表结构来自 `SHOW FULL COLUMNS` 与 `SHOW INDEX`，只能稳定反映字段、索引和当前行数。正式数据库设计还应继续补充 `SHOW CREATE TABLE` 或 `information_schema.KEY_COLUMN_USAGE`，区分普通索引、唯一约束和真实外键。

当前若干表采用弱引用或依赖迁移脚本补强约束，例如资源与课程节点、测验/诊断证据与课程节点、教学互动事件与教师/学生账号、5E 过程证据与课程上下文。详细设计中应明确哪些关系由数据库外键保证，哪些由服务层校验保证。


## 6. 接口设计基线

接口清单来自 OpenAPI 自动生成结果。正式接口说明应继续补充请求字段、响应字段、权限角色和错误码；本候选稿先解决接口覆盖和模块归属问题。

### 6.1 课程数字孪生与课程资源

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

### 6.2 学生学习空间

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

### 6.3 在线测验

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/quiz/answer | Answer Quiz | application/json | 200,422 |
| POST | /api/quiz/complete | Complete Quiz | application/json | 200,422 |
| GET | /api/quiz/definitions | List Quiz Definitions |  | 200,422 |
| POST | /api/quiz/definitions | Save Quiz Definition | application/json | 200,422 |
| POST | /api/quiz/definitions/{definition_id}/publish | Publish Quiz Definition | application/json | 200,422 |
| POST | /api/quiz/start | Start Quiz | application/json | 200,422 |
| POST | /api/quiz/summary | Generate Quiz Summary | application/json | 200,422 |

### 6.4 学生数字孪生

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/digital-twin/collect/{username} | Collect Data |  | 200,422 |
| GET | /api/digital-twin/profile/{username} | Get Profile |  | 200,422 |
| POST | /api/digital-twin/quiz-score | Update Quiz Score | application/json | 200,422 |
| POST | /api/digital-twin/student-course-profile | Get Student Course Profile | application/json | 200,422 |
| GET | /api/digital-twin/student-profile/{username} | Get Student Profile Summary |  | 200,422 |
| GET | /api/homework/twin/my-results | Get My Results For Twin |  | 200,422 |
| GET | /api/homework/twin/student-results | Get Student Results For Twin |  | 200,422 |

### 6.5 诊断智能体

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | /api/digital-twin/diagnosis-corrections | List Diagnosis Corrections |  | 200,422 |
| POST | /api/digital-twin/diagnosis-corrections | Record Diagnosis Correction | application/json | 200,422 |
| POST | /api/digital-twin/diagnosis/{username} | Generate Student Diagnosis | application/json | 200,422 |

### 6.6 个性化学习路径

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/digital-twin/path/generate/{username} | Generate Path | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/current | Get Current Path |  | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node-status/{node_id} | Update Path Node Status | application/json | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node/{node_id} | Update Node Mastery | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/versions | List Path Versions |  | 200,422 |
| POST | /api/learning-plan | Create Learning Plan | application/json | 200,422 |
| POST | /api/learning-plan/from-quiz | Create Learning Plan From Quiz | application/json | 200,422 |

### 6.7 5E 教学智能体

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/5e/chat/history | Get Conversation History | application/json | 200,422 |
| GET | /api/5e/chat/history/{user_id}/{lesson_id} | Conversation History |  | 200,422 |
| POST | /api/5e/chat/message | Receive Chat Content | application/json | 200,422 |
| POST | /api/5e/course/id-by-name | Api Get Course Id By Name | application/json | 200,422 |
| GET | /api/5e/effectiveness/summary | Effectiveness Summary |  | 200,422 |
| GET | /api/5e/ping | Ping |  | 200 |

### 6.8 作业与实践评测

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

### 6.9 教师智能干预任务包

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

### 6.10 教师看板与教师数字孪生

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

### 6.11 教学互动

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

### 6.12 行业情报与能力对接

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

### 6.13 LLM、OCR 与日志支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/chat | Chat | application/json | 200,422 |
| GET | /api/health/llm | Llm Health Check |  | 200,422 |
| GET | /api/languages | Get Languages |  | 200 |
| POST | /api/llm-log | Log Llm Call | application/json | 200,422 |
| GET | /api/llm-logs | Get Llm Logs |  | 200 |
| POST | /api/ocr/extract | Extract Text From Image | multipart/form-data | 200,422 |
| POST | /api/summary | Generate Summary | application/json | 200,422 |

### 6.14 前端页面与历史兼容接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| GET | / | Root |  | 200 |
| GET | /admin.html | Get Admin Page |  | 200 |
| GET | /teacher.html | Get Teacher Page |  | 200 |
| GET | /{full_path} | Frontend Spa |  | 200,422 |

### 6.15 学习行为证据支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/resource-learning/events | Record Resource Learning Event | application/json | 200,422 |
| GET | /api/resource-learning/summary | Get Resource Learning Summary |  | 200,422 |

### 6.16 用户、权限与会话

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

### 6.17 资源文件与课程运行支撑接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/clear-course-cache | Clear Course Cache |  | 200,422 |
| POST | /api/delete-resource | Delete Resource | application/json | 200,422 |
| GET | /api/recycle-bin | Get Recycle Bin |  | 200,422 |
| POST | /api/restore-resource | Restore Resource | application/json | 200,422 |

### 6.18 通用/历史接口

| 方法 | 路径 | 摘要 | 请求体 | 响应码 |
| --- | --- | --- | --- | --- |
| POST | /api/learning-activity | Log Learning Activity | application/json | 200,422 |

## 7. 后续落地顺序

1. 先把正式详细设计 Markdown 的接口章、数据库章替换为本候选稿对应内容。
2. 再按模块补充请求/响应字段、权限控制、状态流转和异常分支。
3. 对 5E、教学互动、教研记录、教师画像事件等空表模块补齐产品化说明或实现任务。
4. 对照需求文档逐章标注“已实现 / 基础实现 / 未实现 / 设计冲突”。
5. Markdown 稳定后，再生成 Word 版并做目录、表格、图题和格式审计。
