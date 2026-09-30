from datetime import date
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from apps.members.models import CustomUser, Member
from apps.employers.models import Employer

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com', 'autocomplete': 'email'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••', 'autocomplete': 'current-password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(email=email.strip().lower(), password=password)
            if not user:
                raise ValidationError("Invalid email or password. Please check your credentials.")
            if not user.is_active:
                raise ValidationError("This account is currently disabled.")
            cleaned_data['user'] = user
        return cleaned_data


class SignUpForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+234 800 000 0000'})
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Minimum 6 characters'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class OnboardingForm(forms.Form):
    employer = forms.ModelChoiceField(
        queryset=Employer.objects.filter(is_active=True, status=Employer.Status.ACTIVE),
        empty_label="-- Select Your Employer --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth = forms.DateField(
        label="Date of Birth",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="Age must be between 18 and 70 years."
    )
    nin = forms.CharField(
        label="National Identity Number (NIN)",
        max_length=11,
        min_length=11,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '11-digit NIN'}),
        help_text="Required 11-digit national identity number."
    )
    gender = forms.ChoiceField(
        choices=Member.Gender.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Your address'})
    )

    def clean_nin(self):
        nin = self.cleaned_data['nin'].strip()
        if not nin.isdigit() or len(nin) != 11:
            raise ValidationError("NIN must be exactly 11 digits.")
        return nin

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise ValidationError(f"You are currently {age} years old. Minimum enrollment age is 18 years.")
        if age > 70:
            raise ValidationError(f"You are currently {age} years old. Maximum enrollment age is 70 years.")
        return dob


class ProfileUpdateForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+234 800 000 0000'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your residential address'})
    )
