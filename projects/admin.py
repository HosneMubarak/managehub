from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from .models import (
    BusinessArea, ProjectType,
    Project, ProjectComment, ProjectStatusHistory
)
from .resources import (
    BusinessAreaResource, ProjectTypeResource, ProjectResource, 
    ProjectCommentResource
)

@admin.register(BusinessArea)
class BusinessAreaAdmin(ImportExportModelAdmin):
    resource_class = BusinessAreaResource
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(ProjectType)
class ProjectTypeAdmin(ImportExportModelAdmin):
    resource_class = ProjectTypeResource
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    ordering = ['name']

class ProjectCommentInline(admin.TabularInline):
    model = ProjectComment
    extra = 0
    fields = ['author', 'comment']
    readonly_fields = ['author']

@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    resource_class = ProjectResource
    list_display = [
        'project_id', 'name', 'business_area', 'project_manager', 
        'status', 'priority', 'start_date', 'estimated_end_date', 'created_at'
    ]
    list_filter = [
        'business_area', 'project_type', 'status', 'priority', 'effort_size',
        'created_at'
    ]
    search_fields = [
        'project_id', 'name', 'description', 'project_manager__first_name',
        'project_manager__last_name'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('project_id', 'name', 'description')
        }),
        ('Categorization', {
            'fields': ('business_area', 'project_type', 'effort_size')
        }),
        ('Management', {
            'fields': ('project_manager', 'assigned_users', 'priority', 'status')
        }),
        ('Timeline', {
            'fields': ('start_date', 'estimated_end_date', 'actual_end_date', 'week_commencing')
        }),
        ('Additional Fields', {
            'fields': ('clarity', 'timeline', 't_code', 'ipbss_remedy'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ProjectCommentInline]
    filter_horizontal = ['assigned_users']
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new project
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProjectComment)
class ProjectCommentAdmin(ImportExportModelAdmin):
    resource_class = ProjectCommentResource
    list_display = ['project', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['project__name', 'project__project_id', 'author__first_name', 'author__last_name', 'comment']
    ordering = ['-created_at']
    readonly_fields = ['author']
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new comment
            obj.author = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProjectStatusHistory)
class ProjectStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['project', 'previous_status', 'new_status', 'changed_by', 'created_at']
    list_filter = ['previous_status', 'new_status', 'created_at']
    search_fields = ['project__name', 'project__project_id', 'changed_by__first_name', 'changed_by__last_name', 'reason']
    ordering = ['-created_at']
    readonly_fields = ['changed_by']
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new status history
            obj.changed_by = request.user
        super().save_model(request, obj, form, change)
