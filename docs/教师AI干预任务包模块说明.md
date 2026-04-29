# 教师 AI 干预任务包模块说明

## 目标
- 为教师新增独立工作台：按学生学习进度与作业情况生成个性化干预策略与任务包。
- 支持阶段化流程：先识别薄弱点，再 AI 出题，教师编辑后推送给学生。
- 学生端新增独立页面，仅本人可见任务包，可选择执行或暂不执行，并回传进度。

## 关键实现
- 后端新增模块：`TeacherInterventionModule`
  - `api.py`：提供教师/学生两端接口。
  - `service.py`：封装诊断、AI 生成、编辑、推送、进度回写。
  - `models.py`：请求模型与字段约束。
- 前端新增页面：
  - 教师端：`/teacher/intervention`（`TeacherInterventionView.vue`）
- 学生端列表：`/student/intervention`（`StudentInterventionView.vue`）
- 学生端逐题作答：`/student/intervention/:packageId`（`StudentInterventionDetailView.vue`）
  - 每题独立备注、自动保存答案与备注
- 教师端推送后详情：`/teacher/intervention/:packageId`（`TeacherInterventionDetailView.vue`）
  - 可查看每题作答内容、每题备注、自动判题结果
  - 可按题录入教师评分与评语（类似作业批改）
- 路由与导航：
  - 教师顶部导航新增“AI干预任务包”
  - 学生顶部导航新增“个性化任务包”

## 阶段化流程
1. 阶段1（快速）：教师点击“识别薄弱点”，系统基于学生孪生节点数据输出薄弱知识点与原因。
2. 阶段2（AI）：按学生调用模型生成策略、概念/视频建议和题目草稿。
   - 题型已对标作业模块：`fill_blank`（填空）/`single_choice`（单选）/`multiple_choice`（多选）/`code`（编程）/`subjective`（主观）。
3. 教师编辑：教师可改写策略与题目内容。
   - 可编辑题型、选项、标准答案、编程测试用例。
4. 推送学生：任务包仅推送给对应学生。
5. 学生反馈：学生可接受/拒绝；接受后按题进入作答并保存答案。
6. 教师跟踪：教师端实时查看推送包状态与完成度。

## 进度计算规则
- 学生端进度为**自动计算**：`完成度 = 已填写答案题数 / 总题数`。
- 每道题有独立 `answer + note`，保存任一题会自动刷新进度。
- 每次学生保存某道题答案后自动刷新状态：
  - 0%：已接受（未作答）
  - 0%~100%：进行中
  - 100%：已完成
- 不再依赖学生手动拖拽进度条。

## AI判题细则（结构化）
- 每题判题结果包含：
  - `ai_score`：自动评分
  - `ai_feedback`：自动反馈摘要
  - `ai_detail.total_score`：总分
  - `ai_detail.criteria[]`：分项细则（分项名、得分、满分、原因）
- 题型化判题：
  - 填空：标准答案匹配
  - 单/多选：选项匹配（多选含漏选/错选惩罚）
  - 编程：基于测试用例的轻量通过率评分
  - 主观：完整性/要点命中/结构表达分项评分

## 数据安全与协作约束
- **未新增/修改共享数据库表结构**。
- 新增状态全部通过 `user_states` 命名空间键 `teacher_intervention_module_v1` 存储，避免影响其他模块字段。
- 教师只可操作自己关联学生；学生仅可读取与操作自己的任务包。

## 主要接口
- 教师：
  - `GET /api/intervention/teacher/students-overview`
  - `POST /api/intervention/teacher/diagnose`
  - `POST /api/intervention/teacher/generate-draft`
  - `GET /api/intervention/teacher/packages`
  - `GET /api/intervention/teacher/packages/{package_id}`
  - `PUT /api/intervention/teacher/packages/{package_id}`
  - `POST /api/intervention/teacher/packages/{package_id}/push`
  - `POST /api/intervention/teacher/packages/{package_id}/grade`
  - `GET /api/intervention/teacher/progress`
- 学生：
  - `GET /api/intervention/student/packages`
  - `GET /api/intervention/student/packages/{package_id}`
  - `POST /api/intervention/student/packages/{package_id}/decision`
  - `POST /api/intervention/student/packages/{package_id}/answers`
  - `POST /api/intervention/student/packages/{package_id}/progress`

