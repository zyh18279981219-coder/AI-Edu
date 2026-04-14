# 后端模块 Python 接口清单（实体优先版）

> 同步日期：2026-04-14

## 1. 存储层（DatabaseModule/sqlite_store.py）

### 用户与身份
- `get_user_by_identifier(user_type, identifier)`：按 `login_id/user_id` 解析用户。
- `resolve_user_identity(user_type, identifier)`：统一身份解析。

### 学生孪生
- `save_twin_profile(username, payload)`
- `get_twin_profile(username)`
- `list_twin_profiles()`
- `save_twin_history(username, snapshot_date, payload)`

### 课程实体
- `sync_course_from_graph(course_id, graph_data, course_name, source_path)`
- `get_course_payload(course_id)`
- `list_learning_nodes_for_course(course_id)`
- `list_resources_for_node_name(course_id, node_name)`
- `get_course_id_by_resource_path(resource_path)`

### 测试实体
- `record_quiz_attempt(...)`

### 其他
- `list_teacher_students(teacher_identifier)`
- `list_llm_logs_for_user(user_identifier, user_type, limit)`
- `list_learning_plans_by_user_identifier(user_identifier, user_type, categories)`

## 2. 数字孪生模块

### TwinProfileStore
- `load(username)`
- `load_or_create(username)`
- `save(profile)`
- `exists(username)`
- `save_daily_snapshot(profile)`

### DataCollector
- `collect_all(username)`
- `collect_progress(username)`
- `collect_llm_interactions(username)`
- `collect_session_duration(username)`
- `collect_quiz_score(username, node_id, score)`

### StudentTwinService
- `build_summary(profile, trend)`

### TrendTracker
- `record_daily_snapshot(username, overall_mastery)`
- `get_trend(username, days)`

## 3. 路径与教师

### PathPlannerAgent
- `plan(username)`
- `get_latest_path(username)`
- `update_path_on_mastery_change(username, node_id, new_score)`

### TeacherTwinService
- `build_summary(teacher_identifier)`

### Dashboard API
- `get_class_overview()`
- `get_student_detail(username)`
- `get_student_trend(username)`
- `get_node_ranking(node_id)`

## 4. 自测脚本

- `scripts/backend_api_selftest.py`
- 运行：
```powershell
python scripts\backend_api_selftest.py --base-url http://127.0.0.1:8010
```

## 5. 数据来源审计

- 日志：`data/Log/data_source_audit.log`
- 常见事件：`users_hit`、`twin_profile_hit`、`learning_plans_hit`、`llm_logs_hit`。
