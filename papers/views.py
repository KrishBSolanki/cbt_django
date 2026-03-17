"""
Papers Views - Paper Generation and Preview
"""
import json
import io
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import connections, transaction

from papers.models import GeneratedPaper, PaperQuestion
from papers.generator import generate_three_paper_sets
from courses.models import Course, Quiz
from questions.models import Question
from integration.sync import (
    backfill_reference_versions,
    backfill_slot_grade_item_id,
    ensure_section,
    fetch_existing_questionbankentry_ids_for_quiz,
    get_next_slot,
    get_questionbankentry_ids,
    get_quiz_grade_item_id,
    get_using_context_id,
    insert_question_reference,
    insert_quiz_slot,
    update_sumgrades,
)


@method_decorator(login_required, name='dispatch')
class GeneratePaperView(View):
    template_name = 'papers/generate.html'

    def get(self, request):
        cs_id = request.GET.get('cs_id')
        exam_id = request.GET.get('exam_id')
        subject_id = request.GET.get('subject_id')
        trms_flag = (request.GET.get('trms') or '').strip()

        trms_mode = bool(cs_id or exam_id or subject_id or trms_flag)

        if trms_mode:
            trms_courses = []
            trms_exams = []
            exam_meta = None
            moodle_categories = []

            with connections['trms'].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, course_name
                    FROM zrtiudp.courses
                    ORDER BY course_name ASC
                    """
                )
                trms_courses = cursor.fetchall()

                if cs_id:
                    cursor.execute(
                        """
                        SELECT
                            ed.id,
                            ed.cs_id,
                            ed.subject_id,
                            ed.type_sort,
                            s.subject_name,
                            s.subject_type,
                            s.total_mark,
                            s.mark,
                            s.weightage
                        FROM zrtiudp.exam_design ed
                        JOIN zrtiudp.subjects s ON s.id = ed.subject_id
                        WHERE ed.cs_id = %s
                        AND ed.status = 1
                        AND s.subject_type IN (2,3)
                        AND s.status = 1
                        ORDER BY s.subject_name ASC, ed.id ASC
                        """,
                        [cs_id]
                    )

                    rows = cursor.fetchall()
                    trms_exams = [
                        {
                            'id': r[0],
                            'cs_id': r[1],
                            'subject_id': r[2],
                            'exam_type': r[3],
                            'subject_name': r[4],
                            'subject_type': r[5],
                            'total_marks': r[6],
                            'min_marks': r[7],
                            'weightage': r[8],
                        }
                        for r in rows
                    ]

                if exam_id:
                    cursor.execute(
                        """
                        SELECT
                            s.total_mark,
                            s.mark,
                            s.weightage
                        FROM zrtiudp.exam_design ed
                        JOIN zrtiudp.subjects s ON s.id = ed.subject_id
                        WHERE ed.id = %s
                        """,
                        [exam_id]
                    )
                    row = cursor.fetchone()
                    if row:
                        exam_meta = {
                            'total': row[0],
                            'min': row[1],
                            'weight': row[2],
                        }

            moodle_categories = []
            try:
                moodle = connections['moodle']
                with moodle.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, parent
                        FROM mdl_question_categories
                        ORDER BY name
                        """
                    )
                    rows = cursor.fetchall()

                categories_by_id = {r[0]: {'id': r[0], 'name': r[1], 'parent': r[2]} for r in rows}
                children_by_parent = {}
                for r in rows:
                    cat_id, _name, parent_id = r
                    children_by_parent.setdefault(parent_id, []).append(cat_id)

                def _flatten(parent_id, depth):
                    flat = []
                    for child_id in sorted(children_by_parent.get(parent_id, []), key=lambda cid: categories_by_id[cid]['name'].lower()):
                        c = categories_by_id[child_id]
                        flat.append(
                            {
                                'id': c['id'],
                                'name': c['name'],
                                'depth': depth,
                                'is_selectable': c['parent'] != 0,
                            }
                        )
                        flat.extend(_flatten(child_id, depth + 1))
                    return flat

                moodle_categories = _flatten(0, 0)
            except Exception as e:
                # Moodle connection failed - log but continue with empty categories
                print(f"WARNING: Moodle connection failed: {e}")
                moodle_categories = []

            return render(
                request,
                self.template_name,
                {
                    'active_page': 'generate',
                    'trms_mode': True,
                    'trms_courses': trms_courses,
                    'trms_exams': trms_exams,
                    'selected_cs_id': cs_id,
                    'selected_exam_id': exam_id,
                    'selected_subject_id': subject_id,
                    'exam_meta': exam_meta,
                    'moodle_categories': moodle_categories,
                    'courses': Course.objects.filter(is_active=True).order_by('course_code'),
                }
            )

        courses = Course.objects.filter(is_active=True).order_by('course_code')
        context = {
            'courses': courses,
            'active_page': 'generate',
            'trms_mode': False,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        course_id = request.POST.get('course_id')
        quiz_id = request.POST.get('quiz_id', '')
        total_questions = int(request.POST.get('total_questions', 30))
        easy_pct = int(request.POST.get('easy_pct', 0))
        medium_pct = int(request.POST.get('medium_pct', 0))
        hard_pct = int(request.POST.get('hard_pct', 0))

        # Validate
        if easy_pct + medium_pct + hard_pct != 100:
            messages.error(request, 'Difficulty percentages must add up to 100%.')
            return redirect('generate_paper')

        if total_questions < 3 or total_questions > 200:
            messages.error(request, 'Total questions must be between 3 and 200.')
            return redirect('generate_paper')

        course = get_object_or_404(Course, id=course_id)
        quiz = None
        if quiz_id:
            quiz = get_object_or_404(Quiz, id=quiz_id)

        try:
            result = generate_three_paper_sets(
                course=course,
                quiz=quiz,
                total_questions=total_questions,
                easy_pct=easy_pct,
                medium_pct=medium_pct,
                hard_pct=hard_pct,
                faculty=request.user,
            )

            if result.get('warnings'):
                for w in result['warnings']:
                    messages.warning(request, w)

            messages.success(request, f"✅ 3 paper sets generated successfully! Group ID: {result['group_id']}")
            
            # Redirect to preview of first paper
            return redirect('paper_group_preview', group_id=result['group_id'])

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('generate_paper')
        except Exception as e:
            messages.error(request, f'Generation failed: {str(e)}')
            return redirect('generate_paper')


@login_required
def get_quizzes_for_course(request, course_id):
    """AJAX: Get quizzes for a course"""

    quizzes = Quiz.objects.filter(
        course_id=course_id,
        is_active=True
    )

    quiz_list = []

    for q in quizzes:
        quiz_list.append({
            "id": q.id,
            "name": q.quiz_name,
            "question_count": q.questions.count()  # count related questions
        })

    return JsonResponse({"quizzes": quiz_list})


@login_required
def get_question_stats(request, course_id):
    """AJAX: Get question stats for a course/quiz"""
    quiz_id = request.GET.get('quiz_id', '')
    qs = Question.objects.filter(is_active=True, course_id=course_id)
    if quiz_id:
        qs = Question.objects.filter(is_active=True, quiz_id=quiz_id)
    
    return JsonResponse({
        'easy': qs.filter(difficulty='easy').count(),
        'medium': qs.filter(difficulty='medium').count(),
        'hard': qs.filter(difficulty='hard').count(),
        'total': qs.count(),
    })


@method_decorator(login_required, name='dispatch')
class PaperGroupPreviewView(View):
    template_name = 'papers/paper_group_preview.html'

    def get(self, request, group_id):
        papers = GeneratedPaper.objects.filter(
            paper_group_id=group_id
        ).order_by('set_name')

        if not papers.exists():
            messages.error(request, 'Paper group not found.')
            return redirect('generated_papers')

        context = {
            'papers': papers,
            'group_id': group_id,
            'course': papers.first().course,
            'quizzes': Quiz.objects.filter(is_active=True).order_by('quiz_name'),
            'active_page': 'generate',
        }
        return render(request, self.template_name, context)


@login_required
def push_paper_to_moodle_quiz(request, paper_id):
    if request.method != 'POST':
        return redirect('paper_detail', paper_id=paper_id)

    paper = get_object_or_404(GeneratedPaper, id=paper_id)
    quiz_pk = request.POST.get('quiz_id')
    if not quiz_pk:
        messages.error(request, 'Please select a quiz.')
        return redirect('paper_group_preview', group_id=paper.paper_group_id)

    quiz = get_object_or_404(Quiz, id=quiz_pk)
    if not quiz.moodle_quiz_id:
        messages.error(request, 'Selected quiz is not linked to Moodle (missing moodle_quiz_id).')
        return redirect('paper_group_preview', group_id=paper.paper_group_id)

    paper_questions = PaperQuestion.objects.filter(paper=paper).select_related('question').order_by('question_number')
    moodle_question_ids = [pq.question.moodle_question_id for pq in paper_questions if pq.question.moodle_question_id]
    if not moodle_question_ids:
        messages.error(request, 'No Moodle-linked questions found in this paper set.')
        return redirect('paper_detail', paper_id=paper.id)

    moodle_conn = connections['moodle']
    target_quizid = int(quiz.moodle_quiz_id)

    added = 0
    skipped = 0
    missing = 0

    try:
        with transaction.atomic(using='moodle'):
            with moodle_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM mdl_quiz_slots WHERE quizid = %s",
                    [target_quizid]
                )

                existing_count = cursor.fetchone()[0]

                if existing_count > 0:
                    messages.warning(
                        request,
                        f'This Moodle quiz already contains {existing_count} questions. '
                        'New questions cannot be added. Please clear the quiz first.'
                    )
                    return redirect('paper_group_preview', group_id=paper.paper_group_id)
                ensure_section(cursor, target_quizid)

                grade_item_id = get_quiz_grade_item_id(cursor, target_quizid)
                backfill_slot_grade_item_id(cursor, target_quizid, grade_item_id)

                using_context_id = get_using_context_id(cursor, target_quizid)
                if not using_context_id:
                    messages.error(request, 'Could not resolve Moodle context for this quiz.')
                    return redirect('paper_group_preview', group_id=paper.paper_group_id)

                existing_qbe = fetch_existing_questionbankentry_ids_for_quiz(cursor, target_quizid)
                next_slot = get_next_slot(cursor, target_quizid)

                qid_to_qbe = get_questionbankentry_ids(cursor, moodle_question_ids)

                for pq in paper_questions:
                    qid = pq.question.moodle_question_id
                    if not qid:
                        missing += 1
                        continue
                    qbe_info = qid_to_qbe.get(int(qid))
                    if not qbe_info:
                        missing += 1
                        continue
                    qbe_id, qbe_version = qbe_info
                    if qbe_id in existing_qbe:
                        skipped += 1
                        continue
                    if qbe_version is None:
                        missing += 1
                        continue

                    maxmark = pq.marks
                    if isinstance(maxmark, Decimal):
                        maxmark = float(maxmark)

                    slot_id = insert_quiz_slot(
                        cursor,
                        quizid=target_quizid,
                        slot=next_slot,
                        maxmark=maxmark,
                        grade_item_id=grade_item_id,
                        page=1,
                        displaynumber=next_slot,
                        requireprevious=0,
                    )

                    insert_question_reference(
                        cursor,
                        using_context_id=using_context_id,
                        slot_id=slot_id,
                        questionbankentryid=qbe_id,
                        version=qbe_version,
                    )

                    existing_qbe.add(qbe_id)
                    next_slot += 1
                    added += 1

                update_sumgrades(cursor, target_quizid)
                backfill_reference_versions(cursor, target_quizid)
                backfill_slot_grade_item_id(cursor, target_quizid, grade_item_id)

        if added:
            messages.success(request, f'Added {added} questions to Moodle quiz "{quiz.quiz_name}". Skipped {skipped} duplicates.')
        else:
            messages.info(request, f'No new questions were added. Skipped {skipped} duplicates. Missing mappings: {missing}.')
    except Exception as e:
        messages.error(request, f'Failed to push questions to Moodle: {str(e)}')

    return redirect('paper_group_preview', group_id=paper.paper_group_id)


