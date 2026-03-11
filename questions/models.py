"""
Questions Models
Tables: dj_questions, dj_question_category
"""
from django.db import models
from courses.models import Course, Quiz


class QuestionCategory(models.Model):
    """
    Question Category model
    Table: dj_question_category
    """
    name = models.CharField(max_length=255)
    moodle_category_id = models.BigIntegerField(null=True, blank=True, unique=True)
    difficulty = models.CharField(max_length=16)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_question_category'
        verbose_name = 'Question Category'
        verbose_name_plural = 'Question Categories'
        managed = False

    def __str__(self):
        return self.name


class Question(models.Model):
    """
    Question model synced from Moodle
    Table: dj_questions
    """
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    QUESTION_TYPE_CHOICES = [
        ('multichoice', 'Multiple Choice'),
        ('truefalse', 'True/False'),
        ('shortanswer', 'Short Answer'),
        ('essay', 'Essay'),
        ('numerical', 'Numerical'),
        ('matching', 'Matching'),
        ('calculated', 'Calculated'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    category = models.ForeignKey(QuestionCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    question_text = models.TextField(db_column='text')
    question_type = models.CharField(max_length=64, choices=QUESTION_TYPE_CHOICES)
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_CHOICES, default='medium')
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    answer_data = models.JSONField(db_column='answer_data')

    moodle_question_id = models.BigIntegerField(null=True, blank=True, unique=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        managed = False

    def __str__(self):
        return f"Q{self.id}: {self.question_text[:80]}..."

    @property
    def short_text(self):
        return self.question_text[:120] + '...' if len(self.question_text) > 120 else self.question_text
