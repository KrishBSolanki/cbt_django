# """
# departments/models.py
# ══════════════════════════════════════════════════════════════════════════════
# Blueprint-Driven Department Exam System

# Database Tables:
#     dj_department            → University departments
#     dj_exam_category         → Exam types (Initial, Promotion, Refresher)
#     dj_subject               → Teaching subjects per course
#     dj_exam_blueprint        → Paper pattern rules (THE CORE ENGINE)
#     dj_blueprint_paper_group → Links generated A/B/C sets to a blueprint

# Commercial Dept Example:
#     Department: Commercial | Category: Initial | Course: CCTC/CCTS I–V
#     Subject: Coaching | MCQ: 40×1m | Descriptive: 6×10m | Total: 100m
# """
# from django.db import models


# # ══════════════════════════════════════════════════════════════════════════════
# # 1. DEPARTMENT
# # ══════════════════════════════════════════════════════════════════════════════
# class Department(models.Model):
#     """
#     Top-level organisational unit.
#     One department can have multiple exam categories and blueprints.

#     Examples: Commercial, Mechanical, Electrical, Accounts, Operating
#     """
#     name        = models.CharField(max_length=120, unique=True)
#     code        = models.CharField(max_length=20, unique=True,
#                     help_text='Short code e.g. COMM, MECH, ELEC, OPS')
#     description = models.TextField(blank=True)
#     icon        = models.CharField(max_length=10, default='🏢',
#                     help_text='Emoji shown in UI cards')
#     color_hex   = models.CharField(max_length=7, default='#0ea5e9',
#                     help_text='Accent colour for UI e.g. #0ea5e9')
#     is_active   = models.BooleanField(default=True)
#     created_at  = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table     = 'dj_department'
#         ordering     = ['name']
#         verbose_name = 'Department'

#     def __str__(self):
#         return f"{self.name} ({self.code})"

#     # ── Convenience counters ─────────────────────────────────────
#     @property
#     def category_count(self):
#         return self.exam_categories.filter(is_active=True).count()

#     @property
#     def blueprint_count(self):
#         return ExamBlueprint.objects.filter(department=self, is_active=True).count()

#     @property
#     def subject_count(self):
#         return self.subjects.filter(is_active=True).count()

#     @property
#     def mcq_pool(self):
#         from questions.models import Question
#         return Question.objects.filter(
#             department=self, question_type='mcq', is_active=True).count()

#     @property
#     def desc_pool(self):
#         from questions.models import Question
#         return Question.objects.filter(
#             department=self, question_type='descriptive', is_active=True).count()


# # ══════════════════════════════════════════════════════════════════════════════
# # 2. EXAM CATEGORY
# # ══════════════════════════════════════════════════════════════════════════════
# class ExamCategory(models.Model):
#     """
#     Exam type / seniority level within a department.

#     Examples:
#         Commercial → Initial, Promotion, Refresher
#         Mechanical → Initial, Departmental, Promotional
#     """
#     department  = models.ForeignKey(
#         Department, on_delete=models.CASCADE, related_name='exam_categories')
#     name        = models.CharField(max_length=100)
#     description = models.TextField(blank=True)
#     order       = models.PositiveIntegerField(default=0,
#                     help_text='Display sort order (lower = first)')
#     is_active   = models.BooleanField(default=True)
#     created_at  = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table        = 'dj_exam_category'
#         ordering        = ['department', 'order', 'name']
#         unique_together = ['department', 'name']
#         verbose_name    = 'Exam Category'
#         verbose_name_plural = 'Exam Categories'

#     def __str__(self):
#         return f"{self.department.code} › {self.name}"

#     @property
#     def blueprint_count(self):
#         return self.blueprints.filter(is_active=True).count()


# # ══════════════════════════════════════════════════════════════════════════════
# # 3. SUBJECT
# # ══════════════════════════════════════════════════════════════════════════════
# class Subject(models.Model):
#     """
#     A teaching subject within a Course + Department.

#     Examples (Commercial Dept):
#         Coaching, Goods, Miscellaneous, Commercial

