# FastAPI 接口清单（当前实现）

生成时间：2026-06-29 13:21:14

接口操作数：164

说明：本文件由 `backend/tools/docs/generate_live_design_artifacts.py` 读取 `app.openapi()` 自动生成。

## 5E 教学智能体

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/5e/chat/history | Get Conversation History |  | application/json | 200,422 |
| GET | /api/5e/chat/history/{user_id}/{lesson_id} | Conversation History |  |  | 200,422 |
| POST | /api/5e/chat/message | Receive Chat Content |  | application/json | 200,422 |
| POST | /api/5e/course/id-by-name | Api Get Course Id By Name |  | application/json | 200,422 |
| GET | /api/5e/effectiveness/summary | Effectiveness Summary |  |  | 200,422 |
| GET | /api/5e/ping | Ping |  |  | 200 |

## LLM、OCR 与日志支撑接口

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/chat | Chat |  | application/json | 200,422 |
| GET | /api/health/llm | Llm Health Check |  |  | 200,422 |
| GET | /api/languages | Get Languages |  |  | 200 |
| POST | /api/llm-log | Log Llm Call |  | application/json | 200,422 |
| GET | /api/llm-logs | Get Llm Logs |  |  | 200 |
| POST | /api/ocr/extract | Extract Text From Image |  | multipart/form-data | 200,422 |
| POST | /api/summary | Generate Summary |  | application/json | 200,422 |

## 个性化学习路径

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/digital-twin/path/generate/{username} | Generate Path | digital-twin | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/current | Get Current Path | digital-twin |  | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node-status/{node_id} | Update Path Node Status | digital-twin | application/json | 200,422 |
| PATCH | /api/digital-twin/path/{username}/node/{node_id} | Update Node Mastery | digital-twin | application/json | 200,422 |
| GET | /api/digital-twin/path/{username}/versions | List Path Versions | digital-twin |  | 200,422 |
| POST | /api/learning-plan | Create Learning Plan |  | application/json | 200,422 |
| POST | /api/learning-plan/from-quiz | Create Learning Plan From Quiz |  | application/json | 200,422 |

## 作业与实践评测

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/homework/ai/generate-draft | Ai Generate Draft | homework | application/json | 200,422 |
| POST | /api/homework/ai/generate-questions | Ai Generate Questions | homework | application/json | 200,422 |
| GET | /api/homework/assignments | List Assignments | homework |  | 200,422 |
| POST | /api/homework/assignments | Publish Assignment | homework | application/json | 200,422 |
| POST | /api/homework/assignments/seed-oj-smoke | Seed Oj Smoke Assignment | homework |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id} | Get Assignment | homework |  | 200,422 |
| PUT | /api/homework/assignments/{assignment_id} | Update Assignment | homework | application/json | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/close | Close Assignment Status | homework |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id}/coverage | Get Assignment Coverage | homework |  | 200,422 |
| PUT | /api/homework/assignments/{assignment_id}/coverage | Update Assignment Coverage | homework | application/json | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/publish | Publish Assignment Status | homework |  | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/reopen | Reopen Assignment Status | homework |  | 200,422 |
| GET | /api/homework/assignments/{assignment_id}/submissions | List Assignment Submissions | homework |  | 200,422 |
| POST | /api/homework/assignments/{assignment_id}/submissions | Submit Assignment | homework | application/json | 200,422 |
| GET | /api/homework/course-nodes | List Course Nodes | homework |  | 200,422 |
| GET | /api/homework/my-submissions | List My Submissions | homework |  | 200,422 |
| GET | /api/homework/submissions/{submission_id} | Get Submission Detail | homework |  | 200,422 |
| POST | /api/homework/submissions/{submission_id}/ai-grade | Ai Grade Submission | homework | application/json | 200,422 |
| POST | /api/homework/submissions/{submission_id}/final-grade | Finalize Grade | homework | application/json | 200,422 |

## 前端页面与历史兼容接口

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | / | Root |  |  | 200 |
| GET | /admin.html | Get Admin Page |  |  | 200 |
| GET | /teacher.html | Get Teacher Page |  |  | 200 |
| GET | /{full_path} | Frontend Spa |  |  | 200,422 |