@method_decorator(login_required, name='dispatch')
class GeneratedPapersListView(View):
    template_name = 'papers/generated_papers.html'

    def get(self, request):
        papers = GeneratedPaper.objects.filter(
            faculty=request.user
        ).select_related('course', 'quiz').order_by('-generated_at')
        
        # Group by paper_group_id
        groups = {}
        for paper in papers:
            gid = paper.paper_group_id
            if gid not in groups:
                groups[gid] = {
                    'group_id': gid,
                    'course': paper.course,
                    'quiz': paper.quiz,
                    'generated_at': paper.generated_at,
                    'sets': [],
                    'total_questions': paper.total_questions,
                }
            groups[gid]['sets'].append(paper)

        context = {
            'paper_groups': list(groups.values()),
            'active_page': 'papers',
        }
        return render(request, self.template_name, context)


@login_required
def paper_detail(request, paper_id):
    """Preview a single paper set"""
    paper = get_object_or_404(GeneratedPaper, id=paper_id)
    paper_questions = PaperQuestion.objects.filter(paper=paper).select_related(
        'question__category', 'question__course'
    ).order_by('question_number')

    context = {
        'paper': paper,
        'paper_questions': paper_questions,
        'active_page': 'papers',
    }
    return render(request, 'papers/paper_detail.html', context)


