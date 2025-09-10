from django.db import models
from django.conf import settings
from django.utils import timezone


class Enrollment(models.Model):
    """
    Model representing an enrollment in the platform with dynamic fields.
    """
    user = models.CharField(max_length=255, unique=True, null=False, blank=False)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    confirmation_code = models.CharField(max_length=64, blank=True, null=True)

class Profile(models.Model):
    username = models.CharField(max_length=255)
    username_org = models.CharField(max_length=255, blank=True, null=True)
    reconciled_affiliation = models.CharField(max_length=255, blank=True, null=True)
    reconciled_territory = models.CharField(max_length=255, blank=True, null=True)
    reconciled_languages = models.JSONField(blank=True, null=True)
    reconciled_projects = models.JSONField(blank=True, null=True)
    reconciled_want_to_learn = models.JSONField(blank=True, null=True)
    reconciled_want_to_share = models.JSONField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.username


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.CharField(max_length=255)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_users')
    issued_at = models.DateTimeField(default=timezone.now)
    verification_code = models.CharField(max_length=10, unique=True)

    class Meta:
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user} - {self.badge}"