# AI-Education 接口与数据库表分模块核对（2026-07-01）

说明：本文件按需求模块核对当前后端接口与本地业务数据库表。备份/修复表不进入正式设计正文。

- 后端接口数：165
- 发布 schema 正式业务表数：46 张。历史本地库可能仍包含修复/备份表，备份/修复表不进入正式设计正文。

## 模块总览

| 章节 | 模块 | 接口数 | 主表 | 支撑/读取表 |
|---|---|---:|---|---|
| 3.1 | 课程数字孪生与课程资源 | 15 | courses, course_metadata, course_nodes, course_node_relations, resources | resource_learning_events, career_positions, career_abilities, course_ability_mappings, teacher_course_assignments |
| 3.2 | 学生学习空间 | 13 | sessions, user_activity_log, resource_learning_events, course_enrollments | courses, course_nodes, resources, learning_path_versions, learning_path_items, learning_plans |
| 3.3 | 在线测验 | 7 | quiz_attempts | course_nodes, twin_profile_nodes, diagnosis_reports |
| 3.4 | 学生数字孪生 | 7 | twin_profiles, twin_profile_nodes, twin_history | quiz_attempts, homework_submissions, homework_assignment_knowledge_points, resource_learning_events, users |
| 3.5 | 诊断智能体 | 3 | diagnosis_reports, diagnosis_corrections | twin_profile_nodes, quiz_attempts, homework_submissions, users |
| 3.6 | 个性化学习路径 | 7 | learning_path_versions, learning_path_items, learning_path_node_status | twin_profiles, diagnosis_reports, course_nodes, resources, resource_learning_events |
| 3.7 | 5E 教学智能体 | 6 | events, user_interaction, fivee_effectiveness_records | courses, course_nodes, users |
| 3.8 | 作业与实践评测 | 19 | homework_assignments, homework_submissions, homework_assignment_knowledge_points, homework_grading_events | course_nodes, users, twin_profile_nodes |
| 3.9 | 教师智能干预任务包 | 16 | intervention_packages, intervention_package_items, intervention_package_student_records, teacher_intervention_events | diagnosis_reports, resources, homework_assignments, users |
| 3.10 | 教师看板与教师数字孪生 | 13 | teaching_interaction_events, teaching_research_events, homework_grading_events, teacher_intervention_events, user_activity_log, llm_logs | teacher_student_links, twin_profiles, twin_profile_nodes, diagnosis_reports, intervention_packages |
| 3.11 | 教学互动 | 23 | teaching_announcements, teaching_discussion_topics, teaching_discussion_posts, teaching_research_records, teaching_interaction_events, teaching_research_events | users, teacher_student_links |
| 3.12 | 行业情报与能力对接 | 14 | career_positions, career_abilities, course_ability_mappings | courses, course_nodes, users |
| 支撑 | 用户、权限、文件与智能服务 | 22 | users, user_profiles, teacher_student_links, course_enrollments, teacher_course_assignments, sessions, user_states, llm_logs, user_activity_log | - |

## 3.1 课程数字孪生与课程资源

模块职责：课程结构、课程节点、资源绑定、课程发布与运行评估。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/clear-course-cache` | `clear_course_cache` | `backend\app.py` |
| GET | `/api/course-digital-twin/courses` | `list_course_digital_twin_courses` | `backend\app.py` |
| POST | `/api/course-digital-twin/initial-graph` | `generate_course_digital_twin_initial_graph` | `backend\app.py` |
| POST | `/api/course-digital-twin/publish` | `publish_course_digital_twin` | `backend\app.py` |
| POST | `/api/course-digital-twin/resource-candidates/bind` | `bind_course_digital_twin_resource_candidates` | `backend\app.py` |
| POST | `/api/course-digital-twin/resource-review` | `review_course_digital_twin_resource` | `backend\app.py` |
| POST | `/api/course-digital-twin/structure` | `upsert_course_digital_twin_structure` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}` | `get_course_digital_twin_summary` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}/resources` | `list_course_digital_twin_resources` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}/runtime-evaluation` | `evaluate_course_digital_twin_runtime` | `backend\app.py` |
| POST | `/api/delete-resource` | `delete_resource` | `backend\app.py` |
| GET | `/api/knowledge-graph` | `get_knowledge_graph` | `backend\app.py` |
| GET | `/api/recycle-bin` | `get_recycle_bin` | `backend\app.py` |
| POST | `/api/restore-resource` | `restore_resource` | `backend\app.py` |
| POST | `/api/upload` | `upload_files` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `courses` | 1 | course_id | 模块直接写入或维护的核心业务表 |
| 主表 | `course_metadata` | 0 | metadata_id | 模块直接写入或维护的核心业务表 |
| 主表 | `course_nodes` | 8 | node_detail_id | 模块直接写入或维护的核心业务表 |
| 主表 | `course_node_relations` | 0 | course_id, node_id, related_node_id | 模块直接写入或维护的核心业务表 |
| 主表 | `resources` | 16 | resource_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `resource_learning_events` | 20 | event_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `career_positions` | 0 | position_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `career_abilities` | 4 | ability_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `course_ability_mappings` | 7 | mapping_id | 模块读取、引用或作为证据来源 |

