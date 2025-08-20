from django.db import models

# Create your models here.

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

    def __str__(self):
        return self.username