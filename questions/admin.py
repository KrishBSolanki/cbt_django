from django.contrib import admin
from questions.models import Question, QuestionCategory, QuestionAnswer


class AnswerInline(admin.TabularInline):
    model = QuestionAnswer
    extra = 0
    fields = ['answer_text', 'is_correct', 'fraction']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_text', 'difficulty', 'question_type', 'course', 'marks', 'is_active']
    list_filter = ['difficulty', 'question_type', 'is_active', 'course__department']
    search_fields = ['question_text']
    raw_id_fields = ['course', 'quiz', 'category']
    inlines = [AnswerInline]
    list_per_page = 50


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'parent']
    search_fields = ['name']