## 3.2 学生学习空间

模块职责：学生学习入口、课程资源学习、学习进度和通知。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/api/graph-visualization` | `get_graph_visualization` | `backend\app.py` |
| POST | `/api/learning-activity` | `log_learning_activity` | `backend\app.py` |
| GET | `/api/learning-nodes` | `get_learning_nodes` | `backend\app.py` |
| GET | `/api/student/courses` | `list_student_visible_courses` | `backend\app.py` |
| GET | `/api/learning-plans` | `get_learning_plans` | `backend\app.py` |
| GET | `/api/learning-progress` | `get_learning_progress` | `backend\app.py` |
| GET | `/api/learning-streak` | `get_learning_streak` | `backend\app.py` |
| POST | `/api/node/resources` | `get_node_resources` | `backend\app.py` |
| GET | `/api/notifications/recent` | `get_recent_notifications` | `backend\app.py` |
| POST | `/api/pdf/select` | `select_pdf` | `backend\app.py` |
| GET | `/api/pdf/{path:path}` | `get_pdf` | `backend\app.py` |
| POST | `/api/resource-learning/events` | `record_resource_learning_event` | `backend\app.py` |
| GET | `/api/resource-learning/summary` | `get_resource_learning_summary` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `sessions` | 17 | session_id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_activity_log` | 0 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `resource_learning_events` | 20 | event_id | 模块直接写入或维护的核心业务表 |
| 主表 | `course_enrollments` | 待迁移 | enrollment_id | 学生可见课程与学习中心课程选择的访问授权表 |
| 支撑/读取 | `courses` | 1 | course_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `resources` | 16 | resource_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `learning_path_versions` | 0 | path_id | 学生端展示当前路径和路径学习项 |
| 支撑/读取 | `learning_path_items` | 0 | item_id | 学生端展示当前路径和路径学习项 |
| 支撑/读取 | `learning_plans` | 11 | plan_id | 日程/任务类学习计划辅助数据，不再作为个性化路径主表 |

## 3.3 在线测验

