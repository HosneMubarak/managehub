from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from .models import (
    LeaveRequest, LeaveType, EmployeeEntitlement, 
    LeaveBalance, HolidayCalendar, Department
)

User = get_user_model()


class LeaveCalculationService:
    """Service class for leave calculations and business logic"""
    
    @staticmethod
    def calculate_leave_duration(start_date, end_date, exclude_weekends=True, exclude_holidays=True):
        """
        Calculate leave duration excluding weekends and holidays
        """
        if not start_date or not end_date or start_date > end_date:
            return 0
        
        duration = 0
        current_date = start_date
        
        # Get holidays if excluding them
        holidays = set()
        if exclude_holidays:
            holidays = set(
                HolidayCalendar.objects.filter(
                    date__range=[start_date, end_date],
                    is_active=True
                ).values_list('date', flat=True)
            )
        
        while current_date <= end_date:
            # Skip weekends if required (Saturday=5, Sunday=6)
            if exclude_weekends and current_date.weekday() in [5, 6]:  # Saturday=5, Sunday=6
                current_date += timedelta(days=1)
                continue
            
            # Skip holidays if required
            if exclude_holidays and current_date in holidays:
                current_date += timedelta(days=1)
                continue
            
            duration += 1
            current_date += timedelta(days=1)
        
        return duration
    
    @staticmethod
    def get_employee_leave_summary(employee, year=None):
        """
        Get comprehensive leave summary for an employee
        """
        if year is None:
            year = timezone.now().year
        
        # Get entitlement
        try:
            entitlement = EmployeeEntitlement.objects.get(employee=employee, year=year)
        except EmployeeEntitlement.DoesNotExist:
            # Create default entitlement if not exists
            department = Department.objects.first()  # Default department
            if not department:
                # Create a default department if none exists
                department = Department.objects.create(
                    name="Default Department",
                    description="Default department for employees"
                )
            entitlement = EmployeeEntitlement.objects.create(
                employee=employee,
                department=department,
                year=year
            )
        
        # Calculate leave taken by status
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            start_date__year=year
        )
        
        approved_days = leave_requests.filter(
            status='APPROVED'
        ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
        
        pending_days = leave_requests.filter(
            status='PENDING'
        ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
        
        # Calculate by leave type
        leave_by_type = {}
        for leave_type in LeaveType.objects.filter(is_active=True):
            type_approved = leave_requests.filter(
                leave_type=leave_type,
                status='APPROVED'
            ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
            
            type_pending = leave_requests.filter(
                leave_type=leave_type,
                status='PENDING'
            ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
            
            leave_by_type[leave_type.code] = {
                'approved': type_approved,
                'pending': type_pending,
                'total': type_approved + type_pending
            }
        
        return {
            'entitlement': entitlement,
            'total_available': entitlement.total_available_days,
            'approved_days': approved_days,
            'pending_days': pending_days,
            'remaining_days': entitlement.total_available_days - approved_days - pending_days,
            'utilization_rate': entitlement.utilization_rate,
            'leave_by_type': leave_by_type
        }
    
    @staticmethod
    def check_leave_eligibility(employee, leave_type, start_date, end_date, duration_days=None):
        """
        Check if employee is eligible for the requested leave
        """
        errors = []
        warnings = []
        
        # Calculate duration if not provided
        if duration_days is None:
            duration_days = LeaveCalculationService.calculate_leave_duration(
                start_date, end_date
            )
        
        # Check date validity
        if start_date > end_date:
            errors.append("Start date cannot be after end date")
        
        if start_date <= timezone.now().date():
            warnings.append("Leave request is for past or current date")
        
        # Check for overlapping requests
        overlapping = LeaveRequest.objects.filter(
            employee=employee,
            status__in=['PENDING', 'APPROVED'],
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if overlapping.exists():
            errors.append("This leave request overlaps with an existing request")
        
        # Check entitlement if leave affects entitlement
        if leave_type.affects_entitlement:
            summary = LeaveCalculationService.get_employee_leave_summary(
                employee, start_date.year
            )
            
            if duration_days > summary['remaining_days']:
                errors.append(
                    f"Insufficient leave balance. Requested: {duration_days} days, "
                    f"Available: {summary['remaining_days']} days"
                )
        
        return {
            'eligible': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'calculated_duration': duration_days
        }
    
    @staticmethod
    def approve_leave_request(leave_request, approved_by, reason=""):
        """
        Approve a leave request and update balances
        """
        from .models import LeaveStatusHistory
        
        # Create status history
        LeaveStatusHistory.objects.create(
            leave_request=leave_request,
            previous_status=leave_request.status,
            new_status='APPROVED',
            changed_by=approved_by,
            reason=reason
        )
        
        # Update leave request
        leave_request.status = 'APPROVED'
        leave_request.approved_by = approved_by
        leave_request.approved_at = timezone.now()
        leave_request.save()
        
        # Update leave balance
        LeaveCalculationService.update_leave_balance(
            leave_request.employee,
            leave_request.leave_type,
            leave_request.start_date.year
        )
        
        return leave_request
    
    @staticmethod
    def reject_leave_request(leave_request, rejected_by, reason):
        """
        Reject a leave request
        """
        from .models import LeaveStatusHistory
        
        # Create status history
        LeaveStatusHistory.objects.create(
            leave_request=leave_request,
            previous_status=leave_request.status,
            new_status='REJECTED',
            changed_by=rejected_by,
            reason=reason
        )
        
        # Update leave request
        leave_request.status = 'REJECTED'
        leave_request.rejection_reason = reason
        leave_request.save()
        
        return leave_request
    
    @staticmethod
    def cancel_leave_request(leave_request, cancelled_by, reason=""):
        """
        Cancel a leave request
        """
        from .models import LeaveStatusHistory
        
        if not leave_request.can_be_cancelled:
            raise ValueError("This leave request cannot be cancelled")
        
        # Create status history
        LeaveStatusHistory.objects.create(
            leave_request=leave_request,
            previous_status=leave_request.status,
            new_status='CANCELLED',
            changed_by=cancelled_by,
            reason=reason
        )
        
        # Update leave request
        leave_request.status = 'CANCELLED'
        leave_request.save()
        
        # Update leave balance if it was previously approved
        if leave_request.status in ['APPROVED', 'CANCELLED']:
            LeaveCalculationService.update_leave_balance(
                leave_request.employee,
                leave_request.leave_type,
                leave_request.start_date.year
            )
        
        return leave_request
    
    @staticmethod
    def update_leave_balance(employee, leave_type, year):
        """
        Update leave balance for an employee and leave type
        """
        balance, created = LeaveBalance.objects.get_or_create(
            employee=employee,
            leave_type=leave_type,
            year=year,
            defaults={'allocated_days': Decimal('0')}
        )
        
        # Calculate used days
        used_days = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            start_date__year=year,
            status='APPROVED'
        ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
        
        # Calculate pending days
        pending_days = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            start_date__year=year,
            status='PENDING'
        ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
        
        balance.used_days = used_days
        balance.pending_days = pending_days
        balance.save()
        
        return balance
    
    @staticmethod
    def get_team_leave_calendar(department=None, start_date=None, end_date=None):
        """
        Get team leave calendar for managers
        """
        if start_date is None:
            start_date = timezone.now().date().replace(day=1)  # First day of current month
        
        if end_date is None:
            # Last day of current month
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        
        # Filter by department if provided
        leave_requests = LeaveRequest.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=['APPROVED', 'PENDING']
        ).select_related('employee', 'leave_type')
        
        if department:
            # Filter by employees in the department
            employee_ids = EmployeeEntitlement.objects.filter(
                department=department
            ).values_list('employee_id', flat=True)
            leave_requests = leave_requests.filter(employee_id__in=employee_ids)
        
        # Group by date
        calendar_data = {}
        current_date = start_date
        
        while current_date <= end_date:
            calendar_data[current_date] = {
                'date': current_date,
                'is_weekend': current_date.weekday() in [5, 6],  # Saturday=5, Sunday=6
                'is_holiday': HolidayCalendar.objects.filter(
                    date=current_date, is_active=True
                ).exists(),
                'leave_requests': []
            }
            current_date += timedelta(days=1)
        
        # Add leave requests to calendar
        for leave_request in leave_requests:
            current_date = leave_request.start_date
            while current_date <= leave_request.end_date:
                if current_date in calendar_data:
                    calendar_data[current_date]['leave_requests'].append(leave_request)
                current_date += timedelta(days=1)
        
        return calendar_data
    
    @staticmethod
    def import_entitlements_from_excel_data(excel_data):
        """
        Import entitlements from Excel data structure
        Expected format: [
            {
                'employee_name': 'John Doe',
                'department': 'Technology Team',
                'annual_holiday_entitlement': 30.0,
                'days_carried_over': 5.0,
                'time_in_lieu': 2.0
            }
        ]
        """
        imported_count = 0
        errors = []
        
        for row in excel_data:
            try:
                # Find or create department
                department, _ = Department.objects.get_or_create(
                    name=row['department'],
                    defaults={'description': f"Imported from Excel: {row['department']}"}
                )
                
                # Find employee by name (you might want to improve this matching)
                employee_names = row['employee_name'].split(' ', 1)
                first_name = employee_names[0]
                last_name = employee_names[1] if len(employee_names) > 1 else ''
                
                try:
                    employee = User.objects.get(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name
                    )
                except User.DoesNotExist:
                    errors.append(f"Employee not found: {row['employee_name']}")
                    continue
                except User.MultipleObjectsReturned:
                    errors.append(f"Multiple employees found: {row['employee_name']}")
                    continue
                
                # Create or update entitlement
                entitlement, created = EmployeeEntitlement.objects.update_or_create(
                    employee=employee,
                    year=timezone.now().year,
                    defaults={
                        'department': department,
                        'annual_holiday_entitlement': Decimal(str(row['annual_holiday_entitlement'])),
                        'days_carried_over': Decimal(str(row['days_carried_over'])),
                        'time_in_lieu': Decimal(str(row['time_in_lieu']))
                    }
                )
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error processing {row.get('employee_name', 'Unknown')}: {str(e)}")
        
        return {
            'imported_count': imported_count,
            'errors': errors
        }


class LeaveReportService:
    """Service for generating leave reports"""
    
    @staticmethod
    def generate_monthly_summary(year, month, department=None):
        """
        Generate monthly leave summary similar to Excel monthly sheets
        """
        from calendar import monthrange
        
        # Get date range for the month
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Get employees
        employees = User.objects.filter(is_active=True)
        if department:
            employee_ids = EmployeeEntitlement.objects.filter(
                department=department, year=year
            ).values_list('employee_id', flat=True)
            employees = employees.filter(id__in=employee_ids)
        
        summary_data = []
        
        for employee in employees:
            # Get leave requests for the month
            leave_requests = LeaveRequest.objects.filter(
                employee=employee,
                start_date__lte=end_date,
                end_date__gte=start_date,
                status='APPROVED'
            ).select_related('leave_type')
            
            # Calculate daily leave codes
            daily_codes = {}
            for day in range(1, last_day + 1):
                current_date = date(year, month, day)
                daily_codes[day] = []
                
                for leave_request in leave_requests:
                    if leave_request.start_date <= current_date <= leave_request.end_date:
                        daily_codes[day].append(leave_request.leave_type.code)
            
            # Calculate totals
            sick_leave_days = leave_requests.filter(
                leave_type__code__in=['SL', 'SL.5']
            ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
            
            holidays_taken = leave_requests.filter(
                leave_type__affects_entitlement=True
            ).aggregate(total=Sum('duration_days'))['total'] or Decimal('0')
            
            # Get entitlement
            try:
                entitlement = EmployeeEntitlement.objects.get(
                    employee=employee, year=year
                )
                remaining = entitlement.remaining_entitlement
            except EmployeeEntitlement.DoesNotExist:
                remaining = Decimal('0')
            
            summary_data.append({
                'employee': employee,
                'daily_codes': daily_codes,
                'sick_leave_days': sick_leave_days,
                'holidays_taken': holidays_taken,
                'entitlement_remaining': remaining
            })
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'employees': summary_data
        }
    
    @staticmethod
    def generate_annual_summary(year, department=None):
        """
        Generate annual leave summary for all employees
        """
        employees = User.objects.filter(is_active=True)
        if department:
            employee_ids = EmployeeEntitlement.objects.filter(
                department=department, year=year
            ).values_list('employee_id', flat=True)
            employees = employees.filter(id__in=employee_ids)
        
        summary_data = []
        
        for employee in employees:
            summary = LeaveCalculationService.get_employee_leave_summary(employee, year)
            summary_data.append({
                'employee': employee,
                'summary': summary
            })
        
        return {
            'year': year,
            'department': department,
            'employees': summary_data
        }
