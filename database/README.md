# 数据库发布资产

本目录保存 AI-Education 的 MySQL 初始化、发布 schema、演示数据和版本迁移脚本。

## 文件说明

- `init_mysql.sql`：创建默认开发数据库和开发用户。
- `schema.sql`：全量创建业务表，是新库初始化的权威入口。
- `demo_data.sql`：发布演示数据，导入后可直接体验默认课程、知识点、资源、学生画像、个性化路径、作业、测验、学习行为和教师看板数据。
- `migrations/`：已有数据库的增量迁移脚本。

`schema.sql` 需要和 `backend/DatabaseModule/mysql_schema_clean.sql` 保持一致。表结构变更时，先更新权威 schema，再补充迁移脚本。

## 空库初始化

在项目根目录执行：

```powershell
mysql -u root -p < database/init_mysql.sql
mysql -u ai_education_design -p ai_education_design < database/schema.sql
```

导入演示数据：

```powershell
mysql -u ai_education_design -p ai_education_design < database/demo_data.sql
```

然后配置 `.env`：

```env
DB_TYPE=mysql
DB_HOST=113.44.141.150
DB_PORT=3306
DB_USER=zyh
DB_PASSWORD=填写共享数据库密码
DB_NAME=dev20260912
DB_CHARSET=utf8mb4
DB_AUTO_MIGRATE=0
AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0
```

`demo_data.sql` 已排除 `sessions`、`llm_logs`、`user_activity_log` 等运行/敏感表。完整本地备份应放在 `output/db_exports/`，不要提交到 Git。

## 2026-10-08 共享数据库切换

课程与教师端采用本地版本，5E 采用服务器的智能体与提示词。所有模块读取同一组 `DB_*`，5E 的 ADK 会话使用 `fivee_*` 表，避免与网站登录表冲突。

切换前由管理员在 `dev20260912` 执行 `migrations/20261008_shared_runtime_tables.sql`。也可临时授予应用账号该库的 `CREATE, REFERENCES` 权限，由维护者完成建表；已有业务表和数据不删除。业务库保持 `DB_AUTO_MIGRATE=0`，关闭启动时自动修改表结构和默认课程种子。

停用旧服务的写入后，用 SQLite backup API 保存服务器 `data/fivee_sessions.db` 的一致性快照，再执行：

```powershell
python backend/tools/migrate_fivee_sqlite.py /path/to/fivee_sessions_snapshot.db
```

迁移保留会话、状态、事件 ID 与时间；重复迁移只接受内容完全相同的主键记录，冲突时回滚。完成 MySQL 会话读写、历史读取和实际对话测试后再切换线上服务。旧项目、环境配置、SQLite 与旧 MySQL 保留用于回退。

当前共享库的 `quiz_questions` 为历史表结构，与新库初始化模板不同；现有课程测验定义通过 `user_states` 持久化，不在本次切换中替换历史题库表。

## 资源种子

如果不导入 `demo_data.sql`，资源种子脚本要求课程节点已存在。可以先启动后端，让系统自动初始化默认课程 `course_big_data`，再执行：

```powershell
$env:PYTHONUTF8='1'
python backend\tools\seed_learning_center_resources.py
```

如需给其他课程绑定资源：

```powershell
$env:RESOURCE_SEED_COURSE_ID='your_course_id'
python backend\tools\seed_learning_center_resources.py
```

## 旧库迁移

当前个性化学习路径的权威表为：

- `learning_path_versions`
- `learning_path_items`
- `learning_path_node_status`

旧库如果仍把个性化路径放在 `learning_plans`、`learning_plan_nodes` 且 `category='path'`，执行：

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260701_canonical_learning_path_cleanup.sql"
```

该迁移会把旧路径载荷迁移到权威路径表，清理旧路径记录、临时备份表和重复约束/索引。

旧库如果缺少多课程学习中心访问控制表，执行：

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260702_course_access_tables.sql"
```

该迁移会创建 `course_enrollments` 和 `teacher_course_assignments`，并为已有学生、教师和管理员补齐已发布课程访问关系。

旧库如果需要补齐 12 个模块数据审查确认的候选资源、测验定义、行业任务、代码题评测、诊断规则、教师画像指标、大模型日志统计和课程发布快照等表字段，执行：

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260702_module_data_support_tables.sql"
```

该迁移只补充表结构和可重复执行的字段，不会清理已有业务数据。

## 发布注意

- 生产部署前必须修改数据库名、用户名和密码。
- 不提交 `.env`、生产凭据、本地完整 dump、日志和运行缓存。
- 表结构变更后，必须用干净数据库验证 `schema.sql`。
- 如果生产环境不希望自动初始化默认课程，设置 `AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0`。
