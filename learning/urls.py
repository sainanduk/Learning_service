# learning/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('learning_paths/institutes/<str:institute>/batch/<str:batch>/user/<uuid:user>/', views.learning_paths_list, name='learning_paths_list'),
    path('learning_paths/<uuid:id>/user/<uuid:user>/', views.learning_path_detail, name='learning_path_detail'),
    path('learning_paths/update-progress/user/<uuid:user>/lecture/<uuid:lecture_id>', views.update_learning_path_progress, name='update_learning_path_progress'),
    path('learning_paths/vendor/', views.vendor_learning_paths_list, name='learning_path_progress'),
    path('learning_paths/vendor/institute/<str:institute>/learning_path/<uuid:learning_path_id>/batch/<str:batch>/', views.vendor_add_learning_path_toInstitute, name='vendor_learning_path_progress'),
]
