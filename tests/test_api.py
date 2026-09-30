from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from apps.employers.models import Employer
from apps.members.models import CustomUser, Member
from apps.contributions.models import Contribution

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestApiEndpoints:
    def test_employer_api_crud(self, api_client):
        # Create employer
        res = api_client.post('/api/v1/employers/', {
            'company_name': 'Guaranty Trust Bank',
            'registration_number': 'RC-GTB-111',
            'email': 'pension@gtbank.com',
            'phone_number': '08033221100',
            'address': 'Plot 635 Akin Adesola St, Lagos'
        }, format='json')
        assert res.status_code == 201
        emp_id = res.data['id']

        # Get list
        res_list = api_client.get('/api/v1/employers/')
        assert res_list.status_code == 200

    def test_member_api_register_and_onboard(self, api_client):
        emp = Employer.objects.create(
            company_name="United Bank for Africa",
            registration_number="RC-UBA-222",
            email="hr@ubagroup.com",
            phone_number="08022114433"
        )

        # 1. Register
        res = api_client.post('/api/v1/members/register/', {
            'email': 'api.contributor@example.com',
            'password': 'StrongPassword@123',
            'first_name': 'Ngozi',
            'last_name': 'Eze',
            'phone_number': '08099881122'
        }, format='json')
        assert res.status_code == 201
        member_id = res.data['id']

        # 2. Onboard
        res_onboard = api_client.post(f'/api/v1/members/{member_id}/onboard/', {
            'employer_id': emp.id,
            'date_of_birth': '1992-07-14',
            'nin': '11223344556',
            'gender': 'FEMALE',
            'address': '57 Marina, Lagos'
        }, format='json')
        assert res_onboard.status_code == 200
        assert res_onboard.data['rsa_pin'].startswith('PEN10')
        assert res_onboard.data['is_onboarded'] is True

    def test_contribution_api_validation(self, api_client):
        user = CustomUser.objects.create_user(
            email="contrib.api@example.com",
            password="Password123",
            first_name="David",
            last_name="Mark"
        )
        member = Member.objects.create(user=user, is_onboarded=True, rsa_pin="PEN1099999999")

        # Record Monthly
        res = api_client.post('/api/v1/contributions/', {
            'member_id': member.id,
            'contribution_type': 'MONTHLY',
            'amount': '60000.00',
            'contribution_year': 2025,
            'contribution_month': 4,
            'payment_date': '2025-04-20'
        }, format='json')
        assert res.status_code == 201

        # Attempt duplicate monthly for same month -> 400 Bad Request
        res_dup = api_client.post('/api/v1/contributions/', {
            'member_id': member.id,
            'contribution_type': 'MONTHLY',
            'amount': '50000.00',
            'contribution_year': 2025,
            'contribution_month': 4,
            'payment_date': '2025-04-22'
        }, format='json')
        assert res_dup.status_code == 400

    def test_statement_api(self, api_client):
        user = CustomUser.objects.create_user(
            email="statement.api@example.com",
            password="Password123",
            first_name="Grace",
            last_name="Danladi"
        )
        member = Member.objects.create(user=user, is_onboarded=True, rsa_pin="PEN1088888888")
        from datetime import date
        Contribution.objects.create(
            member=member,
            contribution_type=Contribution.ContributionType.MONTHLY,
            amount=Decimal('45000.00'),
            contribution_year=2025,
            contribution_month=1,
            payment_date=date(2025, 1, 25),
            status=Contribution.Status.VALIDATED
        )

        res = api_client.get(f'/api/v1/contributions/statement/?member_id={member.id}')
        assert res.status_code == 200
        assert Decimal(str(res.data['closing_balance'])) == Decimal('45000.00')
        assert res.data['transactions_count'] == 1

    def test_background_jobs_api(self, api_client):
        res = api_client.post('/api/v1/jobs/validate-contributions/')
        assert res.status_code == 200
        assert res.data['status'] == 'success'

        res_logs = api_client.get('/api/v1/jobs/logs/')
        assert res_logs.status_code == 200