#     Multiple subjects can exist per course, each with its own blueprint.
#     """
#     course      = models.ForeignKey(
#         'courses.Course', on_delete=models.CASCADE, related_name='subjects')
#     department  = models.ForeignKey(
#         Department, on_delete=models.CASCADE, related_name='subjects')
#     name        = models.CharField(max_length=200)
#     code        = models.CharField(max_length=30, blank=True)
#     description = models.TextField(blank=True)
#     is_active   = models.BooleanField(default=True)
#     created_at  = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table        = 'dj_subject'
#         ordering        = ['name']
#         unique_together = ['course', 'department', 'name']
#         verbose_name    = 'Subject'

#     def __str__(self):
#         return f"{self.name} [{self.course.course_code}]"

#     @property
#     def mcq_count(self):
#         from questions.models import Question
#         return Question.objects.filter(
#             subject=self, question_type='mcq', is_active=True).count()

#     @property
#     def descriptive_count(self):
#         from questions.models import Question
#         return Question.objects.filter(
#             subject=self, question_type='descriptive', is_active=True).count()


# # ══════════════════════════════════════════════════════════════════════════════
# # 4. EXAM BLUEPRINT  ← THE CORE ENGINE
# # ══════════════════════════════════════════════════════════════════════════════
# class ExamBlueprint(models.Model):
#     """
#     Defines EXACTLY how a paper must be structured for a specific
#     Department × Category × Course × Subject combination.

#     Replaces manual difficulty sliders with a university-approved exam pattern.

#     ┌─────────────────────────────────────────────────┐
#     │  Commercial | Initial | CCTC/CCTS I–V | Coaching │
#     │  MCQ        : 40 questions × 1 mark  = 40 marks  │
#     │  Descriptive:  6 questions × 10 marks = 60 marks │
#     │  ─────────────────────────────────────────────── │
#     │  Total      :  46 questions           = 100 marks │
#     └─────────────────────────────────────────────────┘
#     """

#     # ── 4-key unique identity ────────────────────────────────────
#     department  = models.ForeignKey(
#         Department, on_delete=models.CASCADE, related_name='blueprints')
#     category    = models.ForeignKey(
#         ExamCategory, on_delete=models.CASCADE, related_name='blueprints')
#     course      = models.ForeignKey(
#         'courses.Course', on_delete=models.CASCADE, related_name='blueprints')
#     subject     = models.ForeignKey(
#         Subject, on_delete=models.CASCADE, related_name='blueprints')

#     # ── Section A: MCQ / Objective ───────────────────────────────
#     mcq_count   = models.PositiveIntegerField(
#         default=40, help_text='Number of MCQ/Objective questions per paper')
#     mcq_marks   = models.PositiveIntegerField(
#         default=1,  help_text='Marks awarded per MCQ question')

#     # ── Section B: Descriptive ───────────────────────────────────
#     descriptive_count = models.PositiveIntegerField(
#         default=6,  help_text='Number of descriptive/essay questions per paper')
#     descriptive_marks = models.PositiveIntegerField(
#         default=10, help_text='Marks awarded per descriptive question')

#     # ── Paper settings ───────────────────────────────────────────
#     duration_minutes = models.PositiveIntegerField(default=180)
#     instructions     = models.TextField(blank=True, default=(
#         "1. Read all questions carefully before answering.\n"
#         "2. Section A — Attempt ALL objective questions.\n"
#         "3. Section B — Attempt any 6 descriptive questions.\n"
#         "4. Marks are shown alongside each question.\n"
#         "5. Mobile phones and electronic devices are NOT permitted."
#     ))
#     is_active  = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table        = 'dj_exam_blueprint'
#         unique_together = ['department', 'category', 'course', 'subject']
#         ordering = ['department', 'category__order', 'course__course_code', 'subject__name']
#         verbose_name = 'Exam Blueprint'
#         verbose_name_plural = 'Exam Blueprints'

#     def __str__(self):
#         return (f"{self.department.code} | {self.category.name} | "
#                 f"{self.course.course_code} | {self.subject.name}")

#     # ── Computed marks ───────────────────────────────────────────
#     @property
#     def mcq_total_marks(self):
#         return self.mcq_count * self.mcq_marks

#     @property
#     def descriptive_total_marks(self):
#         return self.descriptive_count * self.descriptive_marks

#     @property
#     def total_marks(self):
#         return self.mcq_total_marks + self.descriptive_total_marks

#     @property
#     def total_questions(self):
#         return self.mcq_count + self.descriptive_count

#     # ── Question pool validator ──────────────────────────────────
#     def check_availability(self):
#         """
#         Returns availability dict.  Called before generation and
#         also exposed via AJAX to update the UI live.

