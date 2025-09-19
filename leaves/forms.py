from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import (
    LeaveRequest, LeaveType, EmployeeEntitlement, 
    Department, LeaveComment, HolidayCalendar
)
from .services import LeaveCalculationService

User = get_user_model()


class LeaveRequestForm(forms.ModelForm):
    """Form for creating and editing leave requests"""
    
    class Meta:
        model = LeaveRequest
        fields = [
            'leave_type', 'start_date', 'end_date', 'reason'
        ]
        widgets = {
            'start_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'min': date.today().strftime('%Y-%m-%d')
                }
            ),
            'end_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                    'min': date.today().strftime('%Y-%m-%d')
                }
            ),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Please provide a reason for your leave request...'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Filter active leave types
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        
        # Add help text
        self.fields['start_date'].help_text = "Leave start date"
        self.fields['end_date'].help_text = "Leave end date"
        self.fields['reason'].help_text = "Provide a detailed reason for your leave request"
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        
        # Validate that start and end dates are not weekends
        if start_date:
            if start_date.weekday() in [4, 5]:  # Friday=4, Saturday=5 (common in many regions)
                raise ValidationError({
                    'start_date': 'Leave requests cannot start on weekends (Friday or Saturday).'
                })
        
        if end_date:
            if end_date.weekday() in [4, 5]:  # Friday=4, Saturday=5 (common in many regions)
                raise ValidationError({
                    'end_date': 'Leave requests cannot end on weekends (Friday or Saturday).'
                })
        
        # Validate date range
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError({
                    'end_date': 'End date must be after or equal to start date.'
                })
        
        if start_date and end_date and leave_type and self.employee:
            # Check eligibility
            eligibility = LeaveCalculationService.check_leave_eligibility(
                self.employee, leave_type, start_date, end_date
            )
            
            if not eligibility['eligible']:
                for error in eligibility['errors']:
                    raise ValidationError(error)
            
            # Set calculated duration
            cleaned_data['duration_days'] = eligibility['calculated_duration']
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.employee:
            instance.employee = self.employee
            instance.created_by = self.employee
        
        # Set duration from cleaned data
        if hasattr(self, 'cleaned_data') and 'duration_days' in self.cleaned_data:
            instance.duration_days = self.cleaned_data['duration_days']
        
        if commit:
            instance.save()
        
        return instance


class LeaveRequestFilterForm(forms.Form):
    """Form for filtering leave requests"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + LeaveRequest.STATUS_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    leave_type = forms.ModelChoiceField(
        queryset=LeaveType.objects.filter(is_active=True),
        required=False,
        empty_label="All Leave Types",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="All Employees",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    
    start_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Generate year choices (current year ± 2)
        current_year = timezone.now().year
        year_choices = [('', 'All Years')]
        for year in range(current_year - 2, current_year + 3):
            year_choices.append((year, str(year)))
        
        self.fields['year'].choices = year_choices


class LeaveApprovalForm(forms.Form):
    """Form for approving/rejecting leave requests"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional reason for approval/rejection...'
            }
        ),
        help_text="Optional reason for your decision"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('reason')
        
        # Require reason for rejection
        if action == 'reject' and not reason:
            raise ValidationError("Reason is required when rejecting a leave request")
        
        return cleaned_data


class LeaveCommentForm(forms.ModelForm):
    """Form for adding comments to leave requests"""
    
    class Meta:
        model = LeaveComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Add a comment...'
                }
            )
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
        
        return instance


class EmployeeEntitlementForm(forms.ModelForm):
    """Form for managing employee entitlements"""
    
    class Meta:
        model = EmployeeEntitlement
        fields = [
            'employee', 'department', 'year',
            'annual_holiday_entitlement', 'days_carried_over', 'time_in_lieu'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'annual_holiday_entitlement': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}
            ),
            'days_carried_over': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}
            ),
            'time_in_lieu': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default year
        if not self.instance.pk:
            self.fields['year'].initial = timezone.now().year
        
        # Filter active employees and departments
        self.fields['employee'].queryset = User.objects.filter(is_active=True)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)


class HolidayCalendarForm(forms.ModelForm):
    """Form for managing holidays"""
    
    class Meta:
        model = HolidayCalendar
        fields = ['name', 'date', 'description', 'is_recurring', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LeaveTypeForm(forms.ModelForm):
    """Form for managing leave types"""
    
    class Meta:
        model = LeaveType
        fields = [
            'code', 'name', 'description', 'is_paid', 'affects_entitlement',
            'is_half_day', 'color_code', 'requires_approval', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., AL, SL, AL.5'}
            ),
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'e.g., Annual Leave'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'color_code': forms.TextInput(
                attrs={'type': 'color', 'class': 'form-control form-control-color'}
            ),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'affects_entitlement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_half_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DepartmentForm(forms.ModelForm):
    """Form for managing departments"""
    
    class Meta:
        model = Department
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LeaveCalendarFilterForm(forms.Form):
    """Form for filtering leave calendar"""
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    month = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Month choices
        month_choices = [('', 'Current Month')]
        for i in range(1, 13):
            month_name = date(2000, i, 1).strftime('%B')
            month_choices.append((i, month_name))
        
        self.fields['month'].choices = month_choices
        
        # Year choices
        current_year = timezone.now().year
        year_choices = [('', 'Current Year')]
        for year in range(current_year - 1, current_year + 2):
            year_choices.append((year, str(year)))
        
        self.fields['year'].choices = year_choices
    
    def clean_month(self):
        """Validate month field"""
        month = self.cleaned_data.get('month')
        if month and month != '':
            try:
                month_int = int(month)
                if not (1 <= month_int <= 12):
                    raise forms.ValidationError("Month must be between 1 and 12")
                return month_int
            except (ValueError, TypeError):
                raise forms.ValidationError("Invalid month value")
        return None
    
    def clean_year(self):
        """Validate year field"""
        year = self.cleaned_data.get('year')
        if year and year != '':
            try:
                year_int = int(year)
                current_year = timezone.now().year
                if not (current_year - 10 <= year_int <= current_year + 10):
                    raise forms.ValidationError(f"Year must be between {current_year - 10} and {current_year + 10}")
                return year_int
            except (ValueError, TypeError):
                raise forms.ValidationError("Invalid year value")
        return None


class BulkLeaveImportForm(forms.Form):
    """Form for bulk importing leave data from Excel"""
    
    excel_file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls,.csv'
            }
        ),
        help_text="Upload Excel file with employee entitlement data"
    )
    
    year = forms.IntegerField(
        initial=timezone.now().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Overwrite existing entitlements for the selected year"
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB")
            
            # Check file extension
            allowed_extensions = ['.xlsx', '.xls', '.csv']
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    "Only Excel files (.xlsx, .xls) and CSV files are allowed"
                )
        
        return file
