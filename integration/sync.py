"""
Sync Functions for Moodle and TRMS databases
Stable production version
"""

import logging
import re
from django.db import connections

logger = logging.getLogger(**name**)

def clean_html(text):
"""Remove HTML tags from Moodle text"""
if not text:
return ""
return re.sub(r"<[^>]+>", "", str(text)).strip()

def get_moodle_connection():
return connections["moodle"]

def get_trms_connection():
return connections["trms"]

# ---------------------------------------------------

# COURSES SYNC

# ---------------------------------------------------

def sync_courses_from_moodle():

```
from courses.models import Course

stats = {"created": 0, "updated": 0}

with get_moodle_connection().cursor() as cursor:

    cursor.execute(
        """
        SELECT
            id,
            shortname,
            fullname,
            summary
        FROM mdl_course
        WHERE id != 1
        ORDER BY shortname
        """
    )

    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]

    for row in rows:

        data = dict(zip(cols, row))

        course, created = Course.objects.update_or_create(
            moodle_course_id=data["id"],
            defaults={
                "course_code": data["shortname"][:20],
                "course_name": data["fullname"][:200],
                "description": clean_html(data["summary"]),
                "is_active": True,
            },
        )

        if created:
            stats["created"] += 1
        else:
            stats["updated"] += 1

return stats
```

# ---------------------------------------------------

# QUIZ SYNC

# ---------------------------------------------------

def sync_quizzes_from_moodle():

```
from courses.models import Course, Quiz

stats = {"created": 0, "updated": 0}

with get_moodle_connection().cursor() as cursor:

    cursor.execute(
        """
        SELECT
            id,
            course,
            name,
            intro,
            grade,
            timelimit
        FROM mdl_quiz
        ORDER BY course
        """
    )

    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]

    for row in rows:

        data = dict(zip(cols, row))

        course = Course.objects.filter(
            moodle_course_id=data["course"]
        ).first()

        if not course:
            continue

        quiz, created = Quiz.objects.update_or_create(
            moodle_quiz_id=data["id"],
            defaults={
                "course": course,
                "quiz_name": data["name"][:300],
                "description": clean_html(data["intro"]),
                "total_marks": int(data.get("grade", 0)),
                "time_limit": int(data["timelimit"] / 60)
                if data.get("timelimit")
                else None,
                "is_active": True,
            },
        )

        if created:
            stats["created"] += 1
        else:
            stats["updated"] += 1

return stats
```

# ---------------------------------------------------

# QUESTIONS + ANSWERS SYNC

# ---------------------------------------------------

def sync_questions_from_moodle():

```
from questions.models import Question, QuestionAnswer, QuestionCategory

stats = {
    "questions_created": 0,
    "questions_updated": 0,
    "answers_created": 0,
    "errors": 0,
}

moodle_conn = get_moodle_connection()

# -------------------------
# SYNC CATEGORIES
# -------------------------

with moodle_conn.cursor() as cursor:

    cursor.execute(
        """
        SELECT
            id,
            name,
            info
        FROM mdl_question_categories
        """
    )

    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]

    category_map = {}

    for row in rows:

        data = dict(zip(cols, row))

        cat, _ = QuestionCategory.objects.update_or_create(
            moodle_category_id=data["id"],
            defaults={
                "name": data["name"][:200],
                "description": clean_html(data["info"]),
            },
        )

        category_map[data["id"]] = cat

# -------------------------
# SYNC QUESTIONS
# -------------------------

with moodle_conn.cursor() as cursor:

    cursor.execute(
        """
        SELECT
            id,
            name,
            questiontext,
            qtype,
            defaultmark
        FROM mdl_question
        WHERE hidden = 0
        AND qtype != 'random'
        """
    )

    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]

    for row in rows:

        data = dict(zip(cols, row))

        try:

            text = clean_html(data["questiontext"])

            difficulty = "medium"
            lower = data["name"].lower()

            if "easy" in lower:
                difficulty = "easy"
            elif "hard" in lower:
                difficulty = "hard"

            question, created = Question.objects.update_or_create(
                moodle_question_id=data["id"],
                defaults={
                    "question_text": text,
                    "question_type": data["qtype"],
                    "difficulty": difficulty,
                    "marks": float(data["defaultmark"]),
                    "category": None,
                    "is_active": True,
                },
            )

            if created:
                stats["questions_created"] += 1
            else:
                stats["questions_updated"] += 1

            # -------------------------
            # SYNC ANSWERS
            # -------------------------

            with moodle_conn.cursor() as a_cursor:

                a_cursor.execute(
                    """
                    SELECT
                        id,
                        answer,
                        fraction,
                        feedback
                    FROM mdl_question_answers
                    WHERE question = %s
                    """,
                    [data["id"]],
                )

                ans_rows = a_cursor.fetchall()
                a_cols = [c[0] for c in a_cursor.description]

                for ans in ans_rows:

                    ans_data = dict(zip(a_cols, ans))

                    QuestionAnswer.objects.update_or_create(
                        moodle_answer_id=ans_data["id"],
                        defaults={
                            "question": question,
                            "answer_text": clean_html(ans_data["answer"]),
                            "is_correct": float(ans_data["fraction"]) > 0,
                            "fraction": float(ans_data["fraction"]),
                            "feedback": clean_html(ans_data["feedback"]),
                        },
                    )

                    stats["answers_created"] += 1

        except Exception as e:

            logger.error(f"Question sync error {data['id']} → {e}")
            stats["errors"] += 1

return stats
```
