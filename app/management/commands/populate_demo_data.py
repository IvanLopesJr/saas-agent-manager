"""
Management command to populate database with demo data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from app.models import (
    Company, CompanyMember, Chatbot, CompanyChatbot,
    MemberChatbotAccess, UserStatusHistory, SystemSettings
)
from app.utils.billing import generate_billing_for_company
from app.utils.member_link import ensure_member_for_admin_user

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with demo data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating demo data...'))
        
        # Create companies
        companies = self._create_companies()
        
        # Create chatbots
        chatbots = self._create_chatbots()
        
        # Link chatbots to companies
        self._link_chatbots(companies, chatbots)
        
        # Create members
        self._create_members(companies, chatbots)
        
        # Create users
        self._create_users(companies)
        
        # Generate billing for previous month
        self._generate_billing(companies)
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Demo data created successfully!\n'
                f'  Companies: {len(companies)}\n'
                f'  Chatbots: {len(chatbots)}\n'
                f'  Members: Created for each company\n'
                f'  Users: Super Admin + 1 admin per company\n'
                f'  Billing: Generated for previous month'
            )
        )

    def _create_users(self, companies):
        # Create Super Admin
        if not User.objects.filter(role='super_admin').exists():
            super_admin = User.objects.create_superuser(
                username='admin',
                email='admin@saasmanager.com',
                password='admin123',
                role='super_admin',
                status='active',
            )
            self.stdout.write('  ✓ Super Admin created: admin / admin123')
        else:
            self.stdout.write('  - Super Admin already exists')

        # Create Company Admin for each company
        company_admin_map = {
            'Tech Solutions Ltda': ('admin_tech', 'Tech Admin'),
            'Marketing Pro Inc': ('admin_mkt', 'Marketing Admin'),
            'StartUp Inovação': ('admin_startup', 'Startup Admin'),
        }

        for company in companies:
            username = company_admin_map.get(company.name, (f'admin_{company.id}', company.name))[0]
            full_name = company_admin_map.get(company.name, ('', ''))[1] or f'Admin {company.name}'

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@{company.email.split("@")[1]}',
                    'company': company,
                    'role': 'admin_company',
                    'status': 'active',
                    'sync_member_profile': True,
                    'first_name': full_name.split()[0],
                    'last_name': ' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    'password': make_password('admin123'),
                }
            )
            if created:
                ensure_member_for_admin_user(user, consider_as_member=True, member_active=True)
                self.stdout.write(f'  ✓ User created: {username} / admin123 ({company.name})')
            else:
                self.stdout.write(f'  - User {username} already exists')

    def _generate_billing(self, companies):
        today = date.today()
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        period_start = date(prev_year, prev_month, 1)
        last_day = monthrange(prev_year, prev_month)[1]
        period_end = date(prev_year, prev_month, last_day)

        system_user = User.objects.filter(role='super_admin').first()
        if not system_user:
            self.stdout.write(self.style.WARNING('  ⚠ No super admin found — skipping billing generation'))
            return

        for company in companies:
            if company.billings.filter(period_start=period_start, period_end=period_end).exists():
                self.stdout.write(f'  - Billing already exists for {company.name}')
                continue

            try:
                billing = generate_billing_for_company(
                    company=company,
                    period_start=period_start,
                    period_end=period_end,
                    generated_by=system_user
                )
                if billing:
                    self.stdout.write(
                        f'  ✓ Billing: {company.name} = '
                        f'{company.currency_symbol} {billing.total_value:.2f}'
                    )
                else:
                    self.stdout.write(f'  ⚠ {company.name}: No charges this period')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ {company.name}: Error - {e}'))

    def _create_companies(self):
        companies = []
        
        company_data = [
            {
                'name': 'Tech Solutions Ltda',
                'email': 'contato@techsolutions.com',
                'phone': '(11)98765-4321',
                'identification_document': '12.345.678/0001-99',
                'address': 'Av. Paulista, 1000, São Paulo - SP',
                'member_price': Decimal('50.00'),
                'bill_admin_users': True,
                'currency': 'BRL',
                'billing_mode': 'per_user',
            },
            {
                'name': 'Marketing Pro Inc',
                'email': 'info@marketingpro.com',
                'phone': '(21)91234-5678',
                'identification_document': '98.765.432/0001-88',
                'address': 'Rua das Flores, 200, Rio de Janeiro - RJ',
                'member_price': Decimal('40.00'),
                'bill_admin_users': False,
                'currency': 'USD',
                'billing_mode': 'per_user_chatbot',
            },
            {
                'name': 'StartUp Inovação',
                'email': 'contact@startup.com',
                'phone': '(31)99999-8888',
                'identification_document': '11.222.333/0001-77',
                'address': 'Av. Afonso Pena, 500, Belo Horizonte - MG',
                'member_price': Decimal('35.00'),
                'bill_admin_users': False,
                'currency': 'BRL',
                'billing_mode': 'per_user',
            },
        ]
        
        for data in company_data:
            company, created = Company.objects.get_or_create(
                identification_document=data['identification_document'],
                defaults=data
            )
            companies.append(company)
            
            if created:
                self.stdout.write(f'  ✓ Company created: {company.name}')
        
        return companies

    def _create_chatbots(self):
        chatbots = []
        
        chatbot_data = [
            {
                'name': 'Chatbot Vendas',
                'description': 'Assistente virtual para vendas e atendimento',
                'base_price': Decimal('50.00'),
            },
            {
                'name': 'Chatbot RH',
                'description': 'Assistente para Recursos Humanos',
                'base_price': Decimal('40.00'),
            },
            {
                'name': 'Chatbot Suporte',
                'description': 'Suporte técnico automatizado',
                'base_price': Decimal('30.00'),
            },
        ]
        
        for data in chatbot_data:
            chatbot, created = Chatbot.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            chatbots.append(chatbot)
            
            if created:
                self.stdout.write(f'  ✓ Chatbot created: {chatbot.name}')
        
        return chatbots

    def _link_chatbots(self, companies, chatbots):
        for company in companies:
            for chatbot in chatbots:
                CompanyChatbot.objects.get_or_create(
                    company=company,
                    chatbot=chatbot,
                    defaults={'status': 'active'}
                )

    def _create_members(self, companies, chatbots):
        import random
        from django.utils import timezone
        base_date = date.today() - timedelta(days=90)  # 3 months ago
        created_ids = []
        for company in companies:
            for i in range(5):
                role_cycle = ['management', 'operational', 'technical', 'support', 'other']
                hire_date = base_date - timedelta(days=10*i)
                defaults = {
                    'company': company,
                    'name': f'Membro {i+1} - {company.name}',
                    'email': f'membro{i+1}@{company.email.split("@")[1]}',
                    'phone': f'(11)9{i}000-000{i}',
                    'department': ['Vendas', 'RH', 'TI', 'Marketing', 'Suporte'][i],
                    'regional': 'Sudeste',
                    'role_type': role_cycle[i % len(role_cycle)],
                    'position': 'Analista',
                    'sex': 'male' if i % 2 == 0 else 'female',
                    'birth_date': base_date - timedelta(days=365 * (25 + i)),
                    'hire_date': hire_date,
                    'city': 'São Paulo',
                    'state': 'SP',
                    'country': 'Brasil',
                    'status': 'active' if i < 4 else 'pending',
                }
                member, created = CompanyMember.objects.get_or_create(
                    identification_document=f'{company.id:02d}{i:09d}',
                    defaults=defaults,
                )
                created_ids.append(member.id)

                if not created:
                    member.hire_date = hire_date
                    member.save(update_fields=['hire_date'])

                # Fix status_history to align with hire_date
                try:
                    sh = member.status_history.filter(date_end__isnull=True).latest('date_start')
                    if sh.date_start != hire_date:
                        sh.date_start = hire_date
                        sh.save(update_fields=['date_start'])
                except UserStatusHistory.DoesNotExist:
                    UserStatusHistory.objects.create(
                        member=member,
                        status=member.status,
                        date_start=hire_date,
                        date_end=None,
                    )

                # Assign 1-3 random chatbots to each member
                num_chatbots = random.randint(1, min(3, len(chatbots)))
                selected_chatbots = random.sample(chatbots, num_chatbots)
                for chatbot in selected_chatbots:
                    MemberChatbotAccess.objects.get_or_create(
                        member=member,
                        chatbot=chatbot,
                        defaults={
                            'activation_date': hire_date,
                            'status': 'active'
                        }
                    )

        # Backdate created_at to base_date so billing filters pass
        backdate = timezone.make_aware(
            timezone.datetime.combine(base_date, timezone.datetime.min.time())
        )
        CompanyMember.objects.filter(id__in=created_ids).update(created_at=backdate)