模块职责：测验定义、发布、作答、汇总与测验证据回流。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/quiz/answer` | `answer_quiz` | `backend\app.py` |
| POST | `/api/quiz/complete` | `complete_quiz` | `backend\app.py` |
| GET | `/api/quiz/definitions` | `list_quiz_definitions` | `backend\app.py` |
| POST | `/api/quiz/definitions` | `save_quiz_definition` | `backend\app.py` |
| POST | `/api/quiz/definitions/{definition_id}/publish` | `publish_quiz_definition` | `backend\app.py` |
| POST | `/api/quiz/start` | `start_quiz` | `backend\app.py` |
| POST | `/api/quiz/summary` | `generate_quiz_summary` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `quiz_attempts` | 25 | attempt_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `twin_profile_nodes` | 40 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `diagnosis_reports` | 7 | report_id | 模块读取、引用或作为证据来源 |

## 3.4 学生数字孪生

模块职责：学生画像、知识点掌握、画像历史与风险状态。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/digital-twin/collect/{username}` | `collect_data` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/digital-twin/profile/{username}` | `get_profile` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/quiz-score` | `update_quiz_score` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/student-course-profile` | `get_student_course_profile` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/digital-twin/student-profile/{username}` | `get_student_profile_summary` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/homework/twin/my-results` | `get_my_results_for_twin` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/twin/student-results` | `get_student_results_for_twin` | `backend\HomeworkModule\api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `twin_profiles` | 5 | profile_id | 模块直接写入或维护的核心业务表 |
| 主表 | `twin_profile_nodes` | 40 | node_detail_id | 模块直接写入或维护的核心业务表 |
| 主表 | `twin_history` | 70 | history_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `quiz_attempts` | 25 | attempt_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `homework_submissions` | 13 | id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `homework_assignment_knowledge_points` | 3 | id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `resource_learning_events` | 20 | event_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |

## 3.5 诊断智能体

模块职责：薄弱点诊断、原因解释、证据等级和人工修正。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/api/digital-twin/diagnosis-corrections` | `list_diagnosis_corrections` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/diagnosis-corrections` | `record_diagnosis_correction` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/diagnosis/{username}` | `generate_student_diagnosis` | `backend\DigitalTwinModule\digital_twin_api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `diagnosis_reports` | 7 | report_id | 模块直接写入或维护的核心业务表 |
| 主表 | `diagnosis_corrections` | 0 | correction_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `twin_profile_nodes` | 40 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `quiz_attempts` | 25 | attempt_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `homework_submissions` | 13 | id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |

## 3.6 个性化学习路径

模块职责：路径生成、路径版本、节点状态和学习计划。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/digital-twin/path/generate/{username}` | `generate_path` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/digital-twin/path/{username}/current` | `get_current_path` | `backend\DigitalTwinModule\digital_twin_api.py` |
| PATCH | `/api/digital-twin/path/{username}/node-status/{node_id}` | `update_path_node_status` | `backend\DigitalTwinModule\digital_twin_api.py` |
| PATCH | `/api/digital-twin/path/{username}/node/{node_id}` | `update_node_mastery` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/digital-twin/path/{username}/versions` | `list_path_versions` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/learning-plan` | `create_learning_plan` | `backend\app.py` |
| POST | `/api/learning-plan/from-quiz` | `create_learning_plan_from_quiz` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `learning_path_versions` | 0 | path_id | 模块直接写入或维护的核心业务表 |
| 主表 | `learning_path_items` | 0 | item_id | 模块直接写入或维护的核心业务表 |
| 主表 | `learning_path_node_status` | 4 | status_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `twin_profiles` | 5 | profile_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `diagnosis_reports` | 7 | report_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `resources` | 16 | resource_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `resource_learning_events` | 20 | event_id | 路径推荐排序和资源学习反馈的证据来源 |
| 支撑/读取 | `learning_plans` | 11 | plan_id | 兼容性学习计划/日程辅助数据 |
| 支撑/读取 | `learning_plan_nodes` | 26 | node_id | 兼容性学习计划/日程辅助数据 |

## 3.7 5E 教学智能体

模块职责：5E 对话引导、互动记录和有效度评价。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/5e/chat/history` | `get_conversation_history` | `backend\fiveE\apis.py` |
| GET | `/api/5e/chat/history/{user_id}/{lesson_id}` | `conversation_history` | `backend\fiveE\apis.py` |
| POST | `/api/5e/chat/message` | `receive_chat_content` | `backend\fiveE\apis.py` |
| POST | `/api/5e/course/id-by-name` | `api_get_course_id_by_name` | `backend\fiveE\apis.py` |
| GET | `/api/5e/effectiveness/summary` | `effectiveness_summary` | `backend\fiveE\apis.py` |
| GET | `/api/5e/ping` | `ping` | `backend\fiveE\apis.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `events` | 12 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_interaction` | 12 | interaction_id | 模块直接写入或维护的核心业务表 |
| 主表 | `fivee_effectiveness_records` | 12 | record_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `courses` | 1 | course_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |

## 3.8 作业与实践评测

