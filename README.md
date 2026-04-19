# AI-Education

AI-Education 是一个面向教学与学习场景的智能教育系统，当前项目已整合学生端、教师端、管理端，以及学生数字孪生、个性化学习路径、行业情报分析等核心能力。

## 技术栈

- 后端：Python + FastAPI
- 前端：Vue 3 + Vite + Element Plus
- 数据存储：SQLite
- 大模型能力：通过根目录 `.env` 配置模型服务
- 判题沙箱：go-judge（Docker）

## 核心功能

### 学生端

- 课程内容学习
- AI 助教问答
- 章节总结
- 在线测验
- 学习计划生成
- 个性化学习路径推荐
- 学生数字孪生画像展示
- 行业情报分析

### 教师端

- 班级概览
- 学生学习情况查看
- 学生趋势分析
- 知识点热力图

### 管理端

- 学生与教师信息查看
- LLM 调用日志查看

### 学生数字孪生

- 学习行为采集
- 测验成绩汇总
- 掌握度分析
- 能力雷达图
- 技术分层
- 学习风险预警
- 学习趋势跟踪

### 行业情报模块

- 岗位采集
- 岗位相关性过滤
- 技能提取
- 经验与学历要求分析
- 海内外岗位分析
- 结果持久化与恢复

## 项目结构

```text
AI-Edu/
├─ backend/                      # FastAPI 后端入口与静态资源托管
├─ frontend-vue/                 # Vue 3 前端
├─ DigitalTwinModule/            # 学生数字孪生模块
├─ PathPlannerModule/            # 个性化学习路径模块
├─ LearningPlanModule/           # 学习计划模块
├─ IndustryIntelligenceModule/   # 行业情报模块
├─ DashboardModule/              # 教师端数据看板
├─ AgentModule/                  # AI 助教
├─ QuizModule/                   # 测验模块
├─ SummaryModule/                # 总结模块
├─ DatabaseModule/               # SQLite 存储与迁移
├─ go-judge-sandbox/             # 判题沙箱 Docker 配置
├─ tools/                        # 公共工具层
├─ data/                         # 本地数据、课程资源、数据库
├─ docs/                         # 项目文档
├─ release/                      # 发布用数据库种子与副本
├─ main.py                       # 项目启动入口
└─ requirements.txt              # Python 依赖
```

## 运行环境

- Python 3.10+
- Node.js 18+
- npm 9+
- Docker Desktop（如需启用判题沙箱）
- Windows + PowerShell（当前推荐）

## 环境变量

项目使用根目录 `.env` 管理模型配置，常见字段：

- `model_name`
- `base_url`
- `api_key`
- `embedding_model`

如果模型调用异常，优先检查：

- `.env` 是否存在
- API Key 是否正确
- 模型名是否可用
- 网络是否可访问模型服务

## 本地启动（前后端）

### 1) 安装后端依赖

```powershell
pip install -r requirements.txt
```

### 2) 安装前端依赖

```powershell
cd frontend-vue
npm install
cd ..
```

### 3) 启动后端

```powershell
python main.py
```

或使用热重载：

```powershell
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

后端地址：

- http://localhost:8000/

### 4) 启动前端开发服务器

```powershell
cd frontend-vue
npm run dev
```

前端开发地址通常为：

- http://localhost:5173/

说明：

- 前端通过 Vite 代理访问后端 `/api`
- 后端未启动时，前端接口会连接失败

## Docker 判题沙箱（go-judge）

项目包含独立沙箱目录 `go-judge-sandbox`，用于作业判题的隔离执行环境。

### 1) 构建并启动

```powershell
cd go-judge-sandbox
docker compose up -d --build
```

### 2) 查看运行状态

```powershell
docker compose ps
docker compose logs -f sandbox
```

### 3) 停止并清理

```powershell
docker compose down
```

### 4) 修改 OJ 后台地址（推荐改配置文件）

OJ 判题地址统一在 `config/app_runtime.json` 中配置：

```json
{
	"oj": {
		"run_url": "http://127.0.0.1:5050/run"
	}
}
```

如果你把 OJ 部署在其他机器，修改 `oj.run_url` 即可（例如 `http://192.168.1.88:5050/run`）。

