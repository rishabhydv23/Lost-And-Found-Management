from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .forms import ItemReportForm
from .matching import run_matching
from .models import Category, CampusLocation, ItemReport, ItemImage, PotentialMatch


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
            messages.success(request, 'Report submitted for administrator approval.')
            return redirect('my_reports')
    else:
        form = ItemReportForm()
    return render(request, 'lost_found/report.html', {
        'form': form,
        'report_type': canonical_type,
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
            messages.success(request, 'Report updated.')
            return redirect('my_reports')
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
