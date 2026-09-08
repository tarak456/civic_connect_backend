from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        GOVERNMENT = "GOVERNMENT", "Government Admin"
        MAINTAINER = "MAINTAINER", "Maintainer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CITIZEN)
    is_verified = models.BooleanField(default=False)
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.role in (self.Role.CITIZEN, self.Role.MAINTAINER) and not self.pk:
            self.is_verified = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"