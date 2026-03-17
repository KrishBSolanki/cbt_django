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
# MOODLE QUIZ DB HELPERS (raw mdl_* operations)
# ---------------------------------------------------

def get_quiz_grade_item_id(cursor, quizid):
    cursor.execute(
        """
        SELECT gi.id
        FROM mdl_grade_items gi
        WHERE gi.itemmodule = 'quiz'
          AND gi.iteminstance = %s
        ORDER BY gi.id DESC
        LIMIT 1
        """,
        [int(quizid)],
    )
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def backfill_slot_grade_item_id(cursor, quizid, grade_item_id):
    if not grade_item_id:
        return
    cursor.execute(
        """
        UPDATE mdl_quiz_slots
           SET quizgradeitemid = %s
         WHERE quizid = %s
           AND (quizgradeitemid IS NULL OR quizgradeitemid = 0)
        """,
        [int(grade_item_id), int(quizid)],
    )


# def get_using_context_id(cursor, quizid):
#     cursor.execute(
#         """
#         SELECT qr.usingcontextid
#         FROM mdl_quiz_slots s
#         JOIN mdl_question_references qr
#           ON qr.itemid = s.id
#          AND qr.component = 'mod_quiz'
#          AND qr.questionarea = 'slot'
#         WHERE s.quizid = %s
#         ORDER BY qr.id DESC
#         LIMIT 1
#         """,
#         [int(quizid)],
#     )
#     row = cursor.fetchone()
#     if row and row[0]:
#         return int(row[0])

#     cursor.execute(
#         """
#         SELECT ctx.id
#         FROM mdl_course_modules cm
#         JOIN mdl_modules m ON m.id = cm.module
#         JOIN mdl_context ctx ON ctx.contextlevel = 70 AND ctx.instanceid = cm.id
#         WHERE m.name = 'quiz' AND cm.instance = %s
#         ORDER BY ctx.id DESC
#         LIMIT 1
#         """,
#         [int(quizid)],
#     )
#     row = cursor.fetchone()
#     return int(row[0]) if row else None
def get_using_context_id(cursor, quizid):

    # Try to get context from existing slot reference
    cursor.execute("""
        SELECT qr.usingcontextid
        FROM mdl_quiz_slots s
        JOIN mdl_question_references qr
            ON qr.itemid = s.id
           AND qr.component = 'mod_quiz'
           AND qr.questionarea = 'slot'
        WHERE s.quizid = %s
        LIMIT 1
    """, [int(quizid)])

    row = cursor.fetchone()
    if row and row[0]:
        return int(row[0])

    # Fallback: lookup quiz context directly
    cursor.execute("""
        SELECT ctx.id
        FROM mdl_context ctx
        JOIN mdl_course_modules cm
            ON cm.id = ctx.instanceid
        JOIN mdl_modules m
            ON m.id = cm.module
        WHERE m.name = 'quiz'
          AND cm.instance = %s
        LIMIT 1
    """, [int(quizid)])

    row = cursor.fetchone()
    return int(row[0]) if row else None

def get_questionbankentry_ids(cursor, qids):

    out = {}

    for qid in qids:

        cursor.execute("""
            SELECT
                qbe.id,
                MAX(qv.version)
            FROM mdl_question_versions qv
            JOIN mdl_question_bank_entries qbe
                ON qbe.id = qv.questionbankentryid
            WHERE qv.questionid = %s
            GROUP BY qbe.id
            LIMIT 1
        """, [int(qid)])

        row = cursor.fetchone()

        if row:
            qbe_id = int(row[0])
            version = int(row[1]) if row[1] else 1

            out[int(qid)] = (qbe_id, version)

    return out


def backfill_reference_versions(cursor, quizid):
    cursor.execute(
        """
        UPDATE mdl_question_references qr
        JOIN mdl_quiz_slots s
          ON s.id = qr.itemid
         AND s.quizid = %s
        JOIN mdl_question_versions qv
          ON qv.questionbankentryid = qr.questionbankentryid
        SET qr.version = qv.version
        WHERE qr.component = 'mod_quiz'
          AND qr.questionarea = 'slot'
          AND qr.version IS NULL
          AND qv.status = 'ready'
          AND qv.version = (
            SELECT MAX(qv2.version)
            FROM mdl_question_versions qv2
            WHERE qv2.questionbankentryid = qr.questionbankentryid
              AND qv2.status = 'ready'
          )
        """,
        [int(quizid)],
    )


