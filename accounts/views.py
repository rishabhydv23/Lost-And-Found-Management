from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        # Silent honeypot check against spam bots
        if request.POST.get('honeypot_field'):
            return redirect('login')
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Welcome, {user.first_name or user.username}! Your account was created successfully. Please sign in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the highlighted errors in the form.')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    form.fields['role'].disabled = True
    return render(request, 'accounts/profile.html', {'form': form})
