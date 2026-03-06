from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Faculty


@admin.register(Faculty)
class FacultyAdmin(UserAdmin):
    model = Faculty
    list_display = ['email', 'get_full_name', 'department', 'designation', 'is_active', 'date_joined']
    list_filter = ['department', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    ordering = ['email']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'employee_id', 'phone', 'profile_picture')}),
        ('Academic Info', {'fields': ('department', 'designation', 'trms_faculty_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'department', 'password1', 'password2'),
        }),
    )
