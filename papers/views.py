"""
Papers Views - Paper Generation and Preview
"""
import json
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from papers.models import GeneratedPaper, PaperQuestion
from papers.generator import generate_three_paper_sets
from courses.models import Course, Quiz
from questions.models import Question


@method_decorator(login_required, name='dispatch')
class GeneratePaperView(View):
    template_name = 'papers/generate.html'

    def get(self, request):
        courses = Course.objects.filter(is_active=True).order_by('course_code')
        context = {
            'courses': courses,
            'active_page': 'generate',
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
        ).prefetch_related(
            'paper_questions__question__answers',
        ).order_by('set_name')

        if not papers.exists():
            messages.error(request, 'Paper group not found.')
            return redirect('generated_papers')

        context = {
            'papers': papers,
            'group_id': group_id,
            'course': papers.first().course,
            'active_page': 'generate',
        }
        return render(request, self.template_name, context)


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
    ).prefetch_related('question__answers').order_by('question_number')

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
    ).prefetch_related('question__answers').order_by('question_number')

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
        
        for idx, answer in enumerate(q.answers.all()):
            option = chr(65 + idx)  # A, B, C, D
            lines.append(f"   {option}) {answer.answer_text}")
        lines.append("")

    content = "\n".join(lines)
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="ExamPaper_{paper.paper_id}.txt"'
    return response
