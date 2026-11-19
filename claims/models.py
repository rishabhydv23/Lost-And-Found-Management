from django.contrib.auth.models import User
from django.db import models
from lost_found.models import ItemReport


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    verification_answers = models.TextField(help_text='Private answers that verify ownership')
    evidence = models.FileField(upload_to='claims/', blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_claims')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('report', 'claimant')

    def __str__(self):
        return f"{self.claimant.username} - {self.report.item_name}"


class RecoveryRecord(models.Model):
    report = models.OneToOneField(ItemReport, on_delete=models.CASCADE, related_name='recovery')
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recoveries')
    verified_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='verified_recoveries')
    handover_date = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