模块职责：作业发布、提交、批改、覆盖知识点和实践证据回流。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/homework/ai/generate-draft` | `ai_generate_draft` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/ai/generate-questions` | `ai_generate_questions` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/assignments` | `list_assignments` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments` | `publish_assignment` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments/seed-oj-smoke` | `seed_oj_smoke_assignment` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/assignments/{assignment_id}` | `get_assignment` | `backend\HomeworkModule\api.py` |
| PUT | `/api/homework/assignments/{assignment_id}` | `update_assignment` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments/{assignment_id}/close` | `close_assignment_status` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/assignments/{assignment_id}/coverage` | `get_assignment_coverage` | `backend\HomeworkModule\api.py` |
| PUT | `/api/homework/assignments/{assignment_id}/coverage` | `update_assignment_coverage` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments/{assignment_id}/publish` | `publish_assignment_status` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments/{assignment_id}/reopen` | `reopen_assignment_status` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/assignments/{assignment_id}/submissions` | `list_assignment_submissions` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/assignments/{assignment_id}/submissions` | `submit_assignment` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/course-nodes` | `list_course_nodes` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/my-submissions` | `list_my_submissions` | `backend\HomeworkModule\api.py` |
| GET | `/api/homework/submissions/{submission_id}` | `get_submission_detail` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/submissions/{submission_id}/ai-grade` | `ai_grade_submission` | `backend\HomeworkModule\api.py` |
| POST | `/api/homework/submissions/{submission_id}/final-grade` | `finalize_grade` | `backend\HomeworkModule\api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `homework_assignments` | 3 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `homework_submissions` | 13 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `homework_assignment_knowledge_points` | 3 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `homework_grading_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `twin_profile_nodes` | 40 | node_detail_id | 模块读取、引用或作为证据来源 |

## 3.9 教师智能干预任务包

模块职责：干预任务包生成、审核、下发、学生执行和结果回流。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/api/intervention/student/packages` | `list_student_packages` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/student/packages/{package_id}` | `get_student_package_detail` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/student/packages/{package_id}/answers` | `student_save_answer` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/student/packages/{package_id}/decision` | `student_decide_package` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/student/packages/{package_id}/progress` | `student_update_package_progress` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/student/packages/{package_id}/tasks` | `student_update_structured_task` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/teacher/diagnose` | `diagnose_students` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/teacher/generate-draft` | `generate_intervention_draft` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/teacher/packages` | `list_teacher_packages` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/teacher/packages/{package_id}` | `get_teacher_package_detail` | `backend\TeacherInterventionModule\api.py` |
| PUT | `/api/intervention/teacher/packages/{package_id}` | `update_teacher_package` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/teacher/packages/{package_id}/grade` | `grade_teacher_package_question` | `backend\TeacherInterventionModule\api.py` |
| POST | `/api/intervention/teacher/packages/{package_id}/push` | `push_teacher_package` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/teacher/progress` | `list_teacher_progress` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/teacher/students-overview` | `get_teacher_students_overview` | `backend\TeacherInterventionModule\api.py` |
| GET | `/api/intervention/teacher/task-reference-options` | `list_teacher_task_reference_options` | `backend\TeacherInterventionModule\api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `intervention_packages` | 3 | package_id | 模块直接写入或维护的核心业务表 |
| 主表 | `intervention_package_items` | 3 | item_id | 模块直接写入或维护的核心业务表 |
| 主表 | `intervention_package_student_records` | 3 | record_id | 模块直接写入或维护的核心业务表 |
| 主表 | `teacher_intervention_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `diagnosis_reports` | 7 | report_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `resources` | 16 | resource_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `homework_assignments` | 3 | id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |

## 3.10 教师看板与教师数字孪生

模块职责：班级学情、学生下钻、教师画像和教学支持建议。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/api/dashboard/class-overview` | `get_class_overview` | `backend\DashboardModule\dashboard_api.py` |
| GET | `/api/dashboard/node/{node_id}/ranking` | `get_node_ranking` | `backend\DashboardModule\dashboard_api.py` |
| GET | `/api/dashboard/student/{username}` | `get_student_detail` | `backend\DashboardModule\dashboard_api.py` |
| GET | `/api/dashboard/student/{username}/trend` | `get_student_trend` | `backend\DashboardModule\dashboard_api.py` |
| GET | `/api/dashboard/teacher-twin` | `get_teacher_twin` | `backend\DashboardModule\dashboard_api.py` |
| POST | `/api/dashboard/teacher-twin/ai-suggestions` | `generate_teacher_twin_ai_suggestions` | `backend\DashboardModule\dashboard_api.py` |
| GET | `/api/dashboard/teacher-twin/drilldown` | `get_teacher_twin_drilldown` | `backend\DashboardModule\dashboard_api.py` |
| POST | `/api/digital-twin/teacher-events/grading` | `record_teacher_grading_event` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/teacher-events/interaction` | `record_teacher_interaction_event` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/teacher-events/research` | `record_teacher_research_event` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/digital-twin/teacher-profile/{teacher_username}` | `get_teacher_profile_summary` | `backend\DigitalTwinModule\digital_twin_api.py` |
| POST | `/api/digital-twin/teacher-profile/{teacher_username}/external-sync` | `sync_teacher_external_metrics` | `backend\DigitalTwinModule\digital_twin_api.py` |
| GET | `/api/heatmap` | `get_heatmap` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `teaching_interaction_events` | 5 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_research_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `homework_grading_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teacher_intervention_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_activity_log` | 0 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `llm_logs` | 0 | log_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `teacher_student_links` | 5 | teacher_username, student_username | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `twin_profiles` | 5 | profile_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `twin_profile_nodes` | 40 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `diagnosis_reports` | 7 | report_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `intervention_packages` | 3 | package_id | 模块读取、引用或作为证据来源 |

