# MySQL 真实表结构（当前实现）

生成时间：2026-06-29 13:21:14

数据库：`ai_education_design`
表数量：42

说明：本文件由当前 MySQL `SHOW TABLES`、`SHOW FULL COLUMNS`、`SHOW INDEX` 自动生成。

## 表清单

| 表名 | 当前行数 | 字段数 | 主责/主用途 | 关联或消费模块 | 用途说明 |
| --- | --- | --- | --- | --- | --- |
| career_abilities | 1 | 9 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源 | 职业能力候选。 |
| career_positions | 1 | 10 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源 | 课程目标岗位配置。 |
| course_ability_mappings | 1 | 13 | 行业情报与能力对接 | 行业情报与能力对接、课程数字孪生与课程资源、学生数字孪生 | 职业能力与叶子知识点支撑关系。 |
| course_metadata | 8 | 5 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程扩展结构数据。 |
| course_node_relations | 0 | 6 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程节点关系扩展表。 |
| course_nodes | 282 | 10 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程章节、小节、叶子知识点节点。 |
| courses | 8 | 12 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程数字孪生课程主表。 |
| diagnosis_corrections | 0 | 14 | 诊断智能体 | 诊断智能体 | 诊断人工修正记录。 |
| diagnosis_reports | 6 | 11 | 诊断智能体 | 诊断智能体 | 诊断报告。 |
| events | 0 | 7 | 5E 教学智能体底层事件 | 5E 教学智能体 | 5E 底层事件记录。 |
| fivee_effectiveness_records | 0 | 18 | 5E 教学智能体有效性记录 | 5E 教学智能体 | 5E 引导有效性记录。 |
| homework_assignment_knowledge_points | 4 | 14 | 作业与实践评测 | 学生数字孪生、作业与实践评测、诊断智能体 | 作业覆盖知识点确认表。 |
| homework_assignments | 10 | 20 | 作业与实践评测 | 作业与实践评测 | 作业主表。 |
| homework_grading_events | 3 | 12 | 教师看板与教师数字孪生证据事件 | 作业与实践评测、教师看板与教师数字孪生 | 作业批改行为事件。 |
| homework_submissions | 16 | 14 | 作业与实践评测 | 诊断智能体、作业与实践评测、学生数字孪生 | 作业提交与评分结果。 |
| intervention_package_items | 32 | 14 | 教师智能干预任务包 | 教师智能干预任务包 | 干预任务包任务项。 |
| intervention_package_student_records | 6 | 13 | 教师智能干预任务包 | 教师智能干预任务包 | 学生干预任务包执行记录。 |
| intervention_packages | 6 | 16 | 教师智能干预任务包 | 教师智能干预任务包 | 教师干预任务包主表。 |
| learning_path_node_status | 4 | 17 | 个性化学习路径 | 个性化学习路径 | 路径节点执行状态。 |
| learning_plan_nodes | 26 | 11 | 个性化学习路径 | 个性化学习路径 | 学习计划/路径节点与载荷。 |
| learning_plans | 11 | 11 | 学生学习空间、个性化学习路径 | 学生学习空间、个性化学习路径 | 学习计划和个性化路径版本主表。 |
| llm_logs | 28 | 8 | LLM、OCR 与日志支撑接口 | 教师看板与教师数字孪生、LLM、OCR 与日志支撑接口 | 大模型调用日志。 |
| quiz_attempts | 26 | 10 | 在线测验、诊断智能体 | 在线测验、诊断智能体、学生数字孪生、教师看板与教师数字孪生 | 在线测验作答记录。 |
| resource_learning_events | 22 | 14 | 课程数字孪生与课程资源、学生学习空间、学生数字孪生 | 课程数字孪生与课程资源、学生学习空间、学生数字孪生、学习行为证据支撑接口 | 资源学习事件表。 |
| resources | 290 | 17 | 课程数字孪生与课程资源 | 课程数字孪生与课程资源 | 课程资源和外部资源绑定表。 |
| sessions | 64 | 10 | 学生学习空间 | 学生学习空间 | 登录会话与学习上下文。 |
| teacher_intervention_events | 14 | 10 | 教师看板与教师数字孪生证据事件 | 教师智能干预任务包、教师看板与教师数字孪生 | 教师干预事件。 |
| teacher_student_links | 6 | 5 | 通用/支撑表 | 通用/支撑表 | 教师与学生关系。 |
| teaching_announcements | 0 | 10 | 教学互动 | 教学互动 | 教学公告。 |
| teaching_discussion_posts | 0 | 9 | 教学互动 | 教学互动 | 教学讨论回复。 |
| teaching_discussion_topics | 0 | 11 | 教学互动 | 教学互动 | 教学讨论主题。 |
| teaching_interaction_events | 11 | 11 | 教师看板与教师数字孪生证据事件 | 教师看板与教师数字孪生、教学互动 | 教学互动事件。 |
| teaching_research_events | 3 | 7 | 教师看板与教师数字孪生证据事件 | 教师看板与教师数字孪生、教学互动 | 教研行为事件。 |
| teaching_research_records | 0 | 11 | 教学互动 | 教学互动 | 教研记录。 |
| twin_history | 71 | 8 | 学生数字孪生 | 学生数字孪生 | 学生画像历史快照。 |
| twin_profile_nodes | 41 | 12 | 学生数字孪生、诊断智能体 | 学生数字孪生、诊断智能体 | 学生知识点画像节点。 |
| twin_profiles | 6 | 7 | 学生数字孪生 | 学生数字孪生 | 学生数字孪生总画像。 |
| user_activity_log | 4 | 7 | 通用活动支撑 | 学生学习空间、教师看板与教师数字孪生、用户、权限与会话 | 用户活动日志。 |
| user_interaction | 0 | 12 | 5E 教学智能体交互统计 | 5E 教学智能体 | 5E 或学习交互统计记录。 |
| user_profiles | 0 | 9 | 通用/支撑表 | 通用/支撑表 | 用户扩展资料。 |
| user_states | 2 | 4 | 学生学习空间 | 学生学习空间 | 运行态键值状态。 |
| users | 8 | 10 | 通用/支撑表 | 通用/支撑表 | 用户主表，保存学生、教师、管理员账号及登录标识。 |

