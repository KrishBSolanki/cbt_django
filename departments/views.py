"""
departments/views.py
══════════════════════════════════════════════════════════════════════════════
All views for the Blueprint-Driven Department system.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db import connections

from .models import Department, ExamCategory, Subject, ExamBlueprint, BlueprintPaperGroup
from .generator import generate_blueprint_paper_sets
from courses.models import Course
from .models import TRMSBlueprint


@login_required
def blueprint_design_list(request):

    trms_conn = connections['trms']

    with trms_conn.cursor() as cursor:
        # Debug: Check what subjects exist in blueprints
        cursor.execute(
            """
            SELECT DISTINCT bp.subject_id, s.subject_name
            FROM zrtiudp.cbt_blue_prints bp
            JOIN zrtiudp.subjects s ON s.id = bp.subject_id
            WHERE bp.status = 1
            """
        )
        all_subjects = cursor.fetchall()
        print(f"DEBUG: All subjects in blueprints: {all_subjects}")

        # Get distinct blueprint combinations using GROUP BY (MySQL compatible)
        cursor.execute(
            """
            SELECT 
              bp.cs_id AS course_id,
              CASE 
                WHEN s.subject_name = 'Miscellaneous' THEN 'Transportation & Air Brake (परिवहन एवं एयर ब्रेक)'
                WHEN s.subject_name = 'Engineering' THEN 'C&w (air Brake )'
                ELSE s.subject_name
              END AS course_name,
              bp.exam_id AS exam_id,
              bp.subject_id AS subject_id,
              s.subject_name AS subject_name
            FROM zrtiudp.cbt_blue_prints bp
            JOIN zrtiudp.subjects s ON s.id = bp.subject_id
            WHERE bp.status = 1
            GROUP BY bp.cs_id, bp.exam_id, bp.subject_id, s.subject_name
            ORDER BY course_name ASC, bp.exam_id ASC
            """,
        )

        rows = cursor.fetchall()
        print(f"DEBUG: Fetched {len(rows)} rows:")
        for r in rows:
            print(f"  course_id={r[0]}, mapped_course={r[1]}, exam_id={r[2]}, subject_id={r[3]}, subject_name={r[4]}")

    combined = [
        {
            'course_id': r[0],
            'course_name': r[1],
            'exam_id': r[2],
            'subject_id': r[3],
            'subject_name': r[4],
        }
        for r in rows
    ]

    return render(
        request,
        'blueprints/blueprint_design_list.html',
        {
            'rows': combined,
            'active_page': 'blueprint_design',
        }
    )

@login_required
def trms_blueprint_list(request):

    blueprints = TRMSBlueprint.objects.using('trms').all()

    return render(
        request,
        "departments/trms_blueprints.html",
        {"blueprints": blueprints}
    )


# ═══════════════════════════════════════════════════════════════
# TRMS BLUEPRINT CREATE
# ═══════════════════════════════════════════════════════════════
@login_required
def trms_blueprint_create(request):

    if request.method == "POST":

        cs_id = request.POST.get("cs_id")
        exam_id = request.POST.get("exam_id")
        subject_id = request.POST.get("subject_id")
        mdl_cat_id = request.POST.get("mdl_cat_id")

        tag = request.POST.get("tag")
        ques = request.POST.get("ques")

        TRMSBlueprint.objects.using("trms").create(
            cs_id=cs_id,
            exam_id=exam_id,
            subject_id=subject_id,
            mdl_cat_id=mdl_cat_id,
            tag=tag,
            ques=ques,
            status=1
        )

        messages.success(request, "Blueprint row added successfully")

        return redirect("trms_blueprint_list")

    return render(request, "departments/trms_blueprint_form.html")

# ══════════════════════════════════════════════════════════════════════════════
# DEPARTMENT LIST
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class DepartmentListView(View):
    def get(self, request):
        depts = Department.objects.filter(is_active=True)
        return render(request, 'departments/department_list.html', {
            'departments': depts, 'active_page': 'departments'})


# ══════════════════════════════════════════════════════════════════════════════
# DEPARTMENT DETAIL — shows the blueprint table
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class DepartmentDetailView(View):
    def get(self, request, dept_id):
        dept       = get_object_or_404(Department, id=dept_id, is_active=True)
        categories = ExamCategory.objects.filter(department=dept, is_active=True).order_by('order', 'name')
        blueprints = (ExamBlueprint.objects
                      .filter(department=dept, is_active=True)
                      .select_related('category', 'course', 'subject')
                      .order_by('category__order', 'course__course_code', 'subject__name'))
        # Attach availability to each blueprint for the UI
        for bp in blueprints:
            bp._avail = bp.check_availability()

        return render(request, 'departments/department_detail.html', {
            'department': dept, 'categories': categories,
            'blueprints': blueprints, 'active_page': 'departments'})


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT GENERATE WIZARD
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class BlueprintGenerateView(View):
    template_name = 'departments/blueprint_generate.html'

    def get(self, request):
        depts = Department.objects.filter(is_active=True).order_by('name')
        engg_dept = Department.objects.filter(code='ENGG', is_active=True).first()
        cs_id = request.GET.get('cs_id')
        trms_exam_data = []

        if cs_id:
            try:
                with connections['trms'].cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ed.id, ed.cs_id, ed.subject_id, ed.type_sort,
                               s.subject_name, s.subject_type
                        FROM exam_design ed
                        JOIN subjects s ON s.id = ed.subject_id
                        WHERE ed.cs_id = %s
                        AND ed.status = 1
                        AND s.subject_type IN (2,3)
                        AND s.status = 1
                        """,
                        [cs_id]
                    )

                    rows = cursor.fetchall()

                trms_exam_data = [
                    {
                        'exam_id': r[0],
                        'cs_id': r[1],
                        'subject_id': r[2],
                        'type': r[3],
                        'subject_name': r[4],
                        'subject_type': r[5],
                    }
                    for r in rows
                ]
            except Exception:
                trms_exam_data = []
        # URL params allow arriving pre-filled from department detail page
        sel = {k: request.GET.get(k, '')
               for k in ('dept', 'cat', 'course', 'subject')}
        sel_bp_id = request.GET.get('bp_id', '')
        sel_paper_type = (request.GET.get('paper_type') or '').strip()
        blueprint = None
        if all(sel.values()):
            qs = ExamBlueprint.objects.filter(
                department_id=sel['dept'], category_id=sel['cat'],
                course_id=sel['course'], subject_id=sel['subject'],
                is_active=True)

            if sel_paper_type:
                qs = qs.filter(paper_type=sel_paper_type)

            if sel_bp_id:
                blueprint = qs.filter(id=sel_bp_id).first()
            if blueprint is None:
                blueprint = qs.order_by('-created_at').first()
        return render(request, self.template_name, {
            'departments': depts, 'blueprint': blueprint,
            'steps': ['Dept', 'Category', 'Course', 'Subject', 'Generate'],
            'active_page': 'bp_generate',
            'sel_bp_id': sel_bp_id,
            'sel_paper_type': sel_paper_type,
            'engg_dept_id': engg_dept.id if engg_dept else None,
            'trms_exam_data': trms_exam_data,
            **{f'sel_{k}': v for k, v in sel.items()}})

    def post(self, request):
        d = request.POST
        dept_id, cat_id, course_id, subject_id = (
            d.get('dept_id'), d.get('cat_id'),
            d.get('course_id'), d.get('subject_id'))
        bp_id = d.get('blueprint_id')
        paper_type = (d.get('paper_type') or '').strip()

        if not all([dept_id, cat_id, course_id, subject_id]):
            messages.error(request, 'Please complete all 4 selections.')
            return redirect('blueprint_generate')

        bp_qs = ExamBlueprint.objects.filter(
            department_id=dept_id, category_id=cat_id,
            course_id=course_id, subject_id=subject_id, is_active=True)

        if paper_type:
            bp_qs = bp_qs.filter(paper_type=paper_type)

        if bp_id:
            bp = get_object_or_404(bp_qs, id=bp_id)
        else:
            bp = get_object_or_404(bp_qs.order_by('-created_at'))
        try:
            result = generate_blueprint_paper_sets(bp, request.user)
            for w in result['warnings']:
                messages.warning(request, w)
            messages.success(request,
                f"✅ 3 paper sets (A/B/C) generated! "
                f"{bp.mcq_count} MCQ + {bp.descriptive_count} Descriptive = "
                f"{bp.total_marks} marks. Group: {result['group_id']}")
            return redirect('blueprint_paper_preview', group_id=result['group_id'])
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Generation failed: {e}')

        return redirect(
            f"/departments/generate/?dept={dept_id}&cat={cat_id}"
            f"&course={course_id}&subject={subject_id}")


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT CREATE / EDIT
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class BlueprintCreateView(View):
    template_name = 'departments/blueprint_form.html'

    def get(self, request):
        # Pre-fill from query params if coming from generate page
        initial = {
            'department_id': request.GET.get('dept', ''),
            'category_id': request.GET.get('cat', ''),
            'course_id': request.GET.get('course', ''),
            'subject_id': request.GET.get('subject', ''),
        }
        engg_dept = Department.objects.filter(code='ENGG', is_active=True).first()
        departments = Department.objects.filter(is_active=True).order_by('name')
        categories = ExamCategory.objects.filter(is_active=True).order_by('name') if initial['department_id'] else []
        courses = Course.objects.all().order_by('course_code') if initial['department_id'] else []
        subjects = Subject.objects.filter(is_active=True).order_by('name') if initial['course_id'] else []
        
        return render(request, self.template_name, {
            'departments': departments,
            'categories': categories,
            'courses': courses,
            'subjects': subjects,
            'initial': initial,
            'active_page': 'bp_generate',
            'edit_mode': False,
            'engg_dept_id': engg_dept.id if engg_dept else None,
        })

    def post(self, request):
        data = request.POST
        dept_id = data.get('department')
        cat_id = data.get('category')
        course_id = data.get('course')
        subject_id = data.get('subject')
        paper_type = (data.get('paper_type') or '').strip()

        mcq_count = int(data.get('mcq_count', 40))
        mcq_marks = int(data.get('mcq_marks', 1))
        descriptive_count = int(data.get('descriptive_count', 6))
        descriptive_marks = int(data.get('descriptive_marks', 10))
        
        # Validate required fields
        if not all([dept_id, cat_id, course_id, subject_id]):
            messages.error(request, 'Please select all required fields: Department, Category, Course, and Subject.')
            return redirect('blueprint_create')

        if any(v < 0 for v in (mcq_count, mcq_marks, descriptive_count, descriptive_marks)):
            messages.error(request, 'MCQ and Descriptive counts/marks must be greater than or equal to 0.')
            return redirect('blueprint_create')

        total_marks = (mcq_count * mcq_marks) + (descriptive_count * descriptive_marks)
        dept = Department.objects.filter(id=dept_id).first()
        if not dept:
            messages.error(request, 'Invalid department.')
            return redirect('blueprint_create')

        if dept.code != 'ENGG' and total_marks != 100:
            messages.error(request, 'Total blueprint marks must be exactly 100.')
            return redirect('blueprint_create')
        
        # Check for duplicate (only active blueprints, same mark distribution)
        existing = ExamBlueprint.objects.filter(
            department_id=dept_id,
            category_id=cat_id,
            course_id=course_id,
            subject_id=subject_id,
            paper_type=paper_type,
            mcq_count=mcq_count,
            mcq_marks=mcq_marks,
            descriptive_count=descriptive_count,
            descriptive_marks=descriptive_marks,
            is_active=True,
        ).first()
        
        if existing:
            messages.warning(request, 'A blueprint already exists for this combination. It has been pre-selected below.')
            return redirect(
                f'/departments/generate/?dept={dept_id}&cat={cat_id}'
                f'&course={course_id}&subject={subject_id}&bp_id={existing.id}'
            )
        
        # Create blueprint
        try:
            blueprint = ExamBlueprint.objects.create(
                department_id=dept_id,
                category_id=cat_id,
                course_id=course_id,
                subject_id=subject_id,
                paper_type=paper_type,
                mcq_count=mcq_count,
                mcq_marks=mcq_marks,
                descriptive_count=descriptive_count,
                descriptive_marks=descriptive_marks,
                duration_minutes=int(data.get('duration_minutes', 180)),
                instructions=data.get('instructions', ''),
                is_active=True,
            )
            messages.success(request, f'Blueprint created successfully! You can now generate papers.')
            # Redirect to generate page with the new blueprint pre-selected
            return redirect(
                f'/departments/generate/?dept={dept_id}&cat={cat_id}'
                f'&course={course_id}&subject={subject_id}&bp_id={blueprint.id}'
            )
        except Exception as e:
            messages.error(request, f'Error creating blueprint: {e}')
            return redirect('blueprint_create')


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT PAPER PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
@login_required
def blueprint_paper_preview(request, group_id):
    group  = get_object_or_404(BlueprintPaperGroup, group_id=group_id)
    from papers.models import GeneratedPaper
    papers = (GeneratedPaper.objects
              .filter(paper_group_id=group_id)
              .prefetch_related('paper_questions__question__answers')
              .order_by('set_name'))
    return render(request, 'departments/blueprint_paper_preview.html', {
        'group': group, 'blueprint': group.blueprint,
        'papers': papers, 'group_id': group_id, 'active_page': 'bp_generate'})


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT HISTORY
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class BlueprintHistoryView(View):
    def get(self, request):
        groups = (BlueprintPaperGroup.objects
                  .filter(faculty=request.user)
                  .select_related('blueprint__department', 'blueprint__category',
                                  'blueprint__course', 'blueprint__subject')
                  .order_by('-generated_at'))
        return render(request, 'departments/blueprint_history.html', {
            'groups': groups, 'active_page': 'bp_generate'})


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT LIST ("Generated Blueprints")
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class BlueprintListView(View):
    def get(self, request):

        blueprints = (
            ExamBlueprint.objects
            .filter(is_active=True)
            .select_related(
                'department',
                'category',
                'course',
                'subject'
            )
            .order_by('-created_at')
        )

        return render(
            request,
            'departments/blueprint_list.html',
            {
                'blueprints': blueprints,
                'active_page': 'bp_list',
            }
        )


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT DELETE (safe: soft delete)
# ══════════════════════════════════════════════════════════════════════════════
@method_decorator(login_required, name='dispatch')
class BlueprintDeleteView(View):
    def post(self, request, blueprint_id):
        bp = get_object_or_404(ExamBlueprint, id=blueprint_id, is_active=True)
        bp.is_active = False
        bp.save(update_fields=['is_active'])
        messages.success(request, 'Blueprint deleted successfully.')
        return redirect('blueprint_list')


