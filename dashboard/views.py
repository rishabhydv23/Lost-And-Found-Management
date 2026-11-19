from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import Profile
from claims.models import Claim, RecoveryRecord
from lost_found.models import ItemReport, Category, CampusLocation, PotentialMatch
from lost_found.matching import run_matching
from notifications.models import Notification


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(getattr(user, 'profile', None), 'role', None) == 'ADMIN')


def home(request):
    return render(request, 'dashboard/home.html')


@login_required
def dashboard(request):
    reports = ItemReport.objects.filter(user=request.user)
    context = {
        'lost_count': reports.filter(report_type='LOST').count(),
        'found_count': reports.filter(report_type='FOUND').count(),
        'active_count': reports.exclude(status__in=['REJECTED', 'RECOVERED', 'CLOSED']).count(),
        'match_count': PotentialMatch.objects.filter(lost_report__user=request.user).count(),
        'claim_count': Claim.objects.filter(claimant=request.user, status='PENDING').count(),
        'recovered_count': RecoveryRecord.objects.filter(owner=request.user).count(),
        'notifications': Notification.objects.filter(recipient=request.user)[:5],
        'recent_reports': reports[:5],
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    context = {
        'user_count': User.objects.count(),
        'lost_count': ItemReport.objects.filter(report_type='LOST').count(),
        'found_count': ItemReport.objects.filter(report_type='FOUND').count(),
        'pending_reports': ItemReport.objects.filter(status='PENDING').count(),
        'pending_claims': Claim.objects.filter(status='PENDING').count(),
        'recovered_count': ItemReport.objects.filter(status='RECOVERED').count(),
        'unclaimed_count': ItemReport.objects.filter(report_type='FOUND', status='APPROVED').exclude(claims__status='APPROVED').count(),
        'top_categories': Category.objects.annotate(total=Count('item_reports')).order_by('-total')[:5],
        'top_locations': CampusLocation.objects.annotate(total=Count('item_reports')).order_by('-total')[:5],
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
@user_passes_test(is_admin)
def manage_reports(request):
    items = ItemReport.objects.select_related('user', 'category', 'campus_location').all()
    if request.method == 'POST':
        item = get_object_or_404(ItemReport, pk=request.POST.get('report_id'))
        action = request.POST.get('action')
        if action in ('APPROVED', 'REJECTED', 'RECOVERED', 'CLOSED'):
            item.status = action
            item.reviewed_by = request.user
            item.review_remarks = request.POST.get('remarks', '')
            item.save(update_fields=['status', 'reviewed_by', 'review_remarks'])
            if action == 'APPROVED':
                run_matching(item)
            Notification.objects.create(
                recipient=item.user,
                message=f"Your report '{item.item_name}' was {action.lower()}.",
                notification_type='REPORT',
            )
            messages.success(request, 'Report updated.')
        return redirect('manage_reports')
    return render(request, 'dashboard/manage_reports.html', {'items': items})


@login_required
@user_passes_test(is_admin)
def manage_claims(request):
    claims = Claim.objects.select_related('report', 'claimant').all()
    if request.method == 'POST':
        claim = get_object_or_404(Claim, pk=request.POST.get('claim_id'))
        action = request.POST.get('action')
        if action in ('APPROVED', 'REJECTED'):
            claim.status = action
            claim.admin_remarks = request.POST.get('remarks', '')
            claim.reviewed_by = request.user
            claim.save(update_fields=['status', 'admin_remarks', 'reviewed_by'])
            claim.report.status = 'RECOVERED' if action == 'APPROVED' else claim.report.status
            claim.report.save(update_fields=['status'])
            if action == 'APPROVED':
                RecoveryRecord.objects.get_or_create(
                    report=claim.report,
                    defaults={'owner': claim.claimant, 'verified_by': request.user},
                )
            Notification.objects.create(
                recipient=claim.claimant,
                message=f"Your claim for '{claim.report.item_name}' was {action.lower()}.",
                notification_type='CLAIM',
            )
            messages.success(request, 'Claim updated.')
        return redirect('manage_claims')
    return render(request, 'dashboard/manage_claims.html', {'claims': claims})


@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.select_related('profile').all()
    if request.method == 'POST':
        user = get_object_or_404(User, pk=request.POST.get('user_id'))
        role = request.POST.get('role')
        if role in ('STUDENT', 'FACULTY', 'ADMIN'):
            user.profile.role = role
            user.profile.save(update_fields=['role'])
        user.is_active = request.POST.get('is_active') == 'on'
        user.save(update_fields=['is_active'])
        messages.success(request, 'User updated.')
        return redirect('manage_users')
    return render(request, 'dashboard/manage_users.html', {'users': users})


@login_required
@user_passes_test(is_admin)
def manage_taxonomy(request):
    if request.method == 'POST':
        kind = request.POST.get('kind')
        if kind == 'category':
            name = request.POST.get('name', '').strip()
            if name:
                Category.objects.get_or_create(name=name)
        elif kind == 'location':
            CampusLocation.objects.get_or_create(
                building=request.POST.get('building', '').strip(),
                block=request.POST.get('block', '').strip(),
                floor=request.POST.get('floor', '').strip(),
                specific_location=request.POST.get('specific_location', '').strip(),
            )
        messages.success(request, 'Campus data updated.')
        return redirect('manage_taxonomy')
    return render(request, 'dashboard/manage_taxonomy.html', {
        'categories': Category.objects.all(),
        'locations': CampusLocation.objects.all(),
    })
