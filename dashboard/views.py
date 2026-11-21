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
    tab = request.GET.get('tab', 'overview')
    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # 1. Report update
        if action_type == 'update_report' or 'report_id' in request.POST:
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
                messages.success(request, f"Report '{item.item_name}' was updated to {action.title()}.")
            return redirect(f"{request.path}?tab=reports")

        # 2. Report delete
        elif action_type == 'delete_report':
            item = get_object_or_404(ItemReport, pk=request.POST.get('target_report_id'))
            name = item.item_name
            item.delete()
            messages.success(request, f"Report '{name}' was permanently deleted.")
            return redirect(f"{request.path}?tab=reports")

        # 3. Claim update
        elif action_type == 'update_claim' or 'claim_id' in request.POST:
            claim = get_object_or_404(Claim, pk=request.POST.get('claim_id'))
            action = request.POST.get('action')
            if action in ('APPROVED', 'REJECTED'):
                claim.status = action
                claim.admin_remarks = request.POST.get('remarks', '')
                claim.reviewed_by = request.user
                claim.save(update_fields=['status', 'admin_remarks', 'reviewed_by'])
                if action == 'APPROVED':
                    claim.report.status = 'RECOVERED'
                    claim.report.save(update_fields=['status'])
                    RecoveryRecord.objects.get_or_create(
                        report=claim.report,
                        defaults={'owner': claim.claimant, 'verified_by': request.user},
                    )
                Notification.objects.create(
                    recipient=claim.claimant,
                    message=f"Your claim for '{claim.report.item_name}' was {action.lower()}.",
                    notification_type='CLAIM',
                )
                messages.success(request, f"Claim on '{claim.report.item_name}' updated to {action.title()}.")
            return redirect(f"{request.path}?tab=claims")

        # 4. User update
        elif action_type == 'update_user' or 'user_id' in request.POST:
            target_user = get_object_or_404(User, pk=request.POST.get('user_id'))
            role = request.POST.get('role')
            if role in ('STUDENT', 'FACULTY', 'ADMIN'):
                target_user.profile.role = role
                target_user.profile.save(update_fields=['role'])
            target_user.is_active = request.POST.get('is_active') == 'on'
            target_user.save(update_fields=['is_active'])
            messages.success(request, f"User '{target_user.username}' successfully updated.")
            return redirect(f"{request.path}?tab=users")

        # 5. Taxonomy (Category / Location)
        elif action_type == 'taxonomy' or 'kind' in request.POST:
            kind = request.POST.get('kind')
            if kind == 'category':
                name = request.POST.get('name', '').strip()
                if name:
                    cat, created = Category.objects.get_or_create(name=name)
                    if created:
                        messages.success(request, f"Category '{name}' created.")
                    else:
                        messages.info(request, f"Category '{name}' already exists.")
            elif kind == 'location':
                bld = request.POST.get('building', '').strip()
                loc = request.POST.get('specific_location', '').strip()
                if bld and loc:
                    CampusLocation.objects.get_or_create(
                        building=bld,
                        block=request.POST.get('block', '').strip(),
                        floor=request.POST.get('floor', '').strip(),
                        specific_location=loc,
                    )
                    messages.success(request, f"Campus location '{bld} - {loc}' created.")
            return redirect(f"{request.path}?tab=taxonomy")

    reports_qs = ItemReport.objects.select_related(
        'user', 'user__profile', 'category', 'campus_location', 'reviewed_by'
    ).prefetch_related('images', 'claims', 'claims__claimant').all()

    claims_qs = Claim.objects.select_related(
        'report', 'report__category', 'claimant', 'claimant__profile', 'reviewed_by'
    ).all()

    matches_qs = PotentialMatch.objects.select_related(
        'lost_report', 'lost_report__user', 'found_report', 'found_report__user', 'found_report__category'
    ).all()

    users_qs = User.objects.select_related('profile').annotate(
        reports_total=Count('item_reports', distinct=True),
        claims_total=Count('claims', distinct=True)
    ).order_by('-date_joined')

    categories_qs = Category.objects.annotate(total=Count('item_reports')).order_by('-total')
    locations_qs = CampusLocation.objects.annotate(total=Count('item_reports')).order_by('building', 'specific_location')

    context = {
        'active_tab': tab,
        'user_count': User.objects.count(),
        'lost_count': reports_qs.filter(report_type='LOST').count(),
        'found_count': reports_qs.filter(report_type='FOUND').count(),
        'pending_reports': reports_qs.filter(status='PENDING').count(),
        'approved_reports': reports_qs.filter(status='APPROVED').count(),
        'pending_claims': claims_qs.filter(status='PENDING').count(),
        'recovered_count': reports_qs.filter(status='RECOVERED').count(),
        'rejected_count': reports_qs.filter(status='REJECTED').count(),
        'match_count': matches_qs.count(),
        'all_reports': reports_qs,
        'all_claims': claims_qs,
        'all_matches': matches_qs,
        'all_users': users_qs,
        'all_categories': categories_qs,
        'all_locations': locations_qs,
        'recent_notifications': Notification.objects.select_related('recipient').order_by('-created_at')[:15],
        'recent_recoveries': RecoveryRecord.objects.select_related('report', 'owner', 'verified_by').order_by('-handover_date')[:10],
        'top_categories': categories_qs[:6],
        'top_locations': locations_qs[:6],
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
