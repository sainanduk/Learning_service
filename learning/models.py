# learning/models.py

from datetime import timezone
from django.db import models
import uuid


# Existing models (LearningPath, Module, Lecture, Assignment, Assessment)...



class LearningPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    level = models.CharField(max_length=50)
    time = models.CharField(max_length=50)  
    thumbnail = models.URLField()
    is_published = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    certificate_url = models.URLField(default='')

    def __str__(self):
        return self.title

class InstituteBatchLearningPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.CharField(max_length=100, default='parul')
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    batch = models.CharField(max_length=50)
    

class Module(models.Model):
    module_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(LearningPath, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

class Lecture(models.Model):
    lecture_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, related_name='lectures', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    video_url = models.URLField(max_length=500, blank=True, null=True) 

    def __str__(self):
        return self.title

class Assignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.OneToOneField(Module, related_name='assignment', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    total_marks = models.IntegerField()
    total_questions = models.IntegerField()
    attempts_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.OneToOneField(LearningPath, related_name='assessment', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    total_marks = models.IntegerField()
    total_questions = models.IntegerField()
    total_duration = models.IntegerField(help_text='Duration in minutes')
    total_qualifying_percentage = models.FloatField()
    exam_type = models.CharField(max_length=50)
    password_exists = models.BooleanField(default=False)
    tab_switches_allowed = models.BooleanField(default=False)
    no_of_tab_switches = models.IntegerField(default=0)

    # Proctoring options
    is_fullscreen = models.BooleanField(default=False)
    shuffle = models.BooleanField(default=False)
    voice_monitoring = models.BooleanField(default=False)  # e.g., easy, strict
    face_proctoring = models.BooleanField(default=False)
    electronic_monitoring = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class LectureProgress(models.Model):
    user_id = models.CharField(max_length=255)
    lecture = models.ForeignKey(Lecture, related_name='progress', on_delete=models.CASCADE)
    is_viewed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user_id', 'lecture')

class ModuleProgress(models.Model):
    user_id = models.CharField(max_length=255)
    module = models.ForeignKey(Module, related_name='progress', on_delete=models.CASCADE)
    progress = models.FloatField(default=0.0)  # percentage
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user_id', 'module')

# class LearningPathProgress(models.Model):
#     user_id = models.CharField(max_length=255)
#     learning_path = models.ForeignKey(LearningPath, related_name='progress', on_delete=models.CASCADE)
#     progress = models.FloatField(default=0.0)  # percentage
#     started_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     is_completed = models.BooleanField(default=False)
#     completed_at = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         unique_together = ('user_id', 'learning_path')


class LearningPathProgress(models.Model):
    user_id = models.CharField(max_length=255)
    learning_path = models.ForeignKey(LearningPath, related_name='progress', on_delete=models.CASCADE)
    progress = models.FloatField(default=0.0)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user_id', 'learning_path')

    def save(self, *args, **kwargs):
        if self.progress == 100 and not self.is_completed:
            self.is_completed = True
            if not self.completed_at:
                self.completed_at = timezone.now()
        elif self.progress < 100:
            self.is_completed = False
            self.completed_at = None
        super().save(*args, **kwargs)

class AssignmentAttempt(models.Model):
    user_id = models.CharField(max_length=255)
    assignment = models.ForeignKey(Assignment, related_name='attempts', on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=[('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('completed', 'Completed')])
    score = models.IntegerField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

class AssessmentAttempt(models.Model):
    user_id = models.CharField(max_length=255)
    assessment = models.ForeignKey(Assessment, related_name='attempts', on_delete=models.CASCADE)
    attempt_number = models.IntegerField(default=1)
    score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[('not_attempted', 'Not Attempted'), ('in_progress', 'In Progress'), ('completed', 'Completed')])
    attempted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user_id', 'assessment', 'attempt_number')
