"""
Management command to populate database with demo data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from app.models import (
    Company, CompanyMember, Chatbot, CompanyChatbot,
    MemberChatbotAccess, SystemSettings
)

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
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Demo data created successfully!\n'
                f'  Companies: {len(companies)}\n'
                f'  Chatbots: {len(chatbots)}\n'
                f'  Members: Created for each company'
            )
        )

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
        for company in companies:
            # Create 5 members per company
            for i in range(5):
                role_cycle = ['management', 'operational', 'technical', 'support', 'other']
                member, created = CompanyMember.objects.get_or_create(
                    identification_document=f'{company.id:02d}{i:09d}',
                    defaults={
                        'company': company,
                        'name': f'Membro {i+1} - {company.name}',
                        'email': f'membro{i+1}@{company.email.split("@")[1]}',
                        'phone': f'(11)9{i}000-000{i}',
                        'department': ['Vendas', 'RH', 'TI', 'Marketing', 'Suporte'][i],
                        'regional': 'Sudeste',
                        'role_type': role_cycle[i % len(role_cycle)],
                        'position': 'Analista',
                        'sex': 'male' if i % 2 == 0 else 'female',
                        'birth_date': date.today() - timedelta(days=365 * (25 + i)),
                        'hire_date': date.today() - timedelta(days=30*i),
                        'city': 'São Paulo',
                        'state': 'SP',
                        'country': 'Brasil',
                        'status': 'active',
                    }
                )
                
                if created:
                    # Assign 1-3 random chatbots to each member
                    import random
                    num_chatbots = random.randint(1, 3)
                    selected_chatbots = random.sample(chatbots, num_chatbots)
                    
                    for chatbot in selected_chatbots:
                        MemberChatbotAccess.objects.get_or_create(
                            member=member,
                            chatbot=chatbot,
                            defaults={
                                'activation_date': member.hire_date,
                                'status': 'active'
                            }
                        )
