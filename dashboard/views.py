from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from projects.models import Project, ProjectComment

User = get_user_model()

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Project statistics
        total_projects = Project.objects.count()
        new_projects = Project.objects.filter(status='NEW').count()
        completed_projects = Project.objects.filter(status='COMPLETE').count()
        ongoing_projects = Project.objects.filter(status='IN_PROGRESS').count()
        pending_projects = Project.objects.filter(status='ON_HOLD').count()
        
        # User statistics
        total_users = User.objects.filter(is_active=True).count()
        
        # Calculate estimated revenue based on effort size
        # Using estimated hours from effort size as a proxy for project value
        projects_with_effort = Project.objects.exclude(effort_size__isnull=True)
        total_estimated_hours = 0
        completed_estimated_hours = 0
        
        for project in projects_with_effort:
            hours = project.estimated_hours or 0
            total_estimated_hours += hours
            if project.status == 'COMPLETE':
                completed_estimated_hours += hours
        
        # Convert hours to revenue estimate (assuming $100/hour rate)
        hourly_rate = 100
        total_revenue = total_estimated_hours * hourly_rate
        total_sales = completed_estimated_hours * hourly_rate
        
        # Recent projects for additional sections
        recent_projects = Project.objects.select_related(
            'business_area', 'project_type'
        ).prefetch_related('assigned_users').order_by('-created_at')[:5]
        
        # Team members with project counts
        team_members = User.objects.filter(
            is_active=True
        ).annotate(
            project_count=Count('assigned_projects')
        ).order_by('-project_count')[:7]
        
        # Recent comments for activity
        recent_comments = ProjectComment.objects.select_related(
            'project', 'author'
        ).order_by('-created_at')[:5]
        
        context.update({
            'page_title': 'Dashboard Overview',
            'total_projects': total_projects,
            'total_users': total_users,
            'total_revenue': f"{total_revenue:,.0f}" if total_revenue else "0",
            'total_sales': total_sales,
            'new_projects': new_projects,
            'completed_projects': completed_projects,
            'ongoing_projects': ongoing_projects,
            'pending_projects': pending_projects,
            'recent_projects': recent_projects,
            'team_members': team_members,
            'recent_comments': recent_comments,
        })
        return context
