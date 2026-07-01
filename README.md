# AI-Education

AI-Education is a full-stack intelligent education platform for course knowledge graph management, student learning space, personalized learning paths, student profiles, homework, quizzes, 5E learning support, teacher dashboards, and industry intelligence.

The current implementation uses:

- Backend: Python, FastAPI, MySQL
- Frontend: Vue 3, Vite, TypeScript
- Database: MySQL 8.x
- Optional AI features: OpenAI-compatible chat/completion and embedding endpoints

## Project Structure

```text
AI-Education2/
├─ main.py                         # Backend entry point
├─ backend/                        # FastAPI app and business modules
│  ├─ app.py                       # Main FastAPI application
│  ├─ DatabaseModule/              # MySQL store and database abstraction
│  ├─ DigitalTwinModule/           # Student/teacher/course twin logic
│  ├─ HomeworkModule/              # Homework and grading logic
│  ├─ PathPlannerModule/           # Personalized learning path logic
│  ├─ TeacherInterventionModule/   # Teacher intervention workflow
│  └─ tools/                       # Seed, smoke test, and maintenance scripts
├─ frontend/                       # Vue frontend
├─ database/                       # MySQL bootstrap and schema scripts
├─ docs/                           # Requirements, design docs, diagrams
└─ requirements.txt                # Python dependencies
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL 8.x
- Optional: an OpenAI-compatible model service for AI summary, quiz generation, diagnosis, path planning, and RAG features

## Environment

Create a local `.env` file from the template:

```powershell
Copy-Item .env.example .env
```

Minimum database configuration:

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

Optional AI configuration:

```env
model_name=
base_url=
api_key=
embedding_model=
```

If these AI variables are empty, pages depending on LLM calls may return fallback content or report that the model service is not configured.

## Database Setup

The database scripts are under `database/`:

- `database/init_mysql.sql`: creates the default development database and user.
- `database/schema.sql`: creates all application tables.

Initialize a local MySQL database:

```powershell
mysql -u root -p < database/init_mysql.sql
mysql -u ai_education_design -p ai_education_design < database/schema.sql
```

The backend auto-seeds the default `course_big_data` course at startup when it is missing. After the backend has started once, seed learning-center resources:

```powershell
$env:PYTHONUTF8='1'
python backend\tools\seed_learning_center_resources.py
```

For a custom course, import or publish the course graph first, then run the resource seed script with `RESOURCE_SEED_COURSE_ID`.

To disable automatic default-course seeding in shared or production environments:

```env
AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0
```

## Backend Development

Install Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the backend:

```powershell
python main.py
```

The API and production frontend host run at:

```text
http://localhost:8000/
```

Enable backend reload during development:

```powershell
$env:APP_RELOAD='1'
python main.py
```

## Frontend Development

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Start Vite:

```powershell
npm run dev
```

Default frontend dev URL:

```text
http://localhost:5173/
```

The Vite dev server proxies `/api` and `/static` to `http://127.0.0.1:8000` by default. Override it with:

```powershell
$env:VITE_DEV_API_TARGET='http://127.0.0.1:8000'
npm run dev
```

Build the frontend:

```powershell
npm run build
```

After building, the backend serves `frontend/dist`.

## Demo Accounts

If you use the default seed data, the commonly used local demo accounts are:

- Student: `zyh` / `123456`
- Teacher: `teacher` / `123456`

If the accounts are missing in a fresh database, run the smoke/seed scripts in `backend/tools/` or create accounts through the application registration/admin flow.

## Smoke Tests

Run the core business smoke test after schema or business-flow changes:

```powershell
$env:PYTHONUTF8='1'
python backend\tools\smoke_core_business.py
```

Build-check the frontend before publishing:

```powershell
cd frontend
npm run build
```

## Key Features

- Multi-role login: student, teacher, admin
- Course digital twin and knowledge graph
- Learning center with Bilibili, YouTube, CSDN, and teacher-bound resources
- YouTube precise viewing progress tracking through the official IFrame API
- Bilibili approximate learning evidence tracking through iframe open/stay/manual completion
- Personalized learning path generation and version tracking
- Student profile, diagnosis evidence, risk, trend, and weak-node analysis
- Homework assignment, submission, grading, and knowledge-point coverage
- Quiz generation and quiz evidence feedback
- Teacher intervention packages and effectiveness records
- Course runtime evaluation and teacher dashboard analytics

## Publishing Checklist

1. Make sure `.env` is not committed.
2. Update `database/schema.sql` when database structure changes.
3. Run `mysql < database/init_mysql.sql` and `mysql < database/schema.sql` on a clean database to verify initialization.
4. Run `python backend\tools\smoke_core_business.py`.
5. Run `cd frontend && npm run build`.
6. Commit only source, docs, and database scripts. Do not commit `.local/`, logs, `frontend/dist/`, `.env`, or database dumps.

## Notes

- `.env`, `.env.local`, runtime logs, local MySQL files, `frontend/dist`, and temporary output folders are ignored by Git.
- `database/schema.sql` is the release-facing schema entry. `backend/DatabaseModule/mysql_schema_clean.sql` is kept for backend module reference and should stay aligned with it when schema changes.
- For deployment behind a separate frontend domain, set `VITE_BACKEND_ORIGIN` at frontend build time and configure `CORS_ALLOW_ORIGINS` in the backend environment.