## `career_abilities`

当前行数：1

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| ability_id | bigint | NO | PRI | None | auto_increment |  |
| position_id | bigint | NO | MUL | None |  |  |
| ability_name | varchar(300) | NO |  | None |  |  |
| ability_category | varchar(100) | YES |  | None |  |  |
| demand_level | decimal(5,2) | YES |  | None |  |  |
| support_level | varchar(20) | YES |  | None |  |  |
| evidence_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | ability_id | 0 | 1 | BTREE |
| uk_career_abilities_position_name | position_id | 0 | 1 | BTREE |
| uk_career_abilities_position_name | ability_name | 0 | 2 | BTREE |

## `career_positions`

当前行数：1

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| position_id | bigint | NO | PRI | None | auto_increment |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| position_name | varchar(200) | NO |  | None |  |  |
| normalized_name | varchar(200) | NO |  | None |  |  |
| source_keyword | varchar(200) | YES |  | None |  |  |
| position_type | varchar(50) | YES |  | related |  |  |
| target_rank | int | YES |  | 0 |  |  |
| created_by | int | YES | MUL | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | position_id | 0 | 1 | BTREE |
| uk_career_positions_course_name | course_id | 0 | 1 | BTREE |
| uk_career_positions_course_name | normalized_name | 0 | 2 | BTREE |
| idx_career_positions_created_by | created_by | 1 | 1 | BTREE |
| idx_career_positions_course | course_id | 1 | 1 | BTREE |

## `course_ability_mappings`

当前行数：1

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| mapping_id | bigint | NO | PRI | None | auto_increment |  |
| course_id | varchar(100) | NO | MUL | None |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| ability_id | bigint | NO | MUL | None |  |  |
| support_weight | decimal(6,4) | NO |  | 0.0000 |  |  |
| support_level | varchar(20) | YES |  | None |  |  |
| match_reason | text | YES |  | None |  |  |
| evidence_json | json | YES |  | None |  |  |
| review_status | varchar(50) | NO |  | draft |  |  |
| reviewed_by | int | YES | MUL | None |  |  |
| reviewed_at | datetime | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | mapping_id | 0 | 1 | BTREE |
| uk_course_ability_mapping | course_id | 0 | 1 | BTREE |
| uk_course_ability_mapping | node_id | 0 | 2 | BTREE |
| uk_course_ability_mapping | ability_id | 0 | 3 | BTREE |
| idx_cam_ability | ability_id | 1 | 1 | BTREE |
| fk_cam_reviewed_by | reviewed_by | 1 | 1 | BTREE |

## `course_metadata`

当前行数：8

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| metadata_id | int | NO | PRI | None | auto_increment |  |
| course_id | varchar(100) | NO | UNI | None |  |  |
| additional_data | json | NO |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | metadata_id | 0 | 1 | BTREE |
| uk_course_metadata_course | course_id | 0 | 1 | BTREE |

## `course_node_relations`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| course_id | varchar(100) | NO | PRI | None |  |  |
| node_id | varchar(200) | NO | PRI | None |  |  |
| related_node_id | varchar(200) | NO | PRI | None |  |  |
| relation_type | varchar(64) | NO | PRI | None |  |  |
| payload_json | json | YES |  | None |  |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | course_id | 0 | 1 | BTREE |
| PRIMARY | node_id | 0 | 2 | BTREE |
| PRIMARY | related_node_id | 0 | 3 | BTREE |
| PRIMARY | relation_type | 0 | 4 | BTREE |
| idx_cnr_related | course_id | 1 | 1 | BTREE |
| idx_cnr_related | related_node_id | 1 | 2 | BTREE |

## `course_nodes`

当前行数：282

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| node_detail_id | int | NO | PRI | None | auto_increment |  |
| course_id | varchar(100) | NO | MUL | None |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| node_name | varchar(500) | NO | MUL | None |  |  |
| node_path_json | json | NO |  | None |  |  |
| depth | int | NO |  | 0 |  |  |
| parent_node_id | varchar(200) | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | node_detail_id | 0 | 1 | BTREE |
| uk_course_nodes_course_node | course_id | 0 | 1 | BTREE |
| uk_course_nodes_course_node | node_id | 0 | 2 | BTREE |
| idx_course_nodes_course_depth | course_id | 1 | 1 | BTREE |
| idx_course_nodes_course_depth | depth | 1 | 2 | BTREE |
| idx_course_nodes_parent | course_id | 1 | 1 | BTREE |
| idx_course_nodes_parent | parent_node_id | 1 | 2 | BTREE |
| idx_course_nodes_name | node_name | 1 | 1 | BTREE |

