from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import date, timedelta
from common.models import TimeStampedModel

User = get_user_model()


class Department(TimeStampedModel):
    """Department model for organizing employees"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class LeaveType(TimeStampedModel):
    """Leave type codes from Excel legend (AL, SL, AL.5, etc.)"""
    code = models.CharField(max_length=10, unique=True, help_text="Leave code like AL, SL, AL.5")
    name = models.CharField(max_length=100, help_text="Full name like 'Annual Leave'")
    description = models.TextField(blank=True)
    
    # Properties from Excel structure
    is_paid = models.BooleanField(default=True, help_text="Whether this leave type is paid")
    affects_entitlement = models.BooleanField(default=True, help_text="Counts against annual entitlement")
    is_half_day = models.BooleanField(default=False, help_text="Half-day leave type (.5 codes)")
    color_code = models.CharField(max_length=7, default='#007bff', help_text="Color for calendar display")
    
    # System flags
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        ordering = ['code']


class EmployeeEntitlement(TimeStampedModel):
    """Employee annual entitlements - mirrors Excel Data Entry sheet"""
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entitlements')
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    year = models.PositiveIntegerField(default=timezone.now().year)
    
    # From Excel Data Entry columns
    annual_holiday_entitlement = models.DecimalField(
        max_digits=5, decimal_places=1, default=25.0,
        help_text="Annual holiday entitlement in days"
    )
    days_carried_over = models.DecimalField(
        max_digits=5, decimal_places=1, default=0.0,
        help_text="Days carried over from previous year"
    )
    time_in_lieu = models.DecimalField(
        max_digits=5, decimal_places=1, default=0.0,
        help_text="Time in Lieu (TIL) days available"
    )
    
    class Meta:
        unique_together = ['employee', 'year']
        ordering = ['-year', 'employee__first_name']
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate carry over if not set"""
        # Only auto-calculate if this is a new record and days_carried_over is 0
        is_new = self.pk is None
        
        if is_new and self.days_carried_over == 0:
            # Auto-calculate carry over from previous year
            carry_over_days = self.calculate_unused_days_from_previous_year()
            if carry_over_days > 0:
                self.days_carried_over = carry_over_days
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.year}"
    
    @property
    def total_available_days(self):
        """Total days available (entitlement + carried over + TIL)"""
        return self.annual_holiday_entitlement + self.days_carried_over + self.time_in_lieu
    
    @property
    def days_taken(self):
        """Calculate total days taken this year"""
        taken = self.employee.leave_requests.filter(
            start_date__year=self.year,
            status='APPROVED'
        ).aggregate(total=Sum('duration_days'))['total'] or 0
        return Decimal(str(taken))
    
    @property
    def remaining_entitlement(self):
        """Calculate remaining entitlement"""
        return self.total_available_days - self.days_taken
    
    def calculate_unused_days_from_previous_year(self):
        """Calculate unused days from previous year that can be carried over"""
        previous_year = self.year - 1
        
        try:
            previous_entitlement = EmployeeEntitlement.objects.get(
                employee=self.employee,
                year=previous_year
            )
            
            # Calculate unused days from previous year
            # Only annual entitlement can be carried over (not TIL or already carried over days)
            unused_days = previous_entitlement.annual_holiday_entitlement - previous_entitlement.days_taken
            
            # Ensure we don't carry over negative days
            return max(Decimal('0.0'), unused_days)
            
        except EmployeeEntitlement.DoesNotExist:
            # No previous year entitlement found
            return Decimal('0.0')
    
    def auto_calculate_carried_over_days(self, max_carry_over=None):
        """
        Automatically calculate and set carried over days from previous year
        
        Args:
            max_carry_over (Decimal): Maximum days that can be carried over (default: no limit)
        
        Returns:
            Decimal: The calculated carried over days
        """
        unused_days = self.calculate_unused_days_from_previous_year()
        
        # Apply maximum carry over limit if specified
        if max_carry_over is not None:
            unused_days = min(unused_days, Decimal(str(max_carry_over)))
        
        self.days_carried_over = unused_days
        return unused_days

    @property
    def utilization_rate(self):
        """Calculate utilization rate as percentage"""
        if self.total_available_days > 0:
            return (self.days_taken / self.total_available_days) * 100
        return 0


class LeaveRequest(TimeStampedModel):
    """Main leave request model"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(
        max_digits=4, decimal_places=1,
        help_text="Duration in days (0.5 for half days)"
    )
    
    # Request details
    reason = models.TextField(help_text="Reason for leave")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # Approval workflow
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_leave_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # System fields
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_leave_requests')
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.code} ({self.start_date} to {self.end_date})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate date range
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date")
        
        # Check for overlapping requests
        if self.employee_id:
            overlapping = LeaveRequest.objects.filter(
                employee=self.employee,
                status__in=['PENDING', 'APPROVED'],
                start_date__lte=self.end_date,
                end_date__gte=self.start_date
            ).exclude(pk=self.pk)
            
            if overlapping.exists():
                raise ValidationError("This leave request overlaps with an existing request")
    
    @property
    def is_future(self):
        """Check if leave is in the future"""
        return self.start_date > timezone.now().date()
    
    @property
    def can_be_cancelled(self):
        """Check if leave can be cancelled"""
        return self.status == 'PENDING' or (self.status == 'APPROVED' and self.is_future)
    
    def calculate_duration(self):
        """Calculate duration in days, excluding weekends"""
        if not self.start_date or not self.end_date:
            return 0
        
        duration = 0
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Skip weekends (Saturday=5, Sunday=6) - only count business days
            if current_date.weekday() not in [5, 6]:
                if self.leave_type.is_half_day:
                    duration += 0.5
                else:
                    duration += 1
            current_date += timedelta(days=1)
        
        return duration
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration if not set
        if not self.duration_days:
            self.duration_days = self.calculate_duration()
        
        # Set approval timestamp
        if self.status == 'APPROVED' and not self.approved_at:
            self.approved_at = timezone.now()
        
        super().save(*args, **kwargs)


class HolidayCalendar(TimeStampedModel):
    """National holidays and company holidays"""
    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)
    description = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False, help_text="Recurring annually")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"


class LeaveBalance(TimeStampedModel):
    """Real-time leave balance tracking by employee and leave type"""
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField(default=timezone.now().year)
    
    # Balance tracking
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    class Meta:
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['-year', 'employee__first_name', 'leave_type__code']
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.leave_type.code} ({self.year})"
    
    @property
    def available_days(self):
        """Calculate available days"""
        return self.allocated_days - self.used_days - self.pending_days
    
    @property
    def utilization_percentage(self):
        """Calculate utilization percentage"""
        if self.allocated_days > 0:
            return (self.used_days / self.allocated_days) * 100
        return 0


class LeaveComment(TimeStampedModel):
    """Comments on leave requests"""
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.leave_request} by {self.author.username}"


class LeaveStatusHistory(TimeStampedModel):
    """Track status changes for audit trail"""
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(
        max_length=10, 
        choices=LeaveRequest.STATUS_CHOICES,
        null=True, blank=True
    )
    new_status = models.CharField(max_length=10, choices=LeaveRequest.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Leave status histories"
        ordering = ['-created_at']
    
    def __str__(self):
        prev = dict(LeaveRequest.STATUS_CHOICES).get(self.previous_status, "None") if self.previous_status else "None"
        new = dict(LeaveRequest.STATUS_CHOICES).get(self.new_status, "Unknown")
        return f"{self.leave_request.employee.get_full_name()}: {prev} -> {new}"
