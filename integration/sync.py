# """
# Sync Functions for Moodle and TRMS databases
# Stable production version
# """

# import logging
# import re
# from django.db import connections
# from django.db.utils import OperationalError

# logger = logging.getLogger(__name__)

# # ---------------------------------------------------

# # UTILITY FUNCTIONS

# # ---------------------------------------------------

# def clean_html(text):
#     """Remove HTML tags from Moodle text"""
#     if not text:
#         return ""
#     return re.sub(r"<[^>]+>", "", str(text)).strip()

# def get_moodle_connection():
#     return connections["moodle"]

# def get_trms_connection():
#     return connections["trms"]

# # ---------------------------------------------------

# # COURSES SYNC

# # ---------------------------------------------------

# def sync_courses_from_moodle():
#     from courses.models import Course

#     stats = {"created": 0, "updated": 0}

#     with get_moodle_connection().cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT
#                 id,
#                 shortname,
#                 fullname,
#                 summary
#             FROM mdl_course
#             WHERE id != 1
#             ORDER BY shortname
#             """
#         )

#         rows = cursor.fetchall()
#         cols = [c[0] for c in cursor.description]

#         for row in rows:
#             data = dict(zip(cols, row))

#             course, created = Course.objects.update_or_create(
#                 moodle_course_id=data["id"],
#                 defaults={
#                     "course_code": (data["shortname"] or "")[:50],
#                     "course_name": (data["fullname"] or "")[:255],
#                     "department": clean_html(data["summary"])[:128] or "CSE",
#                     "is_active": True,
#                 },
#             )

#             if created:
#                 stats["created"] += 1
#             else:
#                 stats["updated"] += 1

#     logger.info(f"Courses Sync → {stats}")
#     return stats


# # ---------------------------------------------------

# # QUIZ SYNC

# # ---------------------------------------------------

# def sync_quizzes_from_moodle():
#     from courses.models import Course, Quiz

#     stats = {"created": 0, "updated": 0}

#     with get_moodle_connection().cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT
#                 id,
#                 course,
#                 name,
#                 intro,
#                 grade,
#                 timelimit
#             FROM mdl_quiz
#             ORDER BY course
#             """
#         )

#         rows = cursor.fetchall()
#         cols = [c[0] for c in cursor.description]

#         for row in rows:
#             data = dict(zip(cols, row))

#             course = Course.objects.filter(moodle_course_id=data["course"]).first()

#             if not course:
#                 continue

#             quiz, created = Quiz.objects.update_or_create(
#                 moodle_quiz_id=data["id"],
#                 defaults={
#                     "course": course,
#                     "quiz_name": (data["name"] or "")[:255],
#                     "description": clean_html(data["intro"]),
#                     "total_questions": 0,
#                     "duration_minutes": int(data["timelimit"] / 60) if data.get("timelimit") else 0,
#                     "is_active": True,
#                 },
#             )

#             if created:
#                 stats["created"] += 1
#             else:
#                 stats["updated"] += 1

#     logger.info(f"Quiz Sync → {stats}")
#     return stats

# # ---------------------------------------------------

# # QUESTIONS + ANSWERS SYNC

# # ---------------------------------------------------

# def sync_questions_from_moodle():
#     from questions.models import Question, QuestionCategory

#     stats = {
#         "questions_created": 0,
#         "questions_updated": 0,
#         "answers_created": 0,
#         "errors": 0,
#     }

#     moodle_conn = get_moodle_connection()

#     # -------------------------
#     # SYNC CATEGORIES
#     # -------------------------

#     category_map = {}

#     with moodle_conn.cursor() as cursor:
#         cursor.execute(
#             """
#             SELECT
#                 qc.id AS id,
#                 qc.name AS name,
#                 course_ctx.instanceid AS courseid
#             FROM mdl_question_categories qc
#             LEFT JOIN mdl_context cat_ctx
#                 ON cat_ctx.id = qc.contextid
#             LEFT JOIN mdl_context course_ctx
#                 ON course_ctx.contextlevel = 50
#                 AND (
#                     cat_ctx.path LIKE CONCAT('%/', course_ctx.id, '/%')
#                     OR cat_ctx.path LIKE CONCAT('%/', course_ctx.id)
#                 )
#             """
#         )

