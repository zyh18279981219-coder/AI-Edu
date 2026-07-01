# AI-Education 多课程学习中心与个性化路径重构提示词

你正在 AI-Education2 项目中重构学生学习中心、个性化路径和对应数据库模型。请以当前 FastAPI + Vue + MySQL 实现为准，不要只按旧页面文案理解功能。

## 目标

把系统从“默认单课程 + 学习计划页面”调整为“学生先选择课程，再在课程上下文内查看学习内容、学生画像、个性化路径和任务”。学习中心负责课程资源与知识点内容；个性化路径负责基于学生画像、诊断和课程知识图谱生成的补弱/提升路径；普通学习计划只作为日程和任务安排。

## 数据库改造要求

1. 新增学生选课关系表，用于学习中心先选课程：
   - 表名建议：`course_enrollments`
   - 字段包含：`enrollment_id`, `course_id`, `student_username`, `student_user_id`, `status`, `enrolled_at`, `created_at`, `updated_at`, `payload_json`
   - 对 `(course_id, student_username)` 做唯一约束。

2. 新增教师课程授权表，或补齐教师-课程-班级关系：
   - 表名建议：`teacher_course_assignments`
   - 字段包含：`assignment_id`, `course_id`, `teacher_username`, `teacher_user_id`, `class_name`, `role`, `status`, `created_at`, `updated_at`, `payload_json`
   - 对 `(course_id, teacher_username, class_name)` 做唯一约束。

3. 个性化路径从学习计划中拆出版本表和条目表：
   - `learning_path_versions`: `path_id`, `plan_id`, `username`, `user_id`, `course_id`, `diagnosis_report_id`, `version_no`, `title`, `summary`, `status`, `generated_reason`, `source_payload_json`, `created_at`, `updated_at`
   - `learning_path_items`: `item_id`, `path_id`, `course_id`, `node_id`, `resource_id`, `sequence_order`, `item_type`, `recommendation_reason`, `target_mastery`, `status`, `payload_json`, `created_at`, `updated_at`
   - 继续兼容 `learning_path_node_status`，但路径页面读取优先使用新表。

4. 学习计划保留为日程/任务模型，不再作为路径主模型。`learning_plans` 可增加 `course_id` 和 `plan_type`，其中 `plan_type` 可区分 `schedule`、`path_legacy`、`weekly` 等。

5. 学生画像补齐课程维度：
   - 可给 `twin_profiles`、`twin_history` 增加 `course_id`
   - 或新增课程画像表。当前实现优先选择最小改造：在现有表增加 `course_id` 并建立 `(username, course_id)` 唯一约束。

## 后端要求

- 新增学生端课程接口：返回当前学生可访问课程列表、默认课程、课程摘要和选课状态。
- `/api/knowledge-graph`、`/api/node/resources` 等学生学习接口必须支持 `course_id` 参数或从会话/查询中解析课程。
- 个性化路径接口支持按 `course_id` 查询当前路径、路径版本和路径节点。
- 旧接口保持兼容，不要让现有前端 404。
- 所有新增迁移必须幂等，重复执行不报错。

## 前端要求

### 学习中心

- 页面顶部增加课程选择区，学生必须先知道当前课程。
- 没有课程时显示空状态；有课程时默认选最近或第一个已发布课程。
- 左侧仍为课程目录；中间只展示学习内容；右侧保留 AI 助教。
- 学习中心不再出现页内“个性化路径”切换。
- 知识点资源来自绑定资源，不展示旧视频资源。

### 个性化路径

- 页面语义从“我的学习计划”改为“课程内个性化路径”。
- 顶部展示当前课程、路径生成依据、风险/薄弱点摘要、更新时间。
- 主区域展示路径阶段/节点序列，每个节点应能看到掌握度、推荐理由、资源入口和完成状态。
- 右侧展示下一步建议、待完成任务和资源缺口。
- 普通学习计划/日历可以作为辅助区，不再占据主标签。

## 验收

- 后端 Python 编译通过。
- 前端 `npm run build` 通过。
- 本地 MySQL 迁移脚本执行成功。
- 提交按阶段拆分：数据库、后端、学习中心、个性化路径。
- 不提交无关文档、drawio、旧备份文件。
