from datetime import date
from decimal import Decimal
import pytest
from django.test import Client
from apps.employers.services import EmployerService
from apps.members.services import MemberService
from apps.members.models import Member, CustomUser
from apps.contributions.models import Contribution

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user_and_member(db):
    emp = EmployerService.register_employer(
        company_name="Nigerian Bottling Company",
        registration_number="RC-NBC-999",
        email="pensions@nbc.ng",
        phone_number="08022334455"
    )
    user, member = MemberService.register_user(
        email="frontend.user@example.com",
        password="Password123",
        first_name="Funke",
        last_name="Akindele",
        phone_number="08033445566"
    )
    return user, member, emp

@pytest.mark.django_db
class TestWebViews:
    def test_login_page_renders(self, client):
        response = client.get('/login/')
        assert response.status_code == 200
        assert b"Welcome back" in response.content

    def test_signup_page_renders_and_submits(self, client):
        response = client.get('/signup/')
        assert response.status_code == 200
        assert b"Create an account" in response.content

        # Submit signup form
        post_response = client.post('/signup/', {
            'first_name': 'Segun',
            'last_name': 'Arinze',
            'email': 'segun@example.com',
            'phone_number': '08099887766',
            'password': 'Password@123',
            'confirm_password': 'Password@123',
        })
        # Should redirect to onboarding
        assert post_response.status_code == 302
        assert '/onboarding/' in post_response.url

    def test_onboarding_view_submission(self, client, user_and_member):
        user, member, emp = user_and_member
        client.force_login(user)

        response = client.get('/onboarding/')
        assert response.status_code == 200
        assert b"Set up your profile" in response.content

        # Submit valid onboarding
        post_response = client.post('/onboarding/', {
            'employer': emp.id,
            'date_of_birth': '1991-03-20',
            'nin': '99887766554',
            'gender': 'FEMALE',
            'address': 'Victoria Island, Lagos'
        })
        assert post_response.status_code == 302
        assert '/dashboard/' in post_response.url

        member.refresh_from_db()
        assert member.is_onboarded is True
        assert member.rsa_pin.startswith('PEN10')

    def test_dashboard_renders(self, client, user_and_member):
        user, member, emp = user_and_member
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1991, 3, 20),
            nin='99887766554',
            employer_id=emp.id
        )
        client.force_login(user)

        response = client.get('/dashboard/')
        assert response.status_code == 200
        assert b"TOTAL BALANCE" in response.content
        assert b"Benefit Eligibility" in response.content

    def test_make_contribution_flow(self, client, user_and_member):
        user, member, emp = user_and_member
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1991, 3, 20),
            nin='99887766554',
            employer_id=emp.id
        )
        client.force_login(user)

        response = client.get('/contributions/new/')
        assert response.status_code == 200

        # Submit monthly contribution
        post_res = client.post('/contributions/new/', {
            'contribution_type': 'MONTHLY',
            'amount': '75000.00',
            'contribution_year': 2025,
            'contribution_month': 5,
            'payment_date': str(date.today())
        })
        assert post_res.status_code == 302
        assert Contribution.objects.filter(member=member, contribution_year=2025, contribution_month=5).exists()

    def test_statement_view_renders(self, client, user_and_member):
        user, member, emp = user_and_member
        MemberService.complete_onboarding(
            member=member,
            date_of_birth=date(1991, 3, 20),
            nin='99887766554',
            employer_id=emp.id
        )
        client.force_login(user)

        response = client.get('/statement/')
        assert response.status_code == 200
        assert b"Statement" in response.content

    def test_admin_portal_renders(self, client):
        admin = CustomUser.objects.create_superuser(
            email="portaladmin@nlpcpfa.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Officer"
        )
        client.force_login(admin)

        response = client.get('/portal/')
        assert response.status_code == 200
        assert b"Operations Portal" in response.content
        assert b"Background Tasks" in response.content

    def test_non_admin_gets_404_on_portal(self, client, user_and_member):
        user, member, emp = user_and_member
        client.force_login(user)

        response = client.get('/portal/')
        assert response.status_code == 404
        assert b"Error: Not Found" in response.content
        assert b"The requested URL" in response.content

    def test_non_onboarded_user_can_skip_to_dashboard_and_is_guarded(self, client, user_and_member):
        user, member, emp = user_and_member
        # User is not onboarded initially
        client.force_login(user)

        # 1. Can view dashboard with banner
        response = client.get('/dashboard/')
        assert response.status_code == 200
        assert b"Profile Setup Required" in response.content
        assert b"Pending Setup" in response.content

        # 2. Guarded from adding contribution
        contrib_res = client.get('/contributions/new/')
        assert contrib_res.status_code == 302
        assert '/onboarding/' in contrib_res.url

        # 3. Guarded from generating statement
        stmt_res = client.get('/statement/')
        assert stmt_res.status_code == 302
        assert '/onboarding/' in stmt_res.url

