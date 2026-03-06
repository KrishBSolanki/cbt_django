"""
Courses Models
Tables: dj_courses, dj_quizzes
"""
from django.db import models
from accounts.models import Faculty


class Course(models.Model):
    """
    Course model synced from TRMS and Moodle
    Table: dj_courses
    """
    DEPARTMENT_CHOICES = [
        ('CSE', 'Computer Science & Engineering'),
        ('ECE', 'Electronics & Communication'),
        ('ME', 'Mechanical Engineering'),
        ('CE', 'Civil Engineering'),
        ('EEE', 'Electrical & Electronics'),
        ('IT', 'Information Technology'),
        ('MBA', 'Business Administration'),
        ('MCA', 'Computer Applications'),
        ('OTHER', 'Other'),
    ]

    SEMESTER_CHOICES = [(i, f'Semester {i}') for i in range(1, 9)]

    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default='CSE')
    semester = models.IntegerField(choices=SEMESTER_CHOICES, default=1)
    credits = models.IntegerField(default=3)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # External IDs for sync
    moodle_course_id = models.IntegerField(null=True, blank=True, unique=True)
    trms_course_id = models.IntegerField(null=True, blank=True)

    # Faculty mapping
    faculty = models.ManyToManyField(Faculty, through='CourseFaculty', related_name='courses')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    @property
    def quiz_count(self):
        return self.quizzes.count()

    @property
    def question_count(self):
        return self.questions.count()


class CourseFaculty(models.Model):
    """Junction table for Course-Faculty many-to-many"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dj_course_faculty'
        unique_together = ['course', 'faculty']


class Quiz(models.Model):
    """
    Quiz model synced from Moodle
    Table: dj_quizzes
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    quiz_name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    total_marks = models.IntegerField(default=0)
    time_limit = models.IntegerField(null=True, blank=True, help_text='Time in minutes')
    is_active = models.BooleanField(default=True)

    # Moodle sync
    moodle_quiz_id = models.IntegerField(null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['quiz_name']

    def __str__(self):
        return f"{self.quiz_name} ({self.course.course_code})"

    @property
    def question_count(self):
        return self.questions.count()
