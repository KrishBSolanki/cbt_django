from django.contrib import admin
from django.utils.html import format_html
from .models import Department, ExamCategory, Subject, ExamBlueprint, BlueprintPaperGroup


class ExamCategoryInline(admin.TabularInline):
    model  = ExamCategory
    extra  = 1
    fields = ['name', 'order', 'is_active']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ['icon_col', 'name', 'code', 'category_count', 'blueprint_count', 'subject_count', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name', 'code']
    inlines       = [ExamCategoryInline]
    fieldsets = (
        ('Identity',     {'fields': ('name', 'code', 'icon', 'color_hex', 'is_active')}),
        ('Description',  {'fields': ('description',), 'classes': ('collapse',)}),
    )
    def icon_col(self, o): return format_html('<span style="font-size:20px">{}</span>', o.icon)
    icon_col.short_description = ''


@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'department', 'order', 'blueprint_count', 'is_active']
    list_filter   = ['department', 'is_active']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'course', 'department', 'is_active']
    list_filter   = ['department', 'is_active']
    search_fields = ['name', 'code']
    raw_id_fields = ['course']


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    list_display  = ['department', 'category', 'course', 'subject', 'mcq_col', 'desc_col', 'total_col', 'avail_col', 'is_active']
    list_filter   = ['department', 'category', 'is_active']
    search_fields = ['course__course_code', 'subject__name', 'department__name']
    raw_id_fields = ['course', 'subject']
    fieldsets = (
        ('Blueprint Identity', {'fields': ('department', 'category', 'course', 'subject', 'is_active')}),
        ('Section A — MCQ',    {'fields': ('mcq_count', 'mcq_marks'),         'description': 'e.g. 40 × 1 mark = 40 marks'}),
        ('Section B — Descriptive', {'fields': ('descriptive_count', 'descriptive_marks'), 'description': 'e.g. 6 × 10 marks = 60 marks'}),
        ('Paper Settings',     {'fields': ('duration_minutes', 'instructions')}),
    )
    def mcq_col(self, o):   return format_html('<b style="color:#4f8ef7">{}</b> ×{}m', o.mcq_count, o.mcq_marks)
    def desc_col(self, o):  return format_html('<b style="color:#a78bfa">{}</b> ×{}m', o.descriptive_count, o.descriptive_marks)
    def total_col(self, o): return format_html('<b style="color:#22c55e;font-size:13px">{}M</b>', o.total_marks)
    def avail_col(self, o):
        a = o.check_availability()
        if a['ok']:
            tip = f"MCQ:{a['mcq_available']} Desc:{a['desc_available']}"
            return format_html('<span title="{}">✅</span>', tip)
        parts = []
        if not a['mcq_ok']:  parts.append(f"MCQ:{a['mcq_available']}/{a['mcq_needed']}")
        if not a['desc_ok']: parts.append(f"Desc:{a['desc_available']}/{a['desc_needed']}")
        return format_html('<span title="{}" style="color:#ef4444">⚠️ {}</span>', ', '.join(parts), 'Short')
    mcq_col.short_description  = 'MCQ'
    desc_col.short_description = 'Descriptive'
    total_col.short_description = 'Total'
    avail_col.short_description = 'Ready?'


@admin.register(BlueprintPaperGroup)
class BlueprintPaperGroupAdmin(admin.ModelAdmin):
    list_display  = ['group_id', 'blueprint', 'faculty', 'generated_at']
    list_filter   = ['blueprint__department']
    ordering      = ['-generated_at']