## 3.11 教学互动

模块职责：公告、讨论、答疑、教研记录和教学互动证据。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/api/teaching-interaction/analytics` | `get_interaction_analytics` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-interaction/announcements` | `list_announcements` | `backend\TeachingInteractionModule\api.py` |
| POST | `/api/teaching-interaction/announcements` | `create_announcement` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-interaction/announcements/public` | `list_public_announcements` | `backend\TeachingInteractionModule\api.py` |
| DELETE | `/api/teaching-interaction/announcements/{announcement_id}` | `delete_announcement` | `backend\TeachingInteractionModule\api.py` |
| PUT | `/api/teaching-interaction/announcements/{announcement_id}` | `update_announcement` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-interaction/context-options` | `get_context_options` | `backend\TeachingInteractionModule\api.py` |
| POST | `/api/teaching-interaction/posts` | `create_post` | `backend\TeachingInteractionModule\api.py` |
| DELETE | `/api/teaching-interaction/posts/{post_id}` | `delete_post` | `backend\TeachingInteractionModule\api.py` |
| PUT | `/api/teaching-interaction/posts/{post_id}` | `update_post` | `backend\TeachingInteractionModule\api.py` |
| DELETE | `/api/teaching-interaction/posts/{post_id}/student` | `delete_student_post` | `backend\TeachingInteractionModule\api.py` |
| PUT | `/api/teaching-interaction/posts/{post_id}/student` | `update_student_post` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-interaction/topics` | `list_topics` | `backend\TeachingInteractionModule\api.py` |
| POST | `/api/teaching-interaction/topics` | `create_topic` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-interaction/topics/public` | `list_public_topics` | `backend\TeachingInteractionModule\api.py` |
| DELETE | `/api/teaching-interaction/topics/{topic_id}` | `delete_topic` | `backend\TeachingInteractionModule\api.py` |
| PUT | `/api/teaching-interaction/topics/{topic_id}` | `update_topic` | `backend\TeachingInteractionModule\api.py` |
| POST | `/api/teaching-interaction/topics/{topic_id}/student-question` | `create_student_question` | `backend\TeachingInteractionModule\api.py` |
| GET | `/api/teaching-research/context-options` | `get_context_options` | `backend\TeachingResearchModule\api.py` |
| GET | `/api/teaching-research/records` | `list_research_records` | `backend\TeachingResearchModule\api.py` |
| POST | `/api/teaching-research/records` | `create_research_record` | `backend\TeachingResearchModule\api.py` |
| DELETE | `/api/teaching-research/records/{record_id}` | `delete_research_record` | `backend\TeachingResearchModule\api.py` |
| PUT | `/api/teaching-research/records/{record_id}` | `update_research_record` | `backend\TeachingResearchModule\api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `teaching_announcements` | 2 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_discussion_topics` | 2 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_discussion_posts` | 4 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_research_records` | 2 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_interaction_events` | 5 | id | 模块直接写入或维护的核心业务表 |
| 主表 | `teaching_research_events` | 3 | id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `teacher_student_links` | 5 | teacher_username, student_username | 模块读取、引用或作为证据来源 |

## 3.12 行业情报与能力对接

模块职责：岗位能力获取、能力候选、能力-知识点映射和审核。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| POST | `/api/course-digital-twin/abilities/import` | `import_course_digital_twin_abilities` | `backend\app.py` |
| POST | `/api/course-digital-twin/ability-mappings` | `upsert_course_digital_twin_ability_mappings` | `backend\app.py` |
| POST | `/api/course-digital-twin/ability-mappings/candidates/generate` | `generate_course_digital_twin_ability_mapping_candidates` | `backend\app.py` |
| POST | `/api/course-digital-twin/ability-mappings/review` | `review_course_digital_twin_ability_mappings` | `backend\app.py` |
| POST | `/api/course-digital-twin/positions` | `upsert_course_digital_twin_position` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}/abilities` | `list_course_digital_twin_abilities` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}/ability-mappings` | `list_course_digital_twin_ability_mappings` | `backend\app.py` |
| GET | `/api/course-digital-twin/{course_id}/positions` | `list_course_digital_twin_positions` | `backend\app.py` |
| POST | `/api/industry-intelligence/analyze` | `analyze` | `backend\IndustryIntelligenceModule\api.py` |
| GET | `/api/industry-intelligence/current` | `get_current_task` | `backend\IndustryIntelligenceModule\api.py` |
| POST | `/api/industry-intelligence/reanalyze` | `reanalyze` | `backend\IndustryIntelligenceModule\api.py` |
| GET | `/api/industry-intelligence/status` | `get_status` | `backend\IndustryIntelligenceModule\api.py` |
| GET | `/api/industry-intelligence/tasks/{task_id}` | `get_task` | `backend\IndustryIntelligenceModule\api.py` |
| POST | `/api/industry-intelligence/tasks/{task_id}/cancel` | `cancel_task` | `backend\IndustryIntelligenceModule\api.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `career_positions` | 0 | position_id | 模块直接写入或维护的核心业务表 |
| 主表 | `career_abilities` | 4 | ability_id | 模块直接写入或维护的核心业务表 |
| 主表 | `course_ability_mappings` | 7 | mapping_id | 模块直接写入或维护的核心业务表 |
| 支撑/读取 | `courses` | 1 | course_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `course_nodes` | 8 | node_detail_id | 模块读取、引用或作为证据来源 |
| 支撑/读取 | `users` | 6 | user_id | 模块读取、引用或作为证据来源 |

