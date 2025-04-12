from django.db import models

# Create your models here.

class Enrollment(models.Model):
    """
    Model representing an enrollment in the platform with dynamic fields.
    """
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    confirmation_code = models.CharField(max_length=64, blank=True, null=True)