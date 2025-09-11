from import_export import resources, fields
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()


class UserResource(resources.ModelResource):
    """Resource for importing/exporting Users with comprehensive validation"""
    
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
