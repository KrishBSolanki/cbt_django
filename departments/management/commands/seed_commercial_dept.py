"""
Management command to seed the Commercial Department with:
  - Department: Commercial
  - Categories: Initial, Promotion, Refresher
  - Course: Must exist (create sample if not)
  - Subjects: Coaching, Goods, Miscellaneous, Commercial
  - Blueprints: As per the blueprint sheet
"""
from django.core.management.base import BaseCommand
from departments.models import Department, ExamCategory, Subject, ExamBlueprint
from courses.models import Course


BLUEPRINT_DATA = [
    # (category_name, course_code, course_name, subject_name, mcq_count, mcq_marks, desc_count, desc_marks)
    ('Initial',    'CCTC-I',  'CCTC/CCTS I-V',   'Coaching',      40, 1, 6, 10),
    ('Initial',    'CCTC-I',  'CCTC/CCTS I-V',   'Goods',         40, 1, 6, 10),
    ('Initial',    'CCTC-I',  'CCTC/CCTS I-V',   'Miscellaneous', 40, 1, 6, 10),
    ('Promotion',  'CMI-II',  'CMI/CCTS II-V',   'Coaching',      40, 1, 6, 10),
    ('Promotion',  'CMI-II',  'CMI/CCTS II-V',   'Goods',         40, 1, 6, 10),
    ('Promotion',  'CMI-II',  'CMI/CCTS II-V',   'Miscellaneous', 40, 1, 6, 10),
    ('Refresher',  'CCTC-R',  'CCTC Refresher',  'Commercial',    40, 2, 3, 20),
]


class Command(BaseCommand):
    help = 'Seed Commercial Department blueprint data'

    def handle(self, *args, **options):
        # Create Department
        dept, created = Department.objects.get_or_create(
            code='COMM',
            defaults={'name': 'Commercial', 'icon': '🚂', 'color_hex': '#0ea5e9',
                      'description': 'Commercial department exam blueprints'})
        self.stdout.write(f"{'Created' if created else 'Found'} Department: {dept.name}")

        for cat_name, course_code, course_name, subj_name, mcq_c, mcq_m, desc_c, desc_m in BLUEPRINT_DATA:
            # Category
            cat, _ = ExamCategory.objects.get_or_create(
                department=dept, name=cat_name,
                defaults={'order': ['Initial','Promotion','Refresher'].index(cat_name)})

            # Course
            course, c = Course.objects.get_or_create(
                course_code=course_code,
                defaults={'course_name': course_name, 'department': 'OTHER'})

            # Subject
            subj, _ = Subject.objects.get_or_create(
                course=course, department=dept, name=subj_name)

            # Blueprint
            bp, created = ExamBlueprint.objects.get_or_create(
                department=dept, category=cat, course=course, subject=subj,
                defaults={
                    'mcq_count': mcq_c, 'mcq_marks': mcq_m,
                    'descriptive_count': desc_c, 'descriptive_marks': desc_m,
                })
            status = 'Created' if created else 'Exists '
            self.stdout.write(
                f"  {status} Blueprint: {cat_name} | {course_code} | {subj_name} "
                f"→ MCQ:{mcq_c}×{mcq_m}m  Desc:{desc_c}×{desc_m}m  = {mcq_c*mcq_m + desc_c*desc_m}M")

        self.stdout.write(self.style.SUCCESS('\n✅ Commercial Department seeded successfully!'))
        self.stdout.write('Run: python manage.py migrate && python manage.py seed_commercial_dept')
