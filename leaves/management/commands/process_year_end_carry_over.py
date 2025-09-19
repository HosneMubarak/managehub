from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
from leaves.services import LeaveReportService
from leaves.models import EmployeeEntitlement


class Command(BaseCommand):
    help = 'Process year-end carry over of unused leave days for all employees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Target year to process carry over for (default: current year)'
        )
        parser.add_argument(
            '--max-carry-over',
            type=float,
            help='Maximum days that can be carried over (default: no limit)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing even if carry over already exists'
        )

    def handle(self, *args, **options):
        year = options['year']
        max_carry_over = Decimal(str(options['max_carry_over'])) if options['max_carry_over'] else None
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'Processing year-end carry over for {year}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be saved')
            )

        # Check if carry over has already been processed
        if not force and not dry_run:
            existing_carry_over = EmployeeEntitlement.objects.filter(
                year=year,
                days_carried_over__gt=0
            ).count()
            
            if existing_carry_over > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {existing_carry_over} employees with existing carry over days for {year}. '
                        'Use --force to override existing carry over values.'
                    )
                )
                return

        # Process carry over
        try:
            results = LeaveReportService.process_year_end_carry_over(
                year=year,
                max_carry_over_days=max_carry_over,
                dry_run=dry_run
            )
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(f'Processed {results["processed_employees"]} employees')
            )
            
            if results['employees_with_carry_over']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Total days carried over: {results["total_days_carried_over"]}'
                    )
                )
                
                self.stdout.write('\nEmployees with carry over:')
                for emp in results['employees_with_carry_over']:
                    capped_msg = ' (CAPPED)' if emp['capped'] else ''
                    self.stdout.write(
                        f'  • {emp["employee"]}: {emp["unused_days"]} unused → '
                        f'{emp["carried_over_days"]} carried over{capped_msg}'
                    )
            
            if results['employees_without_previous_year']:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nEmployees without previous year entitlement ({len(results["employees_without_previous_year"])})'
                    )
                )
                for emp in results['employees_without_previous_year']:
                    self.stdout.write(f'  • {emp}')
            
            if results['errors']:
                self.stdout.write(
                    self.style.ERROR(f'\nErrors encountered ({len(results["errors"])}):')
                )
                for error in results['errors']:
                    self.stdout.write(f'  • {error["employee"]}: {error["error"]}')
            
            if not dry_run and results['employees_with_carry_over']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Successfully processed carry over for {len(results["employees_with_carry_over"])} employees'
                    )
                )
            elif dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n🔍 Dry run complete - would process carry over for {len(results["employees_with_carry_over"])} employees'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\n⚠️ No employees had unused days to carry over')
                )
                
        except Exception as e:
            raise CommandError(f'Error processing carry over: {str(e)}')
