from django.urls import path
from . import views

urlpatterns = [
    path('', views.QuestionBankView.as_view(), name='question_bank'),
    path('categories/', views.CategoryListView.as_view(), name='categories'),
]
