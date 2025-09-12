from django.db import models
from django.conf import settings


class Portfolio(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'}
    )

    def __str__(self):
        return f"{self.title} - {self.student.username}"


class Artifact(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='artifacts/')
    artifact_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='artifacts')

    def __str__(self):
        return f"{self.title} - {self.portfolio.title}"
