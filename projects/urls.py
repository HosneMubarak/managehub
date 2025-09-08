from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Project CRUD operations
    path('', views.ProjectListView.as_view(), name='list'),
    path('create/', views.ProjectCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ProjectUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'),
    
    # Project management functionality
    path('<uuid:pk>/comment/', views.add_project_comment, name='add_comment'),
    path('<uuid:pk>/assign/', views.manage_project_assignment, name='manage_assignment'),
    path('<uuid:pk>/assignment/<uuid:user_id>/remove/', views.remove_project_assignment, name='remove_assignment'),
    path('<uuid:pk>/update-field/', views.update_project_field, name='update_field'),
]
