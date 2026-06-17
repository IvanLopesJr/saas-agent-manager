from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.models import (
    Billing,
    BillingDetail,
    Chatbot,
    Company,
    CompanyChatbot,
    CompanyMember,
    MemberChatbotAccess,
    AuditLog,
    User,
)
from app.utils.billing import simulate_billing_for_company, generate_billing_for_company
from app.views.dashboard import get_dashboard_alerts


class SimulateBillingTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super',
            email='super@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )

    def test_simulate_returns_expected_structure(self):
        company = Company.objects.create(
            name='Sim Co',
            email='sim@example.com',
            identification_document='sim-001',
            member_price=Decimal('100.00'),
            billing_mode='per_user',
            charge_inactive_members=True,
        )
        member = CompanyMember.objects.create(
            company=company,
            name='Sim Member',
            email='sim-member@example.com',
            phone='5511000000001',
            identification_document='member-sim-001',
            status='active',
        )
        period_start = date.today().replace(day=1)
        period_end = date.today().replace(day=28)

        result = simulate_billing_for_company(company, period_start, period_end)

        self.assertIn('total_value', result)
        self.assertIn('details', result)
        self.assertIn('full_count', result)
        self.assertIn('proportional_count', result)
        self.assertIn('item_count', result)
        self.assertIsInstance(result['total_value'], Decimal)
        self.assertEqual(result['item_count'], 1)
        self.assertEqual(len(result['details']), 1)

        detail = result['details'][0]
        self.assertIn('member', detail)
        self.assertIn('value', detail)
        self.assertIn('billing_type', detail)
        self.assertIn('unit_price', detail)
        self.assertIn('activation_date', detail)
        self.assertEqual(detail['member'].id, member.id)

    def test_simulate_per_user_chatbot_returns_chatbot_details(self):
        company = Company.objects.create(
            name='Sim Chatbot Co',
            email='sim-chatbot@example.com',
            identification_document='sim-chatbot-001',
            member_price=Decimal('50.00'),
            billing_mode='per_user_chatbot',
        )
        chatbot = Chatbot.objects.create(
            name='Test Bot',
            description='Test',
            base_price=Decimal('30.00'),
        )
        CompanyChatbot.objects.create(company=company, chatbot=chatbot, status='active')
        member = CompanyMember.objects.create(
            company=company,
            name='Sim Chatbot Member',
            email='sim-chatbot-member@example.com',
            phone='5511000000002',
            identification_document='member-sim-chatbot-001',
            status='active',
        )
        MemberChatbotAccess.objects.create(
            member=member,
            chatbot=chatbot,
            activation_date=date.today().replace(day=1),
            status='active',
        )
        period_start = date.today().replace(day=1)
        period_end = date.today().replace(day=28)

        result = simulate_billing_for_company(company, period_start, period_end)

        self.assertEqual(result['item_count'], 1)
        detail = result['details'][0]
        self.assertIsNotNone(detail['chatbot'])
        self.assertEqual(detail['chatbot'].name, 'Test Bot')

    def test_simulate_does_not_persist(self):
        company = Company.objects.create(
            name='Sim NoPersist Co',
            email='sim-nopersist@example.com',
            identification_document='sim-nopersist-001',
            member_price=Decimal('100.00'),
            billing_mode='per_user',
        )
        CompanyMember.objects.create(
            company=company,
            name='NoPersist Member',
            email='sim-nopersist-member@example.com',
            phone='5511000000003',
            identification_document='member-nopersist-001',
            status='active',
        )
        period_start = date.today().replace(day=1)
        period_end = date.today().replace(day=28)

        simulate_billing_for_company(company, period_start, period_end)

        self.assertEqual(Billing.objects.count(), 0)
        self.assertEqual(BillingDetail.objects.count(), 0)

    def test_simulate_matches_generate_for_same_input(self):
        company = Company.objects.create(
            name='Sim Match Co',
            email='sim-match@example.com',
            identification_document='sim-match-001',
            member_price=Decimal('100.00'),
            billing_mode='per_user',
            charge_inactive_members=True,
        )
        CompanyMember.objects.create(
            company=company,
            name='Match Member',
            email='sim-match-member@example.com',
            phone='5511000000004',
            identification_document='member-match-001',
            status='active',
        )
        period_start = date.today().replace(day=1)
        period_end = date.today().replace(day=28)

        sim_result = simulate_billing_for_company(company, period_start, period_end)
        billing = generate_billing_for_company(company, period_start, period_end, self.admin)

        self.assertIsNotNone(billing)
        self.assertEqual(sim_result['total_value'], billing.total_value)
        self.assertEqual(sim_result['item_count'], billing.details.count())


