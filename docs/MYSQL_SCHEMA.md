# MySQL 数据库字段含义说明

> 适用数据库：`ai_education`（MySQL 8.0.31）
>
> 主机：`localhost:3306`
>
> 统一口径：
> - 主键以 `user_id`、`course_id` 等唯一 ID 为主
> - `username`、`teacher_username`、`student_username` 等字段保留为兼容字段或展示字段
> - 所有时间字段使用 `TIMESTAMP`，自动维护 `created_at` / `updated_at`
> - JSON 字段使用 MySQL 原生 `JSON` 类型，支持索引查询
> - 当前共 **14 张表**，数据已从 SQLite 完整迁移

---

## 1. 账号与关系

### 1.1 `users`（用户主数据）

> 当前记录数：**7 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `user_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 用户唯一数字 ID，当前用户主键 |
| `login_id` | VARCHAR(50) | UNIQUE NOT NULL | 登录账号，当前主登录键 |
| `user_type` | ENUM('student','teacher','admin') | NOT NULL, INDEX | 用户类型 |
| `username` | VARCHAR(100) | UNIQUE NOT NULL | 历史用户名，兼容旧业务字段 |
| `password` | VARCHAR(255) | NULL | 登录密码（加密存储） |
| `display_name` | VARCHAR(100) | NULL | 展示名称 |
| `teacher_id` | INT | NULL | 学生对应的教师 user_id（外键预留） |
| `email` | VARCHAR(255) | NULL | 邮箱 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 记录更新时间 |

### 1.2 `user_profiles`（用户扩展信息）

> 当前记录数：**0 条**（从 users.payload_json 规范化，待填充）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `profile_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 扩展信息唯一 ID |
| `user_id` | INT | UNIQUE, FK → users.user_id | 关联用户 ID，一对一 |
| `avatar_url` | VARCHAR(500) | NULL | 头像 URL |
| `phone` | VARCHAR(20) | NULL | 手机号 |
| `address` | TEXT | NULL | 地址 |
| `bio` | TEXT | NULL | 个人简介 |
| `preferences` | JSON | NULL | 用户偏好设置 |
| `metadata` | JSON | NULL | 其他扩展元数据 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 1.3 `teacher_student_links`（教师-学生关系）

> 当前记录数：**5 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `teacher_username` | VARCHAR(100) | PRIMARY KEY(1) | 教师历史用户名，兼容字段 |
| `student_username` | VARCHAR(100) | PRIMARY KEY(2) | 学生历史用户名，兼容字段 |
| `teacher_user_id` | INT | INDEX, FK → users.user_id | 教师 user_id |
| `student_user_id` | INT | INDEX, FK → users.user_id | 学生 user_id |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 关系更新时间 |

---

## 2. 学生数字孪生

### 2.1 `twin_profiles`（学生数字孪生主表）

> 当前记录数：**0 条**（待迁移）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `profile_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 孪生画像唯一 ID |
| `username` | VARCHAR(100) | UNIQUE NOT NULL | 学生历史用户名，兼容字段 |
| `user_id` | INT | NOT NULL, INDEX, FK → users.user_id | 学生 user_id |
| `last_updated` | TIMESTAMP | NULL | 业务侧最后更新时间 |
| `overall_mastery` | DECIMAL(5,4) | DEFAULT 0.0000 | 整体掌握度（0~1） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 2.2 `twin_profile_details`（学生数字孪生详细信息）

> 当前记录数：**0 条**（从 twin_profiles.payload_json 规范化，待填充）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `detail_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 详情唯一 ID |
| `profile_id` | INT | UNIQUE, FK → twin_profiles.profile_id | 关联孪生画像 ID，一对一 |
| `knowledge_graph` | JSON | NULL | 知识图谱掌握情况 |
| `learning_style` | JSON | NULL | 学习风格分析 |
| `strengths` | JSON | NULL | 优势节点列表 |
| `weaknesses` | JSON | NULL | 薄弱节点列表 |
| `recommendations` | JSON | NULL | 学习推荐列表 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 2.3 `twin_profile_nodes`（学生数字孪生节点明细）

