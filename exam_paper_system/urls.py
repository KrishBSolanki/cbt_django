"""
URL Configuration for Exam Paper Generation System
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from integration.views import test_moodle_connection
from integration.views import sync_moodle_questions
from integration import views
urlpatterns = [
    path('', lambda request: redirect('dashboard') if request.user.is_authenticated else redirect('login')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('courses.urls')),
    path('courses/', include('courses.urls')),
    path('questions/', include('questions.urls')),
    path('papers/', include('papers.urls')),
    path('api/', include('integration.urls')),
    path('test-moodle/', test_moodle_connection),
    path("sync-moodle/", sync_moodle_questions),
    path("sync-courses/", views.sync_moodle_courses),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin customization
admin.site.site_header = "ExamGen Admin"
admin.site.site_title = "ExamGen"
admin.site.index_title = "University Exam Paper System"