## `courses`

当前行数：8

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| course_id | varchar(100) | NO | PRI | None |  |  |
| course_name | varchar(500) | NO | MUL | None |  |  |
| source_path | varchar(1000) | YES |  | None |  |  |
| description | text | YES |  | None |  |  |
| difficulty_level | enum('beginner','intermediate','advanced') | YES |  | None |  |  |
| estimated_hours | decimal(6,2) | YES |  | None |  |  |
| lifecycle_status | varchar(50) | NO |  | published |  |  |
| published_at | datetime | YES |  | None |  |  |
| published_by | varchar(100) | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | course_id | 0 | 1 | BTREE |
| idx_courses_course_name | course_name | 1 | 1 | BTREE |

## `diagnosis_corrections`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| correction_id | bigint | NO | PRI | None | auto_increment |  |
| report_id | varchar(100) | NO | MUL | None |  |  |
| username | varchar(100) | NO | MUL | None |  |  |
| course_id | varchar(100) | NO |  | None |  |  |
| node_id | varchar(200) | YES |  | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| teacher_user_id | int | YES | MUL | None |  |  |
| original_reason_type | varchar(100) | YES |  | None |  |  |
| corrected_reason_type | varchar(100) | YES |  | None |  |  |
| original_evidence_level | varchar(50) | YES |  | None |  |  |
| corrected_evidence_level | varchar(50) | YES |  | None |  |  |
| correction_note | text | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | correction_id | 0 | 1 | BTREE |
| idx_dc_report | report_id | 1 | 1 | BTREE |
| idx_dc_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_dc_teacher_time | created_at | 1 | 2 | BTREE |
| idx_dc_student_course | username | 1 | 1 | BTREE |
| idx_dc_student_course | course_id | 1 | 2 | BTREE |
| fk_dc_teacher | teacher_user_id | 1 | 1 | BTREE |

## `diagnosis_reports`

当前行数：6

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| report_id | varchar(100) | NO | PRI | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| username | varchar(100) | YES | MUL | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| report_date | date | NO | MUL | None |  |  |
| persona_summary | text | YES |  | None |  |  |
| evidence_level | varchar(50) | YES |  | None |  |  |
| confidence | decimal(5,2) | YES |  | None |  |  |
| payload_json | json | NO |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | report_id | 0 | 1 | BTREE |
| idx_diagnosis_user_course | user_id | 1 | 1 | BTREE |
| idx_diagnosis_user_course | course_id | 1 | 2 | BTREE |
| idx_diagnosis_username | username | 1 | 1 | BTREE |
| idx_diagnosis_report_date | report_date | 1 | 1 | BTREE |

## `events`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(128) | NO | PRI | None |  |  |
| app_name | varchar(128) | NO | MUL | None |  |  |
| user_id | varchar(128) | NO | MUL | None |  |  |
| session_id | varchar(128) | NO | MUL | None |  |  |
| invocation_id | varchar(256) | NO |  | None |  |  |
| timestamp | datetime | NO | MUL | None |  |  |
| event_data | text | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_events_app_name | app_name | 1 | 1 | BTREE |
| idx_events_user_id | user_id | 1 | 1 | BTREE |
| idx_events_session | session_id | 1 | 1 | BTREE |
| idx_events_timestamp | timestamp | 1 | 1 | BTREE |

## `fivee_effectiveness_records`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| record_id | bigint | NO | PRI | None | auto_increment |  |
| user_identifier | varchar(100) | NO |  | None |  |  |
| student_user_id | int | YES | MUL | None |  |  |
| student_username | varchar(100) | YES | MUL | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| node_id | varchar(200) | YES |  | None |  |  |
| session_id | varchar(255) | YES |  | None |  |  |
| stage | varchar(64) | NO | MUL | None |  |  |
| interaction_count | int | NO |  | 0 |  |  |
| valid_interaction_count | int | NO |  | 0 |  |  |
| completion_rate | decimal(6,2) | YES |  | None |  |  |
| quiz_score_before | decimal(6,2) | YES |  | None |  |  |
| quiz_score_after | decimal(6,2) | YES |  | None |  |  |
| path_continue_rate | decimal(6,2) | YES |  | None |  |  |
| effectiveness_score | decimal(6,2) | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| calculated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | record_id | 0 | 1 | BTREE |
| idx_fer_student_course | student_username | 1 | 1 | BTREE |
| idx_fer_student_course | course_id | 1 | 2 | BTREE |
| idx_fer_stage_time | stage | 1 | 1 | BTREE |
| idx_fer_stage_time | calculated_at | 1 | 2 | BTREE |
| fk_fer_student | student_user_id | 1 | 1 | BTREE |

## `homework_assignment_knowledge_points`

当前行数：4

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | bigint | NO | PRI | None | auto_increment |  |
| assignment_id | varchar(100) | NO | MUL | None |  |  |
| course_id | varchar(100) | NO | MUL | None |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| coverage_source | varchar(50) | NO |  | teacher_confirmed |  |  |
| recommended_by_system | tinyint(1) | NO |  | 0 |  |  |
| confirmed_by_teacher | tinyint(1) | NO |  | 0 |  |  |
| confidence | decimal(5,2) | YES |  | None |  |  |
| reason | text | YES |  | None |  |  |
| teacher_username | varchar(100) | YES |  | None |  |  |
| confirmed_at | datetime | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| uk_hakp_assignment_node | assignment_id | 0 | 1 | BTREE |
| uk_hakp_assignment_node | course_id | 0 | 2 | BTREE |
| uk_hakp_assignment_node | node_id | 0 | 3 | BTREE |
| idx_hakp_course_node | course_id | 1 | 1 | BTREE |
| idx_hakp_course_node | node_id | 1 | 2 | BTREE |
| idx_hakp_assignment | assignment_id | 1 | 1 | BTREE |

