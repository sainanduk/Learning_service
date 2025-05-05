from django.contrib import admin
from .models import LearningPath, Module, Lecture, Assignment, Assessment, AssignmentAttempt, LectureProgress, ModuleProgress, LearningPathProgress, AssessmentAttempt

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0

class LectureInline(admin.TabularInline):
    model = Lecture
    extra = 0

class AssignmentInline(admin.StackedInline):
    model = Assignment
    extra = 0

class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'level', 'time', 'is_published', 'institution')
    search_fields = ('title', 'level', 'institution')
    list_filter = ('is_published',)
    inlines = [ModuleInline]

class ModuleAdmin(admin.ModelAdmin):
    list_display = ('module_id','title', 'learning_path')
    search_fields = ('title',)
    inlines = [LectureInline, AssignmentInline]

class LectureAdmin(admin.ModelAdmin):
    list_display = ('lecture_id','title', 'module')
    search_fields = ('title',)

class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'module', 'total_marks', 'attempts_count', 'total_questions' )
    search_fields = ('name',)

class AssignmentAttemptAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'get_assignment_name', 'status', 'attempted_at', 'score')
    search_fields = ( 'assignment__name',  'status')
    list_filter = ('status',)

    def get_student_username(self, obj):
        return obj.student.username
    get_student_username.admin_order_field = 'student'
    get_student_username.short_description = 'Student'

    def get_assignment_name(self, obj):
        return obj.assignment.name
    get_assignment_name.admin_order_field = 'assignment'
    get_assignment_name.short_description = 'Assignment'

    # Ensure 'attempt_number' and 'last_attempted' are attributes of the model
    def attempt_number(self, obj):
        return obj.attempt_number
    attempt_number.short_description = 'Attempt Number'

    def last_attempted(self, obj):
        return obj.last_attempted
    last_attempted.short_description = 'Last Attempted'


class AssessmentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Assessment._meta.fields]
    search_fields = ('name', 'exam_type', 'learning_path__name')  # assuming learning_path has a name
    list_filter = ('exam_type', 'password_exists', 'tab_switches_allowed', 'is_fullscreen', 'shuffle')

class LectureProgressAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'lecture', 'is_viewed', 'completed_at')
    search_fields = ('user_id', 'lecture__title')

admin.site.register(LectureProgress, LectureProgressAdmin)

class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'module', 'progress', 'is_completed', )
    search_fields = ('user_id', 'module__title')

admin.site.register(ModuleProgress, ModuleProgressAdmin)

class LearningPathProgressAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'learning_path', 'progress' , 'started_at', 'updated_at')
    search_fields = ('user_id', 'learning_path__title')

admin.site.register(LearningPathProgress, LearningPathProgressAdmin)

class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'user_id',
        'assessment',
        'attempt_number',
        'score',
        'status',
        'attempted_at',
    )
    list_filter = ('status', 'attempt_number', 'assessment')
    search_fields = ('user_id', 'assessment__name')
    ordering = ('-attempted_at',)

admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(LearningPath, LearningPathAdmin)
admin.site.register(Module, ModuleAdmin)
admin.site.register(Lecture, LectureAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentAttempt, AssignmentAttemptAdmin)
admin.site.register(AssessmentAttempt, AssessmentAttemptAdmin)