from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import Project, ProjectComment, BusinessArea
from .forms import ProjectForm, ProjectSearchForm, ProjectCommentForm

User = get_user_model()

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/projects-list.html'
    context_object_name = 'projects'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Project.objects.select_related(
            'business_area', 'project_type', 'project_manager'
        )
        
        # Handle search and filters
        form = ProjectSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(project_id__icontains=search) |
                    Q(description__icontains=search) |
                    Q(project_manager__first_name__icontains=search) |
                    Q(project_manager__last_name__icontains=search)
                )
            
            business_area = form.cleaned_data.get('business_area')
            if business_area:
                queryset = queryset.filter(business_area=business_area)
            
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            priority = form.cleaned_data.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)
            
            project_manager = form.cleaned_data.get('project_manager')
            if project_manager:
                queryset = queryset.filter(project_manager=project_manager)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ProjectSearchForm(self.request.GET)
        context['total_projects'] = Project.objects.count()
        context['active_projects'] = Project.objects.filter(
            status__in=['NEW', 'IN_PROGRESS']
        ).count()
        # Add active users for inline editing
        context['active_users'] = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/projects-overview.html'
    context_object_name = 'project'
    
    def get_object(self):
        return get_object_or_404(Project, id=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        context['assigned_users'] = project.assigned_users.all()
        context['comments'] = ProjectComment.objects.filter(
            project=project
        ).select_related('author').order_by('-created_at')
        context['comment_form'] = ProjectCommentForm()
        context['available_users'] = User.objects.filter(
            is_active=True
        ).exclude(id__in=project.assigned_users.values_list('id', flat=True))
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/projects-create.html'
    success_url = reverse_lazy('projects:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Project created successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/projects-create.html'
    
    def get_object(self):
        return get_object_or_404(Project, id=self.kwargs['pk'])
    
    def get_success_url(self):
        return reverse_lazy('projects:detail', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Project updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('projects:list')
    template_name = 'projects/project_confirm_delete.html'
    
    def get_object(self):
        return get_object_or_404(Project, id=self.kwargs['pk'])
    
    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        project_name = project.name
        
        # Many-to-many relationships will be automatically cleared
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Project "{project_name}" deleted successfully!')
        return response

def add_project_comment(request, pk):
    """Add comment to project via AJAX"""
    if request.method == 'POST':
        project = get_object_or_404(Project, id=pk)
        form = ProjectCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.project = project
            comment.author = request.user
            comment.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'author': comment.author.get_full_name() or comment.author.username,
                        'comment': comment.comment,
                        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                        'is_internal': comment.is_internal
                    }
                })
            else:
                messages.success(request, 'Comment added successfully!')
                return redirect('projects:detail', pk=pk)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return redirect('projects:detail', pk=pk)

def manage_project_assignment(request, pk):
    """Manage project assignments"""
    project = get_object_or_404(Project, id=pk)
    
    if request.method == 'POST':
        user_id = request.POST.get('user')
        if user_id:
            try:
                user = User.objects.get(pk=user_id, is_active=True)
                
                # Check if user is already assigned to this project
                if project.assigned_users.filter(pk=user.pk).exists():
                    messages.warning(request, f'{user.get_full_name() or user.username} is already assigned to this project.')
                else:
                    project.assigned_users.add(user)
                    messages.success(request, f'{user.get_full_name() or user.username} assigned to project successfully!')
            except User.DoesNotExist:
                messages.error(request, 'Invalid user selected.')
        else:
            messages.error(request, 'Please select a user to assign.')
    
    return redirect('projects:detail', pk=pk)

