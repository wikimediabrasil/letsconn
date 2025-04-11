from django.db import models

# Create your models here.

class Enrollment(models.Model):
    """
    Model representing an enrollment in the platform.
    """
    user = models.CharField(max_length=150)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    role = models.CharField(max_length=10)
    area = models.CharField(max_length=50)
    gender = models.CharField(max_length=10)
    age = models.IntegerField()
    timestamp = models.DateTimeField()
    confirmation_code = models.CharField(max_length=64, blank=True, null=True)