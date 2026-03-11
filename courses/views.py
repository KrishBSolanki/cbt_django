"""
Courses & Dashboard Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q, Count

from courses.models import Course, Quiz
from questions.models import Question
from papers.models import GeneratedPaper


@login_required
def dashboard(request):
    """Main dashboard view"""
    faculty = request.user
    
    # Stats
    total_courses = Course.objects.filter(is_active=True).count()
    total_questions = Question.objects.filter(is_active=True).count()
    total_quizzes = Quiz.objects.filter(is_active=True).count()
    my_papers = GeneratedPaper.objects.filter(faculty=faculty).count()
    
    # Recent papers
    recent_papers = GeneratedPaper.objects.filter(faculty=faculty).order_by('-generated_at')[:5]
    
    # Question distribution
    easy_count = Question.objects.filter(is_active=True, difficulty='easy').count()
    medium_count = Question.objects.filter(is_active=True, difficulty='medium').count()
    hard_count = Question.objects.filter(is_active=True, difficulty='hard').count()
    
    context = {
        'total_courses': total_courses,
        'total_questions': total_questions,
        'total_quizzes': total_quizzes,
        'my_papers': my_papers,
        'recent_papers': recent_papers,
        'easy_count': easy_count,
        'medium_count': medium_count,
        'hard_count': hard_count,
        'active_page': 'dashboard',
    }
    return render(request, 'dashboard.html', context)


@method_decorator(login_required, name='dispatch')
class CourseListView(View):
    template_name = 'courses/course_list.html'

    def get(self, request):
        courses = Course.objects.filter(is_active=True).annotate(
            quiz_count_ann=Count('quizzes', distinct=True),
            question_count_ann=Count('questions', distinct=True),
        ).order_by('course_code')

        # Search & filter
        search = request.GET.get('search', '')
        department = request.GET.get('department', '')
        
        if search:
            courses = courses.filter(
                Q(course_code__icontains=search) |
                Q(course_name__icontains=search)
            )
        if department:
            courses = courses.filter(department=department)

        departments = (
            Course.objects.exclude(department__isnull=True)
            .exclude(department__exact='')
            .values_list('department', flat=True)
            .distinct()
            .order_by('department')
        )
        departments = [(d, d) for d in departments]

        context = {
            'courses': courses,
            'departments': departments,
            'search': search,
            'selected_dept': department,
            'active_page': 'courses',
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class QuizListView(View):
    template_name = 'courses/quiz_list.html'

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id, is_active=True)
        quizzes = Quiz.objects.filter(course=course, is_active=True).annotate(
            q_count=Count('questions', distinct=True)
        )
        
        context = {
            'course': course,
            'quizzes': quizzes,
            'active_page': 'courses',
        }
        return render(request, self.template_name, context)
