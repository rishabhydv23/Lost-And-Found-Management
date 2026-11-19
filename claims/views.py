from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from lost_found.models import ItemReport
from notifications.models import Notification
from .models import Claim, RecoveryRecord


@login_required
def create_claim(request, pk):
    report = get_object_or_404(ItemReport, pk=pk, status='APPROVED', report_type='FOUND')
    existing = Claim.objects.filter(report=report, claimant=request.user).first()
    if existing:
        messages.info(request, 'You already submitted a claim for this item.')
        return redirect('my_claims')
    if request.method == 'POST':
        answers = request.POST.get('verification_answers', '').strip()
        if len(answers) < 20:
            messages.error(request, 'Please provide at least 20 characters of ownership details.')
        else:
            claim = Claim.objects.create(
                report=report,
                claimant=request.user,
                verification_answers=answers,
                evidence=request.FILES.get('evidence'),
            )
            for admin in report.reviewed_by and [report.reviewed_by] or []:
                Notification.objects.create(recipient=admin, message=f"New claim on {report.item_name}", notification_type='CLAIM')
            messages.success(request, 'Ownership claim submitted.')
            return redirect('my_claims')
    return render(request, 'claims/create.html', {'report': report})


@login_required
def my_claims(request):
    claims = Claim.objects.filter(claimant=request.user).select_related('report')
    return render(request, 'claims/my_claims.html', {'claims': claims})