> 当前记录数：**0 条**（待从 SQLite 迁移）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `node_detail_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 节点记录唯一 ID |
| `username` | VARCHAR(100) | NOT NULL, UNIQUE(username, node_id) | 学生历史用户名，兼容字段 |
| `user_id` | INT | INDEX, FK → users.user_id | 学生 user_id |
| `node_id` | VARCHAR(200) | NOT NULL | 知识点或课程节点 ID |
| `node_path_json` | JSON | NULL | 节点路径 JSON |
| `quiz_score` | DECIMAL(5,2) | NULL | 该节点测验得分 |
| `progress` | DECIMAL(5,2) | DEFAULT 0.00 | 该节点学习进度（0~1） |
| `study_duration_minutes` | DECIMAL(8,2) | DEFAULT 0.00 | 该节点学习时长（分钟） |
| `llm_interaction_count` | INT | DEFAULT 0 | 该节点 AI 交互次数 |
| `mastery_score` | DECIMAL(5,2) | DEFAULT 0.00 | 该节点掌握度（0~1） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 2.4 `twin_history`（学生数字孪生历史快照）

> 当前记录数：**98 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `history_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 历史记录唯一 ID |
| `username` | VARCHAR(100) | NOT NULL, INDEX | 学生历史用户名，兼容字段 |
| `user_id` | INT | INDEX, FK → users.user_id | 学生 user_id |
| `snapshot_date` | VARCHAR(50) | NOT NULL | 快照日期，与 username 联合唯一 |
| `overall_mastery` | DECIMAL(5,2) | DEFAULT 0.00 | 当日整体掌握度 |
| `payload_json` | JSON | NOT NULL | 当日完整历史快照 JSON |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

---

## 3. 课程数字孪生

### 3.1 `courses`（课程主数据）

> 当前记录数：**1 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `course_id` | VARCHAR(100) | PRIMARY KEY | 课程唯一 ID |
| `course_name` | VARCHAR(500) | NOT NULL, INDEX | 课程名称 |
| `source_path` | VARCHAR(1000) | NULL | 课程原始来源路径（知识图谱文件路径） |
| `description` | TEXT | NULL | 课程描述 |
| `difficulty_level` | ENUM('beginner','intermediate','advanced') | NULL | 难度等级 |
| `estimated_hours` | DECIMAL(6,2) | NULL | 预估学习时长（小时） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 3.2 `course_metadata`（课程元数据）

> 当前记录数：**2 条**（从 courses.payload_json 规范化）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `metadata_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 元数据唯一 ID |
| `course_id` | VARCHAR(100) | NOT NULL, FK → courses.course_id | 关联课程 ID |
| `prerequisites` | JSON | NULL | 前置课程要求 |
| `learning_objectives` | JSON | NULL | 学习目标列表 |
| `tags` | JSON | NULL | 课程标签 |
| `additional_data` | JSON | NULL | 其他扩展数据（含课程结构树） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 3.3 `course_nodes`（课程知识点节点）

> 当前记录数：**231 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `node_detail_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 节点记录唯一 ID |
| `course_id` | VARCHAR(100) | NOT NULL, INDEX, FK → courses.course_id | 所属课程 ID |
| `node_id` | VARCHAR(200) | NOT NULL, INDEX | 节点唯一 ID，与 course_id 联合唯一 |
| `node_name` | VARCHAR(500) | NULL | 节点名称 |
| `node_path_json` | JSON | NULL | 节点层级路径 JSON |
| `depth` | INT | DEFAULT 0 | 节点层级深度 |
| `parent_node_id` | VARCHAR(200) | NULL | 父节点 ID |
| `payload_json` | JSON | NOT NULL | 节点完整 JSON 信息 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 3.4 `resources`（课程资源）

> 当前记录数：**249 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `resource_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 资源唯一 ID |
| `course_id` | VARCHAR(100) | NOT NULL, INDEX, FK → courses.course_id | 所属课程 ID |
| `node_id` | VARCHAR(200) | NOT NULL, INDEX | 所属节点 ID |
| `resource_path` | VARCHAR(1000) | NOT NULL | 资源路径或 URL，与 course_id/node_id 联合唯一 |
| `resource_type` | VARCHAR(200) | NULL | 资源类型，如 `pdf` / `video` / `m3u8` |
| `title` | VARCHAR(500) | NULL | 资源标题 |
| `payload_json` | JSON | NOT NULL | 资源扩展信息 JSON |
| `is_deleted` | TINYINT(1) | DEFAULT 0, INDEX | 软删除标记，0=正常，1=已删除 |
| `deleted_at` | DATETIME | NULL | 软删除时间 |
| `deleted_by` | VARCHAR(100) | NULL | 执行软删除的用户名 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

---

## 4. 路径与学习计划

### 4.1 `learning_plans`（学习计划）

> 当前记录数：**38 条**（74 条中 36 条为孤立历史数据，已跳过）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `plan_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 学习计划唯一 ID |
| `username` | VARCHAR(100) | NOT NULL, INDEX | 历史用户名，兼容字段 |
| `user_id` | INT | NOT NULL, INDEX, FK → users.user_id | 用户 user_id |
| `filename` | VARCHAR(255) | NOT NULL | 计划文件名或计划标识，与 username 联合唯一 |
| `plan_path` | VARCHAR(500) | NULL | 历史计划文件路径 |
| `category` | ENUM('global','user','path') | DEFAULT 'user', INDEX | 学习计划类别 |
| `title` | VARCHAR(500) | NULL | 计划标题 |
| `description` | TEXT | NULL | 计划描述 |
| `status` | ENUM('draft','active','completed','archived') | DEFAULT 'draft', INDEX | 计划状态 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 4.2 `learning_plan_nodes`（学习计划节点）

