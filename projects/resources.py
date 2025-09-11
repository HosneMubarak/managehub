from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.contrib.auth import get_user_model
from .models import Project, BusinessArea, ProjectType, ProjectComment

User = get_user_model()


class BusinessAreaResource(resources.ModelResource):
    """Resource for importing/exporting Business Areas"""
    
    class Meta:
        model = BusinessArea
        fields = ('id', 'name', 'description', 'is_active', 'created_at', 'updated_at')
        export_order = ('id', 'name', 'description', 'is_active', 'created_at', 'updated_at')
        import_id_fields = ('name',)
        skip_unchanged = True
        report_skipped = True
        
    def before_import_row(self, row, **kwargs):
        """Clean and validate data before import"""
        # Ensure name is not empty
        if not row.get('name', '').strip():
            raise ValueError("Business Area name cannot be empty")
        
        # Clean name
        row['name'] = row['name'].strip()
        
        # Set default for is_active if not provided
        if 'is_active' not in row or row['is_active'] == '':
            row['is_active'] = True


class ProjectTypeResource(resources.ModelResource):
    """Resource for importing/exporting Project Types"""
    
    class Meta:
        model = ProjectType
        fields = ('id', 'name', 'description')
        export_order = ('id', 'name', 'description')
        import_id_fields = ('name',)
        skip_unchanged = True
        report_skipped = True
        
    def before_import_row(self, row, **kwargs):
        """Clean and validate data before import"""
        if not row.get('name', '').strip():
            raise ValueError("Project Type name cannot be empty")
        
        row['name'] = row['name'].strip()


class ProjectResource(resources.ModelResource):
    """Resource for importing/exporting Projects with comprehensive validation"""
    
    # Foreign key fields with custom widgets
    business_area = fields.Field(
        column_name='business_area',
        attribute='business_area',
        widget=ForeignKeyWidget(BusinessArea, 'name')
    )
    
    project_type = fields.Field(
        column_name='project_type',
        attribute='project_type',
        widget=ForeignKeyWidget(ProjectType, 'name')
    )
    
    project_manager = fields.Field(
        column_name='project_manager',
        attribute='project_manager',
        widget=ForeignKeyWidget(User, 'email')
    )
    
    created_by = fields.Field(
        column_name='created_by',
        attribute='created_by',
        widget=ForeignKeyWidget(User, 'email')
    )
    
    # Many-to-many field for assigned users
    assigned_users = fields.Field(
        column_name='assigned_users',
        attribute='assigned_users',
        widget=ManyToManyWidget(User, field='email', separator='|')
    )
    
    # Choice fields with validation
    status = fields.Field(
        column_name='status',
        attribute='status'
    )
    
    priority = fields.Field(
        column_name='priority',
        attribute='priority'
    )
    
    effort_size = fields.Field(
        column_name='effort_size',
        attribute='effort_size'
    )
    
    class Meta:
        model = Project
        fields = (
            'id', 'project_id', 'name', 'description', 'business_area', 'project_type',
            'project_manager', 'assigned_users', 'effort_size', 'priority', 'status',
            'start_date', 'estimated_end_date', 'actual_end_date', 'week_commencing',
            'clarity', 'timeline', 't_code', 'ipbss_remedy', 'created_by',
            'created_at', 'updated_at'
        )
        export_order = (
            'project_id', 'name', 'description', 'business_area', 'project_type',
            'project_manager', 'assigned_users', 'status', 'priority', 'effort_size',
            'start_date', 'estimated_end_date', 'actual_end_date', 'week_commencing',
            'clarity', 'timeline', 't_code', 'ipbss_remedy', 'created_by',
            'created_at', 'updated_at'
        )
        import_id_fields = ('project_id',)
        skip_unchanged = True
        report_skipped = True
        
    def before_import_row(self, row, **kwargs):
        """Comprehensive validation and cleaning before import"""
        
        # Validate required fields
        required_fields = ['project_id', 'name', 'description', 'business_area', 'project_type', 'project_manager']
        for field in required_fields:
            if not row.get(field, '').strip():
                raise ValueError(f"Required field '{field}' cannot be empty")
        
        # Clean and validate project_id (must be 7 digits)
        project_id = str(row['project_id']).strip()
        if not project_id.isdigit() or len(project_id) != 7:
            raise ValueError(f"Project ID must be exactly 7 digits, got: {project_id}")
        row['project_id'] = project_id
        
        # Clean text fields
        for field in ['name', 'description', 'clarity', 'timeline', 't_code', 'ipbss_remedy', 'week_commencing']:
            if field in row and row[field]:
                row[field] = str(row[field]).strip()
        
        # Validate choice fields
        valid_statuses = dict(Project.STATUS_CHOICES).keys()
        if row.get('status') and row['status'] not in valid_statuses:
            raise ValueError(f"Invalid status '{row['status']}'. Valid options: {', '.join(valid_statuses)}")
        
        valid_priorities = dict(Project.PRIORITY_CHOICES).keys()
        if row.get('priority') and row['priority'] not in valid_priorities:
            raise ValueError(f"Invalid priority '{row['priority']}'. Valid options: {', '.join(valid_priorities)}")
        
        valid_effort_sizes = dict(Project.EFFORT_SIZE_CHOICES).keys()
        if row.get('effort_size') and row['effort_size'] not in valid_effort_sizes:
            raise ValueError(f"Invalid effort size '{row['effort_size']}'. Valid options: {', '.join(valid_effort_sizes)}")
        
        # Set defaults for choice fields if not provided
        if not row.get('status'):
            row['status'] = 'NEW'
        if not row.get('priority'):
            row['priority'] = 'MEDIUM'
        
        # Set created_by to project_manager if not provided
        if not row.get('created_by'):
            row['created_by'] = row['project_manager']
    
    def after_import_instance(self, instance, new, **kwargs):
        """Additional processing after instance creation/update"""
        # Ensure the instance is saved before adding many-to-many relationships
        if new:
            instance.save()
    
    def get_queryset(self):
        """Optimize queryset for export"""
        return Project.objects.select_related(
            'business_area', 'project_type', 'project_manager', 'created_by'
        ).prefetch_related('assigned_users')


