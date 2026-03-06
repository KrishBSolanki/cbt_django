from django.contrib import admin
from papers.models import GeneratedPaper, PaperQuestion


class PaperQuestionInline(admin.TabularInline):
    model = PaperQuestion
    extra = 0
    raw_id_fields = ['question']
    readonly_fields = ['question_number', 'marks']


@admin.register(GeneratedPaper)
class GeneratedPaperAdmin(admin.ModelAdmin):
    list_display = ['paper_id', 'course', 'set_name', 'total_questions', 'status', 'faculty', 'generated_at']
    list_filter = ['set_name', 'status', 'course__department']
    search_fields = ['paper_id', 'course__course_code', 'faculty__email']
    readonly_fields = ['paper_id', 'generated_at', 'paper_group_id']
    inlines = [PaperQuestionInline]
    ordering = ['-generated_at']
