"""
Paper Generation Algorithm
Generates 3 random paper sets (A, B, C) with difficulty distribution
"""

import random
import uuid
import math
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


def calculate_difficulty_counts(total_questions, easy_pct, medium_pct, hard_pct):
    """
    Calculate number of questions per difficulty level.
    Ensures total matches exactly using rounding correction.
    """
    easy_count = math.floor(total_questions * easy_pct / 100)
    medium_count = math.floor(total_questions * medium_pct / 100)
    hard_count = total_questions - easy_count - medium_count
    return easy_count, medium_count, hard_count


def get_questions_by_difficulty(course, quiz, difficulty, count, exclude_ids=None):
    """
    Fetch random questions of specific difficulty.
    """

    from questions.models import Question

    qs = Question.objects.filter(
        is_active=True,
        difficulty=difficulty,
        course_id=course.id,   # ALWAYS filter by course
    )

    # Optional quiz filter
    if quiz:
        qs = qs.filter(quiz_id=quiz.id)

    # Exclude already selected
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)

    # Random selection
    question_list = list(qs.order_by('?')[: count * 2])
    random.shuffle(question_list)

    return question_list[:count]


def generate_paper_set(
    course,
    quiz,
    set_name,
    total_questions,
    easy_pct,
    medium_pct,
    hard_pct,
    faculty,
    group_id,
    exclude_ids=None,
):
    """
    Generate a single paper set.
    """

    from papers.models import GeneratedPaper, PaperQuestion

    if exclude_ids is None:
        exclude_ids = set()

    easy_count, medium_count, hard_count = calculate_difficulty_counts(
        total_questions, easy_pct, medium_pct, hard_pct
    )

    easy_questions = get_questions_by_difficulty(
        course, quiz, "easy", easy_count, exclude_ids
    )

    medium_questions = get_questions_by_difficulty(
        course, quiz, "medium", medium_count, exclude_ids
    )

    hard_questions = get_questions_by_difficulty(
        course, quiz, "hard", hard_count, exclude_ids
    )

    # Logging warnings
    if len(easy_questions) < easy_count:
        logger.warning(
            f"Set {set_name}: Only {len(easy_questions)} easy questions available (needed {easy_count})"
        )

    if len(medium_questions) < medium_count:
        logger.warning(
            f"Set {set_name}: Only {len(medium_questions)} medium questions available (needed {medium_count})"
        )

    if len(hard_questions) < hard_count:
        logger.warning(
            f"Set {set_name}: Only {len(hard_questions)} hard questions available (needed {hard_count})"
        )

    # Combine questions
    all_questions = easy_questions + medium_questions + hard_questions
    random.shuffle(all_questions)

    total_marks = sum(float(q.marks) for q in all_questions)

    with transaction.atomic():

        paper = GeneratedPaper.objects.create(
            faculty=faculty,
            course=course,
            quiz=quiz,
            set_name=set_name,
            total_questions=len(all_questions),
            total_marks=total_marks,
            easy_percentage=easy_pct,
            medium_percentage=medium_pct,
            hard_percentage=hard_pct,
            easy_count=len(easy_questions),
            medium_count=len(medium_questions),
            hard_count=len(hard_questions),
            paper_group_id=group_id,
            status="generated",
        )

        paper_questions = []

        for idx, q in enumerate(all_questions):
            paper_questions.append(
                PaperQuestion(
                    paper=paper,
                    question=q,
                    question_number=idx + 1,
                    marks=q.marks,
                )
            )

        PaperQuestion.objects.bulk_create(paper_questions)

    exclude_ids.update(q.id for q in all_questions)

    return paper


def generate_three_paper_sets(
    course,
    quiz,
    total_questions,
    easy_pct,
    medium_pct,
    hard_pct,
    faculty,
):
    """
    Generate Paper Sets A, B, C
    """

    from questions.models import Question

    if easy_pct + medium_pct + hard_pct != 100:
        raise ValueError("Difficulty percentages must sum to 100%")

    # Base queryset
    base_qs = Question.objects.filter(
        is_active=True,
        course_id=course.id,   # ALWAYS filter by course
    )

    if quiz:
        base_qs = base_qs.filter(quiz_id=quiz.id)

    easy_count, medium_count, hard_count = calculate_difficulty_counts(
        total_questions,
        easy_pct,
        medium_pct,
        hard_pct,
    )

    available_easy = base_qs.filter(difficulty="easy").count()
    available_medium = base_qs.filter(difficulty="medium").count()
    available_hard = base_qs.filter(difficulty="hard").count()

    needed_easy = easy_count * 3
    needed_medium = medium_count * 3
    needed_hard = hard_count * 3

    warnings = []

    if available_easy < needed_easy:
        warnings.append(
            f"Only {available_easy} easy questions available (ideal: {needed_easy})"
        )

    if available_medium < needed_medium:
        warnings.append(
            f"Only {available_medium} medium questions available (ideal: {needed_medium})"
        )

    if available_hard < needed_hard:
        warnings.append(
            f"Only {available_hard} hard questions available (ideal: {needed_hard})"
        )

    if (
        available_easy < easy_count
        or available_medium < medium_count
        or available_hard < hard_count
    ):
        raise ValueError(
            f"Insufficient questions. Available: {available_easy} easy, {available_medium} medium, {available_hard} hard. "
            f"Minimum needed per set: {easy_count} easy, {medium_count} medium, {hard_count} hard."
        )

    group_id = str(uuid.uuid4())[:12].upper()

    papers = []
    exclude_ids = set()

    for set_name in ["A", "B", "C"]:

        paper = generate_paper_set(
            course=course,
            quiz=quiz,
            set_name=set_name,
            total_questions=total_questions,
            easy_pct=easy_pct,
            medium_pct=medium_pct,
            hard_pct=hard_pct,
            faculty=faculty,
            group_id=group_id,
            exclude_ids=exclude_ids,
        )

        papers.append(paper)

    return {
        "papers": papers,
        "group_id": group_id,
        "warnings": warnings,
    }