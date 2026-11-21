from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class CampusLocation(models.Model):
    building = models.CharField(max_length=100)
    block = models.CharField(max_length=50, blank=True)
    floor = models.CharField(max_length=50, blank=True)
    specific_location = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['building', 'specific_location']

    def __str__(self):
        parts = [self.building]
        if self.block and self.block != self.building:
            parts.append(self.block)
        if self.floor:
            parts.append(self.floor)
        if self.specific_location and self.specific_location != self.building:
            parts.append(self.specific_location)
        return ' - '.join(parts)


class ItemReport(models.Model):
    class ReportType(models.TextChoices):
        LOST = 'LOST', 'Lost'
        FOUND = 'FOUND', 'Found'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        RECOVERED = 'RECOVERED', 'Recovered'
        CLOSED = 'CLOSED', 'Closed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='item_reports')
    report_type = models.CharField(max_length=5, choices=ReportType.choices)
    item_name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='item_reports')
    description = models.TextField()
    color = models.CharField(max_length=50)
    brand = models.CharField(max_length=100, blank=True)
    date_occurrence = models.DateField()
    approximate_time = models.TimeField(null=True, blank=True)
    campus_location = models.ForeignKey(CampusLocation, on_delete=models.PROTECT, related_name='item_reports')
    location_details = models.CharField(max_length=150, blank=True, verbose_name="Specific spot / Landmark", help_text="e.g. In front of 25 block, Room 302, Bench near lawn")
    custody = models.CharField(max_length=100, blank=True)
    identifying_details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_reports')
    review_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_name} ({self.get_report_type_display()})"


class ItemImage(models.Model):
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='items/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if getattr(self.image, 'size', 0) > 5 * 1024 * 1024:
            raise ValidationError('Each image must be 5 MB or smaller.')


class PotentialMatch(models.Model):
    class MatchStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        REVIEWED = 'REVIEWED', 'Reviewed'
        DISMISSED = 'DISMISSED', 'Dismissed'

    lost_report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='lost_matches')
    found_report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='found_matches')
    score = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=MatchStatus.choices, default=MatchStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lost_report', 'found_report')
        ordering = ['-score', '-created_at']

    def __str__(self):
        return f"{self.lost_report.item_name} / {self.found_report.item_name}: {self.score}%"