#         rows = cursor.fetchall()
#         cols = [c[0] for c in cursor.description]

#         for row in rows:
#             data = dict(zip(cols, row))

#             name = (data.get("name") or "")[:255]
#             lower = name.lower()
#             difficulty = "medium"
#             if "easy" in lower:
#                 difficulty = "easy"
#             elif "hard" in lower:
#                 difficulty = "hard"

#             cat, _ = QuestionCategory.objects.update_or_create(
#                 moodle_category_id=data["id"],
#                 defaults={
#                     "name": name,
#                     "difficulty": difficulty,
#                 },
#             )

#             category_map[data["id"]] = {
#                 "obj": cat,
#                 "courseid": data.get("courseid"),
#             }

#     # -------------------------
#     # SYNC QUESTIONS
#     # -------------------------

#     answer_col = None
#     feedback_col = None
#     with moodle_conn.cursor() as a_schema_cursor:
#         a_schema_cursor.execute("SHOW COLUMNS FROM mdl_question_answers")
#         answer_table_cols = {r[0] for r in a_schema_cursor.fetchall()}

#     if "answer" in answer_table_cols:
#         answer_col = "answer"
#     elif "answertext" in answer_table_cols:
#         answer_col = "answertext"

#     if "feedback" in answer_table_cols:
#         feedback_col = "feedback"

#     with moodle_conn.cursor() as cursor:
#         category_col = "category"
#         try:
#             cursor.execute(
#                 """
#                 SELECT
#                     id,
#                     name,
#                     questiontext,
#                     qtype,
#                     defaultmark,
#                     category
#                 FROM mdl_question
#                 AND qtype != 'random'
#                 """
#             )
#         except Exception:
#             try:
#                 category_col = "categoryid"
#                 cursor.execute(
#                     """
#                     SELECT
#                         id,
#                         name,
#                         questiontext,
#                         qtype,
#                         defaultmark,
#                         categoryid
#                     FROM mdl_question
#                     WHERE parent = 0
#                     AND qtype != 'random'
#                     """
#                 )
#             except Exception:
#                 try:
#                     category_col = "category_id"
#                     cursor.execute(
#                         """
#                         SELECT
#                             id,
#                             name,
#                             questiontext,
#                             qtype,
#                             defaultmark,
#                             category_id
#                         FROM mdl_question
#                         WHERE parent = 0
#                         AND qtype != 'random'
#                         """
#                     )
#                 except Exception:
#                     category_col = "categoryid"
#                     cursor.execute(
#                         """
#                         SELECT
#                             q.id AS id,
#                             q.name AS name,
#                             q.questiontext AS questiontext,
#                             q.qtype AS qtype,
#                             q.defaultmark AS defaultmark,
#                             qbe.questioncategoryid AS categoryid
#                         FROM mdl_question q
#                         JOIN mdl_question_versions qv
#                             ON qv.questionid = q.id
#                         JOIN mdl_question_bank_entries qbe
#                             ON qbe.id = qv.questionbankentryid
#                         WHERE qv.status = 'ready'
#                         AND q.qtype != 'random'
#                         """
#                     )

#         rows = cursor.fetchall()
#         cols = [c[0] for c in cursor.description]

#         for row in rows:
#             data = dict(zip(cols, row))

#             try:
#                 text = clean_html(data["questiontext"])

#                 difficulty = "medium"
#                 lower = (data["name"] or "").lower()
#                 if "easy" in lower:
#                     difficulty = "easy"
#                 elif "hard" in lower:
#                     difficulty = "hard"

#                 category_id = data.get(category_col)
#                 cat_entry = category_map.get(category_id)
#                 category_obj = cat_entry["obj"] if cat_entry else None
#                 moodle_course_id = cat_entry.get("courseid") if cat_entry else None

#                 if not moodle_course_id:
#                     continue

#                 from courses.models import Course

#                 course = Course.objects.filter(moodle_course_id=moodle_course_id).first()
#                 if not course:
#                     continue