class DashboardAlertsTest(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='super-alert',
            email='super-alert@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        self.company = Company.objects.create(
            name='Alert Co',
            email='alert@example.com',
            identification_document='alert-001',
            member_price=Decimal('50.00'),
        )
        self.company_admin = User.objects.create_user(
            username='company-alert-admin',
            email='company-alert-admin@example.com',
            password='StrongPass123!',
            role='admin_company',
            status='active',
            company=self.company,
        )

    def test_super_admin_gets_orphan_chatbot_alert(self):
        Chatbot.objects.create(
            name='Orphan Bot',
            description='No company linked',
            base_price=Decimal('10.00'),
        )

        alerts = get_dashboard_alerts(self.super_admin)

        alert_titles = [a['title'] for a in alerts]
        self.assertIn('Chatbot sem empresa', alert_titles)

    def test_admin_with_pending_members_gets_alert(self):
        CompanyMember.objects.create(
            company=self.company,
            name='Pending Member',
            email='pending@example.com',
            phone='5511000000005',
            identification_document='pending-001',
            status='pending',
        )

        alerts = get_dashboard_alerts(self.company_admin)

        alert_titles = [a['title'] for a in alerts]
        self.assertIn('Membros pendentes', alert_titles)

    def test_healthy_admin_gets_no_alerts(self):
        alerts = get_dashboard_alerts(self.company_admin)

        self.assertIsInstance(alerts, list)

    def test_alert_contains_url(self):
        alerts = get_dashboard_alerts(self.super_admin)

        for alert in alerts:
            self.assertIn('url', alert)
            self.assertTrue(alert['url'].startswith('/'))

    def test_alert_contains_type_title_message_icon(self):
        Chatbot.objects.create(
            name='Another Orphan',
            description='No company',
            base_price=Decimal('10.00'),
        )

        alerts = get_dashboard_alerts(self.super_admin)

        for alert in alerts:
            self.assertIn('type', alert)
            self.assertIn('title', alert)
            self.assertIn('message', alert)
            self.assertIn('icon', alert)

    def test_no_alerts_for_healthy_setup(self):
        alerts = get_dashboard_alerts(self.super_admin)
        self.assertIsInstance(alerts, list)

    def test_super_admin_stale_pending_members_alert(self):
        thirty_one_days_ago = timezone.now().date() - timedelta(days=31)
        member = CompanyMember.objects.create(
            company=self.company,
            name='Stale Pending',
            email='stale-pending@example.com',
            phone='5511000000006',
            identification_document='stale-pending-001',
            status='pending',
        )
        CompanyMember.objects.filter(pk=member.pk).update(created_at=thirty_one_days_ago)

        alerts = get_dashboard_alerts(self.super_admin)

        alert_titles = [a['title'] for a in alerts]
        self.assertIn('Membros pendentes antigos', alert_titles)


class CompanyDetailViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super-cd',
            email='super-cd@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        self.company = Company.objects.create(
            name='Detail Co',
            email='detail@example.com',
            identification_document='detail-001',
            member_price=Decimal('50.00'),
        )
        self.client.force_login(self.admin)

    def test_company_detail_has_new_context(self):
        response = self.client.get(reverse('company_detail', args=[self.company.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('monthly_cost', response.context)
        self.assertIn('pending_members', response.context)
        self.assertIn('recent_members', response.context)
        self.assertIn('chatbot_active', response.context)
        self.assertIn('chatbot_inactive', response.context)
        self.assertIn('has_current_billing', response.context)
        self.assertIn('billing_trend_chart', response.context)

    def test_company_detail_shows_pending_billing_alert(self):
        response = self.client.get(reverse('company_detail', args=[self.company.pk]))

        self.assertFalse(response.context['has_current_billing'])
        self.assertContains(response, 'Atenção')

    def test_company_detail_has_billing_chart_data(self):
        response = self.client.get(reverse('company_detail', args=[self.company.pk]))

        chart = response.context['billing_trend_chart']
        self.assertIn('labels', chart)
        self.assertIn('values', chart)
        self.assertEqual(len(chart['labels']), 6)
        self.assertEqual(len(chart['values']), 6)


class BillingDetailSummaryTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super-bd',
            email='super-bd@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        self.company = Company.objects.create(
            name='Billing Detail Co',
            email='bd@example.com',
            identification_document='bd-001',
            member_price=Decimal('100.00'),
            billing_mode='per_user',
        )
        self.member = CompanyMember.objects.create(
            company=self.company,
            name='BD Member',
            email='bd-member@example.com',
            phone='5511000000007',
            identification_document='member-bd-001',
            status='active',
        )
        self.billing = Billing.objects.create(
            company=self.company,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            total_value=Decimal('100.00'),
            generated_by=self.admin,
        )
        BillingDetail.objects.create(
            billing=self.billing,
            member=self.member,
            activation_date=date(2026, 2, 1),
            days_active=28,
            daily_rate=Decimal('3.57'),
            value=Decimal('100.00'),
            unit_price=Decimal('100.00'),
            billing_type='full',
        )
        self.client.force_login(self.admin)

    def test_billing_detail_has_summary_stats(self):
        response = self.client.get(reverse('billing_detail', args=[self.billing.pk]))

        self.assertIn('summary_stats', response.context)
        stats = response.context['summary_stats']
        self.assertEqual(stats['total_items'], 1)
        self.assertEqual(stats['full_count'], 1)
        self.assertEqual(stats['proportional_count'], 0)
        self.assertIn('by_type', stats)
        self.assertIn('avg_days', stats)
        self.assertIn('type_chart_data', response.context)
        self.assertIsNotNone(response.context['type_chart_data'])


class BillingPreviewDetailTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super-bp',
            email='super-bp@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        self.company = Company.objects.create(
            name='Preview Co',
            email='preview@example.com',
            identification_document='preview-001',
            member_price=Decimal('100.00'),
            billing_mode='per_user',
        )
        self.client.force_login(self.admin)

    def test_preview_with_simulate_returns_details(self):
        CompanyMember.objects.create(
            company=self.company,
            name='Preview Member',
            email='preview-member@example.com',
            phone='5511000000008',
            identification_document='member-preview-001',
            status='active',
        )
        period_start = date.today().replace(day=1)
        period_end = date.today().replace(day=28)
        url = reverse('billing_preview')
        url += f'?period_start={period_start.isoformat()}&period_end={period_end.isoformat()}&companies={self.company.pk}'

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('preview_results', response.context)
        results = response.context['preview_results']
        self.assertGreaterEqual(len(results), 1)
        self.assertIn('details', results[0])
        self.assertIn('full_count', results[0])
        self.assertIn('proportional_count', results[0])


class AuditLogViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super-al',
            email='super-al@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        AuditLog.objects.create(
            user=self.admin,
            action='company_created',
            description='Test audit entry',
            ip_address='127.0.0.1',
        )
        self.client.force_login(self.admin)

    def test_audit_log_renders_with_logs(self):
        response = self.client.get(reverse('audit_log_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test audit entry')
        self.assertContains(response, 'company_created')

    def test_audit_log_has_context_data(self):
        response = self.client.get(reverse('audit_log_list'))

        self.assertIn('total_30d', response.context)
        self.assertIn('action_choices', response.context)
        self.assertIn('users', response.context)
        self.assertIn('companies', response.context)
        self.assertGreaterEqual(response.context['total_30d'], 0)

    def test_audit_log_filter_by_action(self):
        AuditLog.objects.create(
            user=self.admin,
            action='billing_generated',
            description='Billing entry',
            ip_address='127.0.0.1',
        )

        response = self.client.get(reverse('audit_log_list'), {'action': 'billing_generated'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Billing entry')
        self.assertNotContains(response, 'Test audit entry')

    def test_audit_log_csv_export(self):
        response = self.client.get(reverse('audit_log_list'), {'export': 'csv'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])


class DashboardAlertsInViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='super-dv',
            email='super-dv@example.com',
            password='StrongPass123!',
            role='super_admin',
            status='active',
        )
        self.client.force_login(self.admin)

    def test_super_admin_dashboard_has_alerts(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('alerts', response.context)
        self.assertIsInstance(response.context['alerts'], list)
