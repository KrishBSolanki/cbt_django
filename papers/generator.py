"""
Paper Generation Algorithm
Generates 3 shuffled paper sets (A, B, C)
All sets contain SAME questions but shuffled order
"""

import random
import uuid
import math
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


def calculate_difficulty_counts(total_questions, easy_pct, medium_pct, hard_pct):
    """
    Calculate question count per difficulty.
    Ensures totals match exactly.
    """

    easy_count = math.floor(total_questions * easy_pct / 100)
    medium_count = math.floor(total_questions * medium_pct / 100)
    hard_count = total_questions - easy_count - medium_count

    return easy_count, medium_count, hard_count


def fetch_base_questions(course, quiz, total_questions, easy_pct, medium_pct, hard_pct):
    """
    Select base questions once for all paper sets.
    """

    from questions.models import Question

    easy_count, medium_count, hard_count = calculate_difficulty_counts(
        total_questions,
        easy_pct,
        medium_pct,
        hard_pct,
    )

    base_qs = Question.objects.filter(
        is_active=True,
        course_id=course.id,
    )

    if quiz:
        base_qs = base_qs.filter(quiz_id=quiz.id)

    easy_pool = list(base_qs.filter(difficulty="easy"))
    medium_pool = list(base_qs.filter(difficulty="medium"))
    hard_pool = list(base_qs.filter(difficulty="hard"))

    if len(easy_pool) < easy_count:
        raise ValueError(f"Not enough easy questions ({len(easy_pool)} available, {easy_count} needed)")

    if len(medium_pool) < medium_count:
        raise ValueError(f"Not enough medium questions ({len(medium_pool)} available, {medium_count} needed)")

    if len(hard_pool) < hard_count:
        raise ValueError(f"Not enough hard questions ({len(hard_pool)} available, {hard_count} needed)")

    easy_questions = random.sample(easy_pool, easy_count)
    medium_questions = random.sample(medium_pool, medium_count)
    hard_questions = random.sample(hard_pool, hard_count)

    base_questions = easy_questions + medium_questions + hard_questions

    return base_questions


def create_paper(course, quiz, faculty, group_id, set_name, questions, easy_pct, medium_pct, hard_pct):
    """
    Create a paper with shuffled questions.
    """

    from papers.models import GeneratedPaper, PaperQuestion

    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)

    total_marks = sum(float(q.marks) for q in shuffled_questions)

    easy_count = len([q for q in shuffled_questions if q.difficulty == "easy"])
    medium_count = len([q for q in shuffled_questions if q.difficulty == "medium"])
    hard_count = len([q for q in shuffled_questions if q.difficulty == "hard"])

    with transaction.atomic():

        paper = GeneratedPaper.objects.create(
            faculty=faculty,
            course=course,
            quiz=quiz,
            set_name=set_name,
            total_questions=len(shuffled_questions),
            total_marks=total_marks,
            easy_percentage=easy_pct,
            medium_percentage=medium_pct,
            hard_percentage=hard_pct,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count,
            paper_group_id=group_id,
            status="generated",
        )

        paper_questions = []

        for idx, q in enumerate(shuffled_questions):
            paper_questions.append(
                PaperQuestion(
                    paper=paper,
                    question=q,
                    question_number=idx + 1,
                    marks=q.marks,
                )
            )

        PaperQuestion.objects.bulk_create(paper_questions)

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
    Generate Sets A, B, C using SAME base questions but shuffled order.
    """

    if easy_pct + medium_pct + hard_pct != 100:
        raise ValueError("Difficulty percentages must equal 100")

    base_questions = fetch_base_questions(
        course,
        quiz,
        total_questions,
        easy_pct,
        medium_pct,
        hard_pct,
    )

    group_id = str(uuid.uuid4())[:12].upper()

    papers = []

    for set_name in ["A", "B", "C"]:

        paper = create_paper(
            course=course,
            quiz=quiz,
            faculty=faculty,
            group_id=group_id,
            set_name=set_name,
            questions=base_questions,
            easy_pct=easy_pct,
            medium_pct=medium_pct,
            hard_pct=hard_pct,
        )

        papers.append(paper)

    from integration.sync import push_questions_to_quiz

# ------------------------------------------------
# PUSH QUESTIONS TO MOODLE QUIZ
# ------------------------------------------------

    if quiz:

        try:

            # Use Set A only
            set_a_paper = papers[0]

            question_ids = [
                pq.question.moodle_question_id
                for pq in set_a_paper.paper_questions.all()
                if pq.question.moodle_question_id
            ]

            if question_ids:

                push_questions_to_quiz(
                    quiz.moodle_quiz_id,
                    question_ids
                )

                logger.info(
                    f"Pushed {len(question_ids)} questions to Moodle quiz {quiz.moodle_quiz_id}"
                )

        except Exception as e:

            logger.error(f"Moodle push failed: {str(e)}")


    return {
        "papers": papers,
        "group_id": group_id,
        "warnings": [],
    }


def generate_blueprint_paper(blueprint, faculty):
    """
    Blueprint-driven paper generation wrapper.
    
    Generates 3 paper sets (A, B, C) based on an ExamBlueprint configuration.
    This is a convenience wrapper that delegates to departments.generator.
    
    Args:
        blueprint: ExamBlueprint instance from departments.models
        faculty: Faculty user generating the paper
        
    Returns:
        dict: {
            'papers': [GeneratedPaper_A, GeneratedPaper_B, GeneratedPaper_C],
            'group_id': str,
            'warnings': [str, ...],
            'blueprint': ExamBlueprint
        }
        
    Raises:
        ValueError: If question pool is insufficient for the blueprint requirements
    """
    from departments.generator import generate_blueprint_paper_sets
    return generate_blueprint_paper_sets(blueprint, faculty)