from django.urls import path
from . import views

urlpatterns = [

    path('',                     views.DepartmentListView.as_view(),   name='department_list'),
    path('<int:dept_id>/',       views.DepartmentDetailView.as_view(), name='department_detail'),

    path('generate/',            views.BlueprintGenerateView.as_view(),name='blueprint_generate'),
    path('create/',              views.BlueprintCreateView.as_view(),  name='blueprint_create'),

    path('blueprints/',          views.BlueprintListView.as_view(),    name='blueprint_list'),
    path('blueprints/<int:blueprint_id>/delete/', views.BlueprintDeleteView.as_view(), name='blueprint_delete'),

    path('history/',             views.BlueprintHistoryView.as_view(), name='blueprint_history'),
    path('preview/<str:group_id>/', views.blueprint_paper_preview,    name='blueprint_paper_preview'),

    # ─────────────────────────────────────────
    # TRMS BLUEPRINT CRUD (cbt_blue_prints)
    # ─────────────────────────────────────────

    path(
        'trms-blueprints/',
        views.trms_blueprint_list,
        name='trms_blueprint_list'
    ),

    path(
        'trms-blueprints/create/',
        views.trms_blueprint_create,
        name='trms_blueprint_create'
    ),

    # AJAX
    path('api/categories/<int:dept_id>/', views.api_categories, name='api_cats'),
    path('api/courses/<int:dept_id>/<int:cat_id>/', views.api_courses, name='api_courses'),
    path('api/subjects/<int:dept_id>/<int:cat_id>/<int:course_id>/', views.api_subjects, name='api_subjects'),
    path('api/blueprint/<int:dept_id>/<int:cat_id>/<int:course_id>/<int:subject_id>/', views.api_blueprint, name='api_blueprint'),
    path('api/blueprints/<int:dept_id>/', views.api_blueprints_list, name='api_blueprints_list'),
]