## 在线测验

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/quiz/answer | Answer Quiz |  | application/json | 200,422 |
| POST | /api/quiz/complete | Complete Quiz |  | application/json | 200,422 |
| GET | /api/quiz/definitions | List Quiz Definitions |  |  | 200,422 |
| POST | /api/quiz/definitions | Save Quiz Definition |  | application/json | 200,422 |
| POST | /api/quiz/definitions/{definition_id}/publish | Publish Quiz Definition |  | application/json | 200,422 |
| POST | /api/quiz/start | Start Quiz |  | application/json | 200,422 |
| POST | /api/quiz/summary | Generate Quiz Summary |  | application/json | 200,422 |

## 学习行为证据支撑接口

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/resource-learning/events | Record Resource Learning Event |  | application/json | 200,422 |
| GET | /api/resource-learning/summary | Get Resource Learning Summary |  |  | 200,422 |

## 学生学习空间

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/graph-visualization | Get Graph Visualization |  |  | 200,422 |
| GET | /api/learning-nodes | Get Learning Nodes |  |  | 200,422 |
| GET | /api/learning-plans | Get Learning Plans |  |  | 200,422 |
| GET | /api/learning-progress | Get Learning Progress |  |  | 200,422 |
| GET | /api/learning-streak | Get Learning Streak |  |  | 200,422 |
| POST | /api/node/resources | Get Node Resources |  | application/json | 200,422 |
| GET | /api/notifications/recent | Get Recent Notifications |  |  | 200,422 |
| POST | /api/pdf/select | Select Pdf |  | application/json | 200,422 |
| GET | /api/pdf/{path} | Get Pdf |  |  | 200,422 |

## 学生数字孪生

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/digital-twin/collect/{username} | Collect Data | digital-twin |  | 200,422 |
| GET | /api/digital-twin/profile/{username} | Get Profile | digital-twin |  | 200,422 |
| POST | /api/digital-twin/quiz-score | Update Quiz Score | digital-twin | application/json | 200,422 |
| POST | /api/digital-twin/student-course-profile | Get Student Course Profile | digital-twin | application/json | 200,422 |
| GET | /api/digital-twin/student-profile/{username} | Get Student Profile Summary | digital-twin |  | 200,422 |
| GET | /api/homework/twin/my-results | Get My Results For Twin | homework |  | 200,422 |
| GET | /api/homework/twin/student-results | Get Student Results For Twin | homework |  | 200,422 |

## 教学互动

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/teaching-interaction/analytics | Get Interaction Analytics | teaching-interaction |  | 200,422 |
| GET | /api/teaching-interaction/announcements | List Announcements | teaching-interaction |  | 200,422 |
| POST | /api/teaching-interaction/announcements | Create Announcement | teaching-interaction | application/json | 200,422 |
| GET | /api/teaching-interaction/announcements/public | List Public Announcements | teaching-interaction |  | 200,422 |
| DELETE | /api/teaching-interaction/announcements/{announcement_id} | Delete Announcement | teaching-interaction |  | 200,422 |
| PUT | /api/teaching-interaction/announcements/{announcement_id} | Update Announcement | teaching-interaction | application/json | 200,422 |
| GET | /api/teaching-interaction/context-options | Get Context Options | teaching-interaction |  | 200,422 |
| POST | /api/teaching-interaction/posts | Create Post | teaching-interaction | application/json | 200,422 |
| DELETE | /api/teaching-interaction/posts/{post_id} | Delete Post | teaching-interaction |  | 200,422 |
| PUT | /api/teaching-interaction/posts/{post_id} | Update Post | teaching-interaction | application/json | 200,422 |
| DELETE | /api/teaching-interaction/posts/{post_id}/student | Delete Student Post | teaching-interaction |  | 200,422 |
| PUT | /api/teaching-interaction/posts/{post_id}/student | Update Student Post | teaching-interaction | application/json | 200,422 |
| GET | /api/teaching-interaction/topics | List Topics | teaching-interaction |  | 200,422 |
| POST | /api/teaching-interaction/topics | Create Topic | teaching-interaction | application/json | 200,422 |
| GET | /api/teaching-interaction/topics/public | List Public Topics | teaching-interaction |  | 200,422 |
| DELETE | /api/teaching-interaction/topics/{topic_id} | Delete Topic | teaching-interaction |  | 200,422 |
| PUT | /api/teaching-interaction/topics/{topic_id} | Update Topic | teaching-interaction | application/json | 200,422 |
| POST | /api/teaching-interaction/topics/{topic_id}/student-question | Create Student Question | teaching-interaction |  | 200,422 |
| GET | /api/teaching-research/context-options | Get Context Options | teaching-research |  | 200,422 |
| GET | /api/teaching-research/records | List Research Records | teaching-research |  | 200,422 |
| POST | /api/teaching-research/records | Create Research Record | teaching-research | application/json | 200,422 |
| DELETE | /api/teaching-research/records/{record_id} | Delete Research Record | teaching-research |  | 200,422 |
| PUT | /api/teaching-research/records/{record_id} | Update Research Record | teaching-research | application/json | 200,422 |