class ProjectCommentResource(resources.ModelResource):
    """Resource for importing/exporting Project Comments"""
    
    project = fields.Field(
        column_name='project',
        attribute='project',
        widget=ForeignKeyWidget(Project, 'project_id')
    )
    
    author = fields.Field(
        column_name='author',
        attribute='author',
        widget=ForeignKeyWidget(User, 'email')
    )
    
    class Meta:
        model = ProjectComment
        fields = ('id', 'project', 'author', 'comment', 'created_at', 'updated_at')
        export_order = ('id', 'project', 'author', 'comment', 'created_at', 'updated_at')
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
        
    def before_import_row(self, row, **kwargs):
        """Validate comment data before import"""
        required_fields = ['project', 'author', 'comment']
        for field in required_fields:
            if not row.get(field, '').strip():
                raise ValueError(f"Required field '{field}' cannot be empty")
        
        # Clean comment text
        row['comment'] = str(row['comment']).strip()


class UserResource(resources.ModelResource):
    """Resource for importing/exporting Users"""
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 
            'is_active', 'is_staff', 'date_joined', 'gender', 'occupation',
            'bio', 'phone_number', 'country', 'city_of_origin'
        )
        export_order = (
            'email', 'username', 'first_name', 'last_name', 'is_active', 
            'is_staff', 'gender', 'occupation', 'phone_number', 'country', 
            'city_of_origin', 'bio', 'date_joined'
        )
        import_id_fields = ('email',)
        skip_unchanged = True
        report_skipped = True
        
    def before_import_row(self, row, **kwargs):
        """Validate user data before import"""
        required_fields = ['email', 'first_name', 'last_name']
        for field in required_fields:
            if not row.get(field, '').strip():
                raise ValueError(f"Required field '{field}' cannot be empty")
        
        # Clean and validate email
        email = str(row['email']).strip().lower()
        if '@' not in email:
            raise ValueError(f"Invalid email format: {email}")
        row['email'] = email
        
        # Generate username from email if not provided
        if not row.get('username'):
            row['username'] = email.split('@')[0]
        
        # Clean name fields
        row['first_name'] = str(row['first_name']).strip().title()
        row['last_name'] = str(row['last_name']).strip().title()
        
        # Set defaults
        if 'is_active' not in row or row['is_active'] == '':
            row['is_active'] = True
        if 'is_staff' not in row or row['is_staff'] == '':
            row['is_staff'] = False
        
        # Validate choice fields
        if row.get('gender') and row['gender'] not in dict(User.Gender.choices).keys():
            row['gender'] = User.Gender.OTHER
        
        if row.get('occupation') and row['occupation'] not in dict(User.Occupation.choices).keys():
            row['occupation'] = User.Occupation.OTHER
    
    def after_import_instance(self, instance, new, **kwargs):
        """Set a default password for new users"""
        if new and not instance.password:
            # Set a temporary password that forces password change on first login
            instance.set_password('TempPass123!')
            instance.save()