@login_required
def export_paper_txt(request, paper_id):
    """Export paper as plain text"""
    paper = get_object_or_404(GeneratedPaper, id=paper_id)
    paper_questions = PaperQuestion.objects.filter(paper=paper).select_related(
        'question'
    ).order_by('question_number')

    lines = [
        "=" * 70,
        "UNIVERSITY EXAMINATION",
        f"Course: {paper.course.course_name} ({paper.course.course_code})",
        f"Paper Set: {paper.set_name}",
        f"Total Questions: {paper.total_questions}  |  Total Marks: {paper.total_marks}",
        f"Duration: {paper.duration_minutes} minutes",
        "=" * 70,
        "",
        "INSTRUCTIONS:",
        "1. Answer all questions.",
        "2. Choose the best answer for multiple choice questions.",
        "3. Marks are indicated against each question.",
        "",
        "-" * 70,
        "QUESTIONS",
        "-" * 70,
        "",
    ]

    for pq in paper_questions:
        q = pq.question
        lines.append(f"Q{pq.question_number}. [{q.get_difficulty_display().upper()}] [{pq.marks} marks]")
        lines.append(f"   {q.question_text}")

        for idx, answer in enumerate(q.answer_data or []):
            option = chr(65 + idx)  # A, B, C, D
            lines.append(f"   {option}) {answer.get('answer_text', '')}")
        lines.append("")

    content = "\n".join(lines)
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="ExamPaper_{paper.paper_id}.txt"'
    return response


