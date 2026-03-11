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
    course_code = models.CharField(max_length=50, unique=True, db_column='code')
    course_name = models.CharField(max_length=255, db_column='name')
    department = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    # External IDs for sync
    moodle_course_id = models.BigIntegerField(null=True, blank=True, unique=True)
    trms_course_id = models.BigIntegerField(null=True, blank=True, unique=True)

    # Faculty mapping
    faculty = models.ManyToManyField(Faculty, through='CourseFaculty', related_name='courses')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['course_code']
        managed = False

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
    quiz_name = models.CharField(max_length=255, db_column='title')
    description = models.TextField()
    moodle_quiz_id = models.BigIntegerField(null=True, blank=True)
    total_questions = models.PositiveIntegerField()
    duration_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['quiz_name']
        managed = False

    def __str__(self):
        return f"{self.quiz_name} ({self.course.course_code})"

    @property
    def question_count(self):
        return self.questions.count()
