# learning/views.py

from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import LearningPath, Module, Lecture, Assignment, Assessment, LectureProgress, ModuleProgress, LearningPathProgress, AssignmentAttempt, AssessmentAttempt

def learning_paths_list(request, institute, user):
    learning_paths = LearningPath.objects.filter(institution=institute)
    progress_map = {
        lp_progress.learning_path_id: lp_progress.progress
        for lp_progress in LearningPathProgress.objects.filter(user_id=str(user), learning_path__in=learning_paths)
    }

    data = [
        {
            "id": str(lp.id),
            "title": lp.title,
            "level": lp.level,
            "time": lp.time,
            "thumbnail": lp.thumbnail,
            "is_published": lp.is_published,
            "description": lp.description,
            "progress": progress_map.get(lp.id, 0.0),
        }
        for lp in learning_paths
    ]
    return JsonResponse(data, safe=False)


def learning_path_detail(request, id, user):
    lp = get_object_or_404(LearningPath, pk=id)

    # Preload related objects
    modules = lp.modules.prefetch_related('lectures', 'assignment')
    lectures = Lecture.objects.filter(module__in=modules)
    assignments = Assignment.objects.filter(module__in=modules)
    assessments = Assessment.objects.filter(learning_path=lp)

    # Ensure LearningPathProgress exists
    lp_progress, _ = LearningPathProgress.objects.get_or_create(
        user_id=str(user),
        learning_path=lp,
        defaults={'progress': 0.0}
    )

    # Ensure ModuleProgress exists for each module
    module_progress_map = {}
    for module in modules:
        mp, _ = ModuleProgress.objects.get_or_create(
            user_id=str(user),
            module=module,
            defaults={'progress': 0.0, 'is_completed': False}
        )
        module_progress_map[module.module_id] = mp

    # Ensure LectureProgress exists for each lecture
    lecture_progress_map = {}
    for lecture in lectures:
        lp_obj, _ = LectureProgress.objects.get_or_create(
            user_id=str(user),
            lecture=lecture,
            defaults={'is_viewed': False, 'completed_at': None}
        )
        lecture_progress_map[lecture.lecture_id] = lp_obj

    # Ensure AssignmentAttempt exists for each assignment
    assignment_attempts_map = {}
    for assignment in assignments:
        aa, _ = AssignmentAttempt.objects.get_or_create(
            user_id=str(user),
            assignment=assignment,
            defaults={'status': 'not_started', 'score': None}
        )
        assignment_attempts_map[assignment.id] = aa

    # Ensure AssessmentAttempt exists for the assessment
    assessment_attempt = None
    if assessments.exists():
        assessment = assessments.first()
        assessment_attempt, _ = AssessmentAttempt.objects.get_or_create(
            user_id=str(user),
            assessment=assessment,
            attempt_number=1,
            defaults={'status': 'not_attempted', 'score': None}
        )

    # User-specific progress
    lecture_progress_map = {
        lp.lecture_id: lp for lp in LectureProgress.objects.filter(user_id=str(user), lecture__in=lectures)
    }
    module_progress_map = {
        mp.module_id: mp for mp in ModuleProgress.objects.filter(user_id=str(user), module__in=modules)
    }
    lp_progress = LearningPathProgress.objects.filter(user_id=str(user), learning_path=lp).first()
    assignment_attempts_map = {
        aa.assignment_id: aa for aa in AssignmentAttempt.objects.filter(user_id=str(user), assignment__in=assignments)
    }
    assessment_attempt = AssessmentAttempt.objects.filter(user_id=str(user), assessment__in=assessments).order_by('-attempt_number').first()

    module_data = []
    for module in modules:
        lecture_data = []
        for lec in module.lectures.all():
            progress = lecture_progress_map.get(lec.lecture_id)
            lecture_data.append({
                "lecture_id": str(lec.lecture_id),
                "title": lec.title,
                "content": lec.content,
                "is_viewed": progress.is_viewed if progress else False,
                "completed_at": progress.completed_at if progress else None,
            })

        mod_prog = module_progress_map.get(module.module_id)
        mod_obj = {
            "module_id": str(module.module_id),
            "title": module.title,
            "description": module.description,
            "progress": mod_prog.progress if mod_prog else 0.0,
            "is_completed": mod_prog.is_completed if mod_prog else False,
            "lectures": lecture_data
        }

        if hasattr(module, 'assignment'):
            assignment = module.assignment
            attempt = assignment_attempts_map.get(assignment.id)
            mod_obj["assignment"] = {
                "id": str(assignment.id),
                "name": assignment.name,
                "description": assignment.description,
                "total_marks": assignment.total_marks,
                "total_questions": assignment.total_questions,
                "attempts": assignment.attempts_count,
                "status": attempt.status if attempt else 'not_started',
                "score": attempt.score if attempt else None,
                "attempted_at": attempt.attempted_at if attempt else None,
            }

        module_data.append(mod_obj)

    response = {
        "id": str(lp.id),
        "title": lp.title,
        "level": lp.level,
        "time": lp.time,
        "thumbnail": lp.thumbnail,
        "is_published": lp.is_published,
        "description": lp.description,
        "progress": lp_progress.progress if lp_progress else 0.0,
        "updated_at": lp_progress.updated_at if lp_progress else None,
        "modules": module_data
    }

    if hasattr(lp, 'assessment'):
        assessment = lp.assessment
        response["assessment"] = {
            "id": assessment.id,
            "name": assessment.name,
            "description": assessment.description,
            "total_marks": assessment.total_marks,
            "total_questions": assessment.total_questions,
            "total_duration": assessment.total_duration,
            "total_qualifying_percentage": assessment.total_qualifying_percentage,
            "exam_type": assessment.exam_type,
            "password_exists": assessment.password_exists,
            "tab_switches_allowed": assessment.tab_switches_allowed,
            "no_of_tab_switches": assessment.no_of_tab_switches,
            "is_fullscreen": assessment.is_fullscreen,
            "shuffle": assessment.shuffle,
            "voice_monitoring": assessment.voice_monitoring,
            "face_proctoring": assessment.face_proctoring,
            "electronic_monitoring": assessment.electronic_monitoring,
            "attempt_number": assessment_attempt.attempt_number if assessment_attempt else 0,
            "score": assessment_attempt.score if assessment_attempt else None,
            "status": assessment_attempt.status if assessment_attempt else 'not_attempted',
            "attempted_at": assessment_attempt.attempted_at if assessment_attempt else None,
        }

    return JsonResponse(response)