> 当前记录数：**594 条**（从 learning_plans.payload_json 规范化）

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `node_id` | INT | PRIMARY KEY, AUTO_INCREMENT | 节点唯一 ID |
| `plan_id` | INT | NOT NULL, INDEX, FK → learning_plans.plan_id | 所属学习计划 ID |
| `node_key` | VARCHAR(100) | NOT NULL | 节点键，与 plan_id 联合唯一 |
| `node_name` | VARCHAR(500) | NULL | 节点名称（知识点名或任务主题） |
| `node_type` | VARCHAR(50) | NULL | 节点类型，如 `weak_node`（薄弱点）/ `task`（任务） |
| `sequence_order` | INT | DEFAULT 0 | 节点顺序号 |
| `parent_node_id` | INT | INDEX, FK → learning_plan_nodes.node_id | 父节点 ID（支持层级结构） |
| `mastery_score` | DECIMAL(5,2) | NULL | 该节点掌握度分数 |
| `priority` | INT | NULL | 优先级 |
| `content` | JSON | NULL | 节点内容（资源列表、截止日期等） |
| `metadata` | JSON | NULL | 节点元数据（难度、标签、前置条件等） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

---

## 5. 会话与状态

### 5.1 `sessions`（用户会话）

> 当前记录数：**163 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `session_id` | VARCHAR(255) | PRIMARY KEY | 会话唯一 ID |
| `user_id` | INT | INDEX, FK → users.user_id | 用户 user_id |
| `username` | VARCHAR(100) | NOT NULL, INDEX | 历史用户名，兼容字段 |
| `user_type` | ENUM('student','teacher','admin') | NOT NULL | 用户类型 |
| `created_at` | DATETIME | NULL | 会话创建时间 |
| `last_accessed` | DATETIME | NULL | 最后访问时间 |
| `current_pdf_path` | TEXT | NULL | 当前打开的 PDF 路径 |
| `current_node` | VARCHAR(500) | NULL | 当前所在知识节点 |
| `payload_json` | JSON | NOT NULL | 会话完整状态 JSON |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 5.2 `user_states`（用户扩展状态）

> 当前记录数：**2 条**

| 字段 | 类型 | 约束/索引 | 含义 |
|------|------|-----------|------|
| `username` | VARCHAR(100) | PRIMARY KEY | 用户名（历史主键，兼容字段） |
| `user_id` | INT | INDEX, FK → users.user_id | 用户 user_id |
| `payload_json` | JSON | NOT NULL | 用户状态数据 JSON |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

---

## 附录：表关系总览

```
users (7)
  ├── user_profiles (0)          1:1
  ├── teacher_student_links (5)  N:M（通过 teacher_user_id / student_user_id）
  ├── twin_profiles (0)          1:1
  │     ├── twin_profile_details (0)  1:1
  │     └── twin_profile_nodes (0)    1:N（节点明细，username 关联）
  ├── twin_history (98)          1:N
  ├── sessions (163)             1:N
  ├── user_states (2)            1:N
  └── learning_plans (38)        1:N
        └── learning_plan_nodes (594)  1:N（支持自引用层级）

courses (1)
  ├── course_metadata (2)        1:N
  ├── course_nodes (231)         1:N
  └── resources (249)            1:N
```

## 附录：与 SQLite 的差异

| 项目 | SQLite（旧） | MySQL（新） |
|------|------------|------------|
| JSON 字段 | TEXT 存储 | 原生 JSON 类型 |
| 时间字段 | TEXT（ISO 字符串） | TIMESTAMP（自动维护） |
| 自增主键 | INTEGER PRIMARY KEY | INT AUTO_INCREMENT |
| 外键约束 | 默认关闭 | 强制执行 |
| 字符集 | 默认 | utf8mb4（支持 emoji） |
| 并发支持 | 单写多读 | 多写多读（InnoDB） |
| 规范化 | payload_json 存全量 | 拆分到独立表 |
