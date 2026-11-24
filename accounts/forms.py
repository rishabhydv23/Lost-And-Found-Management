from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Profile


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Rahul', 'class': 'form-control', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Sharma', 'class': 'form-control', 'autocomplete': 'family-name'})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. rahul_sharma', 'class': 'form-control', 'autocomplete': 'username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'e.g. rahul@lpu.in or name@gmail.com', 'class': 'form-control', 'autocomplete': 'email'})
    )
    role = forms.ChoiceField(
        choices=[('STUDENT', 'Student'), ('FACULTY', 'Faculty / Staff')],
        initial='STUDENT',
        required=True,
        widget=forms.HiddenInput()
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a strong password', 'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat your password', 'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email address already exists. Please sign in or use another email.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken. Please choose another username.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            selected_role = self.cleaned_data.get('role', 'STUDENT')
            if selected_role in ('STUDENT', 'FACULTY'):
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.role = selected_role
                profile.save(update_fields=['role'])
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('role', 'phone', 'profile_picture')
        widgets = {'phone': forms.TextInput(attrs={'class': 'form-control'})}


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'placeholder': 'Username or Email (e.g. rahul@lpu.in)',
            'class': 'form-control',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'form-control',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        username_or_email = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password')

        if username_or_email and password:
            # Allow login using either Email or Username
            user_by_email = User.objects.filter(email__iexact=username_or_email).first()
            actual_username = user_by_email.username if user_by_email else username_or_email

            self.user_cache = authenticate(self.request, username=actual_username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
