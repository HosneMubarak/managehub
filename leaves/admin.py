from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from django.contrib.auth import get_user_model

from .models import (
    Department, LeaveType, EmployeeEntitlement, LeaveRequest,
    HolidayCalendar, LeaveBalance, LeaveComment, LeaveStatusHistory
)

User = get_user_model()


# Resources for Import/Export
class EmployeeEntitlementResource(resources.ModelResource):
    employee = fields.Field(
        column_name='employee',
        attribute='employee',
        widget=ForeignKeyWidget(User, 'email')
    )
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(Department, 'name')
    )
    
    class Meta:
        model = EmployeeEntitlement
        fields = (
            'employee', 'department', 'year',
            'annual_holiday_entitlement', 'days_carried_over', 'time_in_lieu'
        )
        export_order = fields


class LeaveTypeResource(resources.ModelResource):
    class Meta:
        model = LeaveType
        fields = (
            'code', 'name', 'description', 'is_paid', 'affects_entitlement',
            'is_half_day', 'color_code', 'requires_approval', 'is_active'
        )
        export_order = fields


class LeaveRequestResource(resources.ModelResource):
    employee = fields.Field(
        column_name='employee',
        attribute='employee',
        widget=ForeignKeyWidget(User, 'email')
    )
    leave_type = fields.Field(
        column_name='leave_type',
        attribute='leave_type',
        widget=ForeignKeyWidget(LeaveType, 'code')
    )
    
    class Meta:
        model = LeaveRequest
        fields = (
            'employee', 'leave_type', 'start_date', 'end_date',
            'duration_days', 'reason', 'status', 'created_at'
        )
        export_order = fields


# Admin Classes
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(LeaveType)
class LeaveTypeAdmin(ImportExportModelAdmin):
    resource_class = LeaveTypeResource
    list_display = [
        'code', 'name', 'is_paid', 'affects_entitlement',
        'is_half_day', 'requires_approval', 'color_display', 'is_active'
    ]
    list_filter = [
        'is_paid', 'affects_entitlement', 'is_half_day',
        'requires_approval', 'is_active'
    ]
    search_fields = ['code', 'name', 'description']
    ordering = ['code']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; color: white; border-radius: 3px;">{}</span>',
            obj.color_code,
            obj.code
        )
    color_display.short_description = 'Color'


@admin.register(EmployeeEntitlement)
class EmployeeEntitlementAdmin(ImportExportModelAdmin):
    resource_class = EmployeeEntitlementResource
    list_display = [
        'employee', 'department', 'year', 'annual_holiday_entitlement',
        'days_carried_over', 'time_in_lieu', 'total_available_days',
        'utilization_display'
    ]
    list_filter = ['year', 'department', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering = ['-year', 'employee__first_name']
    
    def total_available_days(self, obj):
        try:
            return f"{float(obj.total_available_days):.1f}"
        except (ValueError, TypeError):
            return "N/A"
    total_available_days.short_description = 'Total Available'
    
    def utilization_display(self, obj):
        try:
            rate = float(obj.utilization_rate)
            color = 'green' if rate < 70 else 'orange' if rate < 90 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">N/A</span>')
    utilization_display.short_description = 'Utilization'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(ImportExportModelAdmin):
    resource_class = LeaveRequestResource
    list_display = [
        'employee', 'leave_type', 'start_date', 'end_date',
        'duration_days', 'status_display', 'approved_by', 'created_at'
    ]
    list_filter = [
        'status', 'leave_type', 'start_date', 'created_at',
        'employee__entitlements__department'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name',
        'employee__email', 'reason'
    ]
    ordering = ['-start_date']
    readonly_fields = ['duration_days', 'approved_at']
    
    fieldsets = (
        ('Leave Details', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'duration_days', 'reason')
        }),
        ('Status', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('System', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        })
    )
    
    def status_display(self, obj):
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'CANCELLED': 'gray'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'leave_type', 'approved_by', 'created_by'
        )


@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_recurring', 'is_active']
    list_filter = ['is_recurring', 'is_active', 'date']
    search_fields = ['name', 'description']
    ordering = ['date']
    date_hierarchy = 'date'


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'leave_type', 'year', 'allocated_days',
        'used_days', 'pending_days', 'available_days', 'utilization_display'
    ]
    list_filter = ['year', 'leave_type', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    ordering = ['-year', 'employee__first_name', 'leave_type__code']
    
    def utilization_display(self, obj):
        try:
            rate = float(obj.utilization_percentage)
            color = 'green' if rate < 70 else 'orange' if rate < 90 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, rate
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">N/A</span>')
    utilization_display.short_description = 'Utilization'


@admin.register(LeaveComment)
class LeaveCommentAdmin(admin.ModelAdmin):
    list_display = ['leave_request', 'author', 'comment_preview', 'created_at']
    list_filter = ['created_at', 'author']
    search_fields = ['comment', 'author__first_name', 'author__last_name']
    ordering = ['-created_at']
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'leave_request', 'author'
        )


@admin.register(LeaveStatusHistory)
class LeaveStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'leave_request', 'previous_status', 'new_status',
        'changed_by', 'reason_preview', 'created_at'
    ]
    list_filter = ['previous_status', 'new_status', 'created_at']
    search_fields = [
        'leave_request__employee__first_name',
        'leave_request__employee__last_name',
        'changed_by__first_name', 'changed_by__last_name',
        'reason'
    ]
    ordering = ['-created_at']
    
    def reason_preview(self, obj):
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_preview.short_description = 'Reason'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'leave_request', 'changed_by'
        )


# Admin site customization
admin.site.site_header = "ManageHub Leave Management"
admin.site.site_title = "Leave Admin"
admin.site.index_title = "Leave Management Administration"
