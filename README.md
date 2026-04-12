# AI-Education

AI-Education 是一个面向教学与学习场景的智能教育系统，当前项目已经整合了学生端、教师端、管理端，以及学生数字孪生、个性化学习路径、行业情报分析等核心能力。

项目目前采用：

- 后端：Python + FastAPI
- 前端：Vue 3 + Vite + Element Plus
- 数据存储：SQLite
- 大模型能力：通过 `.env` 中配置的模型服务调用

## 核心功能

### 1. 学生端

- 课程内容学习
- AI 助教问答
- 章节总结
- 在线测验
- 学习计划生成
- 个性化学习路径推荐
- 学生数字孪生画像展示
- 行业情报分析

### 2. 教师端

- 班级概览
- 学生学习情况查看
- 学生趋势分析
- 知识点热力图

### 3. 管理端

- 学生与教师信息查看
- LLM 调用日志查看

### 4. 学生数字孪生

- 学习行为采集
- 测验成绩汇总
- 掌握度分析
- 能力雷达图
- 技术分层
- 学习风险预警
- 学习趋势跟踪

### 5. 行业情报模块

- 岗位采集
- 岗位相关性过滤
- 技能提取
- 经验与学历要求分析
- 海内外岗位分析
- 结果持久化与恢复

## 项目结构

```text
AI-Education2/
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
├─ tools/                        # 公共工具层
├─ data/                         # 本地数据、课程资源、数据库
├─ docs/                         # 项目文档
├─ release/                      # 发布用数据库副本
├─ main.py                       # 项目启动入口
└─ requirements.txt              # Python 依赖
```

## 本地启动

### 1. 安装后端依赖

```powershell
cd D:\develop\pythonFile\AI-Education2
pip install -r requirements.txt
```

### 2. 安装前端依赖

```powershell
cd D:\develop\pythonFile\AI-Education2\frontend-vue
npm install
```

### 3. 启动后端

```powershell
cd D:\develop\pythonFile\AI-Education2
python main.py
```

启动后访问：

- [http://localhost:8000/](http://localhost:8000/)

### 4. 启动前端开发模式

```powershell
cd D:\develop\pythonFile\AI-Education2\frontend-vue
npm run dev
```

前端开发地址通常为：

- [http://localhost:5173/](http://localhost:5173/)


### 5. 数据库初始化（数据库的导入导出）
#### 5.1 从原始种子导入本地数据库(团队成员执行)
拉取代码时运行：将文件内容输入本地数据库
```powershell
cd D:\develop\pythonFile\AI-Education2
python tools/export_db_seed.py --mode import --db data/app.db --out release/init_seed.sql
```

#### 5.2 导出当前数据库为原始种子(维护者执行)
这个在你改了数据库要发布到远程仓库的时候先执行
```powershell
cd D:\develop\pythonFile\AI-Education2
python tools/export_db_seed.py --mode export --db data/app.db --out release/init_seed.sql
```

## 运行依赖说明

项目使用根目录下的 `.env` 管理模型配置，常见字段包括：

- `model_name`
- `base_url`
- `api_key`
- `embedding_model`

如果大模型不可用，可先检查：

- `.env` 是否存在
- API Key 是否正确
- 模型名是否可用
- 网络是否可以访问模型服务

## 数据存储

当前系统主要采用 SQLite 本地存储。

数据库文件：

- [data/app.db](/D:/develop/pythonFile/AI-Education2/data/app.db)

发布数据库副本：

- [release/app_release.db](/D:/develop/pythonFile/AI-Education2/release/app_release.db)



主要表包括：

- `users`
- `sessions`
- `twin_profiles`
- `twin_history`
- `learning_plans`
- `user_states`
- `teacher_student_links`
- `llm_logs`

## 常用开发入口

如果你要继续修改项目，最常用的目录是：

- 前端页面：`frontend-vue/src/views`
- 前端接口：`frontend-vue/src/api`
- 后端主接口：`backend/app.py`
- 学生数字孪生：`DigitalTwinModule`
- 个性化学习路径：`PathPlannerModule`
- 行业情报：`IndustryIntelligenceModule`
- 数据库存储：`DatabaseModule`

## 常用文档

- 项目启动与修改说明：[docs/项目启动说明.md](/D:/develop/pythonFile/AI-Education2/docs/项目启动说明.md)
- 系统接口说明：[docs/系统接口说明.md](/D:/develop/pythonFile/AI-Education2/docs/系统接口说明.md)
- 数据库结构 SQL：[docs/database_schema.sql](/D:/develop/pythonFile/AI-Education2/docs/database_schema.sql)
- 当前数据库表说明：[当前数据库表说明.md](/D:/develop/pythonFile/AI-Education2/当前数据库表说明.md)

## 当前状态说明

目前项目已经完成了以下方向的整合与改造：

- 学生端、教师端、管理端统一到 Vue 前端
- 后端统一由 FastAPI 提供接口
- 多数动态数据已切换到 SQLite 持久化
- 学习计划与学习路径已支持区分存储
- 行业情报结果支持持久化与恢复
- 学生数字孪生具备画像、趋势、路径推荐等能力

## 备注

如果你是项目维护者，建议优先阅读：

1. `README.md`
2. `docs/项目启动说明.md`
3. `docs/系统接口说明.md`
4. `当前数据库表说明.md`

这样就能较快接手当前项目结构。
