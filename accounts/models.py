from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        CUSTOMER = "customer", "Customer"
        MECHANIC_OWNER = "mechanic_owner", "Mechanical Shop Owner"
        PETROL_OWNER = "petrol_owner", "Petrol Pump Owner"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Roles.choices, default=Roles.CUSTOMER)
    phone = models.CharField(max_length=32, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    @property
    def name(self):
        full_name = self.get_full_name()
        return full_name or self.username or self.email
