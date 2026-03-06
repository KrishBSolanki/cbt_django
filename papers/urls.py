from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.GeneratePaperView.as_view(), name='generate_paper'),
    path('generated/', views.GeneratedPapersListView.as_view(), name='generated_papers'),
    path('group/<str:group_id>/', views.PaperGroupPreviewView.as_view(), name='paper_group_preview'),
    path('detail/<int:paper_id>/', views.paper_detail, name='paper_detail'),
    path('export/<int:paper_id>/txt/', views.export_paper_txt, name='export_paper_txt'),
    path('api/quizzes/<int:course_id>/', views.get_quizzes_for_course, name='api_quizzes'),
    path('api/stats/<int:course_id>/', views.get_question_stats, name='api_question_stats'),
]