def remove_project_assignment(request, pk, user_id):
    """Remove user from project"""
    if request.method == 'POST':
        project = get_object_or_404(Project, id=pk)
        try:
            user = User.objects.get(id=user_id)  # Use id field (UUID) instead of pk
            if project.assigned_users.filter(id=user.id).exists():  # Use id field for consistency
                project.assigned_users.remove(user)
                user_name = user.get_full_name() or user.username
                messages.success(request, f'{user_name} removed from project successfully!')
            else:
                messages.warning(request, 'User is not assigned to this project.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    return redirect('projects:detail', pk=pk)

def update_project_field(request, pk):
    """Update project field via AJAX for inline editing"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        project = get_object_or_404(Project, id=pk)
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        # Define allowed fields for inline editing
        allowed_fields = {
            'status': Project.STATUS_CHOICES,
            'priority': Project.PRIORITY_CHOICES,
            'project_manager': None,
            'name': None,
            'effort_size': Project.EFFORT_SIZE_CHOICES,
            'timeline': None,
            't_code': None,
            'description': None
        }
        
        if field not in allowed_fields:
            return JsonResponse({'success': False, 'error': 'Invalid field'})
        
        try:
            if field == 'project_manager':
                # Handle project manager update
                if value:
                    manager = User.objects.get(id=value, is_active=True)
                    project.project_manager = manager
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid manager selected'})
            elif field in ['name', 'timeline', 't_code', 'description']:
                # Handle text fields
                if field == 'name' and not value.strip():
                    return JsonResponse({'success': False, 'error': 'Project name cannot be empty'})
                if field == 'name' and len(value.strip()) > 200:
                    return JsonResponse({'success': False, 'error': 'Project name too long (max 200 characters)'})
                if field == 'timeline' and len(value) > 200:
                    return JsonResponse({'success': False, 'error': 'Timeline too long (max 200 characters)'})
                if field == 't_code' and len(value) > 50:
                    return JsonResponse({'success': False, 'error': 'T/Code must be 50 characters or less'})
                if field == 'description' and len(value) > 1000:
                    return JsonResponse({'success': False, 'error': 'Description too long (max 1000 characters)'})
                
                setattr(project, field, value.strip() if value else '')
                display_value = value if value else None
            elif field == 'effort_size':
                # Handle effort size choice field (without hours display)
                valid_choices = [choice[0] for choice in allowed_fields[field]]
                if value and value not in valid_choices:
                    return JsonResponse({'success': False, 'error': 'Invalid effort size'})
                setattr(project, field, value if value else None)
            else:
                # Handle other choice fields (status, priority)
                valid_choices = [choice[0] for choice in allowed_fields[field]]
                if value not in valid_choices:
                    return JsonResponse({'success': False, 'error': 'Invalid choice'})
                setattr(project, field, value)
            
            project.save()
            
            # Return updated display value
            if field == 'project_manager':
                display_value = project.project_manager.get_full_name() or project.project_manager.username
            elif field in ['name', 'timeline', 't_code', 'description']:
                display_value = getattr(project, field) or ''
            elif field == 'effort_size':
                if project.effort_size:
                    display_value = project.get_effort_size_display()
                else:
                    display_value = None
            else:
                display_value = getattr(project, f'get_{field}_display')()
            
            return JsonResponse({
                'success': True,
                'display_value': display_value,
                'field': field
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Manager not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_project_team_data(request, pk):
    """Get project team data for assignment modal"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        project = get_object_or_404(Project, id=pk)
        
        try:
            # Get current team members
            current_team = []
            for user in project.assigned_users.all():
                current_team.append({
                    'id': str(user.id),
                    'name': user.get_full_name() or user.username,
                    'email': user.email,
                    'avatar': user.avatar.url if user.avatar else None
                })
            
            # Get available users (not assigned to this project)
            available_users = []
            for user in User.objects.filter(is_active=True).exclude(
                id__in=project.assigned_users.values_list('id', flat=True)
            ):
                available_users.append({
                    'id': str(user.id),
                    'name': user.get_full_name() or user.username,
                    'email': user.email,
                    'avatar': user.avatar.url if user.avatar else None
                })
            
            return JsonResponse({
                'success': True,
                'current_team': current_team,
                'available_users': available_users
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def bulk_assign_users(request, pk):
    """Bulk assign users to project"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        project = get_object_or_404(Project, id=pk)
        
        try:
            import json
            user_ids_json = request.POST.get('users', '[]')
            user_ids = json.loads(user_ids_json)
            
            # Validate user IDs and get user objects
            users = User.objects.filter(id__in=user_ids, is_active=True)
            
            # Clear current assignments and set new ones
            project.assigned_users.set(users)
            
            # Prepare response data
            assigned_count = users.count()
            user_names = [user.get_full_name() or user.username for user in users]
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully assigned {assigned_count} users to project',
                'assigned_users': user_names
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid user data format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def remove_project_assignment_ajax(request, pk, user_id):
    """Remove user from project via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        project = get_object_or_404(Project, id=pk)
        
        try:
            user = User.objects.get(id=user_id)
            if project.assigned_users.filter(id=user.id).exists():
                project.assigned_users.remove(user)
                user_name = user.get_full_name() or user.username
                return JsonResponse({
                    'success': True,
                    'message': f'{user_name} removed from project successfully'
                })
            else:
                return JsonResponse({'success': False, 'error': 'User is not assigned to this project'})
                
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})
