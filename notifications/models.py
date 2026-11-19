from django.contrib.auth.models import User
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        MATCH = 'MATCH', 'Potential match'
        CLAIM = 'CLAIM', 'Claim update'
        REPORT = 'REPORT', 'Report update'
        RECOVERY = 'RECOVERY', 'Recovery'
        GENERAL = 'GENERAL', 'General'

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=10, choices=Type.choices, default=Type.GENERAL)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
