from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('DIRECTOR', 'Director'),
        ('PROFESOR', 'Profesor'),
        ('ALUMNO', 'Alumno'),
    ]
    
    SPECIALTY_CHOICES = [
        ('MATEMATICAS', 'Matemáticas'),
        ('CIENCIAS', 'Ciencias Naturales'),
        ('LENGUAJE', 'Lenguaje y Literatura'),
        ('HISTORIA', 'Historia y Geografía'),
        ('EDUCACION_FISICA', 'Educación Física'),
        ('ARTES', 'Artes'),
        ('MUSICA', 'Música'),
        ('TECNOLOGIA', 'Tecnología'),
        ('INGLES', 'Inglés'),
        ('FRANCES', 'Francés'),
        ('FILOSOFIA', 'Filosofía'),
        ('PSICOLOGIA', 'Psicología'),
        ('ADMINISTRACION', 'Administración'),
        ('CONTABILIDAD', 'Contabilidad'),
        ('INFORMATICA', 'Informática'),
        ('OTRO', 'Otro'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ALUMNO')
    specialty = models.CharField(max_length=30, choices=SPECIALTY_CHOICES, null=True, blank=True, help_text="Especialidad del profesor")
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_customuser'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"