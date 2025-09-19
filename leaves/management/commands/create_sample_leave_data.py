from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random

from leaves.models import (
    Department, LeaveType, EmployeeEntitlement, 
    LeaveRequest, HolidayCalendar
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample leave data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample data before creating new',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to create sample data for',
        )
    
    def handle(self, *args, **options):
        year = options['year']
        
        if options['clear']:
            self.stdout.write('Clearing existing sample data...')
            LeaveRequest.objects.all().delete()
            EmployeeEntitlement.objects.all().delete()
            HolidayCalendar.objects.all().delete()
            Department.objects.all().delete()
        
        with transaction.atomic():
            # Create departments
            departments_data = [
                {'name': 'Technology Team', 'description': 'Datacentre Network and Security Support & Maintenance'},
                {'name': 'Operations', 'description': 'Operations and Infrastructure Management'},
                {'name': 'Support', 'description': 'Customer Support and Technical Services'},
                {'name': 'Management', 'description': 'Executive and Management Team'},
            ]
            
            departments = []
            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    name=dept_data['name'],
                    defaults={'description': dept_data['description']}
                )
                departments.append(dept)
                if created:
                    self.stdout.write(f'Created department: {dept.name}')
            
            # Create national holidays
            holidays_data = [
                {'name': "New Year's Day", 'date': date(year, 1, 1)},
                {'name': "St. Patrick's Day", 'date': date(year, 3, 17)},
                {'name': 'Good Friday', 'date': date(year, 4, 7)},  # Approximate
                {'name': 'Easter Monday', 'date': date(year, 4, 10)},  # Approximate
                {'name': 'May Bank Holiday', 'date': date(year, 5, 1)},
                {'name': 'June Bank Holiday', 'date': date(year, 6, 5)},  # First Monday
                {'name': 'August Bank Holiday', 'date': date(year, 8, 7)},  # First Monday
                {'name': 'October Bank Holiday', 'date': date(year, 10, 30)},  # Last Monday
                {'name': 'Christmas Day', 'date': date(year, 12, 25)},
                {'name': 'St. Stephen\'s Day', 'date': date(year, 12, 26)},
            ]
            
            for holiday_data in holidays_data:
                holiday, created = HolidayCalendar.objects.get_or_create(
                    date=holiday_data['date'],
                    defaults={
                        'name': holiday_data['name'],
                        'description': f"National holiday: {holiday_data['name']}",
                        'is_recurring': True,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f'Created holiday: {holiday.name} on {holiday.date}')
            
            # Get active users
            users = User.objects.filter(is_active=True)
            if not users.exists():
                self.stdout.write(
                    self.style.WARNING('No active users found. Please create users first.')
                )
                return
            
            # Create employee entitlements
            entitlement_variations = [
                {'annual': 25.0, 'carried': 0.0, 'til': 0.0},
                {'annual': 30.0, 'carried': 5.0, 'til': 1.0},
                {'annual': 32.0, 'carried': 7.0, 'til': 0.0},
                {'annual': 25.0, 'carried': 14.0, 'til': 1.0},
                {'annual': 20.0, 'carried': 1.5, 'til': 0.0},
            ]
            
            for user in users[:10]:  # Limit to first 10 users
                dept = random.choice(departments)
                entitlement_data = random.choice(entitlement_variations)
                
                entitlement, created = EmployeeEntitlement.objects.get_or_create(
                    employee=user,
                    year=year,
                    defaults={
                        'department': dept,
                        'annual_holiday_entitlement': Decimal(str(entitlement_data['annual'])),
                        'days_carried_over': Decimal(str(entitlement_data['carried'])),
                        'time_in_lieu': Decimal(str(entitlement_data['til'])),
                    }
                )
                
                if created:
                    self.stdout.write(
                        f'Created entitlement for {user.get_full_name()}: '
                        f'{entitlement_data["annual"]} days + {entitlement_data["carried"]} carried + '
                        f'{entitlement_data["til"]} TIL'
                    )
            
            # Get leave types
            leave_types = list(LeaveType.objects.filter(is_active=True))
            if not leave_types:
                self.stdout.write(
                    self.style.WARNING(
                        'No leave types found. Run "populate_leave_codes" command first.'
                    )
                )
                return
            
            # Create sample leave requests
            entitlements = EmployeeEntitlement.objects.filter(year=year)
            leave_request_count = 0
            
            for entitlement in entitlements:
                user = entitlement.employee
                
                # Create 3-8 random leave requests per employee
                num_requests = random.randint(3, 8)
                
                for _ in range(num_requests):
                    # Random leave type (bias towards AL and SL)
                    if random.random() < 0.6:
                        leave_type = LeaveType.objects.filter(code__in=['AL', 'SL']).first()
                    else:
                        leave_type = random.choice(leave_types)
                    
                    if not leave_type:
                        continue
                    
                    # Random date in the year
                    start_of_year = date(year, 1, 1)
                    end_of_year = date(year, 12, 31)
                    
                    # Generate random start date
                    days_in_year = (end_of_year - start_of_year).days
                    random_days = random.randint(0, days_in_year - 10)
                    start_date = start_of_year + timedelta(days=random_days)
                    
                    # Random duration (1-10 days, bias towards shorter)
                    if leave_type.is_half_day:
                        duration = 0.5
                        end_date = start_date
                    else:
                        duration_days = random.choices(
                            [1, 2, 3, 4, 5, 7, 10],
                            weights=[30, 25, 20, 15, 5, 3, 2]
                        )[0]
                        duration = duration_days
                        end_date = start_date + timedelta(days=duration_days - 1)
                    
                    # Random status (bias towards approved)
                    status = random.choices(
                        ['PENDING', 'APPROVED', 'REJECTED'],
                        weights=[20, 70, 10]
                    )[0]
                    
                    # Create leave request
                    try:
                        leave_request = LeaveRequest.objects.create(
                            employee=user,
                            leave_type=leave_type,
                            start_date=start_date,
                            end_date=end_date,
                            duration_days=Decimal(str(duration)),
                            reason=f"Sample {leave_type.name.lower()} request",
                            status=status,
                            created_by=user,
                        )
                        
                        # Set approval details for approved requests
                        if status == 'APPROVED':
                            # Find a staff user to be the approver
                            approver = User.objects.filter(is_staff=True).first()
                            if approver:
                                leave_request.approved_by = approver
                                leave_request.approved_at = timezone.now()
                                leave_request.save()
                        
                        leave_request_count += 1
                        
                    except Exception as e:
                        # Skip if there are validation errors (e.g., overlapping dates)
                        continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created sample data:\n'
                    f'- {len(departments)} departments\n'
                    f'- {len(holidays_data)} holidays\n'
                    f'- {entitlements.count()} employee entitlements\n'
                    f'- {leave_request_count} leave requests'
                )
            )
            
            # Display summary statistics
            self.stdout.write('\nSample Data Summary:')
            self.stdout.write('-' * 40)
            
            for dept in departments:
                dept_entitlements = entitlements.filter(department=dept)
                if dept_entitlements.exists():
                    avg_entitlement = sum(
                        e.total_available_days for e in dept_entitlements
                    ) / dept_entitlements.count()
                    
                    self.stdout.write(
                        f'{dept.name}: {dept_entitlements.count()} employees, '
                        f'avg {avg_entitlement:.1f} days entitlement'
                    )
            
            # Leave request statistics
            total_requests = LeaveRequest.objects.count()
            pending = LeaveRequest.objects.filter(status='PENDING').count()
            approved = LeaveRequest.objects.filter(status='APPROVED').count()
            rejected = LeaveRequest.objects.filter(status='REJECTED').count()
            
            self.stdout.write(f'\nLeave Requests: {total_requests} total')
            self.stdout.write(f'- Pending: {pending}')
            self.stdout.write(f'- Approved: {approved}')
            self.stdout.write(f'- Rejected: {rejected}')
