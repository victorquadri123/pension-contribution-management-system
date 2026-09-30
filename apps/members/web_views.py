from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.members.forms import LoginForm, SignUpForm, OnboardingForm, ProfileUpdateForm
from apps.members.models import Member, CustomUser
from apps.members.services import MemberService
from apps.contributions.services import ContributionService
from apps.benefits.models import BenefitEligibility

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.cleaned_data['user']
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name}!")
        if user.role == CustomUser.Role.ADMIN:
            return redirect('admin_portal')
        return redirect('dashboard')

    return render(request, 'auth/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user, member = MemberService.register_user(
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            phone_number=form.cleaned_data.get('phone_number', '')
        )
        login(request, user)
        messages.success(request, "Account created! Set up your pension profile now or skip to explore first.")
        return redirect('onboarding')

    return render(request, 'auth/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def onboarding_view(request):
    user = request.user
    member, _ = Member.objects.get_or_create(user=user)

    if member.is_onboarded:
        return redirect('dashboard')

    form = OnboardingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            MemberService.complete_onboarding(
                member=member,
                date_of_birth=form.cleaned_data['date_of_birth'],
                nin=form.cleaned_data['nin'],
                employer_id=form.cleaned_data['employer'].id,
                gender=form.cleaned_data['gender'],
                address=form.cleaned_data.get('address', '')
            )
            messages.success(
                request,
                f"Profile complete! Your RSA PIN is {member.rsa_pin}."
            )
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'members/onboarding.html', {'form': form})


@login_required
def dashboard_view(request):
    user = request.user
    member = getattr(user, 'member_profile', None)
    if not member:
        member, _ = Member.objects.get_or_create(user=user)

    # For admin previewing without an onboarded profile, show first active member
    if not member.is_onboarded and (user.role == CustomUser.Role.ADMIN or user.is_staff):
        demo_member = Member.objects.filter(is_onboarded=True, is_deleted=False).first()
        if demo_member:
            member = demo_member

    totals = ContributionService.get_member_totals(member)
    eligibility, _ = BenefitEligibility.objects.get_or_create(member=member)
    recent_contributions = member.contributions.filter(is_deleted=False).order_by('-payment_date')[:5]

    context = {
        'member': member,
        'totals': totals,
        'eligibility': eligibility,
        'recent_contributions': recent_contributions,
    }
    return render(request, 'members/dashboard.html', context)


@login_required
def profile_view(request):
    user = request.user
    member, _ = Member.objects.get_or_create(user=user)

    if not member.is_onboarded:
        form = OnboardingForm(request.POST or None, initial={
            'address': member.address
        })
        if request.method == 'POST' and form.is_valid():
            try:
                MemberService.complete_onboarding(
                    member=member,
                    date_of_birth=form.cleaned_data['date_of_birth'],
                    nin=form.cleaned_data['nin'],
                    employer_id=form.cleaned_data['employer'].id,
                    gender=form.cleaned_data['gender'],
                    address=form.cleaned_data.get('address', '')
                )
                phone = request.POST.get('phone_number', '').strip()
                if phone:
                    user.phone_number = phone
                    user.save(update_fields=['phone_number'])

                messages.success(request, f"Profile setup complete! Your RSA PIN is {member.rsa_pin}.")
                return redirect('profile')
            except Exception as e:
                messages.error(request, str(e))

        return render(request, 'members/profile.html', {
            'member': member,
            'form': form,
            'is_onboarding': True
        })

    # Already onboarded: allow updating phone & address
    form = ProfileUpdateForm(request.POST or None, initial={
        'phone_number': user.phone_number,
        'address': member.address
    })

    if request.method == 'POST' and form.is_valid():
        phone = form.cleaned_data.get('phone_number', '').strip()
        address = form.cleaned_data.get('address', '').strip()
        user.phone_number = phone
        user.save(update_fields=['phone_number'])
        member.address = address
        member.save(update_fields=['address'])
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    return render(request, 'members/profile.html', {
        'member': member,
        'form': form,
        'is_onboarding': False
    })
