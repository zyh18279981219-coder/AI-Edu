# AI-Education 智能教育平台

AI-Education 是一个面向课程知识图谱、学生画像、个性化学习路径、学习中心、作业测评、在线测验、5E 智能体、教师看板和行业能力对接的智能教育系统。

系统目标是把“课程底座建设 -> 学生学习证据 -> 学生画像与诊断 -> 个性化路径 -> 教师看板与干预 -> 结果回流”串成闭环。

## 技术栈

- 后端：Python、FastAPI、MySQL
- 前端：Vue 3、Vite、TypeScript
- 数据库：MySQL 8.x
- 可选智能能力：兼容 OpenAI 协议的对话、补全和 Embedding 服务

## 项目结构

```text
AI-Education2/
|-- main.py                         # 后端启动入口
|-- backend/                        # FastAPI 应用和业务模块
|   |-- app.py                      # 主应用与核心接口
|   |-- DatabaseModule/             # MySQL 数据访问层
|   |-- DigitalTwinModule/          # 学生/教师数字孪生与诊断
|   |-- HomeworkModule/             # 作业发布、提交与批改
|   |-- PathPlannerModule/          # 个性化学习路径
|   |-- TeacherInterventionModule/  # 教师干预任务包
|   `-- tools/                      # 初始化、种子数据、冒烟测试和维护脚本
|-- frontend/                       # Vue 前端
|-- database/                       # MySQL 初始化、权威 schema 和迁移脚本
|-- docs/                           # 需求、概要设计、详细设计和归档材料
`-- requirements.txt                # Python 依赖
```

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.x
- 可选：兼容 OpenAI 协议的模型服务，用于摘要、测验生成、诊断、路径规划和 RAG

## 环境变量

从模板创建本地环境文件：

```powershell
Copy-Item .env.example .env
```

最小数据库配置：

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

可选模型配置：

```env
model_name=
base_url=
api_key=
embedding_model=
```

如果模型配置为空，依赖 LLM 的页面会返回兜底内容或提示模型服务未配置。

## 数据库初始化

数据库脚本位于 `database/`：

- `database/init_mysql.sql`：创建默认开发库和开发用户。
- `database/schema.sql`：全量创建发布用业务表，是新库初始化的权威入口。
- `database/demo_data.sql`：发布演示数据，导入后可直接体验默认课程、知识点、资源、画像、作业、测验和教师看板数据。
- `database/migrations/`：已有数据库升级脚本。

初始化空库：

```powershell
mysql -u root -p < database/init_mysql.sql
mysql -u ai_education_design -p ai_education_design < database/schema.sql
```

导入演示数据：

```powershell
mysql -u ai_education_design -p ai_education_design < database/demo_data.sql
```

`demo_data.sql` 已排除 `sessions`、`llm_logs`、`user_activity_log` 等运行/敏感表；完整本地备份如需保留，应放在 `output/db_exports/`，不要提交到 Git。

如果是从旧版本数据库升级，需要按实际情况执行迁移：

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260701_canonical_learning_path_cleanup.sql"
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260702_course_access_tables.sql"
```

其中：

- `20260701_canonical_learning_path_cleanup.sql`：把旧的学习计划式个性化路径迁移到 `learning_path_versions`、`learning_path_items`、`learning_path_node_status`。
- `20260702_course_access_tables.sql`：补齐并初始化 `course_enrollments`、`teacher_course_assignments`，用于学习中心课程选择和教师任课范围。

后端启动时会在缺少默认课程时自动初始化 `course_big_data`。后端启动一次后，可绑定学习中心演示资源：

```powershell
$env:PYTHONUTF8='1'
python backend\tools\seed_learning_center_resources.py
```

如果要给其他课程绑定资源，先导入或发布课程图谱，再指定课程 ID：

```powershell
$env:RESOURCE_SEED_COURSE_ID='your_course_id'
python backend\tools\seed_learning_center_resources.py
```

共享或生产环境如需关闭默认课程自动初始化：

```env
AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0
```

## 后端运行

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动后端：

```powershell
python main.py
```

默认访问地址：

```text
http://localhost:8000/
```

开发时启用热重载：

```powershell
$env:APP_RELOAD='1'
python main.py
```

## 前端运行

安装前端依赖：

```powershell
cd frontend
npm install
```

启动开发服务：

```powershell
npm run dev
```

默认前端开发地址：

```text
http://localhost:5173/
```

Vite 默认把 `/api` 和 `/static` 代理到 `http://127.0.0.1:8000`。如需指定后端地址：

```powershell
$env:VITE_DEV_API_TARGET='http://127.0.0.1:8000'
npm run dev
```

构建前端：

```powershell
npm run build
```

构建完成后，后端会服务 `frontend/dist`。

## 演示账号

默认种子数据常用账号：

- 学生：`zyh` / `123456`
- 教师：`teacher` / `123456`

如果新库里账号不存在，可以运行 `backend/tools/` 下的初始化或冒烟脚本，也可以通过系统注册/管理流程创建账号。

## 核心功能

- 多角色登录：学生、教师、管理员
- 课程数字孪生、课程知识图谱和课程发布
- 学习中心按课程展示知识点、本地资源、B 站、YouTube、CSDN 和教师绑定资源
- YouTube 通过官方 IFrame API 记录播放进度和完成情况
- B 站采用 iframe 打开、停留、关闭、手动完成等近似学习行为记录
- 个性化学习路径生成、版本管理和节点状态跟踪
- 学生画像、诊断证据、薄弱知识点、风险和趋势分析
- 作业发布、提交、批改和知识点覆盖确认
- 在线测验生成、答题和测验证据回流
- 教师干预任务包和干预效果记录
- 课程运行评估、资源缺口、测评缺口和教师看板分析
- 行业岗位能力导入、能力候选、能力到叶子知识点映射和教师审核

## 测试与检查

数据库或核心业务变更后运行冒烟测试：

```powershell
$env:PYTHONUTF8='1'
python backend\tools\smoke_core_business.py
```

发布前构建前端：

```powershell
cd frontend
npm run build
```

## 发布检查

1. 确认 `.env`、日志、运行缓存和本地完整数据库 dump 没有提交。
2. 确认 `database/schema.sql` 与 `backend/DatabaseModule/mysql_schema_clean.sql` 完全一致。
3. 如果表结构变更，必须在 `database/migrations/` 下补充迁移脚本。
4. 用 `database/init_mysql.sql`、`database/schema.sql` 和 `database/demo_data.sql` 验证空库初始化与演示数据导入。
5. 运行后端冒烟测试或相关模块 pytest。
6. 运行 `cd frontend && npm run build`。
7. 只提交源码、发布脚本、数据库脚本和最新正式文档；旧文档、归档材料、图件和生成物不提交。

## 文档与 Git 规则

- 根目录只保留 `README.md` 和 `最新文档清单.md`。
- 最新正式文档保留在 `docs/requirements`、`docs/outline-design`、`docs/detailed-design` 中。
- 历史文档、草稿、图件、提示词和生成物放在 `docs/archive` 或对应本地目录，并由 `.gitignore` 忽略。
- `database/schema.sql` 是发布用数据库入口；`backend/DatabaseModule/mysql_schema_clean.sql` 是后端参考副本，两者需要保持一致。
- 部署到独立前端域名时，前端构建设置 `VITE_BACKEND_ORIGIN`，后端设置 `CORS_ALLOW_ORIGINS`。
