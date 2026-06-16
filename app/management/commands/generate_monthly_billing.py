"""
Management command to generate monthly billing for all companies
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from calendar import monthrange
from app.models import Company
from app.utils.billing import generate_billing_for_company

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate monthly billing for all active companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month (1-12). Default: current month',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year (YYYY). Default: current year',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Company ID to generate billing for (optional)',
        )

    def handle(self, *args, **options):
        # Get period
        today = date.today()
        month = options.get('month') or today.month
        year = options.get('year') or today.year
        
        # Calculate period dates
        period_start = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        period_end = date(year, month, last_day)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Generating billing for period: {period_start} to {period_end}'
            )
        )
        
        # Get companies
        if options.get('company'):
            companies = Company.objects.filter(
                id=options['company'],
                status='active'
            )
        else:
            companies = Company.objects.filter(status='active')
        
        if not companies.exists():
            self.stdout.write(
                self.style.WARNING('No active companies found.')
            )
            return
        
        # Get system user for billing generation
        system_user = User.objects.filter(role='super_admin').first()
        if not system_user:
            self.stdout.write(
                self.style.ERROR('No Super Admin found. Cannot generate billing.')
            )
            return
        
        # Generate billing for each company
        success_count = 0
        error_count = 0
        
        for company in companies:
            try:
                # Check if billing already exists
                existing = company.billings.filter(
                    period_start=period_start,
                    period_end=period_end
                ).exists()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {company.name}: Billing already exists for this period'
                        )
                    )
                    continue
                
                # Generate billing
                billing = generate_billing_for_company(
                    company=company,
                    period_start=period_start,
                    period_end=period_end,
                    generated_by=system_user
                )
                
                if billing:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ {company.name}: {company.currency_symbol} {billing.total_value:.2f}'
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {company.name}: No charges for this period'
                        )
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ {company.name}: Error - {str(e)}'
                    )
                )
                error_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(
                f'Billing generation completed:\n'
                f'  Success: {success_count}\n'
                f'  Errors: {error_count}\n'
                f'  Total companies: {companies.count()}'
            )
        )
