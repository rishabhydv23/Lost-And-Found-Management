from django import forms
from django.contrib.auth.forms import UserCreationForm
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