## 教师智能干预任务包

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/intervention/student/packages | List Student Packages | teacher-intervention |  | 200,422 |
| GET | /api/intervention/student/packages/{package_id} | Get Student Package Detail | teacher-intervention |  | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/answers | Student Save Answer | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/decision | Student Decide Package | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/progress | Student Update Package Progress | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/student/packages/{package_id}/tasks | Student Update Structured Task | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/teacher/diagnose | Diagnose Students | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/teacher/generate-draft | Generate Intervention Draft | teacher-intervention | application/json | 200,422 |
| GET | /api/intervention/teacher/packages | List Teacher Packages | teacher-intervention |  | 200,422 |
| GET | /api/intervention/teacher/packages/{package_id} | Get Teacher Package Detail | teacher-intervention |  | 200,422 |
| PUT | /api/intervention/teacher/packages/{package_id} | Update Teacher Package | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/teacher/packages/{package_id}/grade | Grade Teacher Package Question | teacher-intervention | application/json | 200,422 |
| POST | /api/intervention/teacher/packages/{package_id}/push | Push Teacher Package | teacher-intervention |  | 200,422 |
| GET | /api/intervention/teacher/progress | List Teacher Progress | teacher-intervention |  | 200,422 |
| GET | /api/intervention/teacher/students-overview | Get Teacher Students Overview | teacher-intervention |  | 200,422 |
| GET | /api/intervention/teacher/task-reference-options | List Teacher Task Reference Options | teacher-intervention |  | 200,422 |

## 教师看板与教师数字孪生

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/dashboard/class-overview | Get Class Overview | dashboard |  | 200,422 |
| GET | /api/dashboard/node/{node_id}/ranking | Get Node Ranking | dashboard |  | 200,422 |
| GET | /api/dashboard/student/{username} | Get Student Detail | dashboard |  | 200,422 |
| GET | /api/dashboard/student/{username}/trend | Get Student Trend | dashboard |  | 200,422 |
| GET | /api/dashboard/teacher-twin | Get Teacher Twin | dashboard |  | 200,422 |
| POST | /api/dashboard/teacher-twin/ai-suggestions | Generate Teacher Twin Ai Suggestions | dashboard |  | 200,422 |
| GET | /api/dashboard/teacher-twin/drilldown | Get Teacher Twin Drilldown | dashboard |  | 200,422 |
| POST | /api/digital-twin/teacher-events/grading | Record Teacher Grading Event | digital-twin | application/json | 200,422 |
| POST | /api/digital-twin/teacher-events/interaction | Record Teacher Interaction Event | digital-twin | application/json | 200,422 |
| POST | /api/digital-twin/teacher-events/research | Record Teacher Research Event | digital-twin | application/json | 200,422 |
| GET | /api/digital-twin/teacher-profile/{teacher_username} | Get Teacher Profile Summary | digital-twin |  | 200,422 |
| POST | /api/digital-twin/teacher-profile/{teacher_username}/external-sync | Sync Teacher External Metrics | digital-twin | application/json | 200,422 |
| GET | /api/heatmap | Get Heatmap |  |  | 200,422 |