# def ensure_section(cursor, quizid):
#     cursor.execute(
#         "SELECT id, firstslot FROM mdl_quiz_sections WHERE quizid = %s ORDER BY id ASC LIMIT 1",
#         [int(quizid)],
#     )
#     row = cursor.fetchone()
#     if row:
#         return
#     cursor.execute(
#         """
#         INSERT INTO mdl_quiz_sections (quizid, firstslot, heading, shufflequestions)
#         VALUES (%s, %s, %s, %s)
#         """,
#         [int(quizid), 1, '', 0],
#     )
def ensure_section(cursor, quizid):

    cursor.execute(
        "SELECT id FROM mdl_quiz_sections WHERE quizid=%s LIMIT 1",
        [int(quizid)]
    )

    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO mdl_quiz_sections
        (quizid, firstslot, heading, shufflequestions)
        VALUES (%s, 1, '', 0)
        """,
        [int(quizid)]
    )


def update_sumgrades(cursor, quizid):
    cursor.execute(
        "SELECT COALESCE(SUM(maxmark), 0) FROM mdl_quiz_slots WHERE quizid = %s",
        [int(quizid)],
    )
    total = cursor.fetchone()[0]
    cursor.execute(
        "UPDATE mdl_quiz SET sumgrades = %s WHERE id = %s",
        [total, int(quizid)],
    )


def fetch_existing_questionbankentry_ids_for_quiz(cursor, quizid):
    cursor.execute(
        """
        SELECT DISTINCT qr.questionbankentryid
        FROM mdl_quiz_slots s
        JOIN mdl_question_references qr
          ON qr.itemid = s.id
         AND qr.component = 'mod_quiz'
         AND qr.questionarea = 'slot'
        WHERE s.quizid = %s
        """,
        [int(quizid)],
    )
    return {int(r[0]) for r in cursor.fetchall() if r and r[0] is not None}


def get_next_slot(cursor, quizid):
    cursor.execute(
        "SELECT COALESCE(MAX(slot), 0) FROM mdl_quiz_slots WHERE quizid = %s",
        [int(quizid)],
    )
    return int(cursor.fetchone()[0]) + 1


# def insert_quiz_slot(cursor, quizid, slot, maxmark, grade_item_id=None, page=1, displaynumber=None, requireprevious=0):
#     displaynumber = str(displaynumber if displaynumber is not None else slot)
#     cursor.execute(
#         """
#         INSERT INTO mdl_quiz_slots (slot, quizid, page, displaynumber, requireprevious, maxmark, quizgradeitemid)
#         VALUES (%s, %s, %s, %s, %s, %s, %s)
#         """,
#         [int(slot), int(quizid), int(page), displaynumber, int(requireprevious), maxmark, int(grade_item_id) if grade_item_id else None],
#     )
#     return cursor.lastrowid
def insert_quiz_slot(cursor, quizid, slot, maxmark, grade_item_id=None, page=1, displaynumber=None, requireprevious=0):

    displaynumber = str(displaynumber if displaynumber is not None else slot)

    grade_item = int(grade_item_id) if grade_item_id else None

    cursor.execute(
        """
        INSERT INTO mdl_quiz_slots
        (slot, quizid, page, displaynumber, requireprevious, maxmark, quizgradeitemid)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        [slot, quizid, page, displaynumber, requireprevious, maxmark, grade_item]
    )

    return cursor.lastrowid


# def insert_question_reference(cursor, using_context_id, slot_id, questionbankentryid, version):
#     cursor.execute(
#         """
#         INSERT INTO mdl_question_references
#             (usingcontextid, component, questionarea, itemid, questionbankentryid, version)
#         VALUES
#             (%s, %s, %s, %s, %s, %s)
#         """,
#         [int(using_context_id), 'mod_quiz', 'slot', int(slot_id), int(questionbankentryid), int(version) if version is not None else None],
#     )
def insert_question_reference(cursor, using_context_id, slot_id, questionbankentryid, version):

    # 🔹 Ensure version is never NULL
    if version is None:

        cursor.execute("""
            SELECT MAX(version)
            FROM mdl_question_versions
            WHERE questionbankentryid = %s
        """, [int(questionbankentryid)])

        row = cursor.fetchone()

        if row and row[0]:
            version = int(row[0])
        else:
            version = 1   # safe fallback

    cursor.execute(
        """
        INSERT INTO mdl_question_references
        (usingcontextid, component, questionarea, itemid, questionbankentryid, version)
        VALUES (%s,'mod_quiz','slot',%s,%s,%s)
        """,
        [int(using_context_id), int(slot_id), int(questionbankentryid), int(version)]
    )


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


def push_questions_to_quiz(quizid, question_ids):

    """
    Push generated paper questions into Moodle quiz.
    """

    moodle_conn = get_moodle_connection()

    inserted = 0

    with moodle_conn.cursor() as cursor:

        using_context_id = get_using_context_id(cursor, quizid)

        if not using_context_id:
            raise Exception("Quiz context not found")

        grade_item_id = get_quiz_grade_item_id(cursor, quizid)

        ensure_section(cursor, quizid)

        qbe_map = get_questionbankentry_ids(cursor, question_ids)

        existing_qbe_ids = fetch_existing_questionbankentry_ids_for_quiz(cursor, quizid)

        for qid in question_ids:

            if qid not in qbe_map:
                continue

            questionbankentryid, version = qbe_map[qid]

            if questionbankentryid in existing_qbe_ids:
                continue

            slot = get_next_slot(cursor, quizid)

            slot_id = insert_quiz_slot(
                cursor,
                quizid=quizid,
                slot=slot,
                maxmark=1,
                grade_item_id=grade_item_id
            )

            insert_question_reference(
                cursor,
                using_context_id,
                slot_id,
                questionbankentryid,
                version
            )

            inserted += 1

        backfill_slot_grade_item_id(cursor, quizid, grade_item_id)

        backfill_reference_versions(cursor, quizid)

        update_sumgrades(cursor, quizid)

    logger.info(f"{inserted} questions inserted into quiz {quizid}")

    return inserted