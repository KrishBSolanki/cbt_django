"""
departments/generator.py
══════════════════════════════════════════════════════════════════════════════
Blueprint Paper Generation Engine

Generates 3 randomised paper sets (A / B / C) driven entirely by
ExamBlueprint rules — no manual sliders required.

Algorithm
─────────
1. Validate question pool against blueprint requirements
2. For each set A → B → C:
   a. Randomly pick  mcq_count  MCQ questions        (exclude used IDs)
   b. Randomly pick  desc_count Descriptive questions (exclude used IDs)
   c. Build ordered paper: MCQ first → Descriptive after
   d. Persist  GeneratedPaper  +  PaperQuestion  rows atomically
3. Save  BlueprintPaperGroup  linking all 3 sets
4. Return result dict to the view

Fallback behaviour
──────────────────
If the pool is too small for 3 fully unique sets (but large enough for 1),
questions may repeat across sets.  A warning is added — generation proceeds.
"""
import uuid
import random
import logging
from django.db import transaction

log = logging.getLogger(__name__)

# Question types treated as MCQ
_MCQ_TYPES   = {'mcq', 'multichoice', 'truefalse'}
# Question types treated as Descriptive
_DESC_TYPES  = {'descriptive', 'essay', 'shortanswer'}


# ─────────────────────────────────────────────────────────────────────────────
def _pick(blueprint, type_set, count, exclude_ids):
    """
    Randomly fetch `count` active questions matching the blueprint.
    Prefers questions NOT in exclude_ids; falls back to reusing them
    if the pool is too small.
    """
    from questions.models import Question

    qs = Question.objects.filter(
        department         = blueprint.department,
        course             = blueprint.course,
        subject            = blueprint.subject,
        question_type__in  = type_set,
        is_active          = True,
    )

    fresh   = list(qs.exclude(id__in=exclude_ids).order_by('?')[:count * 2])
    shortfall = count - len(fresh)

    if shortfall > 0:
        fresh_ids = {q.id for q in fresh}
        reused = list(
            qs.filter(id__in=exclude_ids)
              .exclude(id__in=fresh_ids)
              .order_by('?')[:shortfall]
        )
        fresh += reused

    random.shuffle(fresh)
    return fresh[:count]


def _marks_for(question, blueprint):
    return (blueprint.mcq_marks
            if question.question_type in _MCQ_TYPES
            else blueprint.descriptive_marks)


# ─────────────────────────────────────────────────────────────────────────────
def _save_set(blueprint, set_name, group_id, faculty, mcq_qs, desc_qs):
    """Persist one paper set atomically. Returns the GeneratedPaper."""
    from papers.models import GeneratedPaper, PaperQuestion

    all_qs      = list(mcq_qs) + list(desc_qs)
    total_marks = (len(mcq_qs)  * blueprint.mcq_marks +
                   len(desc_qs) * blueprint.descriptive_marks)
    title = (f"{blueprint.department.name} | {blueprint.category.name} | "
             f"{blueprint.course.course_code} | {blueprint.subject.name} — Set {set_name}")

    with transaction.atomic():
        paper = GeneratedPaper.objects.create(
            faculty           = faculty,
            course            = blueprint.course,
            set_name          = set_name,
            title             = title,
            total_questions   = len(all_qs),
            total_marks       = total_marks,
            duration_minutes  = blueprint.duration_minutes,
            instructions      = blueprint.instructions,
            paper_group_id    = group_id,
            status            = 'generated',
            # Reuse existing integer columns to store MCQ / Desc counts
            easy_count        = len(mcq_qs),
            medium_count      = len(desc_qs),
            hard_count        = 0,
            easy_percentage   = blueprint.mcq_marks,
            medium_percentage = blueprint.descriptive_marks,
            hard_percentage   = 0,
        )
        PaperQuestion.objects.bulk_create([
            PaperQuestion(
                paper           = paper,
                question        = q,
                question_number = idx + 1,
                marks           = _marks_for(q, blueprint),
            )
            for idx, q in enumerate(all_qs)
        ])

    log.info("Blueprint Set %s generated: paper_id=%s  MCQ=%d  Desc=%d",
             set_name, paper.paper_id, len(mcq_qs), len(desc_qs))
    return paper


# ─────────────────────────────────────────────────────────────────────────────
def generate_blueprint_paper_sets(blueprint, faculty):
    """
    Public entry point.

    Args:
        blueprint : ExamBlueprint instance (already validated by view)
        faculty   : Faculty (request.user)

    Returns:
        {
          'papers'   : [GeneratedPaper_A, _B, _C],
          'group_id' : 'BP-XXXXXXXX',
          'warnings' : [str, ...],
          'blueprint': ExamBlueprint,
        }

    Raises:
        ValueError  when the pool cannot fill even ONE set.
    """
    from departments.models import BlueprintPaperGroup

    # ── 1. Hard-fail check ───────────────────────────────────────
    avail = blueprint.check_availability()
    if not avail['mcq_ok']:
        raise ValueError(
            f"Not enough MCQ questions. "
            f"Need {avail['mcq_needed']}, "
            f"have {avail['mcq_available']} for subject '{blueprint.subject.name}'. "
            f"Add more MCQ questions via the Question Bank."
        )
    if not avail['desc_ok']:
        raise ValueError(
            f"Not enough Descriptive questions. "
            f"Need {avail['desc_needed']}, "
            f"have {avail['desc_available']} for subject '{blueprint.subject.name}'. "
            f"Add more Descriptive questions via the Question Bank."
        )

    # ── 2. Soft warnings for non-unique sets ─────────────────────
    warnings = []
    if not avail['fully_unique']:
        if avail['mcq_available'] < avail['ideal_mcq']:
            warnings.append(
                f"MCQ pool ({avail['mcq_available']}) is smaller than "
                f"the ideal {avail['ideal_mcq']} for 3 unique sets. "
                f"Some questions may repeat across Set A/B/C."
            )
        if avail['desc_available'] < avail['ideal_desc']:
            warnings.append(
                f"Descriptive pool ({avail['desc_available']}) is smaller than "
                f"the ideal {avail['ideal_desc']} for 3 unique sets."
            )

    # ── 3. Generate 3 sets ───────────────────────────────────────
    group_id = 'BP-' + str(uuid.uuid4())[:8].upper()
    papers   = []
    used_ids = set()

    for set_name in ['A', 'B', 'C']:
        mcq_qs  = _pick(blueprint, _MCQ_TYPES,  blueprint.mcq_count,         used_ids)
        desc_qs = _pick(blueprint, _DESC_TYPES, blueprint.descriptive_count,  used_ids)
        paper   = _save_set(blueprint, set_name, group_id, faculty, mcq_qs, desc_qs)
        papers.append(paper)
        used_ids.update(q.id for q in mcq_qs)
        used_ids.update(q.id for q in desc_qs)

    # ── 4. Save group record ─────────────────────────────────────
    BlueprintPaperGroup.objects.create(
        blueprint=blueprint, faculty=faculty, group_id=group_id)

    return {'papers': papers, 'group_id': group_id,
            'warnings': warnings, 'blueprint': blueprint}