#                 answers_payload = []
#                 with moodle_conn.cursor() as a_cursor:
#                     if answer_col:
#                         feedback_select = feedback_col if feedback_col else "NULL"
#                         a_cursor.execute(
#                             f"""
#                             SELECT
#                                 id,
#                                 {answer_col} AS answer,
#                                 fraction,
#                                 {feedback_select} AS feedback
#                             FROM mdl_question_answers
#                             WHERE question = %s
#                             """,
#                             [data["id"]],
#                         )
#                     else:
#                         a_cursor.execute(
#                             """
#                             SELECT
#                                 id,
#                                 NULL AS answer,
#                                 fraction,
#                                 NULL AS feedback
#                             FROM mdl_question_answers
#                             WHERE question = %s
#                             """,
#                             [data["id"]],
#                         )

#                     ans_rows = a_cursor.fetchall()
#                     a_cols = [c[0] for c in a_cursor.description]

#                     for ans in ans_rows:
#                         ans_data = dict(zip(a_cols, ans))
#                         fraction = float(ans_data.get("fraction") or 0)
#                         answers_payload.append(
#                             {
#                                 "moodle_answer_id": ans_data.get("id"),
#                                 "answer_text": clean_html(ans_data.get("answer")),
#                                 "fraction": fraction,
#                                 "is_correct": fraction > 0,
#                                 "feedback": clean_html(ans_data.get("feedback")),
#                             }
#                         )

#                 question, created = Question.objects.update_or_create(
#                     moodle_question_id=data["id"],
#                     defaults={
#                         "course": course,
#                         "quiz": None,
#                         "category": category_obj,
#                         "question_text": text,
#                         "question_type": data["qtype"],
#                         "difficulty": difficulty,
#                         "marks": float(data["defaultmark"] or 1),
#                         "answer_data": answers_payload,
#                         "is_active": True,
#                     },
#                 )

#                 if created:
#                     stats["questions_created"] += 1
#                 else:
#                     stats["questions_updated"] += 1

#                 stats["answers_created"] += len(answers_payload)

#             except Exception as e:
#                 logger.error(f"Question sync error {data['id']} → {e}")
#                 stats["errors"] += 1

#     logger.info(f"Question Sync → {stats}")
#     return stats
"""
Sync Functions for Moodle and TRMS databases
Clean Moodle 5.x compatible version
"""

import logging
import re
from django.db import connections

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------

