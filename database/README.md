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
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=ai_education_design
DB_PASSWORD=ai_education_design
DB_NAME=ai_education_design
DB_CHARSET=utf8mb4
DB_AUTO_MIGRATE=0
```

`demo_data.sql` 已排除 `sessions`、`llm_logs`、`user_activity_log` 等运行/敏感表。完整本地备份应放在 `output/db_exports/`，不要提交到 Git。

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
