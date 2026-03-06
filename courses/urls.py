from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.CourseListView.as_view(), name='course_list'),
    path('<int:course_id>/quiz/', views.QuizListView.as_view(), name='quiz_list'),
]