## `homework_assignments`

当前行数：10

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(100) | NO | PRI | None |  |  |
| title | varchar(500) | NO |  | None |  |  |
| description | text | YES |  | None |  |  |
| assignment_type | varchar(50) | NO |  | None |  |  |
| class_name | varchar(200) | YES |  | None |  |  |
| course_id | varchar(100) | NO | MUL | course_big_data |  |  |
| node_id | varchar(255) | YES |  | None |  |  |
| node_name | varchar(500) | YES |  | None |  |  |
| node_path_json | json | NO |  | None |  |  |
| chapter_context | text | YES |  | None |  |  |
| objective_result_mode | varchar(50) | NO |  | immediate |  |  |
| due_at | datetime | YES |  | None |  |  |
| allow_late | tinyint(1) | NO |  | 0 |  |  |
| total_score | decimal(8,2) | NO |  | 100.00 |  |  |
| rubric | text | YES |  | None |  |  |
| questions_json | json | NO |  | None |  |  |
| created_by | varchar(100) | NO | MUL | None |  |  |
| created_at | datetime | NO | MUL | None |  |  |
| status | varchar(50) | YES |  | None |  |  |
| updated_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_homework_assignments_created_by | created_by | 1 | 1 | BTREE |
| idx_homework_assignments_created_at | created_at | 1 | 1 | BTREE |
| idx_homework_assignments_course_node | course_id | 1 | 1 | BTREE |
| idx_homework_assignments_course_node | node_id | 1 | 2 | BTREE |

## `homework_grading_events`

当前行数：3

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | int | NO | PRI | None | auto_increment |  |
| assignment_id | varchar(255) | NO | MUL | None |  |  |
| submission_id | varchar(255) | YES |  | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| student_username | varchar(100) | YES |  | None |  |  |
| event_type | varchar(100) | NO |  | None |  |  |
| grading_minutes | double | YES |  | None |  |  |
| is_ai_recommended | tinyint | YES |  | 0 |  |  |
| is_ai_executed | tinyint | YES |  | 0 |  |  |
| payload_json | longtext | NO |  | None |  |  |
| created_at | varchar(40) | NO |  | None |  |  |
| occurred_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_hge_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_hge_teacher_time | created_at | 1 | 2 | BTREE |
| idx_hge_assignment | assignment_id | 1 | 1 | BTREE |

## `homework_submissions`

当前行数：16

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(100) | NO | PRI | None |  |  |
| assignment_id | varchar(100) | NO | MUL | None |  |  |
| student_username | varchar(100) | NO | MUL | None |  |  |
| answers_json | json | NO |  | None |  |  |
| submitted_at | datetime | NO |  | None |  |  |
| status | varchar(50) | NO |  | submitted |  |  |
| ai_score | decimal(8,2) | YES |  | None |  |  |
| ai_feedback | text | YES |  | None |  |  |
| ai_rationale | text | YES |  | None |  |  |
| teacher_score | decimal(8,2) | YES |  | None |  |  |
| teacher_comment | text | YES |  | None |  |  |
| graded_at | datetime | YES |  | None |  |  |
| grader_username | varchar(100) | YES |  | None |  |  |
| updated_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_homework_submissions_assignment | assignment_id | 1 | 1 | BTREE |
| idx_homework_submissions_student | student_username | 1 | 1 | BTREE |

## `intervention_package_items`

当前行数：32

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| item_id | bigint | NO | PRI | None | auto_increment |  |
| package_id | varchar(100) | NO | MUL | None |  |  |
| item_type | varchar(50) | NO |  | None |  |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| node_id | varchar(200) | YES |  | None |  |  |
| resource_id | int | YES | MUL | None |  |  |
| homework_assignment_id | varchar(100) | YES | MUL | None |  |  |
| quiz_payload_json | json | YES |  | None |  |  |
| reminder_text | text | YES |  | None |  |  |
| sequence_order | int | NO |  | 0 |  |  |
| required | tinyint(1) | NO |  | 1 |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | item_id | 0 | 1 | BTREE |
| idx_ipi_package_order | package_id | 1 | 1 | BTREE |
| idx_ipi_package_order | sequence_order | 1 | 2 | BTREE |
| idx_ipi_course_node | course_id | 1 | 1 | BTREE |
| idx_ipi_course_node | node_id | 1 | 2 | BTREE |
| fk_ipi_resource | resource_id | 1 | 1 | BTREE |
| fk_ipi_homework | homework_assignment_id | 1 | 1 | BTREE |

## `intervention_package_student_records`