## 支撑 用户、权限、文件与智能服务

模块职责：登录会话、用户资料、文件处理、日志和通用智能服务。

### 接口

| 方法 | 路径 | 处理函数 | 源文件 |
|---|---|---|---|
| GET | `/` | `root` | `backend\app.py` |
| GET | `/admin.html` | `get_admin_page` | `backend\app.py` |
| POST | `/api/auth/login` | `login_json` | `backend\app.py` |
| POST | `/api/change-password` | `change_password` | `backend\app.py` |
| POST | `/api/chat` | `chat` | `backend\app.py` |
| GET | `/api/current-user` | `get_current_user_info` | `backend\app.py` |
| GET | `/api/health/llm` | `llm_health_check` | `backend\app.py` |
| GET | `/api/languages` | `get_languages` | `backend\app.py` |
| POST | `/api/llm-log` | `log_llm_call` | `backend\app.py` |
| GET | `/api/llm-logs` | `get_llm_logs` | `backend\app.py` |
| POST | `/api/logout` | `logout` | `backend\app.py` |
| POST | `/api/ocr/extract` | `extract_text_from_image` | `backend\app.py` |
| POST | `/api/register` | `register_user` | `backend\app.py` |
| GET | `/api/students` | `get_students` | `backend\app.py` |
| POST | `/api/summary` | `generate_summary` | `backend\app.py` |
| GET | `/api/teachers` | `get_teachers` | `backend\app.py` |
| POST | `/api/update-profile` | `update_profile` | `backend\app.py` |
| POST | `/login/admin` | `login_admin` | `backend\app.py` |
| POST | `/login/student` | `login_student` | `backend\app.py` |
| POST | `/login/teacher` | `login_teacher` | `backend\app.py` |
| GET | `/teacher.html` | `get_teacher_page` | `backend\app.py` |
| GET | `/{full_path:path}` | `frontend_spa` | `backend\app.py` |

### 数据表

| 类型 | 表名 | 当前行数 | 关键字段示例 | 说明 |
|---|---|---:|---|---|
| 主表 | `users` | 6 | user_id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_profiles` | 0 | user_id | 模块直接写入或维护的核心业务表 |
| 主表 | `teacher_student_links` | 5 | teacher_username, student_username | 模块直接写入或维护的核心业务表 |
| 主表 | `course_enrollments` | 待迁移 | enrollment_id | 学生课程选课与学习中心访问授权表 |
| 主表 | `teacher_course_assignments` | 待迁移 | assignment_id | 教师任课范围与课程维护授权表 |
| 主表 | `sessions` | 17 | session_id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_states` | 0 | username | 模块直接写入或维护的核心业务表 |
| 主表 | `llm_logs` | 0 | log_id | 模块直接写入或维护的核心业务表 |
| 主表 | `user_activity_log` | 0 | id | 模块直接写入或维护的核心业务表 |
