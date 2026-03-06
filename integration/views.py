from django.db import connections
from django.http import JsonResponse
from questions.models import Question, QuestionCategory
from courses.models import Course


# ------------------------------
# Test Moodle DB Connection
# ------------------------------
def test_moodle_connection(request):

    with connections['moodle'].cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

    return JsonResponse({"tables": tables})


# ------------------------------
# Sync Moodle Questions
# ------------------------------
def sync_moodle_questions(request):

    with connections['moodle'].cursor() as cursor:

        cursor.execute("""
        SELECT
            q.id,
            q.questiontext,
            qc.name
        FROM mdl_question q
        JOIN mdl_question_versions qv ON qv.questionid = q.id
        JOIN mdl_question_bank_entries qbe ON qbe.id = qv.questionbankentryid
        JOIN mdl_question_categories qc ON qc.id = qbe.questioncategoryid
        WHERE q.qtype = 'multichoice'
        LIMIT 100
        """)

        rows = cursor.fetchall()

    created = 0

    for row in rows:

        moodle_id, text, category_name = row

        # Create category
        category_obj, _ = QuestionCategory.objects.get_or_create(
            name=category_name
        )

        # Insert Question
        obj, created_flag = Question.objects.update_or_create(
            moodle_question_id=moodle_id,
            defaults={
                "question_text": text,
                "category": category_obj,
                "course": category_obj.course,
                "difficulty": "medium"
            }
        )

        if created_flag:
            created += 1

    return JsonResponse({
        "status": "question sync complete",
        "questions_added": created
    })


# ------------------------------
# Sync Moodle Courses
# ------------------------------
def sync_moodle_courses(request):

    with connections['moodle'].cursor() as cursor:

        cursor.execute("""
        SELECT id, fullname, shortname
        FROM mdl_course
        WHERE visible = 1
        """)

        rows = cursor.fetchall()

    created = 0

    for row in rows:

        moodle_id, fullname, shortname = row

        obj, created_flag = Course.objects.update_or_create(
            moodle_course_id=moodle_id,
            defaults={
                "course_name": fullname,
                "course_code": shortname
            }
        )

        if created_flag:
            created += 1

    return JsonResponse({
        "status": "course sync complete",
        "courses_added": created
    })