from django.core.management.base import BaseCommand
from leaves.models import LeaveType, EmployeeEntitlement, Department
from django.contrib.auth import get_user_model
from leaves.services import LeaveCalculationService

User = get_user_model()


class Command(BaseCommand):
    help = 'Debug leave data'

    def handle(self, *args, **options):
        # Check if leave types exist
        self.stdout.write(f'Leave Types: {LeaveType.objects.count()}')
        for lt in LeaveType.objects.all()[:5]:
            self.stdout.write(f'  {lt.code}: {lt.name} (Active: {lt.is_active})')

        # Check if departments exist  
        self.stdout.write(f'Departments: {Department.objects.count()}')
        for dept in Department.objects.all():
            self.stdout.write(f'  {dept.name}')

        # Check if user exists
        user = User.objects.first()
        self.stdout.write(f'User: {user.username if user else "No users"}')

        # Check entitlements
        self.stdout.write(f'Entitlements: {EmployeeEntitlement.objects.count()}')
        for ent in EmployeeEntitlement.objects.all():
            self.stdout.write(f'  {ent.employee.username}: {ent.total_available_days} days')

        # Test service
        if user:
            try:
                summary = LeaveCalculationService.get_employee_leave_summary(user)
                self.stdout.write(f'Summary keys: {list(summary.keys())}')
                self.stdout.write(f'Total available: {summary.get("total_available")}')
                self.stdout.write(f'Remaining days: {summary.get("remaining_days")}')
            except Exception as e:
                self.stdout.write(f'Error in service: {e}')