# ══════════════════════════════════════════════════════════════════════════════
# AJAX CASCADE SELECTORS
# ══════════════════════════════════════════════════════════════════════════════
@login_required
def api_categories(request, dept_id):
    cats = ExamCategory.objects.filter(department_id=dept_id, is_active=True).order_by('order', 'name')
    return JsonResponse({'categories': [{'id': c.id, 'name': c.name} for c in cats]})


@login_required
def api_courses(request, dept_id, cat_id):
    # Return all courses for the department (not just those with blueprints)
    # This allows creating new blueprints for any course
    dept = get_object_or_404(Department, id=dept_id, is_active=True)
    courses = Course.objects.filter(department__iexact=dept.name).order_by('course_code')
    return JsonResponse({'courses': [
        {'id': c.id, 'code': c.course_code, 'name': c.course_name} for c in courses]})


@login_required
def api_subjects(request, dept_id, cat_id, course_id):
    # Return all subjects for the course (not just those with blueprints)
    # This allows creating new blueprints for any subject
    subjects = Subject.objects.filter(course_id=course_id, is_active=True).order_by('name')
    return JsonResponse({'subjects': [{'id': s.id, 'name': s.name} for s in subjects]})


@login_required
def api_blueprint(request, dept_id, cat_id, course_id, subject_id):
    # Convert IDs to integers for proper comparison
    try:
        dept_id = int(dept_id)
        cat_id = int(cat_id)
        course_id = int(course_id)
        subject_id = int(subject_id)
    except (ValueError, TypeError):
        return JsonResponse({'found': False, 'error': 'Invalid ID format'})
    
    bp_id = request.GET.get('bp_id')
    paper_type = (request.GET.get('paper_type') or '').strip()

    qs = ExamBlueprint.objects.filter(
        department_id=dept_id, category_id=cat_id,
        course_id=course_id, subject_id=subject_id, is_active=True)

    if paper_type:
        qs = qs.filter(paper_type=paper_type)

    if bp_id:
        bp = qs.filter(id=bp_id).first()
    else:
        bp = qs.order_by('-created_at').first()
    
    if not bp:
        # Debug: check if any blueprints exist for this dept
        all_bps = ExamBlueprint.objects.filter(department_id=dept_id, is_active=True).values(
            'id', 'department_id', 'category_id', 'course_id', 'subject_id'
        )
        return JsonResponse({
            'found': False, 
            'searched': {'dept': dept_id, 'cat': cat_id, 'course': course_id, 'subject': subject_id},
            'existing_blueprints_for_dept': list(all_bps)
        })
    
    avail = bp.check_availability()
    return JsonResponse({
        'found': True, 'blueprint_id': bp.id,
        'mcq_count': bp.mcq_count, 'mcq_marks': bp.mcq_marks,
        'mcq_total': bp.mcq_total_marks,
        'descriptive_count': bp.descriptive_count,
        'descriptive_marks': bp.descriptive_marks,
        'desc_total': bp.descriptive_total_marks,
        'total_marks': bp.total_marks, 'total_questions': bp.total_questions,
        'duration': bp.duration_minutes, 'avail': avail,
    })


@login_required
def api_blueprints_list(request, dept_id):
    """List all blueprints for a department with their details."""
    blueprints = ExamBlueprint.objects.filter(
        department_id=dept_id, is_active=True
    ).select_related('category', 'course', 'subject')
    
    data = []
    for bp in blueprints:
        data.append({
            'id': bp.id,
            'category': bp.category.name,
            'category_id': bp.category.id,
            'course': bp.course.course_code,
            'course_id': bp.course.id,
            'subject': bp.subject.name,
            'subject_id': bp.subject.id,
            'mcq_count': bp.mcq_count,
            'descriptive_count': bp.descriptive_count,
        })
    
    return JsonResponse({'count': len(data), 'blueprints': data})
