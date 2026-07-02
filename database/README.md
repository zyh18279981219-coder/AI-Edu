# Database Assets

This directory contains the release-facing MySQL scripts for AI-Education.

## Files

- `init_mysql.sql`: creates the default database and development user.
- `schema.sql`: creates all application tables for fresh deployments.
- `migrations/`: contains versioned SQL migrations for existing databases.

`schema.sql` is the main schema entry for fresh deployments. Keep it aligned with `backend/DatabaseModule/mysql_schema_clean.sql` when table structure changes.

For existing databases, apply only migrations that have not already been run. Back up the target database first.

## Fresh Local Setup

Run these commands from the project root:

```powershell
mysql -u root -p < database/init_mysql.sql
mysql -u ai_education_design -p ai_education_design < database/schema.sql
```

Then configure `.env`:

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

The resource seed script expects course nodes to already exist. Start the backend once to let it auto-seed `course_big_data`, or import/publish your own course graph first. Then seed resources:

```powershell
$env:PYTHONUTF8='1'
python backend\tools\seed_learning_center_resources.py
```

For another course:

```powershell
$env:RESOURCE_SEED_COURSE_ID='your_course_id'
python backend\tools\seed_learning_center_resources.py
```

## Existing Database Migration

The current canonical personalized-path schema uses:

- `learning_path_versions`
- `learning_path_items`
- `learning_path_node_status`

Older databases may still store personalized paths in `learning_plans` and `learning_plan_nodes` with `category='path'`. Migrate them with:

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260701_canonical_learning_path_cleanup.sql"
```

The migration moves legacy path payloads into the canonical path tables, removes legacy path rows from `learning_plans`, drops temporary backup tables created by earlier local cleanup scripts, and removes duplicate legacy constraints/indexes.

Databases created before the multi-course learning-center change may not have course access tables. Add and seed them with:

```powershell
mysql -u ai_education_design -p ai_education_design --execute="source database/migrations/20260702_course_access_tables.sql"
```

The migration creates `course_enrollments` and `teacher_course_assignments`, then grants active access to existing published courses for current student, teacher, and admin accounts.

## Deployment Notes

- Change the database name, username, and password before production deployment.
- Do not commit database dumps or production credentials.
- Run schema changes against a clean database before publishing.
- If you disable automatic course seed in production, set `AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0`.
