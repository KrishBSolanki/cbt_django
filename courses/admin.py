from django.contrib import admin
from courses.models import Course, Quiz, CourseFaculty


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'department', 'is_active', 'quiz_count', 'question_count']
    list_filter = ['department', 'is_active']
    search_fields = ['course_code', 'course_name']
    ordering = ['course_code']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'total_questions', 'duration_minutes', 'is_active', 'question_count']
    list_filter = ['is_active', 'course__department']
    search_fields = ['title', 'course__course_code']
    raw_id_fields = ['course']