def clean_html(text):
    """Remove HTML tags from Moodle text"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).strip()


def get_moodle_connection():
    return connections["moodle"]


# ---------------------------------------------------
# COURSES SYNC
# ---------------------------------------------------

def sync_courses_from_moodle():
    from courses.models import Course

    stats = {"created": 0, "updated": 0}

    with get_moodle_connection().cursor() as cursor:
        cursor.execute("""
            SELECT id, shortname, fullname, summary
            FROM mdl_course
            WHERE id != 1
            ORDER BY shortname
        """)

        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

        for row in rows:
            data = dict(zip(cols, row))

            course, created = Course.objects.update_or_create(
                moodle_course_id=data["id"],
                defaults={
                    "course_code": (data["shortname"] or "")[:50],
                    "course_name": (data["fullname"] or "")[:255],
                    "department": clean_html(data["summary"])[:128] or "General",
                    "is_active": True,
                },
            )

            if created:
                stats["created"] += 1
            else:
                stats["updated"] += 1

    logger.info(f"Courses Sync → {stats}")
    return stats


# ---------------------------------------------------
# QUIZ SYNC
# ---------------------------------------------------

def sync_quizzes_from_moodle():
    from courses.models import Course, Quiz

    stats = {"created": 0, "updated": 0}

    with get_moodle_connection().cursor() as cursor:
        cursor.execute("""
            SELECT id, course, name, intro, timelimit
            FROM mdl_quiz
            ORDER BY course
        """)

        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

        for row in rows:
            data = dict(zip(cols, row))

            course = Course.objects.filter(moodle_course_id=data["course"]).first()

            if not course:
                continue

            quiz, created = Quiz.objects.update_or_create(
                moodle_quiz_id=data["id"],
                defaults={
                    "course": course,
                    "quiz_name": data["name"][:255],
                    "description": clean_html(data["intro"]),
                    "duration_minutes": int(data["timelimit"] / 60) if data["timelimit"] else 0,
                    "total_questions": 0,
                    "is_active": True,
                },
            )

            if created:
                stats["created"] += 1
            else:
                stats["updated"] += 1

    logger.info(f"Quiz Sync → {stats}")
    return stats


# ---------------------------------------------------
# QUESTIONS + ANSWERS SYNC
# ---------------------------------------------------

def sync_questions_from_moodle():
    from questions.models import Question, QuestionCategory
    from courses.models import Course

    stats = {
        "questions_created": 0,
        "questions_updated": 0,
        "answers_created": 0,
        "errors": 0,
    }

    moodle_conn = get_moodle_connection()

    # ---------------------------------------------------
    # SYNC QUESTION CATEGORIES
    # ---------------------------------------------------

    category_map = {}

    with moodle_conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM mdl_question_categories
        """)

        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

        for row in rows:
            data = dict(zip(cols, row))

            name = data["name"][:255]
            lower = name.lower()

            difficulty = "medium"

            if "easy" in lower:
                difficulty = "easy"
            elif "hard" in lower:
                difficulty = "hard"

            category, _ = QuestionCategory.objects.update_or_create(
                moodle_category_id=data["id"],
                defaults={
                    "name": name,
                    "difficulty": difficulty
                }
            )

            category_map[data["id"]] = category

    # ---------------------------------------------------
    # SYNC QUESTIONS
    # ---------------------------------------------------

    with moodle_conn.cursor() as cursor:

        cursor.execute("""
            SELECT
                q.id,
                q.name,
                q.questiontext,
                q.qtype,
                q.defaultmark,
                qbe.questioncategoryid AS categoryid
            FROM mdl_question q
            JOIN mdl_question_versions qv
                ON qv.questionid = q.id
            JOIN mdl_question_bank_entries qbe
                ON qbe.id = qv.questionbankentryid
            WHERE qv.status = 'ready'
            AND q.qtype != 'random'
        """)

        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

        for row in rows:
            data = dict(zip(cols, row))

            try:
                category_obj = category_map.get(data["categoryid"])

                difficulty = "medium"
                if category_obj:
                    difficulty = category_obj.difficulty

                course = Course.objects.first()
                if not course:
                    continue

                # -------------------------
                # FETCH ANSWERS
                # -------------------------

                answers_payload = []

                with moodle_conn.cursor() as a_cursor:
                    a_cursor.execute("""
                        SELECT id, answer, fraction, feedback
                        FROM mdl_question_answers
                        WHERE question = %s
                    """, [data["id"]])

                    ans_rows = a_cursor.fetchall()
                    a_cols = [c[0] for c in a_cursor.description]

                    for ans in ans_rows:
                        ans_data = dict(zip(a_cols, ans))

                        fraction = float(ans_data.get("fraction") or 0)

                        answers_payload.append({
                            "moodle_answer_id": ans_data["id"],
                            "answer_text": clean_html(ans_data["answer"]),
                            "fraction": fraction,
                            "is_correct": fraction > 0,
                            "feedback": clean_html(ans_data.get("feedback")),
                        })

                question, created = Question.objects.update_or_create(
                    moodle_question_id=data["id"],
                    defaults={
                        "course": course,
                        "quiz": None,
                        "category": category_obj,
                        "question_text": clean_html(data["questiontext"]),
                        "question_type": data["qtype"],
                        "difficulty": difficulty,
                        "marks": float(data["defaultmark"] or 1),
                        "answer_data": answers_payload,
                        "is_active": True,
                    },
                )

                if created:
                    stats["questions_created"] += 1
                else:
                    stats["questions_updated"] += 1

                stats["answers_created"] += len(answers_payload)

            except Exception as e:
                logger.error(f"Question sync error {data['id']} → {e}")
                stats["errors"] += 1

    logger.info(f"Question Sync → {stats}")
    return stats