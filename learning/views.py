# learning/views.py

from uuid import UUID
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
import logging

from .models import (
    LearningPath, Module, Lecture, Assignment, Assessment, 
    LectureProgress, ModuleProgress, LearningPathProgress, 
    AssignmentAttempt, AssessmentAttempt, InstituteBatchLearningPath
)

from django.utils import timezone

# Get logger for this module
logger = logging.getLogger(__name__)

def vendor_learning_paths_list(request):
    """
    View to list all learning paths for vendors to manage.
    This allows vendors to see all learning paths regardless of institute or batch assignments.
    """
    try:
        # Try to get from cache first
        cache_key = 'vendor_learning_paths'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return JsonResponse(cached_data)
        
        # Get all learning paths
        learning_paths = LearningPath.objects.all()
        
        if not learning_paths.exists():
            return JsonResponse({
                'message': 'No learning paths found in the system'
            }, status=404)
        
        # For each learning path, get all institute-batch mappings
        result = []
        for lp in learning_paths:            
            # Add to result
            result.append({
                'id': str(lp.id),
                'title': lp.title,
                'level': lp.level,
                'certificate_url': lp.certificate_url,
                'time': lp.time,
                'thumbnail': lp.thumbnail,
                'is_published': lp.is_published,
                'description': lp.description
            })
        
        response_data = {
            'learning_paths': result,
            'total': len(result)
        }
        
        # Cache the response
        cache.set(cache_key, response_data, settings.CACHE_TTL)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def vendor_add_learning_path_toInstitute(request, institute, learning_path_id, batch):
    """
    View to add or remove a learning path to/from an institute-batch combination.
    
    If the request method is POST:
        - Creates association between learning path and institute-batch
    If the request method is DELETE:
        - Removes the association
    """
    try:
        # Validate the learning path exists
        learning_path = get_object_or_404(LearningPath, pk=learning_path_id)
        
        # Handle POST request (create association)
        if request.method == 'POST':
            # Check if this mapping already exists
            existing_mapping = InstituteBatchLearningPath.objects.filter(
                institution=institute,
                learning_path=learning_path,
                batch=batch
            ).first()
            
            if existing_mapping:
                return JsonResponse({
                    'message': f'This learning path is already assigned to institute "{institute}" and batch "{batch}"'
                }, status=400)
            
            # Create new mapping
            mapping = InstituteBatchLearningPath.objects.create(
                institution=institute,
                learning_path=learning_path,
                batch=batch
            )
            
            return JsonResponse({
                'message': f'Successfully assigned learning path "{learning_path.title}" to institute "{institute}" and batch "{batch}"',
                'mapping_id': str(mapping.id)
            }, status=201)
            
        # Handle DELETE request (remove association)
        elif request.method == 'DELETE':
            # Find and delete mapping
            mapping = InstituteBatchLearningPath.objects.filter(
                institution=institute,
                learning_path=learning_path,
                batch=batch
            ).first()
            
            if not mapping:
                return JsonResponse({
                    'error': f'No mapping found for learning path "{learning_path.title}" with institute "{institute}" and batch "{batch}"'
                }, status=404)
            
            # Delete the mapping
            mapping.delete()
            
            return JsonResponse({
                'message': f'Successfully removed learning path "{learning_path.title}" from institute "{institute}" and batch "{batch}"'
            })
            
        # Handle other HTTP methods
        else:
            return JsonResponse({
                'error': f'Method {request.method} not allowed. Use POST to create or DELETE to remove mapping.'
            }, status=405)
            
    except Http404:
        return JsonResponse({
            'error': f'Learning path with ID {learning_path_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt

def update_learning_path_progress(request, user, lecture_id):
    try:
        lecture_uuid = UUID(str(lecture_id))
    except ValueError:
        raise Http404("Invalid lecture ID format.")
    
    lecture = get_object_or_404(Lecture, lecture_id=lecture_id)
    module = lecture.module
    learning_path = module.learning_path

    # Toggle or create LectureProgress
    lecture_progress, created = LectureProgress.objects.get_or_create(
        user_id=str(user),
        lecture=lecture,
        defaults={'is_viewed': True, 'completed_at': timezone.now()}
    )

    if not created:
        if lecture_progress.is_viewed:
            lecture_progress.is_viewed = False
            lecture_progress.completed_at = None
        else:
            lecture_progress.is_viewed = True
            lecture_progress.completed_at = timezone.now()
        lecture_progress.save()

    # Calculate ModuleProgress
    lectures = module.lectures.all()
    total_lectures = lectures.count()

    if total_lectures > 0:
        viewed_lectures = LectureProgress.objects.filter(
            user_id=str(user),
            lecture__in=lectures,
            is_viewed=True
        ).count()
        module_progress_value = (viewed_lectures / total_lectures) * 100
        is_module_completed = module_progress_value == 100

        ModuleProgress.objects.update_or_create(
            user_id=str(user),
            module=module,
            defaults={'progress': module_progress_value, 'is_completed': is_module_completed}
        )
    else:
        module_progress_value = 0
        is_module_completed = False

    # Calculate LearningPathProgress
    modules = learning_path.modules.all()
    total_modules = modules.count()

    if total_modules > 0:
        total_progress = 0
        for mod in modules:
            mod_lectures = mod.lectures.all()
            mod_total_lectures = mod_lectures.count()

            if mod_total_lectures > 0:
                mod_viewed_lectures = LectureProgress.objects.filter(
                    user_id=str(user),
                    lecture__in=mod_lectures,
                    is_viewed=True
                ).count()
                mod_progress = (mod_viewed_lectures / mod_total_lectures) * 100
            else:
                mod_progress = 0

            total_progress += mod_progress

        learning_path_progress_value = total_progress / total_modules
    else:
        learning_path_progress_value = 0

    LearningPathProgress.objects.update_or_create(
        user_id=str(user),
        learning_path=learning_path,
        defaults={'progress': learning_path_progress_value}
    )

    return JsonResponse({
        'status': 'success',
        'lecture_progress': {
            'is_viewed': lecture_progress.is_viewed,
            'completed_at': lecture_progress.completed_at
        },
        'module_progress': {
            'progress': int(module_progress_value),
            'is_completed': is_module_completed
        },
        'learning_path_progress': {
            'progress': int(learning_path_progress_value)
        }
    })

def certificate_list(request, institute, batch, user):
    try:
        cache_key = f'learning_paths_certificates_{institute}_{batch}'
        logger.debug(f"Debug - Cache key: {cache_key}")

        cached_data = cache.get(cache_key)
        logger.debug(f"Debug - Cached data found: {cached_data is not None}")

        if cached_data:
            all_learning_paths_data = cached_data['data']
        else:
            logger.debug("Debug - Cache miss, fetching from database")
            mappings = InstituteBatchLearningPath.objects.filter(
                institution=institute,
                batch=batch
            )
            if not mappings.exists():
                return JsonResponse({'error': 'No learning paths found for this institute and batch'}, status=404)

            learning_path_ids = mappings.values_list('learning_path_id', flat=True)
            all_learning_paths = LearningPath.objects.filter(id__in=learning_path_ids)

            if not all_learning_paths.exists():
                return JsonResponse({'error': 'No active learning paths found'}, status=404)

            all_learning_paths_data = [
                {
                    "id": str(lp.id),
                    "title": lp.title,
                    "certificate_url": lp.certificate_url
                }
                for lp in all_learning_paths
            ]

            cache_data = {
                "data": all_learning_paths_data,
                "pagination": {
                    "totalItems": len(all_learning_paths_data),
                    "totalPages": 1
                }
            }

            try:
                cache.set(cache_key, cache_data, settings.CACHE_TTL)
                logger.debug("Debug - Cache set successfully")
            except Exception as cache_error:
                logger.debug(f"Debug - Cache set failed: {cache_error}")

        learning_path_ids = [item['id'] for item in all_learning_paths_data]
        learning_path_uuids = [UUID(lp_id) for lp_id in learning_path_ids]

        progress_qs = LearningPathProgress.objects.filter(
            user_id=str(user),
            learning_path_id__in=learning_path_uuids
        )

        progress_map = {
            str(p.learning_path_id): {
                'progress': int(p.progress),
                'certificate_issue_date': p.completed_at
            }
            for p in progress_qs
        }

        for item in all_learning_paths_data:
            lp_id = item['id']
            progress_info = progress_map.get(lp_id, {})
            item['progress'] = progress_info.get('progress', 0)
            item['certificate_issue_date'] = progress_info.get('certificate_issue_date')

        return JsonResponse({
            "data": all_learning_paths_data
        }, safe=False, status=200)

    except Exception as e:
        logger.debug(f"Debug - Exception occurred: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


def learning_paths_list(request, institute, batch, user):
    try:
        current_page = int(request.GET.get('currentPage', 1))
        items_per_page = 10

        cache_key = f'learning_paths_{institute}_{batch}'
        logger.debug(f"Debug - Cache key: {cache_key}")
        
        cached_data = cache.get(cache_key)
        logger.debug(f"Debug - Cached data found: {cached_data is not None}")

        if cached_data:
            # Cache hit: Get paginated learning path data
            paginated_data = cached_data['data']
            total_items = cached_data['pagination']['totalItems']
            total_pages = cached_data['pagination']['totalPages']

        else:
            # Cache miss: Fetch from DB and cache (without progress)
            logger.debug(f"Debug - Cache miss, fetching from database")
            mappings = InstituteBatchLearningPath.objects.filter(
                institution=institute,
                batch=batch
            )
            if not mappings.exists():
                return JsonResponse({'error': 'No learning paths found for this institute and batch'}, status=404)

            learning_path_ids = mappings.values_list('learning_path_id', flat=True)
            all_learning_paths = LearningPath.objects.filter(id__in=learning_path_ids)

            if not all_learning_paths.exists():
                return JsonResponse({'error': 'No active learning paths found'}, status=404)

            # Convert learning paths to dict (no progress)
            learning_paths_data = [
                {
                    "id": str(lp.id),
                    "title": lp.title,
                    "level": lp.level,
                    "certificate_url": lp.certificate_url,
                    "time": lp.time,
                    "thumbnail": lp.thumbnail,
                    "is_published": lp.is_published,
                    "description": lp.description,
                }
                for lp in all_learning_paths
            ]

            # Pagination setup
            total_items = len(learning_paths_data)
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Save all data in cache (no progress)
            cache_data = {
                "data": learning_paths_data,
                "pagination": {
                    "totalItems": total_items,
                    "totalPages": total_pages
                }
            }
            
            logger.debug(f"Debug - About to set cache with TTL: {settings.CACHE_TTL}")
            try:
                cache.set(cache_key, cache_data, settings.CACHE_TTL)
                logger.debug(f"Debug - Cache set successfully")
            except Exception as cache_error:
                logger.debug(f"Debug - Cache set failed: {cache_error}")

            paginated_data = learning_paths_data

        # Apply pagination to cached data
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_data = paginated_data[start_idx:end_idx]

        # Fetch progress for learning paths on this page
        learning_path_ids = [item['id'] for item in page_data]
        # Convert string IDs to UUID objects for the database query
        learning_path_uuids = [UUID(lp_id) for lp_id in learning_path_ids]
        
        progress_map = {
            str(lp_progress.learning_path_id): (lp_progress.progress)
            for lp_progress in LearningPathProgress.objects.filter(
                user_id=str(user),
                learning_path_id__in=learning_path_uuids
            )
        }

        # Debug: Print progress map to see what's being fetched
        logger.debug(f"Debug - User: {user}")
        logger.debug(f"Debug - Learning path IDs: {learning_path_ids}")
        logger.debug(f"Debug - Progress map: {progress_map}")

        # Add progress to each item
        for item in page_data:
            item['progress'] = int(progress_map.get(item['id'], 0.0))

        return JsonResponse({
            "data": page_data,
            "pagination": {
                "currentPage": current_page,
                "totalPages": total_pages,
                "totalItems": total_items,
                "itemsPerPage": items_per_page
            }
        }, safe=False, status=200)

    except Exception as e:
        logger.debug(f"Debug - Exception occurred: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


def learning_path_detail(request, id, user):
    try:
        # Try to get from cache first
        cache_key = f'learning_path_detail_{id}'
        logger.debug(f"Debug - Detail cache key: {cache_key}")
        
        cached_data = cache.get(cache_key)
        logger.debug(f"Debug - Detail cached data found: {cached_data is not None}")
        
        if cached_data:
            logger.debug(f"Debug - Using cached detail data")
            # Get user-specific progress data from database
            lp = get_object_or_404(LearningPath, pk=id)
            modules = lp.modules.prefetch_related('lectures', 'assignment')
            lectures = Lecture.objects.filter(module__in=modules)
            assignments = Assignment.objects.filter(module__in=modules)
            assessments = Assessment.objects.filter(learning_path=lp)
            
            # Get user progress from database - FIXED: Use lecture.lecture_id instead of lp.lecture_id
            lecture_progress_map = {
                str(lecture_progress.lecture_id): lecture_progress 
                for lecture_progress in LectureProgress.objects.filter(user_id=str(user), lecture__in=lectures)
            }
            
            # Debug: Print lecture progress map
            logger.debug(f"Debug - User: {user}")
            logger.debug(f"Debug - Lecture progress map: {lecture_progress_map}")
            
            # FIXED: Properly fetch module progress using module_id as string key
            module_progress_map = {
                str(mp.module_id): mp for mp in ModuleProgress.objects.filter(user_id=str(user), module__in=modules)
            }
            logger.debug(f"Debug - Module progress map: {module_progress_map}")
            
            lp_progress = LearningPathProgress.objects.filter(user_id=str(user), learning_path=lp).first()
            assignment_attempts_map = {
                aa.assignment_id: aa for aa in AssignmentAttempt.objects.filter(user_id=str(user), assignment__in=assignments)
            }
            assessment_attempt = AssessmentAttempt.objects.filter(user_id=str(user), assessment__in=assessments).order_by('-attempt_number').first()
            
            # Add progress to cached data
            cached_data['progress'] = int(lp_progress.progress if lp_progress else 0.0)
            cached_data['updated_at'] = lp_progress.updated_at if lp_progress else None
            
            # Update module data with progress - FIXED: Use string module_id as key
            for module in cached_data['modules']:
                mod_prog = module_progress_map.get(module['module_id'])
                module['progress'] = int(mod_prog.progress if mod_prog else 0.0)
                module['is_completed'] = mod_prog.is_completed if mod_prog else False
                
                # Update lecture progress
                for lecture in module['lectures']:
                    progress = lecture_progress_map.get(lecture['lecture_id'])
                    lecture['is_viewed'] = progress.is_viewed if progress else False
                    lecture['completed_at'] = progress.completed_at if progress else None
                
                # Update assignment progress
                if 'assignment' in module:
                    attempt = assignment_attempts_map.get(module['assignment']['id'])
                    module['assignment']['status'] = attempt.status if attempt else 'not_started'
                    module['assignment']['score'] = attempt.score if attempt else None
                    module['assignment']['attempted_at'] = attempt.attempted_at if attempt else None
            
            # Update assessment progress
            if 'assessment' in cached_data:
                cached_data['assessment']['attempt_number'] = assessment_attempt.attempt_number if assessment_attempt else 0
                cached_data['assessment']['score'] = assessment_attempt.score if assessment_attempt else None
                cached_data['assessment']['status'] = assessment_attempt.status if assessment_attempt else 'not_attempted'
                cached_data['assessment']['attempted_at'] = assessment_attempt.attempted_at if assessment_attempt else None
            
            return JsonResponse(cached_data)
        
        logger.debug(f"Debug - Cache miss for detail, fetching from database")
        # Get the learning path
        lp = get_object_or_404(LearningPath, pk=id)

        # Preload related objects
        modules = lp.modules.prefetch_related('lectures', 'assignment')
        lectures = Lecture.objects.filter(module__in=modules)
        assignments = Assignment.objects.filter(module__in=modules)
        assessments = Assessment.objects.filter(learning_path=lp)

        # Get total counts
        total_lectures = lectures.count()
        total_assignments = assignments.count()

        # Get user-specific progress from database - FIXED: Use lecture.lecture_id instead of lp.lecture_id
        lecture_progress_map = {
            str(lecture_progress.lecture_id): lecture_progress 
            for lecture_progress in LectureProgress.objects.filter(user_id=str(user), lecture__in=lectures)
        }
        
        # Debug: Print lecture progress map
        logger.debug(f"Debug - User: {user}")
        logger.debug(f"Debug - Lecture progress map: {lecture_progress_map}")
        
        # FIXED: Properly fetch module progress using module_id as string key
        module_progress_map = {
            str(mp.module_id): mp for mp in ModuleProgress.objects.filter(user_id=str(user), module__in=modules)
        }
        logger.debug(f"Debug - Module progress map: {module_progress_map}")
        
        lp_progress = LearningPathProgress.objects.filter(user_id=str(user), learning_path=lp).first()
        assignment_attempts_map = {
            aa.assignment_id: aa for aa in AssignmentAttempt.objects.filter(user_id=str(user), assignment__in=assignments)
        }
        assessment_attempt = AssessmentAttempt.objects.filter(user_id=str(user), assessment__in=assessments).order_by('-attempt_number').first()

        module_data = []
        for module in modules:
            lecture_data = []
            for lec in module.lectures.all():
                progress = lecture_progress_map.get(str(lec.lecture_id))
                lecture_data.append({
                    "lecture_id": str(lec.lecture_id),
                    "title": lec.title,
                    "content": lec.content,
                    "video_url": lec.video_url,
                    "is_viewed": progress.is_viewed if progress else False,
                    "completed_at": progress.completed_at if progress else None,
                })

            mod_prog = module_progress_map.get(str(module.module_id))
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
            "certificate_url": lp.certificate_url,
            "time": lp.time,
            "thumbnail": lp.thumbnail,
            "is_published": lp.is_published,
            "description": lp.description,
            "progress": lp_progress.progress if lp_progress else 0.0,
            "updated_at": lp_progress.updated_at if lp_progress else None,
            "total_lectures": total_lectures,
            "total_assignments": total_assignments,
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

        # Cache the response without user-specific data
        cache_data = response.copy()
        cache_data.pop('progress', None)
        cache_data.pop('updated_at', None)
        for module in cache_data['modules']:
            module.pop('progress', None)
            module.pop('is_completed', None)
            for lecture in module['lectures']:
                lecture.pop('is_viewed', None)
                lecture.pop('completed_at', None)
            if 'assignment' in module:
                module['assignment'].pop('status', None)
                module['assignment'].pop('score', None)
                module['assignment'].pop('attempted_at', None)
        if 'assessment' in cache_data:
            cache_data['assessment'].pop('attempt_number', None)
            cache_data['assessment'].pop('score', None)
            cache_data['assessment'].pop('status', None)
            cache_data['assessment'].pop('attempted_at', None)
        
        logger.debug(f"Debug - Setting detail cache with TTL: {settings.CACHE_TTL}")
        try:
            cache.set(cache_key, cache_data, settings.CACHE_TTL)
            logger.debug(f"Debug - Detail cache set successfully")
        except Exception as cache_error:
            logger.debug(f"Debug - Detail cache set failed: {cache_error}")

        return JsonResponse(response)
        
    except Http404:
        return JsonResponse({'error': f'Learning path with ID {id} not found'}, status=404)
    except Exception as e:
        logger.debug(f"Debug - Detail exception occurred: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

@csrf_exempt
def create_learning_path_with_modules(request):
    """
    Create a learning path with multiple modules.
    Expected JSON payload:
    {
        "title": "Learning Path Title",
        "level": "beginner",
        "time": "2 hours",
        "thumbnail": "https://example.com/thumbnail.jpg",
        "description": "Learning path description",
        "certificate_url": "https://example.com/certificate.pdf",
        "is_published": false,
        "modules": [
            {
                "title": "Module 1",
                "description": "Module 1 description"
            },
            {
                "title": "Module 2", 
                "description": "Module 2 description"
            }
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({
            'error': 'Only POST method is allowed'
        }, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        # Validate required fields for learning path
        required_fields = ['title', 'level', 'time', 'thumbnail']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({
                    'error': f'Field "{field}" is required and cannot be empty'
                }, status=400)
        
        # Validate title length
        if len(data['title']) > 100:
            return JsonResponse({
                'error': 'Title must be 100 characters or less'
            }, status=400)
        
        # Validate level
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if data['level'].lower() not in valid_levels:
            return JsonResponse({
                'error': f'Level must be one of: {", ".join(valid_levels)}'
            }, status=400)
        
        # Validate URL fields
        import re
        url_pattern = re.compile(r'^https?://')
        if not url_pattern.match(data['thumbnail']):
            return JsonResponse({
                'error': 'Thumbnail must be a valid URL starting with http:// or https://'
            }, status=400)
        
        if 'certificate_url' in data and data['certificate_url']:
            if not url_pattern.match(data['certificate_url']):
                return JsonResponse({
                    'error': 'Certificate URL must be a valid URL starting with http:// or https://'
                }, status=400)
        
        # Validate modules
        if 'modules' not in data or not isinstance(data['modules'], list):
            return JsonResponse({
                'error': 'Modules field is required and must be a list'
            }, status=400)
        
        if len(data['modules']) == 0:
            return JsonResponse({
                'error': 'At least one module is required'
            }, status=400)
        
        # Validate each module
        for i, module in enumerate(data['modules']):
            if not isinstance(module, dict):
                return JsonResponse({
                    'error': f'Module {i+1} must be an object'
                }, status=400)
            
            if 'title' not in module or not module['title']:
                return JsonResponse({
                    'error': f'Module {i+1} must have a title'
                }, status=400)
            
            if len(module['title']) > 100:
                return JsonResponse({
                    'error': f'Module {i+1} title must be 100 characters or less'
                }, status=400)
        
        # Create learning path
        learning_path = LearningPath.objects.create(
            title=data['title'],
            level=data['level'].lower(),
            time=data['time'],
            thumbnail=data['thumbnail'],
            description=data.get('description', ''),
            certificate_url=data.get('certificate_url', ''),
            is_published=data.get('is_published', False)
        )
        
        # Create modules
        created_modules = []
        for module_data in data['modules']:
            module = Module.objects.create(
                learning_path=learning_path,
                title=module_data['title'],
                description=module_data.get('description', '')
            )
            created_modules.append({
                'module_id': str(module.module_id),
                'title': module.title,
                'description': module.description
            })
        
        return JsonResponse({
            'message': 'Learning path and modules created successfully',
            'learning_path': {
                'id': str(learning_path.id),
                'title': learning_path.title,
                'level': learning_path.level,
                'time': learning_path.time,
                'thumbnail': learning_path.thumbnail,
                'description': learning_path.description,
                'certificate_url': learning_path.certificate_url,
                'is_published': learning_path.is_published
            },
            'modules': created_modules,
            'total_modules': len(created_modules)
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating learning path with modules: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def create_lectures_for_module(request, module_id):
    """
    Create lectures for a specific module.
    Expected JSON payload:
    {
        "lectures": [
            {
                "title": "Lecture 1",
                "content": "Lecture content here",
                "video_url": "https://example.com/video1.mp4"
            },
            {
                "title": "Lecture 2",
                "content": "Lecture content here",
                "video_url": "https://example.com/video2.mp4"
            }
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({
            'error': 'Only POST method is allowed'
        }, status=405)
    
    try:
        # Validate module_id format
        try:
            module_uuid = UUID(str(module_id))
        except ValueError:
            return JsonResponse({
                'error': 'Invalid module ID format'
            }, status=400)
        
        # Get the module
        try:
            module = Module.objects.get(module_id=module_uuid)
        except Module.DoesNotExist:
            return JsonResponse({
                'error': f'Module with ID {module_id} not found'
            }, status=404)
        
        import json
        data = json.loads(request.body)
        
        # Validate lectures field
        if 'lectures' not in data or not isinstance(data['lectures'], list):
            return JsonResponse({
                'error': 'Lectures field is required and must be a list'
            }, status=400)
        
        if len(data['lectures']) == 0:
            return JsonResponse({
                'error': 'At least one lecture is required'
            }, status=400)
        
        # Validate each lecture
        for i, lecture in enumerate(data['lectures']):
            if not isinstance(lecture, dict):
                return JsonResponse({
                    'error': f'Lecture {i+1} must be an object'
                }, status=400)
            
            if 'title' not in lecture or not lecture['title']:
                return JsonResponse({
                    'error': f'Lecture {i+1} must have a title'
                }, status=400)
            
            if len(lecture['title']) > 100:
                return JsonResponse({
                    'error': f'Lecture {i+1} title must be 100 characters or less'
                }, status=400)
            
            # Validate video_url if provided
            if 'video_url' in lecture and lecture['video_url']:
                import re
                url_pattern = re.compile(r'^https?://')
                if not url_pattern.match(lecture['video_url']):
                    return JsonResponse({
                        'error': f'Lecture {i+1} video URL must be a valid URL starting with http:// or https://'
                    }, status=400)
        
        # Create lectures
        created_lectures = []
        for lecture_data in data['lectures']:
            lecture = Lecture.objects.create(
                module=module,
                title=lecture_data['title'],
                content=lecture_data.get('content', ''),
                video_url=lecture_data.get('video_url', '')
            )
            created_lectures.append({
                'lecture_id': str(lecture.lecture_id),
                'title': lecture.title,
                'content': lecture.content,
                'video_url': lecture.video_url
            })
        
        return JsonResponse({
            'message': f'Lectures created successfully for module "{module.title}"',
            'module': {
                'module_id': str(module.module_id),
                'title': module.title,
                'description': module.description
            },
            'lectures': created_lectures,
            'total_lectures': len(created_lectures)
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating lectures for module {module_id}: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def add_module_to_learning_path(request, learning_path_id):
    """
    Add a single module to an existing learning path.
    Expected JSON payload:
    {
        "title": "New Module Title",
        "description": "Module description"
    }
    """
    if request.method != 'POST':
        return JsonResponse({
            'error': 'Only POST method is allowed'
        }, status=405)
    
    try:
        # Validate learning_path_id format
        try:
            learning_path_uuid = UUID(str(learning_path_id))
        except ValueError:
            return JsonResponse({
                'error': 'Invalid learning path ID format'
            }, status=400)
        
        # Get the learning path
        try:
            learning_path = LearningPath.objects.get(id=learning_path_uuid)
        except LearningPath.DoesNotExist:
            return JsonResponse({
                'error': f'Learning path with ID {learning_path_id} not found'
            }, status=404)
        
        import json
        data = json.loads(request.body)
        
        # Validate required fields
        if 'title' not in data or not data['title']:
            return JsonResponse({
                'error': 'Title is required and cannot be empty'
            }, status=400)
        
        if len(data['title']) > 100:
            return JsonResponse({
                'error': 'Title must be 100 characters or less'
            }, status=400)
        
        # Create the module
        module = Module.objects.create(
            learning_path=learning_path,
            title=data['title'],
            description=data.get('description', '')
        )
        
        return JsonResponse({
            'message': f'Module added successfully to learning path "{learning_path.title}"',
            'learning_path': {
                'id': str(learning_path.id),
                'title': learning_path.title
            },
            'module': {
                'module_id': str(module.module_id),
                'title': module.title,
                'description': module.description
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error adding module to learning path {learning_path_id}: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def modify_module(request, module_id):
    """
    Modify an existing module.
    Expected JSON payload:
    {
        "title": "Updated Module Title",
        "description": "Updated module description"
    }
    """
    if request.method != 'PUT':
        return JsonResponse({
            'error': 'Only PUT method is allowed'
        }, status=405)
    
    try:
        # Validate module_id format
        try:
            module_uuid = UUID(str(module_id))
        except ValueError:
            return JsonResponse({
                'error': 'Invalid module ID format'
            }, status=400)
        
        # Get the module
        try:
            module = Module.objects.get(module_id=module_uuid)
        except Module.DoesNotExist:
            return JsonResponse({
                'error': f'Module with ID {module_id} not found'
            }, status=404)
        
        import json
        data = json.loads(request.body)
        
        # Validate title if provided
        if 'title' in data:
            if not data['title']:
                return JsonResponse({
                    'error': 'Title cannot be empty'
                }, status=400)
            
            if len(data['title']) > 100:
                return JsonResponse({
                    'error': 'Title must be 100 characters or less'
                }, status=400)
            
            module.title = data['title']
        
        # Update description if provided
        if 'description' in data:
            module.description = data['description']
        
        module.save()
        
        return JsonResponse({
            'message': 'Module updated successfully',
            'module': {
                'module_id': str(module.module_id),
                'title': module.title,
                'description': module.description,
                'learning_path': {
                    'id': str(module.learning_path.id),
                    'title': module.learning_path.title
                }
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error modifying module {module_id}: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def add_lecture_to_module(request, module_id):
    """
    Add a single lecture to an existing module.
    Expected JSON payload:
    {
        "title": "New Lecture Title",
        "content": "Lecture content here",
        "video_url": "https://example.com/video.mp4"
    }
    """
    if request.method != 'POST':
        return JsonResponse({
            'error': 'Only POST method is allowed'
        }, status=405)
    
    try:
        # Validate module_id format
        try:
            module_uuid = UUID(str(module_id))
        except ValueError:
            return JsonResponse({
                'error': 'Invalid module ID format'
            }, status=400)
        
        # Get the module
        try:
            module = Module.objects.get(module_id=module_uuid)
        except Module.DoesNotExist:
            return JsonResponse({
                'error': f'Module with ID {module_id} not found'
            }, status=404)
        
        import json
        data = json.loads(request.body)
        
        # Validate required fields
        if 'title' not in data or not data['title']:
            return JsonResponse({
                'error': 'Title is required and cannot be empty'
            }, status=400)
        
        if len(data['title']) > 100:
            return JsonResponse({
                'error': 'Title must be 100 characters or less'
            }, status=400)
        
        # Validate video_url if provided
        if 'video_url' in data and data['video_url']:
            import re
            url_pattern = re.compile(r'^https?://')
            if not url_pattern.match(data['video_url']):
                return JsonResponse({
                    'error': 'Video URL must be a valid URL starting with http:// or https://'
                }, status=400)
        
        # Create the lecture
        lecture = Lecture.objects.create(
            module=module,
            title=data['title'],
            content=data.get('content', ''),
            video_url=data.get('video_url', '')
        )
        
        return JsonResponse({
            'message': f'Lecture added successfully to module "{module.title}"',
            'module': {
                'module_id': str(module.module_id),
                'title': module.title
            },
            'lecture': {
                'lecture_id': str(lecture.lecture_id),
                'title': lecture.title,
                'content': lecture.content,
                'video_url': lecture.video_url
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error adding lecture to module {module_id}: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
def modify_lecture(request, lecture_id):
    """
    Modify an existing lecture.
    Expected JSON payload:
    {
        "title": "Updated Lecture Title",
        "content": "Updated lecture content",
        "video_url": "https://example.com/updated-video.mp4"
    }
    """
    if request.method != 'PUT':
        return JsonResponse({
            'error': 'Only PUT method is allowed'
        }, status=405)
    
    try:
        # Validate lecture_id format
        try:
            lecture_uuid = UUID(str(lecture_id))
        except ValueError:
            return JsonResponse({
                'error': 'Invalid lecture ID format'
            }, status=400)
        
        # Get the lecture
        try:
            lecture = Lecture.objects.get(lecture_id=lecture_uuid)
        except Lecture.DoesNotExist:
            return JsonResponse({
                'error': f'Lecture with ID {lecture_id} not found'
            }, status=404)
        
        import json
        data = json.loads(request.body)
        
        # Validate title if provided
        if 'title' in data:
            if not data['title']:
                return JsonResponse({
                    'error': 'Title cannot be empty'
                }, status=400)
            
            if len(data['title']) > 100:
                return JsonResponse({
                    'error': 'Title must be 100 characters or less'
                }, status=400)
            
            lecture.title = data['title']
        
        # Update content if provided
        if 'content' in data:
            lecture.content = data['content']
        
        # Update video_url if provided
        if 'video_url' in data:
            if data['video_url']:
                import re
                url_pattern = re.compile(r'^https?://')
                if not url_pattern.match(data['video_url']):
                    return JsonResponse({
                        'error': 'Video URL must be a valid URL starting with http:// or https://'
                    }, status=400)
            lecture.video_url = data['video_url']
        
        lecture.save()
        
        return JsonResponse({
            'message': 'Lecture updated successfully',
            'lecture': {
                'lecture_id': str(lecture.lecture_id),
                'title': lecture.title,
                'content': lecture.content,
                'video_url': lecture.video_url,
                'module': {
                    'module_id': str(lecture.module.module_id),
                    'title': lecture.module.title
                }
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error modifying lecture {lecture_id}: {str(e)}")
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)