## 用户、权限与会话

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/auth/login | Login Json |  | application/json | 200,422 |
| POST | /api/change-password | Change Password |  | application/json | 200,422 |
| GET | /api/current-user | Get Current User Info |  |  | 200,422 |
| POST | /api/logout | Logout |  |  | 200,422 |
| POST | /api/register | Register User |  | application/json | 200,422 |
| GET | /api/students | Get Students |  |  | 200,422 |
| GET | /api/teachers | Get Teachers |  |  | 200 |
| POST | /api/update-profile | Update Profile |  | application/json | 200,422 |
| POST | /login/admin | Login Admin |  | application/x-www-form-urlencoded | 200,422 |
| POST | /login/student | Login Student |  | application/x-www-form-urlencoded | 200,422 |
| POST | /login/teacher | Login Teacher |  | application/x-www-form-urlencoded | 200,422 |

## 行业情报与能力对接

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/course-digital-twin/abilities/import | Import Course Digital Twin Abilities |  | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings | Upsert Course Digital Twin Ability Mappings |  | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings/candidates/generate | Generate Course Digital Twin Ability Mapping Candidates |  | application/json | 200,422 |
| POST | /api/course-digital-twin/ability-mappings/review | Review Course Digital Twin Ability Mappings |  | application/json | 200,422 |
| POST | /api/course-digital-twin/positions | Upsert Course Digital Twin Position |  | application/json | 200,422 |
| GET | /api/course-digital-twin/{course_id}/abilities | List Course Digital Twin Abilities |  |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/ability-mappings | List Course Digital Twin Ability Mappings |  |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/positions | List Course Digital Twin Positions |  |  | 200,422 |
| POST | /api/industry-intelligence/analyze | Analyze | industry-intelligence | application/json | 200,422 |
| GET | /api/industry-intelligence/current | Get Current Task | industry-intelligence |  | 200,422 |
| POST | /api/industry-intelligence/reanalyze | Reanalyze | industry-intelligence | application/json | 200,422 |
| GET | /api/industry-intelligence/status | Get Status | industry-intelligence |  | 200 |
| GET | /api/industry-intelligence/tasks/{task_id} | Get Task | industry-intelligence |  | 200,422 |
| POST | /api/industry-intelligence/tasks/{task_id}/cancel | Cancel Task | industry-intelligence |  | 200,422 |

## 诊断智能体

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/digital-twin/diagnosis-corrections | List Diagnosis Corrections | digital-twin |  | 200,422 |
| POST | /api/digital-twin/diagnosis-corrections | Record Diagnosis Correction | digital-twin | application/json | 200,422 |
| POST | /api/digital-twin/diagnosis/{username} | Generate Student Diagnosis | digital-twin | application/json | 200,422 |

## 课程数字孪生与课程资源

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| GET | /api/course-digital-twin/courses | List Course Digital Twin Courses |  |  | 200,422 |
| POST | /api/course-digital-twin/initial-graph | Generate Course Digital Twin Initial Graph |  | application/json | 200,422 |
| POST | /api/course-digital-twin/publish | Publish Course Digital Twin |  | application/json | 200,422 |
| POST | /api/course-digital-twin/resource-candidates/bind | Bind Course Digital Twin Resource Candidates |  | application/json | 200,422 |
| POST | /api/course-digital-twin/resource-review | Review Course Digital Twin Resource |  | application/json | 200,422 |
| POST | /api/course-digital-twin/structure | Upsert Course Digital Twin Structure |  | application/json | 200,422 |
| GET | /api/course-digital-twin/{course_id} | Get Course Digital Twin Summary |  |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/resources | List Course Digital Twin Resources |  |  | 200,422 |
| GET | /api/course-digital-twin/{course_id}/runtime-evaluation | Evaluate Course Digital Twin Runtime |  |  | 200,422 |
| GET | /api/knowledge-graph | Get Knowledge Graph |  |  | 200,422 |
| POST | /api/upload | Upload Files |  | multipart/form-data | 200,422 |

## 资源文件与课程运行支撑接口

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/clear-course-cache | Clear Course Cache |  |  | 200,422 |
| POST | /api/delete-resource | Delete Resource |  | application/json | 200,422 |
| GET | /api/recycle-bin | Get Recycle Bin |  |  | 200,422 |
| POST | /api/restore-resource | Restore Resource |  | application/json | 200,422 |

## 通用/历史接口

| 方法 | 路径 | 摘要 | Tag | 请求体 | 响应码 |
| --- | --- | --- | --- | --- | --- |
| POST | /api/learning-activity | Log Learning Activity |  | application/json | 200,422 |