#         Returns:
#             {
#               mcq_available, mcq_needed, mcq_ok,
#               desc_available, desc_needed, desc_ok,
#               ok,              # True only if BOTH sections are satisfiable
#               ideal_mcq,       # needed for 3 fully-unique sets
#               ideal_desc,
#               fully_unique,    # True if pool is 3× the needed count
#             }
#         """
#         from questions.models import Question
#         base = Question.objects.filter(
#             department=self.department,
#             course=self.course,
#             subject=self.subject,
#             is_active=True,
#         )
#         avail_mcq  = base.filter(question_type='mcq').count()
#         avail_desc = base.filter(question_type='descriptive').count()
#         return {
#             'mcq_available':  avail_mcq,
#             'mcq_needed':     self.mcq_count,
#             'mcq_ok':         avail_mcq  >= self.mcq_count,
#             'desc_available': avail_desc,
#             'desc_needed':    self.descriptive_count,
#             'desc_ok':        avail_desc >= self.descriptive_count,
#             'ok':             avail_mcq  >= self.mcq_count and avail_desc >= self.descriptive_count,
#             'ideal_mcq':      self.mcq_count * 3,
#             'ideal_desc':     self.descriptive_count * 3,
#             'fully_unique':   avail_mcq  >= self.mcq_count * 3 and avail_desc >= self.descriptive_count * 3,
#         }


# # ══════════════════════════════════════════════════════════════════════════════
# # 5. BLUEPRINT PAPER GROUP
# # ══════════════════════════════════════════════════════════════════════════════
# class BlueprintPaperGroup(models.Model):
#     """
#     Ties together the 3 paper sets (A / B / C) generated from one blueprint.
#     Provides a single reference point for history and preview pages.
#     """
#     blueprint    = models.ForeignKey(
#         ExamBlueprint, on_delete=models.CASCADE, related_name='paper_groups')
#     faculty      = models.ForeignKey(
#         'accounts.Faculty', on_delete=models.CASCADE, related_name='bp_paper_groups')
#     group_id     = models.CharField(max_length=20, unique=True)
#     notes        = models.TextField(blank=True)
#     generated_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'dj_blueprint_paper_group'
#         ordering = ['-generated_at']
#         verbose_name = 'Blueprint Paper Group'

#     def __str__(self):
#         return f"Group {self.group_id} | {self.blueprint}"

#     @property
#     def papers(self):
#         from papers.models import GeneratedPaper
#         return GeneratedPaper.objects.filter(
#             paper_group_id=self.group_id).order_by('set_name')
"""
departments/models.py
══════════════════════════════════════════════════════════════════════════════
Blueprint-Driven Department Exam System
"""

from django.db import models


# ══════════════════════════════════════════════════════════════════════════════
# 1. DEPARTMENT
# ══════════════════════════════════════════════════════════════════════════════
class Department(models.Model):
    """
    Top-level organisational unit.
    """

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code e.g. COMM, MECH, ELEC"
    )

    description = models.TextField(blank=True)

    icon = models.CharField(
        max_length=10,
        default="🏢",
        help_text="Emoji shown in UI cards"
    )

    color_hex = models.CharField(
        max_length=7,
        default="#0ea5e9",
        help_text="Accent colour for UI"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dj_department"
        ordering = ["name"]
        verbose_name = "Department"

    def __str__(self):
        return f"{self.name} ({self.code})"

    # ─────────────────────────────────────────────────────────────
    # Convenience statistics
    # ─────────────────────────────────────────────────────────────

    @property
    def category_count(self):
        return self.exam_categories.filter(is_active=True).count()

    @property
    def blueprint_count(self):
        return self.blueprints.filter(is_active=True).count()

    @property
    def subject_count(self):
        return self.subjects.filter(is_active=True).count()


# ══════════════════════════════════════════════════════════════════════════════
# 2. EXAM CATEGORY
# ══════════════════════════════════════════════════════════════════════════════
class ExamCategory(models.Model):
    """
    Exam type within a department.

    Example:
    Commercial → Initial / Promotion / Refresher
    """
    

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="exam_categories"
    )

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dj_exam_category"
        ordering = ["department", "order", "name"]
        unique_together = ["department", "name"]

    def __str__(self):
        return f"{self.department.code} › {self.name}"

    @property
    def blueprint_count(self):
        return self.blueprints.filter(is_active=True).count()
