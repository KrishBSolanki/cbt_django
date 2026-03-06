"""
Papers Models - Generated Question Papers
Tables: dj_generated_papers, dj_paper_questions
"""
from django.db import models
from accounts.models import Faculty
from courses.models import Course, Quiz
from questions.models import Question


class GeneratedPaper(models.Model):
    """
    Generated Question Paper
    Table: dj_generated_papers
    """
    SET_CHOICES = [
        ('A', 'Set A'),
        ('B', 'Set B'),
        ('C', 'Set C'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('approved', 'Approved'),
        ('published', 'Published'),
    ]

    paper_id = models.CharField(max_length=20, unique=True, editable=False)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='generated_papers')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='papers')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='papers', null=True, blank=True)

    set_name = models.CharField(max_length=1, choices=SET_CHOICES)
    title = models.CharField(max_length=300, blank=True)
    total_questions = models.IntegerField(default=30)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Difficulty distribution (percentages)
    easy_percentage = models.IntegerField(default=40)
    medium_percentage = models.IntegerField(default=40)
    hard_percentage = models.IntegerField(default=20)

    # Actual counts
    easy_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    hard_count = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')

    # Metadata
    exam_date = models.DateField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=180)
    instructions = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Group ID to link Set A, B, C together
    paper_group_id = models.CharField(max_length=50, blank=True, help_text='Groups related A/B/C sets')

    class Meta:
        db_table = 'dj_generated_papers'
        verbose_name = 'Generated Paper'
        verbose_name_plural = 'Generated Papers'
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.paper_id} - {self.course.course_code} Set {self.set_name}"

    def save(self, *args, **kwargs):
        if not self.paper_id:
            import datetime
            import random
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M')
            rand = random.randint(100, 999)
            self.paper_id = f"EP{timestamp}{rand}{self.set_name}"
        if not self.title:
            self.title = f"{self.course.course_name} - Set {self.set_name}"
        super().save(*args, **kwargs)


class PaperQuestion(models.Model):
    """
    Questions included in a generated paper
    Table: dj_paper_questions
    """
    paper = models.ForeignKey(GeneratedPaper, on_delete=models.CASCADE, related_name='paper_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='paper_appearances')
    question_number = models.IntegerField()
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    class Meta:
        db_table = 'dj_paper_questions'
        unique_together = ['paper', 'question']
        ordering = ['question_number']

    def __str__(self):
        return f"Paper {self.paper.paper_id} - Q{self.question_number}"
