# AI-Education 核心接口说明

本文件由详细设计生成脚本同步生成，便于后续单独维护接口清单。

| 方法 | 路径 | 模块 | 用途 | 关键输入 | 关键输出 | 异常 |
|---|---|---|---|---|---|---|
| GET | /api/course-digital-twin/courses | 课程数字孪生/教师端 | 查询课程建设底座列表 | teacher/admin session | 课程状态、节点数、资源数、发布时间 | 403 |
| POST | /api/course-digital-twin/initial-graph | 课程数字孪生/教师端 | 根据教师录入课程大纲生成初始知识图谱 | course_id,course_name,outline_text,bind_resource_candidates | 图谱结构、节点校验结果、资源候选绑定结果、课程摘要 | 400/403 |
| POST | /api/course-digital-twin/structure | 课程数字孪生/教师端 | 保存课程结构草稿或发布版 | course_id,course_name,graph_data,lifecycle_status | 校验结果、同步节点数、资源数、课程摘要 | 400/403 |
| GET | /api/course-digital-twin/{course_id} | 课程数字孪生/教师端 | 查看课程结构与运行摘要 | course_id | 课程摘要、图谱结构 | 403/404 |
| GET | /api/course-digital-twin/{course_id}/resources | 课程数字孪生/教师端 | 查看课程资源审核清单 | course_id | 资源来源、质量状态、审核状态、启用状态 | 403 |
| POST | /api/course-digital-twin/resource-candidates/bind | 课程数字孪生/教师端 | 按叶子知识点生成并绑定资源候选 | course_id,max_resources_per_leaf,overwrite,review_status | 绑定统计、审核清单、课程摘要 | 400/403/404 |
| POST | /api/course-digital-twin/resource-review | 课程数字孪生/教师端 | 审核启用或禁用课程资源 | course_id,node_id,resource_path,is_enabled | 更新后的课程摘要 | 403/404 |
| POST | /api/course-digital-twin/publish | 课程数字孪生/教师端 | 发布课程底座 | course_id | 发布后的课程摘要 | 400/403/404 |
| GET | /api/course-digital-twin/{course_id}/runtime-evaluation | 课程数字孪生/教师端 | 按需求文档五个角度评估课程发布后的运行状态 | course_id,window_days,min_quiz_attempts | 课程结构质量、资源覆盖与有效性、测评证据、运行薄弱点、职业能力支撑、课程健康分、动作清单、公式说明、不可计算指标说明 | 403/404 |
| GET | /api/course-digital-twin/{course_id}/positions | 课程数字孪生/行业能力 | 查询课程目标岗位 | course_id | 主要岗位、关联岗位、排序 | 403 |
| POST | /api/course-digital-twin/positions | 课程数字孪生/行业能力 | 配置主要岗位或关联岗位 | course_id,position_name,position_type | 岗位配置结果 | 400/403 |
| GET | /api/course-digital-twin/{course_id}/abilities | 课程数字孪生/行业能力 | 查询职业能力候选 | course_id | 岗位、能力、需求强度、证据摘要 | 403 |
| POST | /api/course-digital-twin/abilities/import | 课程数字孪生/行业能力 | 将行业情报技能导入为能力候选 | course_id,position_id,abilities/industry_payload | 导入数量、能力候选列表 | 400/403 |
| GET | /api/course-digital-twin/{course_id}/ability-mappings | 课程数字孪生/行业能力 | 查看职业能力-叶子知识点映射 | course_id | 能力、支撑知识点、支撑强度、审核状态 | 403 |
| POST | /api/course-digital-twin/ability-mappings | 课程数字孪生/行业能力 | 保存能力与叶子知识点支撑关系 | course_id,mappings | 保存数量、拒绝原因、映射列表 | 400/403 |
| POST | /api/course-digital-twin/ability-mappings/review | 课程数字孪生/行业能力 | 教师确认或驳回能力映射 | course_id,mapping_id,review_status,support_level | 更新数量、映射列表 | 400/403 |
| GET | /api/knowledge-graph | 课程数字孪生/学习空间 | 读取课程知识图谱 | session_id | 课程树、节点、资源关系 | 401/404/500 |
| POST | /api/upload | 课程数字孪生/教师端 | 上传本地课程资料并绑定节点 | files,node_name | 上传路径、RAG 入库状态 | 400/404/500 |
| POST | /api/node/resources | 学习空间/课程孪生 | 读取知识点资源 | node_name | 资源路径列表 | 404/500 |
| POST | /api/quiz/start | 在线测验/学生端 | 按知识点生成测验 | subject,lang_choice | 首题、测验状态、是否使用检索 | 400/500 |
| POST | /api/quiz/answer | 在线测验/学生端 | 提交单题答案 | state,choice | 是否正确、下一题或结果 | 400 |
| POST | /api/quiz/complete | 在线测验/学生画像 | 测验完成回流 | node_name,score,total | 通过状态、画像更新结果 | 401/404 |
| GET | /api/digital-twin/student-profile/{username} | 学生数字孪生 | 获取学生画像摘要 | username | 掌握度、雷达、薄弱点、风险、趋势 | 404/500 |
| POST | /api/digital-twin/quiz-score | 学生数字孪生 | 写入知识点测验分数 | username,node_id,score | 更新后的画像 | 500 |
| POST | /api/digital-twin/diagnosis/{username} | 诊断智能体/学生数字孪生 | 生成学生学习诊断报告并可落库 | course_id,persist | 薄弱知识点、原因类型、证据等级、证据不足原因、置信度、学生端说明、教师端证据时间线 | 404/500 |
| POST | /api/digital-twin/diagnosis-corrections | 诊断智能体/教师端 | 教师修正诊断结论并沉淀修正记录 | report_id,username,course_id,teacher_username,node_id,correction_note | correction_id | 400/500 |
| GET | /api/digital-twin/diagnosis-corrections | 诊断智能体/教师端 | 查询诊断人工修正历史 | report_id,username,course_id,teacher_username,limit | 修正记录列表 | 500 |
| GET | /api/digital-twin/path/{username}/current | 个性化路径 | 读取当前路径版本 | username | 诊断摘要、正式路径节点、资源、建议、补充学习项 | 404/500 |
| POST | /api/digital-twin/path/generate/{username} | 个性化路径 | 根据诊断结果生成路径版本 | username | 诊断摘要、正式路径节点、资源、建议、补充学习项 | 404/500 |
| PATCH | /api/digital-twin/path/{username}/node/{node_id} | 个性化路径 | 根据掌握度变化更新路径 | new_score | 更新后的路径 | 404 |
| GET | /api/dashboard/class-overview | 教师看板 | 读取班级概览 | teacher session | 班级平均掌握度、分布、节点平均 | 403 |
| GET | /api/dashboard/student/{username} | 教师看板/诊断 | 查看学生详情和薄弱点 | username | 画像详情、弱点列表 | 403/404 |
| GET | /api/dashboard/teacher-twin | 教师数字孪生 | 获取教师六维画像 | teacher session | 雷达、维度、数据来源 | 403/404/500 |
| GET | /api/dashboard/teacher-twin/drilldown | 教师数字孪生 | 查看某维度证据下钻 | dimension,window_days | 证据时间线、建议 | 403/404/500 |
| POST | /api/dashboard/teacher-twin/ai-suggestions | 教师数字孪生 | 按需生成 AI 教学建议 | teacher session | 教学策略建议、干预建议 | 403/500 |
| POST | /api/homework/assignments | 作业与实践评测 | 教师创建作业 | title,type,course,node,questions | 作业记录 | 401/403 |
| GET | /api/homework/assignments | 作业与实践评测 | 查询作业列表 | course_id,node_id,node_name | 作业列表 | 401 |
| GET | /api/homework/assignments/{id}/coverage | 作业与实践评测 | 查询作业可选覆盖知识点 | assignment_id | 覆盖知识点列表 | 401/403/404 |
| PUT | /api/homework/assignments/{id}/coverage | 作业与实践评测 | 教师确认或调整作业覆盖知识点 | assignment_id,covered_knowledge_points | 更新后的覆盖知识点列表 | 401/403/404 |
| POST | /api/homework/assignments/{id}/submissions | 作业与实践评测 | 学生提交作业 | answers | 提交记录 | 401/403/404 |
| POST | /api/homework/submissions/{id}/final-grade | 作业与实践评测/教师孪生 | 教师终评 | teacher_score,comment | 评分结果 | 403/404 |
| POST | /api/intervention/teacher/diagnose | 诊断/干预 | 教师批量诊断学生 | student_usernames | 诊断结果 | 401/403 |
| POST | /api/intervention/teacher/generate-draft | 教师智能干预 | 生成任务包草稿 | student_username,question_count,difficulty | 任务包草稿 | 403/500 |
| GET | /api/intervention/teacher/packages | 教师智能干预 | 查看教师任务包列表，包含数据库已落库记录 | teacher session | 任务包列表 | 401/403 |
| PUT | /api/intervention/teacher/packages/{id} | 教师智能干预 | 教师修改任务包草稿 | strategy_summary,recommended_concepts,recommended_videos,questions | 更新后的任务包 | 400/403 |
| POST | /api/intervention/teacher/packages/{id}/push | 教师智能干预 | 审核后下发任务包 | package_id | 下发后的任务包 | 400/403 |
| POST | /api/intervention/teacher/packages/{id}/grade | 教师智能干预 | 教师对任务包题目进行终评 | question_id,teacher_score,teacher_comment | 更新后的任务包 | 400/403 |
| GET | /api/intervention/student/packages | 学生端干预 | 学生查看任务包 | student session | 任务包列表 | 401/403 |
| POST | /api/intervention/student/packages/{id}/decision | 学生端干预 | 学生接受或暂不执行任务包 | decision,note | 任务包状态 | 404 |
| POST | /api/intervention/student/packages/{id}/answers | 学生端干预 | 学生提交任务答案 | question_id,answer,note | 任务包状态 | 400/404 |
| POST | /api/intervention/student/packages/{id}/progress | 学生端干预 | 学生更新任务包进度或完成状态 | status,completion_rate,note | 任务包状态 | 404 |
| POST | /api/5e/chat/message | 5E 教学智能体 | 流式对话 | user_id,course_id,content | 文本流/结构化响应 | 运行时不可用时返回降级消息 |
| GET | /api/5e/chat/history/{user_id}/{lesson_id} | 5E 教学智能体 | 读取对话历史 | user_id,lesson_id | 历史消息 | 空列表 |
| POST | /api/industry-intelligence/analyze | 课程孪生/行业能力 | 岗位情报分析任务 | keyword,country,city,sources | task_id | 400/401 |
| GET | /api/industry-intelligence/tasks/{task_id} | 课程孪生/行业能力 | 查询情报任务状态 | task_id | 任务状态和结果 | 403/404 |