当前行数：6

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| record_id | bigint | NO | PRI | None | auto_increment |  |
| package_id | varchar(100) | NO | MUL | None |  |  |
| item_id | bigint | YES | MUL | None |  |  |
| student_username | varchar(100) | NO | MUL | None |  |  |
| student_user_id | int | YES | MUL | None |  |  |
| status | varchar(50) | NO |  | pending |  |  |
| score | decimal(8,2) | YES |  | None |  |  |
| feedback | text | YES |  | None |  |  |
| started_at | datetime | YES |  | None |  |  |
| completed_at | datetime | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | record_id | 0 | 1 | BTREE |
| idx_ipsr_student_status | student_username | 1 | 1 | BTREE |
| idx_ipsr_student_status | status | 1 | 2 | BTREE |
| idx_ipsr_package | package_id | 1 | 1 | BTREE |
| fk_ipsr_item | item_id | 1 | 1 | BTREE |
| fk_ipsr_student | student_user_id | 1 | 1 | BTREE |

## `intervention_packages`

当前行数：6

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| package_id | varchar(100) | NO | PRI | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| teacher_user_id | int | YES | MUL | None |  |  |
| student_username | varchar(100) | NO | MUL | None |  |  |
| student_user_id | int | YES | MUL | None |  |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| diagnosis_report_id | varchar(100) | YES | MUL | None |  |  |
| package_title | varchar(500) | NO |  | None |  |  |
| status | varchar(50) | NO |  | draft |  |  |
| risk_level | varchar(50) | YES |  | None |  |  |
| review_note | text | YES |  | None |  |  |
| pushed_at | datetime | YES |  | None |  |  |
| completed_at | datetime | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | package_id | 0 | 1 | BTREE |
| idx_ip_teacher_status | teacher_username | 1 | 1 | BTREE |
| idx_ip_teacher_status | status | 1 | 2 | BTREE |
| idx_ip_student_status | student_username | 1 | 1 | BTREE |
| idx_ip_student_status | status | 1 | 2 | BTREE |
| idx_ip_course | course_id | 1 | 1 | BTREE |
| fk_ip_teacher | teacher_user_id | 1 | 1 | BTREE |
| fk_ip_student | student_user_id | 1 | 1 | BTREE |
| fk_ip_diagnosis | diagnosis_report_id | 1 | 1 | BTREE |

## `learning_path_node_status`

当前行数：4

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| status_id | bigint | NO | PRI | None | auto_increment |  |
| plan_id | int | NO | MUL | None |  |  |
| plan_node_id | int | YES | MUL | None |  |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| node_id | varchar(200) | YES |  | None |  |  |
| item_type | varchar(50) | NO |  | course_knowledge_point |  |  |
| source_type | varchar(50) | NO |  | published_course_graph |  |  |
| status | varchar(50) | NO |  | pending |  |  |
| mastery_before | decimal(6,2) | YES |  | None |  |  |
| mastery_after | decimal(6,2) | YES |  | None |  |  |
| started_at | datetime | YES |  | None |  |  |
| completed_at | datetime | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | status_id | 0 | 1 | BTREE |
| uk_lpns_plan_item | plan_id | 0 | 1 | BTREE |
| uk_lpns_plan_item | item_type | 0 | 2 | BTREE |
| uk_lpns_plan_item | source_type | 0 | 3 | BTREE |
| uk_lpns_plan_item | node_id | 0 | 4 | BTREE |
| idx_lpns_username_status | username | 1 | 1 | BTREE |
| idx_lpns_username_status | status | 1 | 2 | BTREE |
| idx_lpns_course_node | course_id | 1 | 1 | BTREE |
| idx_lpns_course_node | node_id | 1 | 2 | BTREE |
| fk_lpns_plan_node | plan_node_id | 1 | 1 | BTREE |
| fk_lpns_user | user_id | 1 | 1 | BTREE |

## `learning_plan_nodes`

当前行数：26

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| node_id | int | NO | PRI | None | auto_increment |  |
| plan_id | int | NO | MUL | None |  |  |
| node_key | varchar(100) | NO |  | None |  |  |
| node_name | varchar(500) | YES |  | None |  |  |
| node_type | varchar(50) | YES |  | None |  |  |
| sequence_order | int | YES |  | 0 |  |  |
| parent_node_id | int | YES | MUL | None |  |  |
| content | json | YES |  | None |  |  |
| metadata | json | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | node_id | 0 | 1 | BTREE |
| uk_plan_node | plan_id | 0 | 1 | BTREE |
| uk_plan_node | node_key | 0 | 2 | BTREE |
| idx_plan_id | plan_id | 1 | 1 | BTREE |
| idx_parent_node | parent_node_id | 1 | 1 | BTREE |

## `learning_plans`

当前行数：11

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| plan_id | int | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | NO | MUL | None |  |  |
| filename | varchar(255) | NO |  | None |  |  |
| plan_path | varchar(500) | YES |  | None |  |  |
| category | enum('global','user','path') | YES | MUL | user |  |  |
| title | varchar(500) | YES |  | None |  |  |
| description | text | YES |  | None |  |  |
| status | enum('draft','active','completed','archived') | YES | MUL | draft |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | plan_id | 0 | 1 | BTREE |
| uk_username_filename | username | 0 | 1 | BTREE |
| uk_username_filename | filename | 0 | 2 | BTREE |
| idx_user_id | user_id | 1 | 1 | BTREE |
| idx_category | category | 1 | 1 | BTREE |
| idx_status | status | 1 | 1 | BTREE |

## `llm_logs`

