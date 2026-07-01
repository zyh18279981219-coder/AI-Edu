# Database Assets

This directory contains the release-facing MySQL scripts for AI-Education.

## Files

- `init_mysql.sql`: creates the default database and development user.
- `schema.sql`: creates all application tables.

`schema.sql` is the main schema entry for fresh deployments. Keep it aligned with `backend/DatabaseModule/mysql_schema_clean.sql` when table structure changes.

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

## Deployment Notes

- Change the database name, username, and password before production deployment.
- Do not commit database dumps or production credentials.
- Run schema changes against a clean database before publishing.
- If you disable automatic course seed in production, set `AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=0`.
