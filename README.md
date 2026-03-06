# ExamGen — University Exam Paper Generation System

A production-ready Django web application for generating randomized university lab examination question papers, integrated with Moodle and TRMS databases.

---

## 🏗️ Architecture

```
exam_paper_system/
├── accounts/          # Faculty authentication (custom user model)
├── courses/           # Courses & quizzes (synced from TRMS + Moodle)
├── questions/         # Question bank (synced from Moodle)
├── papers/            # Paper generation & export
├── integration/       # Multi-DB router + sync scripts
├── templates/         # HTML templates (Tailwind + Bootstrap 5)
└── static/            # Static assets
```

---

## 🗄️ Database Schema

### Primary Django DB (exam_paper_db)
| Table | Purpose |
|---|---|
| `dj_faculty` | Faculty users |
| `dj_courses` | Courses (synced from TRMS/Moodle) |
| `dj_course_faculty` | Faculty-Course mapping |
| `dj_quizzes` | Quizzes (synced from Moodle) |
| `dj_question_category` | Question categories |
| `dj_questions` | Question bank |
| `dj_question_answers` | Answer options |
| `dj_generated_papers` | Generated exam papers |
| `dj_paper_questions` | Questions per paper |

### External: Moodle DB (read-only)
- `mdl_course`, `mdl_quiz`, `mdl_question`, `mdl_question_answers`, `mdl_question_categories`

### External: TRMS DB (read-only)
- `trms_courses`, `trms_faculty_courses`

---

## 🚀 Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Create a `.env` file or set environment variables:
```env
# Django Database
DJ_DB_NAME=exam_paper_db
DJ_DB_USER=root
DJ_DB_PASSWORD=your_password
DJ_DB_HOST=127.0.0.1
DJ_DB_PORT=3306

# Moodle Database (read-only)
MOODLE_DB_NAME=moodle
MOODLE_DB_USER=moodle_user
MOODLE_DB_PASSWORD=moodle_pass
MOODLE_DB_HOST=127.0.0.1

# TRMS Database (read-only)
TRMS_DB_NAME=trms
TRMS_DB_USER=trms_user
TRMS_DB_PASSWORD=trms_pass
TRMS_DB_HOST=127.0.0.1
```

### 3. Create MySQL database
```sql
CREATE DATABASE exam_paper_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Run migrations
```bash
python manage.py makemigrations accounts courses questions papers
python manage.py migrate
```

### 5. Create superuser
```bash
python manage.py createsuperuser
```

### 6. Sync from external databases
```bash
# Sync all (TRMS courses + Moodle courses, quizzes, questions)
python manage.py sync_moodle_questions

# Sync specific module
python manage.py sync_moodle_questions --module trms_courses
python manage.py sync_moodle_questions --module moodle_questions
```

### 7. Run development server
```bash
python manage.py runserver
```

Visit: **http://localhost:8000**

---

## 🔗 URL Routes

| URL | Page |
|---|---|
| `/` | Redirect to dashboard or login |
| `/accounts/login/` | Faculty login |
| `/accounts/logout/` | Logout |
| `/dashboard/` | Main dashboard |
| `/courses/list/` | Course directory |
| `/courses/<id>/quiz/` | Quizzes for a course |
| `/questions/` | Question bank |
| `/questions/categories/` | Question categories |
| `/papers/generate/` | Generate paper form |
| `/papers/generated/` | Generated papers list |
| `/papers/group/<group_id>/` | View 3 paper sets |
| `/papers/detail/<paper_id>/` | Single paper detail |
| `/papers/export/<paper_id>/txt/` | Export as TXT |
| `/admin/` | Django admin |

---

## ⚡ Paper Generation Algorithm

1. Faculty selects **course**, optional **quiz**, **total questions**, and **difficulty %**
2. System calculates exact counts: `Easy = floor(total × easy%)`, etc.
3. For each set (A, B, C):
   - Randomly fetches questions per difficulty (`ORDER BY RAND()`)
   - Excludes already-used questions from previous sets
   - Combines and shuffles all questions
   - Saves `GeneratedPaper` + `PaperQuestion` records
4. All 3 sets are grouped by a `paper_group_id`

---

## 🔧 Management Commands

```bash
# Full sync
python manage.py sync_moodle_questions

# Partial sync
python manage.py sync_moodle_questions --module moodle_courses
python manage.py sync_moodle_questions --module moodle_quizzes
python manage.py sync_moodle_questions --module moodle_questions
python manage.py sync_moodle_questions --module trms_courses
```

---

## 🛡️ Security

- CSRF protection on all forms
- `@login_required` on all views
- Custom Faculty user model (email-based auth)
- Environment-based database credentials
- Read-only connections to Moodle and TRMS

---

## 🎨 UI Stack

- **Tailwind CSS** (CDN) — utility classes
- **Bootstrap 5** — components
- **Alpine.js** — reactive UI (quiz loading, difficulty preview)
- **Bootstrap Icons** — icon set
- **DM Sans + Fraunces** — typography

---

## 📦 Extending

### Add PDF export
```bash
pip install reportlab
```
Implement in `papers/views.py` → `export_paper_pdf()`.

### Add Word export
```bash
pip install python-docx
```
Implement in `papers/views.py` → `export_paper_docx()`.

### Schedule sync
Use Django management commands with cron:
```bash
# Crontab: sync every night at 2 AM
0 2 * * * /path/to/venv/bin/python manage.py sync_moodle_questions
```