当前行数：28

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| log_id | int | NO | PRI | None | auto_increment |  |
| timestamp | datetime | YES |  | None |  |  |
| username | varchar(100) | YES | MUL | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| module | varchar(100) | YES | MUL | None |  |  |
| model | varchar(100) | YES |  | None |  |  |
| payload_json | json | NO |  | None |  |  |
| created_at | timestamp | YES | MUL | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | log_id | 0 | 1 | BTREE |
| idx_llm_logs_username | username | 1 | 1 | BTREE |
| idx_llm_logs_user_id | user_id | 1 | 1 | BTREE |
| idx_llm_logs_module | module | 1 | 1 | BTREE |
| idx_llm_logs_created_at | created_at | 1 | 1 | BTREE |

## `quiz_attempts`

当前行数：26

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| attempt_id | int | NO | PRI | None | auto_increment |  |
| user_id | int | YES | MUL | None |  |  |
| username | varchar(100) | YES | MUL | None |  |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| node_id | varchar(200) | YES |  | None |  |  |
| score | decimal(6,2) | YES |  | None |  |  |
| total | decimal(6,2) | YES |  | None |  |  |
| passed | tinyint(1) | YES |  | 0 |  |  |
| payload_json | json | NO |  | None |  |  |
| created_at | timestamp | YES | MUL | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | attempt_id | 0 | 1 | BTREE |
| idx_quiz_attempts_user_id | user_id | 1 | 1 | BTREE |
| idx_quiz_attempts_username | username | 1 | 1 | BTREE |
| idx_quiz_attempts_course_node | course_id | 1 | 1 | BTREE |
| idx_quiz_attempts_course_node | node_id | 1 | 2 | BTREE |
| idx_quiz_attempts_created_at | created_at | 1 | 1 | BTREE |

## `resource_learning_events`

当前行数：22

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| event_id | bigint | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| course_id | varchar(100) | NO | MUL | None |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| resource_id | int | YES | MUL | None |  |  |
| resource_path | varchar(1000) | YES |  | None |  |  |
| event_type | varchar(50) | NO |  | None |  |  |
| duration_seconds | int | YES |  | 0 |  |  |
| progress_percent | decimal(6,2) | YES |  | None |  |  |
| is_completed | tinyint(1) | NO |  | 0 |  |  |
| occurred_at | datetime | NO | MUL | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | event_id | 0 | 1 | BTREE |
| idx_rle_user_course_node | username | 1 | 1 | BTREE |
| idx_rle_user_course_node | course_id | 1 | 2 | BTREE |
| idx_rle_user_course_node | node_id | 1 | 3 | BTREE |
| idx_rle_resource | resource_id | 1 | 1 | BTREE |
| idx_rle_occurred_at | occurred_at | 1 | 1 | BTREE |
| fk_rle_user | user_id | 1 | 1 | BTREE |
| fk_rle_course_node | course_id | 1 | 1 | BTREE |
| fk_rle_course_node | node_id | 1 | 2 | BTREE |

## `resources`

当前行数：290

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| resource_id | int | NO | PRI | None | auto_increment |  |
| course_id | varchar(100) | NO | MUL | None |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| resource_path | varchar(1000) | NO |  | None |  |  |
| resource_path_hash | char(64) | YES |  | None | STORED GENERATED |  |
| resource_type | varchar(200) | YES |  | None |  |  |
| title | varchar(500) | YES |  | None |  |  |
| payload_json | json | NO |  | None |  |  |
| resource_source | varchar(50) | NO |  | local |  |  |
| quality_status | varchar(50) | NO |  | unchecked |  |  |
| review_status | varchar(50) | NO |  | enabled |  |  |
| is_enabled | tinyint(1) | NO |  | 1 |  |  |
| is_deleted | tinyint(1) | NO | MUL | 0 |  |  |
| deleted_at | datetime | YES |  | None |  |  |
| deleted_by | varchar(100) | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | resource_id | 0 | 1 | BTREE |
| uk_resources_course_node_path | course_id | 0 | 1 | BTREE |
| uk_resources_course_node_path | node_id | 0 | 2 | BTREE |
| uk_resources_course_node_path | resource_path_hash | 0 | 3 | BTREE |
| idx_resources_course_node | course_id | 1 | 1 | BTREE |
| idx_resources_course_node | node_id | 1 | 2 | BTREE |
| idx_resources_deleted | is_deleted | 1 | 1 | BTREE |

## `sessions`

当前行数：64

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| session_id | varchar(255) | NO | PRI | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_type | enum('student','teacher','admin') | NO |  | None |  |  |
| created_at | datetime | YES |  | None |  |  |
| last_accessed | datetime | YES |  | None |  |  |
| current_pdf_path | text | YES |  | None |  |  |
| current_node | varchar(500) | YES |  | None |  |  |
| payload_json | json | NO |  | None |  |  |
| updated_at | datetime | YES | MUL | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | session_id | 0 | 1 | BTREE |
| idx_sessions_user_id | user_id | 1 | 1 | BTREE |
| idx_sessions_username | username | 1 | 1 | BTREE |
| idx_sessions_updated_at | updated_at | 1 | 1 | BTREE |

## `teacher_intervention_events`

当前行数：14

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | int | NO | PRI | None | auto_increment |  |
| package_id | varchar(255) | YES |  | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| student_username | varchar(100) | YES |  | None |  |  |
| event_type | varchar(100) | NO |  | None |  |  |
| weak_node_count | int | YES |  | 0 |  |  |
| completion_rate | double | YES |  | 0 |  |  |
| payload_json | longtext | NO |  | None |  |  |
| created_at | varchar(40) | NO |  | None |  |  |
| occurred_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_tievt_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_tievt_teacher_time | created_at | 1 | 2 | BTREE |

