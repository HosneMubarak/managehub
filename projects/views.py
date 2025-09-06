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
            user = User.objects.get(pk=user_id)
            if project.assigned_users.filter(pk=user.pk).exists():
                project.assigned_users.remove(user)
                user_name = user.get_full_name() or user.username
                messages.success(request, f'{user_name} removed from project successfully!')
            else:
                messages.warning(request, 'User is not assigned to this project.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    return redirect('projects:detail', pk=pk)
