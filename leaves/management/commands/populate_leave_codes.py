from django.core.management.base import BaseCommand
from django.db import transaction
from leaves.models import LeaveType, Department


class Command(BaseCommand):
    help = 'Populate leave type codes from Excel reference table'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing leave types before populating',
        )
    
    def handle(self, *args, **options):
        # Leave codes from Excel reference table with their properties
        leave_codes = [
            # Full Day Leave Types
            {'code': 'AL', 'name': 'Day Annual Leave', 'is_paid': True, 'affects_entitlement': True, 'is_half_day': False, 'color_code': '#007bff'},
            {'code': 'SL', 'name': 'Sick Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#dc3545'},
            {'code': 'C', 'name': 'Compassionate Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#6f42c1'},
            {'code': 'SFL', 'name': 'Special Forces Leave', 'is_paid': True, 'affects_entitlement': True, 'is_half_day': False, 'color_code': '#28a745'},
            {'code': 'J', 'name': 'Jury Duty', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#ffc107'},
            {'code': 'T', 'name': 'Training Day', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#17a2b8'},
            {'code': 'FM', 'name': 'Force Majeure', 'is_paid': False, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#6c757d'},
            {'code': 'UL', 'name': 'Unpaid Leave', 'is_paid': False, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#343a40'},
            {'code': 'MA', 'name': 'Offsite Meeting attendance', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#fd7e14'},
            {'code': 'CA', 'name': 'Conference attendance', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#e83e8c'},
            {'code': 'DL', 'name': 'Days in Lieu', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#20c997'},
            {'code': 'M/P', 'name': 'Maternity/Paternity Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#f8d7da'},
            {'code': 'STU', 'name': 'Study Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#d4edda'},
            {'code': 'EX', 'name': 'Exam Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#d1ecf1'},
            {'code': 'NH', 'name': 'National Holidays', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#fff3cd'},
            {'code': 'W', 'name': 'Weekends', 'is_paid': False, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#f8f9fa'},
            {'code': 'M', 'name': 'Moved departments', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#ffeaa7'},
            {'code': 'L', 'name': 'Left company', 'is_paid': False, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#636e72'},
            {'code': 'TIL', 'name': 'Time in Lieu', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#00b894'},
            {'code': 'ERD', 'name': 'Eircom Recovery Day', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#a29bfe'},
            {'code': 'LSL', 'name': 'Long Service Leave', 'is_paid': True, 'affects_entitlement': True, 'is_half_day': False, 'color_code': '#fd79a8'},
            {'code': 'TRA', 'name': 'Travel Time', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': False, 'color_code': '#fdcb6e'},
            {'code': 'CF', 'name': 'Carry Forward', 'is_paid': True, 'affects_entitlement': True, 'is_half_day': False, 'color_code': '#6c5ce7'},
            
            # Half Day Leave Types (.5 codes)
            {'code': 'AL.5', 'name': 'Half Day Annual Leave', 'is_paid': True, 'affects_entitlement': True, 'is_half_day': True, 'color_code': '#74b9ff'},
            {'code': 'SL.5', 'name': 'Half Day Sick Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#ff7675'},
            {'code': 'T.5', 'name': 'Half Day Training', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#55a3ff'},
            {'code': 'MA.5', 'name': 'Half Day Offsite Meeting attendance', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#ff9f43'},
            {'code': 'CA.5', 'name': 'Half Day Conference attendance', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#ff6b9d'},
            {'code': 'STU.5', 'name': 'Half Day Study Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#7bed9f'},
            {'code': 'EX.5', 'name': 'Half Day Exam Leave', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#70a1ff'},
            {'code': 'TIL.5', 'name': 'Half Time in Lieu', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#7fcdcd'},
            {'code': 'ERD.5', 'name': 'Half Eircom Recovery Day', 'is_paid': True, 'affects_entitlement': False, 'is_half_day': True, 'color_code': '#c7ecee'},
        ]
        
        if options['clear']:
            self.stdout.write('Clearing existing leave types...')
            LeaveType.objects.all().delete()
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for leave_data in leave_codes:
                leave_type, created = LeaveType.objects.get_or_create(
                    code=leave_data['code'],
                    defaults={
                        'name': leave_data['name'],
                        'description': f"Leave type: {leave_data['name']}",
                        'is_paid': leave_data['is_paid'],
                        'affects_entitlement': leave_data['affects_entitlement'],
                        'is_half_day': leave_data['is_half_day'],
                        'color_code': leave_data['color_code'],
                        'requires_approval': True,
                        'is_active': True,
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created leave type: {leave_type.code} - {leave_type.name}')
                    )
                else:
                    # Update existing leave type
                    leave_type.name = leave_data['name']
                    leave_type.is_paid = leave_data['is_paid']
                    leave_type.affects_entitlement = leave_data['affects_entitlement']
                    leave_type.is_half_day = leave_data['is_half_day']
                    leave_type.color_code = leave_data['color_code']
                    leave_type.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated leave type: {leave_type.code} - {leave_type.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated leave codes: {created_count} created, {updated_count} updated'
            )
        )
