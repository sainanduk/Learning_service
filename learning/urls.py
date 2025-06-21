# learning/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('learning_paths/institutes/<str:institute>/batch/<str:batch>/user/<uuid:user>/', views.learning_paths_list, name='learning_paths_list'),
    path('learning_paths/<uuid:id>/user/<uuid:user>/', views.learning_path_detail, name='learning_path_detail'),
    path('learning_paths/update-progress/user/<uuid:user>/lecture/<uuid:lecture_id>', views.update_learning_path_progress, name='update_learning_path_progress'),
    path('learning_paths/vendor/', views.vendor_learning_paths_list, name='learning_path_progress'),
    path('learning_paths/vendor/institute/<str:institute>/learning_path/<uuid:learning_path_id>/batch/<str:batch>/', views.vendor_add_learning_path_toInstitute, name='vendor_learning_path_progress'),
    
    # New routes for creating learning paths and lectures
    path('learning_paths/create/', views.create_learning_path_with_modules, name='create_learning_path_with_modules'),
    path('modules/<uuid:module_id>/lectures/create/', views.create_lectures_for_module, name='create_lectures_for_module'),
    
    # New routes for module and lecture management
    path('learning_paths/<uuid:learning_path_id>/modules/add/', views.add_module_to_learning_path, name='add_module_to_learning_path'),
    path('modules/<uuid:module_id>/modify/', views.modify_module, name='modify_module'),
    path('modules/<uuid:module_id>/lectures/add/', views.add_lecture_to_module, name='add_lecture_to_module'),
    path('lectures/<uuid:lecture_id>/modify/', views.modify_lecture, name='modify_lecture'),
]
