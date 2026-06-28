# AI-Education

`zyh` 分支用于按新需求重构项目结构与后续开发。`main` 分支保持原状，当前分支默认面向本地 MySQL 克隆库开发。

## 目录结构

```text
AI-Education2/
├─ main.py                         # 后端统一启动入口
├─ backend/                        # FastAPI 后端、智能体、业务模块、运行数据
├─ frontend/                       # Vue 前端
├─ database/                       # 本地 MySQL 表结构与调整记录
├─ docs/                           # 正式文档与图源
├─ AI-Education需求分析文档.docx
├─ AI-Education系统概要设计说明书.docx
├─ AI-Education系统详细设计说明书.docx
├─ AI-Education核心接口说明.md
└─ requirements.txt
```

## 文档维护

- 需求文档：`docs/requirements/AI-Education需求分析文档.docx`
- 概要设计：`docs/outline-design/AI-Education系统概要设计说明书.docx`
- 详细设计：`docs/detailed-design/AI-Education系统详细设计说明书.docx`
- 接口说明：`docs/detailed-design/AI-Education核心接口说明.md`
- 图源与导出：`docs/diagrams/`
- 数据库资料：`database/`

根目录保留同名交付文档副本，方便直接打开；后续修改文档时需要同步更新 `docs/` 内正式版本和根目录副本。

## 本地数据库

当前 `.env` 已切换到本地 MySQL 克隆库：

```text
DB_HOST=127.0.0.1
DB_PORT=3307
DB_USER=ai_education_design
DB_PASSWORD=ai_education_design
DB_NAME=ai_education_design
```

结构调整先在本地库完成，稳定后更新 `database/schema.sql`、概要设计和详细设计文档。

本分支已初始化一个项目本地 MySQL 运行目录：

```text
.local/mysql3307/
```

如 `3307` 未监听，可启动本地实例：

```powershell
Start-Process -FilePath "D:\develop\mysql-8.0.31-winx64\bin\mysqld.exe" -ArgumentList "--defaults-file=D:\pythonFile\AI-Education2\.local\mysql3307\my.ini" -WindowStyle Hidden
```

初始化库和导入 schema：

```powershell
& "D:\develop\mysql-8.0.31-winx64\bin\mysql.exe" --protocol=TCP --host=127.0.0.1 --port=3307 --user=root -e "CREATE DATABASE IF NOT EXISTS ai_education_design CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'ai_education_design'@'%' IDENTIFIED BY 'ai_education_design'; GRANT ALL PRIVILEGES ON ai_education_design.* TO 'ai_education_design'@'%'; FLUSH PRIVILEGES;"
cmd /c """D:\develop\mysql-8.0.31-winx64\bin\mysql.exe"" --protocol=TCP --host=127.0.0.1 --port=3307 --user=ai_education_design --password=ai_education_design ai_education_design < ""D:\pythonFile\AI-Education2\database\schema.sql"""
```

## 启动方式

后端：

```powershell
python main.py
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

前端生产构建：

```powershell
cd frontend
npm run build
```

后端会托管 `frontend/dist`，开发阶段也可以使用 Vite 代理访问后端 API。

默认开发启动会在 `course_big_data` 缺失或没有节点时，从 `backend/data/course/big_data.json` 补种并发布默认课程。共享库或生产库可设置 `AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0` 关闭该行为。

当前本地演示账号：

- 学生：`zyh` / `123456`
- 教师：`teacher` / `123456`

## 核心链路自测

数据库 schema 或核心模块改动后，先运行 smoke test：

```powershell
$env:PYTHONUTF8='1'
python backend\tools\smoke_core_business.py
```

当前 smoke test 覆盖课程图谱同步、外部资源写入、作业创建与提交、学生画像保存读取、测验作答记录回流。
