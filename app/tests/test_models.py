import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.db.models.deletion import ProtectedError
from app.models import Company, User, CompanyMember, Chatbot, CompanyChatbot, MemberChatbotAccess, Billing, SystemSettings


class CompanyModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Teste Ltda',
            email='teste@teste.com',
            identification_document='12.345.678/0001-99',
            member_price=Decimal('50.00'),
        )

    def test_charge_inactive_members_default_false(self):
        self.assertFalse(self.company.charge_inactive_members)

    def test_billing_mode_default_per_user(self):
        self.assertEqual(self.company.billing_mode, 'per_user')

    def test_currency_symbol_auto_set(self):
        self.assertEqual(self.company.currency_symbol, 'R$')


class UserModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Teste Ltda',
            email='teste@teste.com',
            identification_document='12.345.678/0001-00',
            member_price=Decimal('50.00'),
        )

    def test_super_admin_creation(self):
        user = User.objects.create_user(
            username='admin', email='admin@teste.com',
            password='teste123', role='super_admin'
        )
        self.assertTrue(user.is_super_admin())
        self.assertFalse(user.is_admin_company())

    def test_admin_company_needs_company(self):
        user = User(username='admin2', email='admin2@teste.com', role='admin_company')
        with self.assertRaises(Exception):
            user.full_clean()


class BillingTest(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.company = Company.objects.create(
            name='Teste Ltda', email='teste@teste.com',
            identification_document='12.345.678/0001-11',
            member_price=Decimal('50.00'), billing_mode='per_user',
        )

    def test_billing_generation_per_user_no_members(self):
        from app.utils.billing import generate_billing_for_company
        result = generate_billing_for_company(
            self.company, date(2026, 6, 1), date(2026, 6, 30), None
        )
        self.assertIsNone(result)

    def test_estimated_cost_no_members(self):
        from app.utils.billing import calculate_estimated_cost
        cost = calculate_estimated_cost(self.company)
        self.assertEqual(cost, Decimal('0.00'))
