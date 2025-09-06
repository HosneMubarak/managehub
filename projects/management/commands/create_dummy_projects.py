from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
import random
from datetime import datetime, timedelta
from projects.models import Project, BusinessArea, ProjectType, ProjectComment

User = get_user_model()

class Command(BaseCommand):
    help = 'Create 10 dummy projects with realistic data'

    def handle(self, *args, **options):
        fake = Faker()
        
        # Get all users for assignments
        users = list(User.objects.all())
        if not users:
            self.stdout.write(
                self.style.ERROR('No users found. Please create users first using: python manage.py create_dummy_users')
            )
            return
        
        # Create business areas if they don't exist
        business_areas = []
        ba_names = ['Technology', 'Marketing', 'Operations', 'Finance', 'HR', 'Sales']
        for ba_name in ba_names:
            ba, created = BusinessArea.objects.get_or_create(
                name=ba_name,
                defaults={'description': f'{ba_name} department projects'}
            )
            business_areas.append(ba)
        
        # Create project types if they don't exist
        project_types = []
        pt_names = ['Software Development', 'Marketing Campaign', 'Process Improvement', 'Research', 'Infrastructure', 'Training']
        for pt_name in pt_names:
            pt, created = ProjectType.objects.get_or_create(
                name=pt_name,
                defaults={'description': f'{pt_name} projects'}
            )
            project_types.append(pt)
        
        # Project name templates
        project_templates = [
            "Customer Portal Redesign",
            "Mobile App Development",
            "Data Analytics Platform",
            "Marketing Automation System",
            "Employee Training Program",
            "Security Audit Implementation",
            "Cloud Migration Project",
            "Performance Optimization",
            "User Experience Enhancement",
            "Integration Platform Development",
            "Digital Transformation Initiative",
            "Quality Assurance Framework",
            "Business Process Automation",
            "Customer Feedback System",
            "Inventory Management System"
        ]
        
        projects_created = 0
        
        for i in range(10):
            # Generate unique project ID (7 digits as per model validation)
            project_id = str(fake.random_int(min=1000000, max=9999999))
            while Project.objects.filter(project_id=project_id).exists():
                project_id = str(fake.random_int(min=1000000, max=9999999))
            
            # Generate project data
            project_name = random.choice(project_templates)
            if Project.objects.filter(name=project_name).exists():
                project_name = f"{project_name} {fake.random_int(min=1, max=999)}"
            
            # Generate dates
            start_date = fake.date_between(start_date='-6m', end_date='today')
            estimated_end_date = fake.date_between(start_date=start_date, end_date=start_date + timedelta(days=random.randint(30, 365)))
            
            # Create project with correct field names
            project = Project.objects.create(
                project_id=project_id,
                name=project_name,
                description=fake.text(max_nb_chars=500),
                business_area=random.choice(business_areas),
                project_type=random.choice(project_types),
                project_manager=random.choice(users),
                priority=random.choice([choice[0] for choice in Project.PRIORITY_CHOICES]),
                status=random.choice([choice[0] for choice in Project.STATUS_CHOICES]),
                effort_size=random.choice([choice[0] for choice in Project.EFFORT_SIZE_CHOICES]),
                start_date=start_date,
                estimated_end_date=estimated_end_date,
                week_commencing=f"w/c {start_date.strftime('%m/%d/%y')}",
                created_by=random.choice(users)
            )
            
            # Assign 1-4 users to each project using direct M2M relationship
            assigned_users = random.sample(users, k=random.randint(1, min(4, len(users))))
            project.assigned_users.set(assigned_users)
            
            # Add 1-3 comments to each project
            for _ in range(random.randint(1, 3)):
                ProjectComment.objects.create(
                    project=project,
                    author=random.choice(users),
                    comment=fake.text(max_nb_chars=300)
                )
            
            projects_created += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created project: {project.name} (ID: {project.project_id})')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {projects_created} dummy projects with assignments and comments')
        )
