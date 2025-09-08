from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Project, BusinessArea, ProjectType, 
    ProjectComment
)

User = get_user_model()

class ProjectForm(forms.ModelForm):
    """Form for creating and updating projects"""
    
    assigned_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select users to assign to this project"
    )
    
    effort_size = forms.ChoiceField(
        choices=Project.EFFORT_SIZE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=Project.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=Project.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Project
        fields = [
            'project_id', 'name', 'description', 'business_area', 'project_type',
            'project_manager', 'effort_size', 'priority', 'status',
            'start_date', 'estimated_end_date', 'actual_end_date', 'week_commencing',
            'clarity', 'timeline', 't_code'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter project name'
            }),
            'project_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter project description'
            }),
            'business_area': forms.Select(attrs={'class': 'form-select'}),
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'project_manager': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'estimated_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actual_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'week_commencing': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'w/c 9/6/25'
            }),
            'clarity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter project clarity description'
            }),
            'timeline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter timeline information'
            }),
            't_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter t/code'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter project managers to active users
        self.fields['project_manager'].queryset = User.objects.filter(is_active=True)
        
        # If editing existing project, populate assigned users
        if self.instance and self.instance.pk:
            self.fields['assigned_users'].initial = self.instance.assigned_users.all()
    
    def save(self, commit=True):
        project = super().save(commit=False)
        if commit:
            project.save()
            # Handle user assignments for both new and existing projects
            assigned_users = self.cleaned_data.get('assigned_users', [])
            project.assigned_users.set(assigned_users)
        return project

class ProjectSearchForm(forms.Form):
    """Form for searching and filtering projects"""
    
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search projects...'
        })
    )
    
    business_area = forms.ModelChoiceField(
        queryset=BusinessArea.objects.filter(is_active=True),
        required=False,
        empty_label="All Business Areas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Project.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + Project.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    effort_size = forms.ChoiceField(
        choices=[('', 'All Effort Sizes')] + Project.EFFORT_SIZE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    project_manager = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="All Managers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class ProjectCommentForm(forms.ModelForm):
    """Form for adding comments to projects"""
    
    class Meta:
        model = ProjectComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add your comment...'
            }),
        }