## `teacher_student_links`

当前行数：6

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| teacher_username | varchar(100) | NO | PRI | None |  |  |
| student_username | varchar(100) | NO | PRI | None |  |  |
| teacher_user_id | int | YES | MUL | None |  |  |
| student_user_id | int | YES | MUL | None |  |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | teacher_username | 0 | 1 | BTREE |
| PRIMARY | student_username | 0 | 2 | BTREE |
| idx_tsl_teacher_user_id | teacher_user_id | 1 | 1 | BTREE |
| idx_tsl_student_user_id | student_user_id | 1 | 1 | BTREE |

## `teaching_announcements`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(64) | NO | PRI | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| title | varchar(500) | NO |  | None |  |  |
| content | text | NO |  | None |  |  |
| class_name | varchar(255) | YES |  | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| status | varchar(50) | NO |  | published |  |  |
| published_at | datetime | YES |  | None |  |  |
| created_at | datetime | NO |  | None |  |  |
| updated_at | datetime | NO |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_ta_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_ta_teacher_time | published_at | 1 | 2 | BTREE |

## `teaching_discussion_posts`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(64) | NO | PRI | None |  |  |
| topic_id | varchar(64) | NO | MUL | None |  |  |
| author_username | varchar(100) | NO |  | None |  |  |
| author_role | varchar(50) | NO |  | None |  |  |
| content | text | NO |  | None |  |  |
| replied_to_post_id | varchar(64) | YES |  | None |  |  |
| response_minutes | double | YES |  | None |  |  |
| created_at | datetime | NO |  | None |  |  |
| updated_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_tdp_topic_time | topic_id | 1 | 1 | BTREE |
| idx_tdp_topic_time | created_at | 1 | 2 | BTREE |

## `teaching_discussion_topics`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(64) | NO | PRI | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| title | varchar(500) | NO |  | None |  |  |
| content | text | NO |  | None |  |  |
| class_name | varchar(255) | YES |  | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| status | varchar(50) | NO |  | open |  |  |
| student_question_count | int | NO |  | 0 |  |  |
| teacher_reply_count | int | NO |  | 0 |  |  |
| created_at | datetime | NO |  | None |  |  |
| updated_at | datetime | NO |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_tdt_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_tdt_teacher_time | created_at | 1 | 2 | BTREE |

## `teaching_interaction_events`

当前行数：11

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | int | NO | PRI | None | auto_increment |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| class_name | varchar(255) | YES |  | None |  |  |
| event_type | varchar(100) | NO | MUL | None |  |  |
| target_id | varchar(255) | YES |  | None |  |  |
| student_username | varchar(100) | YES |  | None |  |  |
| response_minutes | double | YES |  | None |  |  |
| payload_json | longtext | NO |  | None |  |  |
| created_at | varchar(40) | NO |  | None |  |  |
| occurred_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_tie_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_tie_teacher_time | created_at | 1 | 2 | BTREE |
| idx_tie_type_time | event_type | 1 | 1 | BTREE |
| idx_tie_type_time | created_at | 1 | 2 | BTREE |

## `teaching_research_events`

当前行数：3

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | int | NO | PRI | None | auto_increment |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| event_type | varchar(100) | NO |  | None |  |  |
| resource_id | varchar(255) | YES |  | None |  |  |
| payload_json | longtext | NO |  | None |  |  |
| created_at | varchar(40) | NO |  | None |  |  |
| occurred_at | datetime | YES |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_tre_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_tre_teacher_time | created_at | 1 | 2 | BTREE |

## `teaching_research_records`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | varchar(64) | NO | PRI | None |  |  |
| teacher_username | varchar(100) | NO | MUL | None |  |  |
| activity_type | varchar(100) | NO |  | None |  |  |
| title | varchar(500) | NO |  | None |  |  |
| description | text | YES |  | None |  |  |
| resource_link | varchar(1000) | YES |  | None |  |  |
| class_name | varchar(255) | YES |  | None |  |  |
| course_id | varchar(100) | YES |  | None |  |  |
| happened_at | datetime | NO |  | None |  |  |
| created_at | datetime | NO |  | None |  |  |
| updated_at | datetime | NO |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| idx_trr_teacher_time | teacher_username | 1 | 1 | BTREE |
| idx_trr_teacher_time | happened_at | 1 | 2 | BTREE |

## `twin_history`

当前行数：71

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| history_id | int | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| snapshot_date | date | NO |  | None |  |  |
| overall_mastery | decimal(5,2) | YES |  | 0.00 |  |  |
| payload_json | json | NO |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | history_id | 0 | 1 | BTREE |
| uk_twin_history_user_date | username | 0 | 1 | BTREE |
| uk_twin_history_user_date | snapshot_date | 0 | 2 | BTREE |
| idx_twin_history_user_id | user_id | 1 | 1 | BTREE |

## `twin_profile_nodes`

