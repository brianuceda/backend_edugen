from django.db import models
from django.conf import settings
from academic.models import Course, Section


class Portfolio(models.Model):
    """Portafolio de un estudiante para un curso específico"""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'},
        related_name='portfolios'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='portfolios', null=True, blank=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='portfolios', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'section']  # Un estudiante solo puede tener un portafolio por sección
        verbose_name = 'Portafolio'
        verbose_name_plural = 'Portafolios'

    def __str__(self):
        return f"{self.title} - {self.student.first_name} {self.student.last_name} - {self.section.name}"
    
    def get_courses(self):
        """Obtener todos los cursos asociados a este portafolio"""
        return self.courses.all()


class PortfolioCourse(models.Model):
    """Relación entre portafolio y cursos - permite múltiples cursos por portafolio"""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='portfolio_courses')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['portfolio', 'course']  # Un curso solo puede estar una vez en un portafolio
        verbose_name = 'Curso del Portafolio'
        verbose_name_plural = 'Cursos del Portafolio'
    
    def __str__(self):
        return f"{self.portfolio.student.first_name} - {self.course.name}"


class Activity(models.Model):
    """Actividades que puede asignar un profesor"""
    ACTIVITY_TYPES = [
        ('GROUP', 'Actividad Grupal'),
        ('INDIVIDUAL', 'Actividad Individual'),
    ]
    
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESOR'},
        related_name='created_activities'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='activities')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    instructions = models.TextField(help_text="Instrucciones detalladas para la actividad")
    due_date = models.DateTimeField()
    points = models.PositiveIntegerField(default=100, help_text="Puntos totales de la actividad")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.course.name} - {self.section.name}"


class ActivityAssignment(models.Model):
    """Asignación de actividades a estudiantes"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'},
        related_name='activity_assignments'
    )
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='activity_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    submission_notes = models.TextField(blank=True, help_text="Notas del estudiante sobre su entrega")

    class Meta:
        unique_together = ['activity', 'student']
        verbose_name = 'Asignación de Actividad'
        verbose_name_plural = 'Asignaciones de Actividades'

    def __str__(self):
        return f"{self.activity.title} - {self.student.first_name} {self.student.last_name}"


class Artifact(models.Model):
    """Artefactos/archivos subidos por los estudiantes para las actividades"""
    assignment = models.ForeignKey(ActivityAssignment, on_delete=models.CASCADE, related_name='artifacts', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='artifacts/')
    artifact_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Artefacto'
        verbose_name_plural = 'Artefactos'

    def __str__(self):
        return f"{self.title} - {self.assignment.activity.title}"
