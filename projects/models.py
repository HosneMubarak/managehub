from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
from common.models import TimeStampedModel

User = get_user_model()

class BusinessArea(TimeStampedModel):
    """Business areas like IT, CTO, OE, Consumer, etc."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ProjectType(models.Model):
    """Project types like 'Project', 'n/a', etc."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Project(TimeStampedModel):
    """Main project model"""
    
    # Status choices - simplified from ProjectStatus model
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETE', 'Complete'),
        ('ON_HOLD', 'On Hold'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Priority choices - simplified from Priority model
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Effort size choices - simplified from EffortSize model
    EFFORT_SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
    ]
    
    # Basic project information
    project_id = models.CharField(
        max_length=20, 
        unique=True, 
        help_text="Project ID like 1007127",
        validators=[RegexValidator(regex=r'^\d{7}$', message='Project ID must be 7 digits')]
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Categorization
    business_area = models.ForeignKey(BusinessArea, on_delete=models.PROTECT)
    project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT)
    
    # Management
    project_manager = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='managed_projects'
    )
    assigned_users = models.ManyToManyField(
        User,
        related_name='assigned_projects',
        help_text="Engineers assigned to this project"
    )
    
    # Project details - now using choice fields instead of foreign keys
    effort_size = models.CharField(
        max_length=1, 
        choices=EFFORT_SIZE_CHOICES, 
        null=True, 
        blank=True,
        help_text="Estimated effort size"
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='MEDIUM'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='NEW'
    )
    
    # Timeline
    start_date = models.DateField(null=True, blank=True)
    estimated_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    week_commencing = models.CharField(
        max_length=20, 
        blank=True, 
        help_text="Week commencing date like 'w/c 9/6/25'"
    )
    
    # New fields as requested
    clarity = models.CharField(
        max_length=200,
        blank=True,
        help_text="Project clarity description"
    )
    timeline = models.CharField(
        max_length=200,
        blank=True,
        help_text="Project timeline information"
    )
    t_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="T/code identifier"
    )
    
    # Additional tracking
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_projects')
    
    class Meta:
        indexes = [
            models.Index(fields=['project_id']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['business_area', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project_id} - {self.name}"
    
    @property
    def is_overdue(self):
        """Check if project is overdue"""
        if self.estimated_end_date and self.status != 'COMPLETE':
            return timezone.now().date() > self.estimated_end_date
        return False
    
    @property
    def duration_days(self):
        """Calculate project duration"""
        if self.start_date:
            end_date = self.actual_end_date or timezone.now().date()
            return (end_date - self.start_date).days
        return None
    
    @property
    def priority_order(self):
        """Return numeric priority for sorting (1=highest)"""
        priority_map = {'CRITICAL': 1, 'HIGH': 2, 'MEDIUM': 3, 'LOW': 4}
        return priority_map.get(self.priority, 5)
    
    @property
    def estimated_hours(self):
        """Get estimated hours based on effort size"""
        hours_map = {'S': 40, 'M': 80, 'L': 160}
        return hours_map.get(self.effort_size, 0) if self.effort_size else None

class ProjectComment(TimeStampedModel):
    """Comments and notes on projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.project} by {self.author.username}"

class ProjectStatusHistory(TimeStampedModel):
    """Track status changes"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(
        max_length=20, 
        choices=Project.STATUS_CHOICES,
        null=True, 
        blank=True
    )
    new_status = models.CharField(
        max_length=20, 
        choices=Project.STATUS_CHOICES
    )
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Project status histories"
        ordering = ['-created_at']
    
    def __str__(self):
        prev = dict(Project.STATUS_CHOICES).get(self.previous_status, "None") if self.previous_status else "None"
        new = dict(Project.STATUS_CHOICES).get(self.new_status, "Unknown")
        return f"{self.project}: {prev} -> {new}"