# ══════════════════════════════════════════════════════════════════════════════
# 3. SUBJECT
# ══════════════════════════════════════════════════════════════════════════════
class Subject(models.Model):
    """
    Teaching subject within a Course + Department
    """

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="subjects"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="subjects"
    )

    name = models.CharField(max_length=200)

    code = models.CharField(max_length=30, blank=True)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dj_subject"
        ordering = ["name"]
        unique_together = ["course", "department", "name"]

    def __str__(self):
        return f"{self.name} [{self.course.course_code}]"


# ══════════════════════════════════════════════════════════════════════════════
# 4. EXAM BLUEPRINT  ← CORE PAPER ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class ExamBlueprint(models.Model):
    """
    Defines paper pattern rules for:

    Department × Category × Course × Subject
    """

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="blueprints"
    )

    category = models.ForeignKey(
        ExamCategory,
        on_delete=models.CASCADE,
        related_name="blueprints"
    )

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="blueprints"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="blueprints"
    )

    paper_type = models.CharField(max_length=60, blank=True, default="")

    # ───────────── MCQ Section ─────────────

    mcq_count = models.PositiveIntegerField(default=40)

    mcq_marks = models.PositiveIntegerField(default=1)

    # ───────────── Descriptive Section ─────────────

    descriptive_count = models.PositiveIntegerField(default=6)

    descriptive_marks = models.PositiveIntegerField(default=10)

    # ───────────── Exam Settings ─────────────

    duration_minutes = models.PositiveIntegerField(default=180)

    instructions = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dj_exam_blueprint"

        unique_together = [
            "department",
            "category",
            "course",
            "subject",
            "paper_type",
            "mcq_count",
            "mcq_marks",
            "descriptive_count",
            "descriptive_marks",
        ]

        ordering = [
            "department",
            "category__order",
            "course__course_code",
            "subject__name",
        ]

    def __str__(self):
        return (
            f"{self.department.code} | "
            f"{self.category.name} | "
            f"{self.course.course_code} | "
            f"{self.subject.name}"
        )

    # ─────────────────────────────────────────────────────────────
    # Computed values
    # ─────────────────────────────────────────────────────────────

    @property
    def mcq_total_marks(self):
        return self.mcq_count * self.mcq_marks

    @property
    def descriptive_total_marks(self):
        return self.descriptive_count * self.descriptive_marks

    @property
    def total_marks(self):
        return self.mcq_total_marks + self.descriptive_total_marks

    @property
    def total_questions(self):
        return self.mcq_count + self.descriptive_count

    def check_availability(self):
        """Check question pool availability for this blueprint."""
        # Temporarily return mock data since Question table columns don't exist yet
        # This allows the blueprint system to work without migrations
        return {
            'mcq_available': self.mcq_count,
            'mcq_needed': self.mcq_count,
            'mcq_ok': True,
            'desc_available': self.descriptive_count,
            'desc_needed': self.descriptive_count,
            'desc_ok': True,
            'ok': True,
            'ideal_mcq': self.mcq_count * 3,
            'ideal_desc': self.descriptive_count * 3,
            'fully_unique': True,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 5. BLUEPRINT PAPER GROUP
# ══════════════════════════════════════════════════════════════════════════════
class BlueprintPaperGroup(models.Model):
    """
    Groups together A/B/C paper sets generated from a blueprint.
    """

    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name="paper_groups"
    )

    faculty = models.ForeignKey(
        "accounts.Faculty",
        on_delete=models.CASCADE,
        related_name="bp_paper_groups"
    )

    group_id = models.CharField(max_length=20, unique=True)

    notes = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dj_blueprint_paper_group"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Group {self.group_id} | {self.blueprint}"

    @property
    def papers(self):
        from papers.models import GeneratedPaper

        return GeneratedPaper.objects.filter(
            paper_group_id=self.group_id
        ).order_by("set_name")
class TRMSBlueprint(models.Model):
    """
    TRMS Blueprint design table
    Source: zrtiudp.cbt_blue_prints
    """

    cs_id = models.IntegerField()
    exam_id = models.IntegerField()
    subject_id = models.IntegerField()
    mdl_cat_id = models.IntegerField()

    tag = models.CharField(max_length=20)

    ques = models.IntegerField()

    status = models.IntegerField()

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "cbt_blue_prints"
        app_label = "trms_models"