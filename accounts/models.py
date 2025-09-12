from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('DIRECTOR', 'Director'),
        ('PROFESOR', 'Profesor'),
        ('ALUMNO', 'Alumno'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ALUMNO')
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_customuser'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"