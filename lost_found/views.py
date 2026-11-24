import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from notifications.models import Notification

from .forms import ItemReportForm
from .matching import run_matching
from .models import CampusLocation, Category, ItemImage, ItemReport, PotentialMatch


def browse(request):
    report_type = request.GET.get('type', 'LOST')
    items = ItemReport.objects.filter(status='APPROVED', report_type=report_type)
    search = request.GET.get('q')
    if search:
        items = items.filter(item_name__icontains=search)
    category = request.GET.get('category')
    if category:
        items = items.filter(category_id=category)
    location = request.GET.get('location')
    if location:
        items = items.filter(campus_location_id=location)
    color = request.GET.get('color')
    if color:
        items = items.filter(color__icontains=color)
    date = request.GET.get('date')
    if date:
        items = items.filter(date_occurrence=date)
    items = items.select_related('category', 'campus_location', 'user').prefetch_related('images')
    paginator = Paginator(items, 9)
    return render(request, 'lost_found/browse.html', {
        'items': paginator.get_page(request.GET.get('page')),
        'categories': Category.objects.all(),
        'locations': CampusLocation.objects.all(),
        'report_type': report_type,
    })


def item_detail(request, pk):
    item = get_object_or_404(
        ItemReport.objects.select_related('category', 'campus_location', 'user').prefetch_related('images'),
        pk=pk,
    )
    if item.status != 'APPROVED' and item.user != request.user and not request.user.is_superuser:
        from django.http import Http404
        raise Http404
    return render(request, 'lost_found/detail.html', {'item': item})


@login_required
def report_item(request, report_type):
    if report_type not in ('lost', 'found'):
        return redirect('browse')
    match_hint = request.GET.get('match_hint')
    if match_hint and report_type == 'found':
        return redirect('report_found_for_item', pk=match_hint)

    canonical_type = 'LOST' if report_type == 'lost' else 'FOUND'
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.report_type = canonical_type
            item.save()
            for uploaded in request.FILES.getlist('images'):
                ItemImage.objects.create(report=item, image=uploaded)

            # Trigger candidate matching against existing opposite reports
            run_matching(item)

            messages.success(request, f'🎉 Your {report_type} item report has been submitted successfully!')
            # Redirect to item detail page so user does not loop back to the report form
            return redirect('item_detail', pk=item.pk)
        else:
            messages.error(request, 'Please correct the highlighted errors in the form.')
    else:
        form = ItemReportForm()
    return render(request, 'lost_found/report.html', {
        'form': form,
        'report_type': canonical_type,
    })


@login_required
def report_found_for_lost_item(request, pk):
    lost_item = get_object_or_404(ItemReport, pk=pk, report_type='LOST')

    if request.method == 'POST':
        custody_choice = request.POST.get('custody_choice', 'security')
        sec_office = request.POST.get('security_office_name', '').strip()
        phone = request.POST.get('finder_phone', '').strip()
        location_id = request.POST.get('campus_location')
        location_details = request.POST.get('location_details', '').strip()
        date_occurrence = request.POST.get('date_occurrence') or datetime.date.today().isoformat()
        notes = request.POST.get('notes', '').strip()

        if custody_choice == 'finder':
            phone_str = f" ({phone})" if phone else ""
            custody = f"With Finder{phone_str}"
            finder_phone = phone
            if phone and hasattr(request.user, 'profile') and not request.user.profile.phone:
                request.user.profile.phone = phone
                request.user.profile.save(update_fields=['phone'])
        else:
            sec_str = f": {sec_office}" if sec_office else ""
            custody = f"Security Office{sec_str}"
            finder_phone = ''

        campus_loc = None
        if location_id:
            campus_loc = CampusLocation.objects.filter(pk=location_id).first()
        if not campus_loc:
            campus_loc = lost_item.campus_location

        found_item = ItemReport.objects.create(
            user=request.user,
            report_type='FOUND',
            item_name=lost_item.item_name,
            category=lost_item.category,
            campus_location=campus_loc,
            location_details=location_details or lost_item.location_details,
            date_occurrence=date_occurrence,
            color=lost_item.color,
            brand=lost_item.brand,
            description=notes or f"Reported as found for lost report #{lost_item.pk} ({lost_item.item_name}).",
            custody=custody,
            finder_phone=finder_phone,
            status='PENDING',
        )

        for uploaded in request.FILES.getlist('images'):
            ItemImage.objects.create(report=found_item, image=uploaded)

        # Directly link PotentialMatch between this lost item and the newly created found item
        PotentialMatch.objects.get_or_create(
            lost_report=lost_item,
            found_report=found_item,
            defaults={'score': 98}
        )

        # Notify the owner of the lost item
        Notification.objects.create(
            recipient=lost_item.user,
            notification_type='MATCH',
            message=f"🎉 Someone reported finding your lost item: {lost_item.item_name}!"
        )

        messages.success(request, f"🎉 Thank you for reporting! Your found report has been created and linked to {lost_item.user.username}'s lost item ({lost_item.item_name}).")
        return redirect('item_detail', pk=found_item.pk)

    default_phone = getattr(request.user.profile, 'phone', '') if hasattr(request.user, 'profile') else ''
    return render(request, 'lost_found/report_found_for_item.html', {
        'lost_item': lost_item,
        'default_phone': default_phone,
    })


@login_required
def my_reports(request):
    items = ItemReport.objects.filter(user=request.user).prefetch_related('images')
    return render(request, 'lost_found/my_reports.html', {'items': items})


@login_required
def edit_report(request, pk):
    item = get_object_or_404(ItemReport, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Report updated successfully.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemReportForm(instance=item)
    return render(request, 'lost_found/report.html', {
        'form': form,
        'report_type': item.report_type,
        'editing': True,
    })


@login_required
def matches(request):
    lost_matches = PotentialMatch.objects.filter(lost_report__user=request.user).select_related(
        'lost_report', 'found_report', 'found_report__category', 'found_report__campus_location'
    )
    return render(request, 'lost_found/matches.html', {'matches': lost_matches})
