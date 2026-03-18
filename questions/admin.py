from django.contrib import admin
from questions.models import Question, QuestionCategory


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'difficulty', 'question_type', 'course', 'marks', 'is_active']
    list_filter = ['difficulty', 'question_type', 'is_active', 'course__department']
    search_fields = ['question_text']
    raw_id_fields = ['course', 'quiz', 'category']
    list_per_page = 50


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'moodle_category_id']
    search_fields = ['name']
