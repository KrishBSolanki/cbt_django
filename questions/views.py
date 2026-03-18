"""
Questions Views
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Count

from questions.models import Question, QuestionCategory
from courses.models import Course


@method_decorator(login_required, name='dispatch')
class QuestionBankView(View):
    template_name = 'questions/question_bank.html'

    def get(self, request):
        questions = Question.objects.filter(is_active=True).select_related(
            'course', 'quiz', 'category'
        ).order_by('-created_at')

        # Filters
        course_id = request.GET.get('course', '')
        difficulty = request.GET.get('difficulty', '')
        category_id = request.GET.get('category', '')
        q_type = request.GET.get('type', '')
        search = request.GET.get('search', '')

        if course_id:
            questions = questions.filter(course_id=course_id)
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        if category_id:
            questions = questions.filter(category_id=category_id)
        if q_type:
            questions = questions.filter(question_type=q_type)
        if search:
            questions = questions.filter(question_text__icontains=search)

        # Pagination
        paginator = Paginator(questions, 20)
        page = request.GET.get('page', 1)
        page_obj = paginator.get_page(page)

        # Stats by difficulty
        total_easy = Question.objects.filter(is_active=True, difficulty='easy').count()
        total_medium = Question.objects.filter(is_active=True, difficulty='medium').count()
        total_hard = Question.objects.filter(is_active=True, difficulty='hard').count()

        context = {
            'page_obj': page_obj,
            'questions': page_obj,
            'courses': Course.objects.filter(is_active=True).order_by('course_code'),
            'categories': QuestionCategory.objects.all().order_by('name'),
            'selected_course': course_id,
            'selected_difficulty': difficulty,
            'selected_category': category_id,
            'selected_type': q_type,
            'search': search,
            'total_easy': total_easy,
            'total_medium': total_medium,
            'total_hard': total_hard,
            'total_questions': total_easy + total_medium + total_hard,
            'active_page': 'questions',
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class CategoryListView(View):
    template_name = 'questions/categories.html'

    def get(self, request):
        categories = QuestionCategory.objects.annotate(
            q_count=Count('questions')
        ).order_by('name')

        context = {
            'categories': categories,
            'active_page': 'questions',
        }
        return render(request, self.template_name, context)
