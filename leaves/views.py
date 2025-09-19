from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from datetime import date, timedelta
import calendar
import json
import decimal

from .models import (
    LeaveRequest, LeaveType, EmployeeEntitlement, Department,
    LeaveComment, HolidayCalendar, LeaveBalance
)
from .forms import (
    LeaveRequestForm, AdminLeaveRequestForm, LeaveRequestFilterForm, LeaveApprovalForm,
    LeaveCommentForm, EmployeeEntitlementForm, HolidayCalendarForm,
    LeaveCalendarFilterForm, BulkLeaveImportForm
)
from .services import LeaveCalculationService, LeaveReportService


class LeaveRequestListView(LoginRequiredMixin, ListView):
    """List all leave requests with filtering"""
    model = LeaveRequest
    template_name = 'leaves/leave_request_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = LeaveRequest.objects.select_related(
            'employee', 'leave_type', 'approved_by'
        ).order_by('-start_date')
        
        # Apply filters
        form = LeaveRequestFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
            
            if form.cleaned_data.get('leave_type'):
                queryset = queryset.filter(leave_type=form.cleaned_data['leave_type'])
            
            if form.cleaned_data.get('year'):
                queryset = queryset.filter(start_date__year=form.cleaned_data['year'])
            
            if form.cleaned_data.get('employee'):
                queryset = queryset.filter(employee=form.cleaned_data['employee'])
            
            if form.cleaned_data.get('start_date_from'):
                queryset = queryset.filter(start_date__gte=form.cleaned_data['start_date_from'])
            
            if form.cleaned_data.get('start_date_to'):
                queryset = queryset.filter(start_date__lte=form.cleaned_data['start_date_to'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = LeaveRequestFilterForm(self.request.GET)
        
        # Add summary statistics
        queryset = self.get_queryset()
        total_requests = queryset.count()
        pending_requests = queryset.filter(status='PENDING').count()
        approved_requests = queryset.filter(status='APPROVED').count()
        rejected_requests = queryset.filter(status='REJECTED').count()
        
        context['stats'] = {
            'total': total_requests,
            'pending': pending_requests,
            'approved': approved_requests,
            'rejected': rejected_requests,
        }
        
        return context


class MyLeaveRequestsView(LoginRequiredMixin, ListView):
    """Employee's personal leave requests"""
    model = LeaveRequest
    template_name = 'leaves/my_leave_requests.html'
    context_object_name = 'leave_requests'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = LeaveRequest.objects.filter(
            employee=self.request.user
        ).select_related('leave_type', 'approved_by').order_by('-start_date')
        
        # Apply filters
        status = self.request.GET.get('status')
        leave_type = self.request.GET.get('leave_type')
        year = self.request.GET.get('year')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if leave_type:
            queryset = queryset.filter(leave_type_id=leave_type)
        
        if year:
            queryset = queryset.filter(start_date__year=year)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get employee leave summary
        summary = LeaveCalculationService.get_employee_leave_summary(
            self.request.user
        )
        context['leave_summary'] = summary
        
        # Get leave requests by status
        requests = self.get_queryset()
        context['stats'] = {
            'total': requests.count(),
            'pending': requests.filter(status='PENDING').count(),
            'approved': requests.filter(status='APPROVED').count(),
            'rejected': requests.filter(status='REJECTED').count(),
        }
        
        return context


class EmployeeLeaveRequestsView(LoginRequiredMixin, ListView):
    """View a specific employee's leave requests (for staff/admin)"""
    model = LeaveRequest
    template_name = 'leaves/employee_leave_requests.html'
    context_object_name = 'leave_requests'
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        # Only staff can view other employees' requests
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden("You don't have permission to view this page.")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get the employee from URL parameter
        user_id = self.kwargs.get('user_id')
        try:
            # Use id field (UUID) instead of pkid
            self.employee = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise Http404("Employee not found")
        
        queryset = LeaveRequest.objects.filter(
            employee=self.employee
        ).select_related('leave_type', 'approved_by').order_by('-start_date')
        
        # Apply filters
        status = self.request.GET.get('status')
        leave_type = self.request.GET.get('leave_type')
        year = self.request.GET.get('year')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if leave_type:
            queryset = queryset.filter(leave_type_id=leave_type)
        
        if year:
            queryset = queryset.filter(start_date__year=year)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get employee leave summary
        summary = LeaveCalculationService.get_employee_leave_summary(
            self.employee
        )
        context['leave_summary'] = summary
        context['employee'] = self.employee
        
        # Get leave requests by status
        requests = self.get_queryset()
        context['stats'] = {
            'total': requests.count(),
            'pending': requests.filter(status='PENDING').count(),
            'approved': requests.filter(status='APPROVED').count(),
            'rejected': requests.filter(status='REJECTED').count(),
        }
        
        return context


class LeaveRequestDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a leave request"""
    model = LeaveRequest
    template_name = 'leaves/leave_request_detail.html'
    context_object_name = 'leave_request'
    slug_field = 'id'
    slug_url_kwarg = 'id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add comment form
        context['comment_form'] = LeaveCommentForm()
        
        # Add approval form for managers
        if self.request.user.is_staff or self.request.user.is_superuser:
            context['approval_form'] = LeaveApprovalForm()
        
        # Get employee leave summary
        summary = LeaveCalculationService.get_employee_leave_summary(
            self.object.employee, self.object.start_date.year
        )
        context['employee_summary'] = summary
        
        return context


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """Create a new leave request"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/leave_request_form.html'
    success_url = reverse_lazy('leaves:my_requests')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['employee'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add leave balance information
        summary = LeaveCalculationService.get_employee_leave_summary(self.request.user)
        context['leave_summary'] = summary
        
        # Add leave types for the sidebar
        context['leave_types'] = LeaveType.objects.filter(is_active=True).order_by('code')
        
        return context
    
    def form_valid(self, form):
        messages.success(
            self.request,
            'Your leave request has been submitted successfully.'
        )
        return super().form_valid(form)


class AdminLeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """Create a leave request on behalf of any user (for managers/HR)"""
    model = LeaveRequest
    form_class = AdminLeaveRequestForm
    template_name = 'leaves/admin_leave_request_form.html'
    success_url = reverse_lazy('leaves:list')
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow staff users to access this view
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to create leave requests for other users.')
            return redirect('leaves:create')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['created_by'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add leave types for the sidebar
        context['leave_types'] = LeaveType.objects.filter(is_active=True).order_by('code')
        
        # Add departments for filtering
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        return context
    
    def form_valid(self, form):
        employee = form.cleaned_data['employee']
        messages.success(
            self.request,
            f'Leave request for {employee.get_full_name()} has been created successfully.'
        )
        return super().form_valid(form)


class LeaveRequestUpdateView(LoginRequiredMixin, UpdateView):
    """Update a leave request (only if pending and owned by user)"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/leave_request_form.html'
    slug_field = 'id'
    slug_url_kwarg = 'id'
    
    def get_queryset(self):
        # Only allow editing own pending requests
        return LeaveRequest.objects.filter(
            employee=self.request.user,
            status='PENDING'
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['employee'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add leave balance information
        summary = LeaveCalculationService.get_employee_leave_summary(self.request.user)
        context['leave_summary'] = summary
        
        # Add leave types for the sidebar
        context['leave_types'] = LeaveType.objects.filter(is_active=True).order_by('code')
        
        return context
    
    def get_success_url(self):
        return reverse_lazy('leaves:detail', kwargs={'id': self.object.id})


@login_required
def dashboard_view(request):
    """Leave management dashboard"""
    # Get employee summary
    summary = LeaveCalculationService.get_employee_leave_summary(request.user)
    
    # Get recent leave requests
    recent_requests = LeaveRequest.objects.filter(
        employee=request.user
    ).select_related('leave_type')[:5]
    
    # Get upcoming leave
    upcoming_leave = LeaveRequest.objects.filter(
        employee=request.user,
        status='APPROVED',
        start_date__gte=timezone.now().date()
    ).select_related('leave_type').order_by('start_date')[:3]
    
    # Manager view - pending approvals
    pending_approvals = []
    if request.user.is_staff or request.user.is_superuser:
        pending_approvals = LeaveRequest.objects.filter(
            status='PENDING'
        ).select_related('employee', 'leave_type')[:10]
    
    context = {
        'leave_summary': summary,
        'recent_requests': recent_requests,
        'upcoming_leave': upcoming_leave,
        'pending_approvals': pending_approvals,
    }
    
    return render(request, 'leaves/dashboard.html', context)


@login_required
def leave_calendar_view(request):
    """Monthly leave calendar view"""
    # Get filter parameters
    form = LeaveCalendarFilterForm(request.GET)
    department = None
    month = timezone.now().month
    year = timezone.now().year
    
    if form.is_valid():
        department = form.cleaned_data.get('department')
        
        # Get month and year from cleaned data (already converted to int or None)
        month_value = form.cleaned_data.get('month')
        if month_value is not None:
            month = month_value
        
        year_value = form.cleaned_data.get('year')
        if year_value is not None:
            year = year_value
    else:
        # If form is not valid, try to get parameters directly from request
        try:
            month_param = request.GET.get('month')
            if month_param and month_param.strip():
                month = int(month_param)
        except (ValueError, TypeError):
            month = timezone.now().month
            
        try:
            year_param = request.GET.get('year')
            if year_param and year_param.strip():
                year = int(year_param)
        except (ValueError, TypeError):
            year = timezone.now().year
    
    # Validate month and year ranges
    if not (1 <= month <= 12):
        month = timezone.now().month
    
    current_year = timezone.now().year
    if not (current_year - 10 <= year <= current_year + 10):
        year = current_year
    
    # Get calendar data
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    calendar_data = LeaveCalculationService.get_team_leave_calendar(
        department, start_date, end_date
    )
    
    # Generate calendar weeks for grid display
    calendar_weeks = generate_calendar_weeks(year, month, calendar_data)
    
    # Calculate navigation dates
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
        
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    context = {
        'calendar_data': calendar_data,
        'calendar_weeks': calendar_weeks,
        'filter_form': form,
        'current_month': month,
        'current_year': year,
        'month_name': date(year, month, 1).strftime('%B %Y'),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    }
    
    return render(request, 'leaves/leave_calendar.html', context)


@login_required
def entitlement_list_view(request):
    """List employee entitlements"""
    year = request.GET.get('year', timezone.now().year)
    department = request.GET.get('department')
    
    entitlements = EmployeeEntitlement.objects.filter(
        year=year
    ).select_related('employee', 'department')
    
    if department:
        entitlements = entitlements.filter(department_id=department)
    
    # Paginate results
    paginator = Paginator(entitlements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'entitlements': page_obj,
        'departments': Department.objects.filter(is_active=True),
        'selected_year': int(year),
        'selected_department': department,
        'years': range(timezone.now().year - 2, timezone.now().year + 3),
    }
    
    return render(request, 'leaves/entitlement_list.html', context)


# AJAX Views
@login_required
def add_comment_ajax(request, pk):
    """Add comment to leave request via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        leave_request = get_object_or_404(LeaveRequest, id=pk)
        form = LeaveCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.leave_request = leave_request
            comment.author = request.user
            comment.save()
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'author': comment.author.get_full_name(),
                    'comment': comment.comment,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                }
            })
        
        return JsonResponse({'error': 'Invalid form data'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def approve_leave_ajax(request, pk):
    """Approve/reject leave request via AJAX - Following projects app pattern"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        leave_request = get_object_or_404(LeaveRequest, id=pk)
        
        if leave_request.status != 'PENDING':
            return JsonResponse({'success': False, 'error': 'Request is not pending'})
        
        try:
            # Get data from FormData like projects app
            action = request.POST.get('action')
            reason = request.POST.get('reason', '').strip()
            
            if action not in ['approve', 'reject']:
                return JsonResponse({'success': False, 'error': 'Invalid action'})
            
            if action == 'reject' and not reason:
                return JsonResponse({'success': False, 'error': 'Rejection reason is required'})
            
            if action == 'approve':
                LeaveCalculationService.approve_leave_request(
                    leave_request, request.user, reason
                )
                message = 'Leave request approved successfully'
            else:
                LeaveCalculationService.reject_leave_request(
                    leave_request, request.user, reason
                )
                message = 'Leave request rejected successfully'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'new_status': leave_request.status,
                'status_display': leave_request.get_status_display()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def cancel_leave_ajax(request, pk):
    """Cancel leave request via AJAX - Following projects app pattern"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        leave_request = get_object_or_404(LeaveRequest, id=pk)
        
        # Check permissions - only request owner can cancel
        if request.user != leave_request.employee:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        if not leave_request.can_be_cancelled:
            return JsonResponse({'success': False, 'error': 'Cannot cancel this request'})
        
        try:
            LeaveCalculationService.cancel_leave_request(
                leave_request, request.user, "Cancelled by user"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Leave request cancelled successfully',
                'new_status': leave_request.status,
                'status_display': leave_request.get_status_display()
            })
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def get_leave_balance_ajax(request):
    """Get employee leave balance via AJAX"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    year = request.GET.get('year', timezone.now().year)
    employee_id = request.GET.get('employee_id')
    
    # If employee_id is provided (for admin create form), use that employee
    # Otherwise, use the current user (for regular forms)
    if employee_id and request.user.is_staff:
        try:
            # Use pkid (primary key) instead of id (UUID field)
            employee = User.objects.get(pkid=employee_id, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Employee not found'}, status=404)
        except ValueError:
            return JsonResponse({'error': 'Invalid employee ID'}, status=400)
    else:
        employee = request.user
    
    summary = LeaveCalculationService.get_employee_leave_summary(
        employee, int(year)
    )
    
    return JsonResponse({
        'total_available': float(summary['total_available']),
        'approved_days': float(summary['approved_days']),
        'pending_days': float(summary['pending_days']),
        'remaining_days': float(summary['remaining_days']),
        'utilization_rate': float(summary['utilization_rate']),
        'employee_name': employee.get_full_name(),
        'leave_by_type': {
            code: {
                'approved': float(data['approved']),
                'pending': float(data['pending']),
                'total': float(data['total'])
            }
            for code, data in summary['leave_by_type'].items()
        }
    })


# Management Views (for staff/admin)
class EntitlementCreateView(LoginRequiredMixin, CreateView):
    """Create employee entitlement"""
    model = EmployeeEntitlement
    form_class = EmployeeEntitlementForm
    template_name = 'leaves/entitlement_form.html'
    success_url = reverse_lazy('leaves:entitlements')
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


class EntitlementUpdateView(LoginRequiredMixin, UpdateView):
    """Update employee entitlement"""
    model = EmployeeEntitlement
    form_class = EmployeeEntitlementForm
    template_name = 'leaves/entitlement_form.html'
    success_url = reverse_lazy('leaves:entitlements')
    slug_field = 'id'
    slug_url_kwarg = 'id'
    
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)


@login_required
def reports_view(request):
    """Leave reports view"""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden()
    
    # Get parameters
    year = int(request.GET.get('year', timezone.now().year))
    month = request.GET.get('month')
    department_id = request.GET.get('department')
    
    department = None
    if department_id:
        department = get_object_or_404(Department, id=department_id)
    
    context = {
        'year': year,
        'departments': Department.objects.filter(is_active=True),
        'selected_department': department,
    }
    
    if month:
        # Monthly report
        month = int(month)
        report_data = LeaveReportService.generate_monthly_summary(
            year, month, department
        )
        context.update({
            'report_type': 'monthly',
            'month': month,
            'report_data': report_data,
        })
    else:
        # Annual report
        report_data = LeaveReportService.generate_annual_summary(
            year, department
        )
        context.update({
            'report_type': 'annual',
            'report_data': report_data,
        })
    
    return render(request, 'leaves/reports.html', context)


def generate_calendar_weeks(year, month, calendar_data):
    """Generate calendar weeks for grid display"""
    from collections import namedtuple
    
    CalendarDay = namedtuple('CalendarDay', [
        'date', 'is_today', 'is_weekend', 'is_holiday', 
        'is_other_month', 'leave_requests'
    ])
    
    # Get the first day of the month and the calendar
    # Set first day of week to Saturday (5) for regional calendar format
    calendar.setfirstweekday(5)  # Saturday = 5
    first_day = date(year, month, 1)
    cal = calendar.monthcalendar(year, month)
    today = timezone.now().date()
    
    weeks = []
    
    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                # Previous/next month days - skip for now to keep it simple
                # We'll show empty cells for previous/next month
                day_date = None
                is_other_month = True
                is_today = False
                is_weekend = False
                is_holiday = False
                day_leave_requests = []
            else:
                day_date = date(year, month, day)
                is_other_month = False
                
                # Get leave requests for this day
                day_leave_requests = calendar_data.get(day_date, {}).get('leave_requests', [])
                
                # Check if it's today
                is_today = day_date == today
                
                # Check if it's weekend (Saturday=5, Sunday=6)
                is_weekend = day_date.weekday() in [5, 6]
                
                # Check if it's holiday
                is_holiday = calendar_data.get(day_date, {}).get('is_holiday', False)
            
            calendar_day = CalendarDay(
                date=day_date,
                is_today=is_today,
                is_weekend=is_weekend,
                is_holiday=is_holiday,
                is_other_month=is_other_month,
                leave_requests=day_leave_requests[:3] if day_leave_requests else []  # Limit to 3 for display
            )
            
            week_days.append(calendar_day)
        
        weeks.append(week_days)
    
    return weeks
