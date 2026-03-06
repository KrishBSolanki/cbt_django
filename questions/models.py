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
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    moodle_category_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dj_question_category'
        verbose_name = 'Question Category'
        verbose_name_plural = 'Question Categories'

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

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    category = models.ForeignKey(QuestionCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multichoice')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')

    # Moodle sync
    moodle_question_id = models.IntegerField(null=True, blank=True, unique=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dj_questions'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"Q{self.id}: {self.question_text[:80]}..."

    @property
    def short_text(self):
        return self.question_text[:120] + '...' if len(self.question_text) > 120 else self.question_text


class QuestionAnswer(models.Model):
    """
    Answer options for questions
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    fraction = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    feedback = models.TextField(blank=True)
    moodle_answer_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'dj_question_answers'

    def __str__(self):
        return f"{'✓' if self.is_correct else '✗'} {self.answer_text[:50]}"