详细说明见 `docs/OJ判题与内置测试题使用说明.md`。

## 数据库初始化与团队协作

为避免团队成员本地 SQLite 数据不一致，建议统一使用种子文件。

### 1) 导出当前数据库为种子（维护者执行）

```powershell
python tools/export_db_seed.py --mode export --db data/app.db --out release/init_seed.sql
```

### 2) 从种子导入本地数据库（团队成员执行）

```powershell
python tools/export_db_seed.py --mode import --db data/app.db --out release/init_seed.sql
```

说明：

- 导入前会默认备份已有数据库到 `data/app.db.bak`
- 导入后本地库重建为统一版本

### 3) 补齐 teacher 雷达图数据

```powershell
python tools/seed_teacher_twin_data.py
```

或指定 teacher 用户名：

```powershell
python tools/seed_teacher_twin_data.py --teacher tea001
```

说明：

- 脚本仅处理现有 teacher 账号，不新增学生账号
- 默认不覆盖已存在学生 `twin_profiles`，只补缺失数据
- 如需覆盖学生画像，可加 `--overwrite-student-twins`

### 4) 协作约定

- 不提交本地运行态数据库 `data/app.db`
- 统一通过 `release/init_seed.sql` 同步初始数据
- 需要刷新 teacher 雷达图时执行 `tools/seed_teacher_twin_data.py`

## 前后端联调流程

推荐流程：

1. 启动后端：`python main.py`
2. 启动前端：`npm run dev`
3. 前端改动观察浏览器热更新
4. 后端改动观察终端日志

如果涉及接口字段改动：

1. 先改后端返回结构
2. 再改 `frontend-vue/src/api/studentTwin.ts`
3. 最后改页面展示逻辑

## 常用修改入口

### 前端页面

- `frontend-vue/src/views/student`
- `frontend-vue/src/views/teacher`
- `frontend-vue/src/views/admin`
- `frontend-vue/src/components`
- `frontend-vue/src/styles`

### 前端接口

- `frontend-vue/src/api/client.ts`
- `frontend-vue/src/api/studentTwin.ts`

### 后端接口

- `backend/app.py`
- `DigitalTwinModule/digital_twin_api.py`
- `DashboardModule/dashboard_api.py`
- `IndustryIntelligenceModule/api.py`

### 核心业务模块

- 学生数字孪生：`DigitalTwinModule`
- 个性化学习路径：`PathPlannerModule`
- 学习计划：`LearningPlanModule`
- 测验：`QuizModule`
- 总结：`SummaryModule`
- AI 助教：`AgentModule`
- 行业情报：`IndustryIntelligenceModule`
- 数据库：`DatabaseModule`
- 工具层：`tools`

## 数据存储

当前主数据采用 SQLite 本地存储：

- 数据库文件：`data/app.db`

重点表包括：

- `users`
- `sessions`
- `twin_profiles`
- `twin_history`
- `learning_plans`
- `user_states`
- `teacher_student_links`
- `llm_logs`

仍需保留的 JSON 资源：

- `data/course/big_data.json`
- `data/user_data/*/big_data.json`
- `data/user_data/*/graph.json`
- `data/Video/video_urls.json`
- `data/Book`
- `data/chroma_db`

## 修改后建议检查

### 前端构建检查

```powershell
cd frontend-vue
npm run build
```

### 后端语法检查

```powershell
python -m py_compile backend\app.py
```

## 常用文档

- 系统接口说明：`docs/系统接口说明.md`
- 数据库结构 SQL：`docs/database_schema.sql`
- 当前数据库表说明：`当前数据库表说明.md`
- OJ 判题与地址配置：`docs/OJ判题与内置测试题使用说明.md`
- 数字孪生指标与对接文档：`docs/` 目录下其他 `.md`

## 当前状态

目前项目已经完成：

- 学生端、教师端、管理端统一到 Vue 前端
- 后端统一由 FastAPI 提供接口
- 多数动态数据已切换到 SQLite 持久化
- 学习计划与学习路径已支持区分存储
- 行业情报结果支持持久化与恢复
- 学生数字孪生具备画像、趋势、路径推荐等能力

## 说明

启动与开发说明已经统一合并到本 README，根目录 `项目启动说明.md` 已删除，避免重复维护。