from django.views.decorators.csrf import csrf_exempt
from datetime import datetime


@csrf_exempt
def save_blueprint(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request"})

    try:
        data = json.loads(request.body)
        
        # Debug: Log received data
        print(f"DEBUG save_blueprint: received data: {data}")

        cs_id = data.get("cs_id")
        exam_id = data.get("exam_id")
        subject_id = data.get("subject_id")
        rows = data.get("rows", [])
        
        # Debug: Log parsed values
        print(f"DEBUG: cs_id={cs_id}, exam_id={exam_id}, subject_id={subject_id}, rows={rows}")

        if not cs_id or not exam_id or not rows:
            return JsonResponse({"success": False, "error": "Missing data"})

        now = datetime.now()
        
        # Debug: Check connection
        print(f"DEBUG: Using connection 'trms': {connections['trms']}")

        with connections['trms'].cursor() as cursor:
            # Delete old entries
            cursor.execute("""
                DELETE FROM zrtiudp.cbt_blue_prints
                WHERE cs_id=%s AND exam_id=%s AND subject_id=%s
            """, [cs_id, exam_id, subject_id])
            print(f"DEBUG: Deleted existing rows for cs_id={cs_id}, exam_id={exam_id}")
            
            # Insert new rows
            for r in rows:
                print(f"DEBUG: Inserting row: {r}")
                cursor.execute("""
                    INSERT INTO zrtiudp.cbt_blue_prints
                    (cs_id, exam_id, subject_id, mdl_cat_id, tag, ques, status, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s)
                """, [
                    cs_id,
                    exam_id,
                    subject_id,
                    r.get("category_id"),
                    r["tag"],
                    r["ques"],
                    now,
                    now
                ])
                print(f"DEBUG: Row inserted successfully")
            
            # CRITICAL: Commit the transaction for raw SQL
            connections['trms'].commit()
            print(f"DEBUG: Transaction committed")

        return JsonResponse({"success": True})

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in save_blueprint: {str(e)}\n{error_trace}")
        return JsonResponse({"success": False, "error": str(e)})
