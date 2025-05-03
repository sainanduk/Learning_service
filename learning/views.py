# learning/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from django.contrib.auth.models import User
from .models import LearningPath, LearningPathProgress

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
    
    modules = []
    for module in lp.modules.all():
        lectures = [
            {
                "lecture_id": str(lec.lecture_id),
                "title": lec.title,
                "content": lec.content,
            } for lec in module.lectures.all()
        ]
        module_data = {
            "module_id": str(module.module_id),
            "title": module.title,
            "description": module.description,
            "lectures": lectures,
        }
        if hasattr(module, 'assignment'):
            assignment = module.assignment
            module_data["assignment"] = {
                "id": str(assignment.id),
                "name": assignment.name,
                "description": assignment.description,
                "total_marks": assignment.total_marks,
                "total_questions": assignment.total_questions,
                "attempts": assignment.attempts_count,
            }
        modules.append(module_data)

    response = {
        "id": str(lp.id),
        "title": lp.title,
        "level": lp.level,
        "time": lp.time,
        "thumbnail": lp.thumbnail,
        "is_published": lp.is_published,
        "description": lp.description,
        "modules": modules,
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
        }

    return JsonResponse(response)
