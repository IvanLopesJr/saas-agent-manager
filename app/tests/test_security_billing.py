from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from app.models import (
    Billing,
    BillingDetail,
    Chatbot,
    Company,
    CompanyChatbot,
    CompanyMember,
    MemberChatbotAccess,
    User,
)
from app.utils.billing import generate_billing_for_company


class LoginSecurityTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )

    def test_failed_login_attempts_are_rate_limited(self):
        url = reverse('login')
        for _ in range(5):
            self.client.post(url, {'username': 'admin', 'password': 'wrong'})

        response = self.client.post(url, {'username': 'admin', 'password': 'wrong'})

        self.assertContains(response, 'Muitas tentativas de login')

    def test_login_next_rejects_external_url(self):
        response = self.client.post(
            f"{reverse('login')}?next=https://example.invalid/phishing",
            {'username': 'admin', 'password': 'StrongPass123!'},
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_company_cannot_login_when_company_is_inactive(self):
        company = Company.objects.create(
            name='Inactive Co',
            email='inactive@example.com',
            identification_document='inactive-001',
            member_price=Decimal('50.00'),
            status='inactive',
        )
        User.objects.create_user(
            username='company-admin',
            email='company-admin@example.com',
            password='StrongPass123!',
            role='admin_company',
            status='active',
            company=company,
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'company-admin', 'password': 'StrongPass123!'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class BillingConsistencyTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super',
            email='super@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )

    def test_charge_inactive_members_closes_first_cycle_without_chatbot(self):
        company = Company.objects.create(
            name='Charge All Co',
            email='charge@example.com',
            identification_document='charge-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user',
            charge_inactive_members=True,
        )
        member = CompanyMember.objects.create(
            company=company,
            name='Member One',
            email='member@example.com',
            phone='5511999999999',
            identification_document='member-001',
            status='active',
        )

        billing = generate_billing_for_company(
            company,
            date.today().replace(day=1),
            date.today().replace(day=28),
            self.admin,
        )

        member.refresh_from_db()
        self.assertIsNotNone(billing)
        self.assertTrue(member.first_cycle_completed)
        self.assertEqual(billing.details.count(), 1)

    def test_desvincular_chatbot_inactivates_member_accesses(self):
        company = Company.objects.create(
            name='Bot Co',
            email='bot@example.com',
            identification_document='bot-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user_chatbot',
        )
        chatbot = Chatbot.objects.create(
            name='Agent',
            description='Agent description',
            base_price=Decimal('25.00'),
        )
        CompanyChatbot.objects.create(company=company, chatbot=chatbot, status='active')
        member = CompanyMember.objects.create(
            company=company,
            name='Member Two',
            email='member2@example.com',
            phone='5511888888888',
            identification_document='member-002',
            status='active',
        )
        access = MemberChatbotAccess.objects.create(
            member=member,
            chatbot=chatbot,
            activation_date=date.today(),
            status='active',
        )
        self.client.force_login(self.admin)

        response = self.client.post(reverse('chatbot_desvincular', args=[chatbot.pk, company.pk]))

        access.refresh_from_db()
        self.assertRedirects(response, reverse('chatbot_list'))
        self.assertEqual(access.status, 'inactive')

    def test_billing_detail_per_chatbot_renders(self):
        company = Company.objects.create(
            name='Invoice Co',
            email='invoice@example.com',
            identification_document='invoice-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user_chatbot',
        )
        chatbot = Chatbot.objects.create(
            name='Invoice Agent',
            description='Agent description',
            base_price=Decimal('25.00'),
        )
        member = CompanyMember.objects.create(
            company=company,
            name='Invoice Member',
            email='invoice-member@example.com',
            phone='5511777777777',
            identification_document='member-003',
            status='active',
        )
        billing = Billing.objects.create(
            company=company,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            total_value=Decimal('25.00'),
            generated_by=self.admin,
        )
        BillingDetail.objects.create(
            billing=billing,
            member=member,
            chatbot=chatbot,
            activation_date=date(2026, 1, 1),
            days_active=31,
            daily_rate=Decimal('0.81'),
            value=Decimal('25.00'),
            unit_price=Decimal('25.00'),
            billing_type='full',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('billing_detail', args=[billing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invoice Agent')

    def test_inactivated_member_is_billed_when_active_during_period(self):
        company = Company.objects.create(
            name='Historical Member Co',
            email='historical-member@example.com',
            identification_document='historical-member-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user',
            charge_inactive_members=True,
        )
        member = CompanyMember.objects.create(
            company=company,
            name='Historical Member',
            email='historical-member-user@example.com',
            phone='5511666666666',
            identification_document='member-004',
            status='active',
        )
        member.status = 'inactive'
        member.save()

        billing = generate_billing_for_company(
            company,
            date.today().replace(day=1),
            date.today().replace(day=28),
            self.admin,
        )

        self.assertIsNotNone(billing)
        self.assertEqual(billing.details.count(), 1)

    def test_inactivated_access_is_billed_when_active_during_period(self):
        company = Company.objects.create(
            name='Historical Access Co',
            email='historical-access@example.com',
            identification_document='historical-access-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user_chatbot',
        )
        chatbot = Chatbot.objects.create(
            name='Historical Agent',
            description='Agent description',
            base_price=Decimal('25.00'),
        )
        CompanyChatbot.objects.create(company=company, chatbot=chatbot, status='active')
        member = CompanyMember.objects.create(
            company=company,
            name='Historical Access Member',
            email='historical-access-member@example.com',
            phone='5511555555555',
            identification_document='member-005',
            status='active',
        )
        access = MemberChatbotAccess.objects.create(
            member=member,
            chatbot=chatbot,
            activation_date=date.today().replace(day=1),
            status='active',
        )
        access.status = 'inactive'
        access.save()

        billing = generate_billing_for_company(
            company,
            date.today().replace(day=1),
            date.today().replace(day=28),
            self.admin,
        )

        self.assertIsNotNone(billing)
        self.assertEqual(billing.details.count(), 1)

    def test_company_chatbot_rejects_non_positive_custom_price(self):
        company = Company.objects.create(
            name='Price Co',
            email='price@example.com',
            identification_document='price-001',
            member_price=Decimal('50.00'),
        )
        chatbot = Chatbot.objects.create(
            name='Price Agent',
            description='Agent description',
            base_price=Decimal('25.00'),
        )
        link = CompanyChatbot(
            company=company,
            chatbot=chatbot,
            custom_price=Decimal('0.00'),
        )

        with self.assertRaises(ValidationError):
            link.full_clean()