当前行数：41

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| node_detail_id | int | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | NO | MUL | None |  |  |
| course_id | varchar(100) | NO | MUL | course_big_data |  |  |
| node_id | varchar(200) | NO |  | None |  |  |
| node_path_json | json | NO |  | None |  |  |
| quiz_score | decimal(6,2) | YES |  | None |  |  |
| progress | decimal(6,2) | YES |  | 0.00 |  |  |
| study_duration_minutes | decimal(10,2) | YES |  | 0.00 |  |  |
| llm_interaction_count | int | YES |  | 0 |  |  |
| mastery_score | decimal(6,2) | YES |  | 0.00 |  |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | node_detail_id | 0 | 1 | BTREE |
| uk_tpn_user_course_node | username | 0 | 1 | BTREE |
| uk_tpn_user_course_node | course_id | 0 | 2 | BTREE |
| uk_tpn_user_course_node | node_id | 0 | 3 | BTREE |
| idx_tpn_user_id | user_id | 1 | 1 | BTREE |
| idx_tpn_course_node | course_id | 1 | 1 | BTREE |
| idx_tpn_course_node | node_id | 1 | 2 | BTREE |

## `twin_profiles`

当前行数：6

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| profile_id | int | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | UNI | None |  |  |
| user_id | int | NO | MUL | None |  |  |
| last_updated | datetime | YES |  | None |  |  |
| overall_mastery | decimal(5,2) | YES |  | 0.00 |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | profile_id | 0 | 1 | BTREE |
| username | username | 0 | 1 | BTREE |
| idx_twin_profiles_user_id | user_id | 1 | 1 | BTREE |

## `user_activity_log`

当前行数：4

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| id | int | NO | PRI | None | auto_increment |  |
| username | varchar(100) | NO | MUL | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| activity_date | date | NO | MUL | None |  |  |
| activity_type | varchar(50) | NO |  | None |  |  |
| activity_details | text | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | id | 0 | 1 | BTREE |
| unique_user_date_type | username | 0 | 1 | BTREE |
| unique_user_date_type | activity_date | 0 | 2 | BTREE |
| unique_user_date_type | activity_type | 0 | 3 | BTREE |
| idx_username_date | username | 1 | 1 | BTREE |
| idx_username_date | activity_date | 1 | 2 | BTREE |
| idx_user_activity_user_id | user_id | 1 | 1 | BTREE |
| idx_activity_date | activity_date | 1 | 1 | BTREE |

## `user_interaction`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| interaction_id | bigint | NO | PRI | None | auto_increment |  |
| user_identifier | varchar(100) | NO | MUL | None |  |  |
| student_user_id | int | YES | MUL | None |  |  |
| student_username | varchar(100) | YES |  | None |  |  |
| course_id | varchar(100) | YES | MUL | None |  |  |
| session_id | varchar(255) | YES |  | None |  |  |
| stage | varchar(64) | NO |  | None |  |  |
| question_type | varchar(100) | YES |  | None |  |  |
| question_count | int | NO |  | 0 |  |  |
| error | text | YES |  | None |  |  |
| payload_json | json | YES |  | None |  |  |
| created_at | datetime | NO |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | interaction_id | 0 | 1 | BTREE |
| idx_ui_user_time | user_identifier | 1 | 1 | BTREE |
| idx_ui_user_time | created_at | 1 | 2 | BTREE |
| idx_ui_student_user_id | student_user_id | 1 | 1 | BTREE |
| idx_ui_course_stage | course_id | 1 | 1 | BTREE |
| idx_ui_course_stage | stage | 1 | 2 | BTREE |

## `user_profiles`

当前行数：0

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| user_id | int | NO | PRI | None |  |  |
| avatar_url | varchar(500) | YES |  | None |  |  |
| phone | varchar(20) | YES |  | None |  |  |
| address | varchar(500) | YES |  | None |  |  |
| bio | text | YES |  | None |  |  |
| preferences | json | YES |  | None |  |  |
| metadata | json | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | user_id | 0 | 1 | BTREE |

## `user_states`

当前行数：2

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| username | varchar(150) | NO | PRI | None |  |  |
| user_id | int | YES | MUL | None |  |  |
| payload_json | json | NO |  | None |  |  |
| updated_at | datetime | NO |  | None |  |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | username | 0 | 1 | BTREE |
| idx_user_states_user_id | user_id | 1 | 1 | BTREE |

## `users`

当前行数：8

| 字段 | 类型 | 可空 | 键 | 默认值 | 额外 | 注释 |
| --- | --- | --- | --- | --- | --- | --- |
| user_id | int | NO | PRI | None | auto_increment |  |
| login_id | varchar(50) | NO | UNI | None |  |  |
| user_type | enum('student','teacher','admin') | NO | MUL | None |  |  |
| username | varchar(100) | NO | MUL | None |  |  |
| password | varchar(255) | YES |  | None |  |  |
| display_name | varchar(200) | YES |  | None |  |  |
| teacher_id | int | YES | MUL | None |  |  |
| email | varchar(255) | YES |  | None |  |  |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED |  |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |  |

索引：

| 索引名 | 字段 | 非唯一 | 顺序 | 类型 |
| --- | --- | --- | --- | --- |
| PRIMARY | user_id | 0 | 1 | BTREE |
| login_id | login_id | 0 | 1 | BTREE |
| uk_type_username | user_type | 0 | 1 | BTREE |
| uk_type_username | username | 0 | 2 | BTREE |
| idx_login_id | login_id | 1 | 1 | BTREE |
| idx_teacher_id | teacher_id | 1 | 1 | BTREE |
| idx_username | username | 1 | 1 | BTREE |
