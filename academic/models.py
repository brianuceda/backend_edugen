from django.db import models
from django.conf import settings


class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    credits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE)
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESOR'},
        related_name='created_courses',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.code} - {self.name}"


class Topic(models.Model):
    """Modelo para temas que pueden ser asignados a cursos"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESOR'},
        related_name='created_topics'
    )
    order = models.PositiveIntegerField(default=0, help_text="Orden de presentación del tema")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ['course', 'name']  # Un tema no puede repetirse en el mismo curso

    def __str__(self):
        return f"{self.name} - {self.course.name}"


class Section(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, related_name='sections', null=True, blank=True)
    professors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        limit_choices_to={'role': 'PROFESOR'},
        related_name='sections_taught',
        blank=True
    )
    term = models.ForeignKey('institutions.Term', on_delete=models.CASCADE)
    grade_level = models.ForeignKey('institutions.GradeLevel', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.course:
            return f"{self.course.name} - {self.name}"
        return self.name
    
    def get_professors_display(self):
        """Return a string representation of all professors"""
        return ", ".join([prof.get_full_name() for prof in self.professors.all()])


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'}
    )
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'section')

    def __str__(self):
        return f"{self.student.username} - {self.section}"


class Assessment(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    max_score = models.DecimalField(decimal_places=2, max_digits=5)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='assessments')

    def __str__(self):
        return f"{self.name} - {self.section}"


class Grade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'}
    )
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    score = models.DecimalField(decimal_places=2, max_digits=5)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'assessment')

    def __str__(self):
        return f"{self.student.username} - {self.assessment.name}: {self.score}"


class Material(models.Model):
    """Modelo para materiales educativos que pueden ser asignados a temas"""
    MATERIAL_TYPES = [
        ('DOCUMENT', 'Documento'),
        ('VIDEO', 'Video'),
        ('AUDIO', 'Audio'),
        ('IMAGE', 'Imagen'),
        ('LINK', 'Enlace'),
        ('SCORM', 'SCORM'),
        ('OTHER', 'Otro'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='DOCUMENT')
    file = models.FileField(upload_to='materials/', null=True, blank=True)
    url = models.URLField(blank=True, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='materials')
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESOR'},
        related_name='created_materials'
    )
    is_shared = models.BooleanField(default=True, help_text="True = material de clase, False = personalizado")
    assigned_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'role': 'ALUMNO'},
        related_name='assigned_materials',
        blank=True,
        help_text="Estudiantes específicos para materiales personalizados"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

    def __str__(self):
        return f"{self.name} - {self.topic.name}"

    def clean(self):
        """Validar que el material tenga archivo o URL según el tipo"""
        from django.core.exceptions import ValidationError
        
        if self.material_type == 'LINK' and not self.url:
            raise ValidationError('Los materiales de tipo enlace deben tener una URL')
        
        if self.material_type != 'LINK' and not self.file:
            raise ValidationError('Los materiales que no son enlaces deben tener un archivo')
        
        if self.url and self.file:
            raise ValidationError('Un material no puede tener tanto archivo como URL')


class MaterialViewingSession(models.Model):
    """Modelo para rastrear las sesiones de visualización de materiales por parte de los estudiantes"""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ALUMNO'},
        related_name='material_viewing_sessions'
    )
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='viewing_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0, help_text="Duración total en segundos")
    is_completed = models.BooleanField(default=False, help_text="Si el estudiante completó la visualización")
    progress_percentage = models.FloatField(default=0.0, help_text="Porcentaje de progreso (0-100)")
    last_activity = models.DateTimeField(auto_now=True, help_text="Última actividad registrada")
    
    class Meta:
        ordering = ['-started_at']
        unique_together = ('student', 'material', 'started_at')
        verbose_name = 'Sesión de Visualización'
        verbose_name_plural = 'Sesiones de Visualización'
    
    def __str__(self):
        return f"{self.student.username} - {self.material.name} ({self.duration_seconds}s)"
    
    @property
    def duration_formatted(self):
        """Retorna la duración en formato legible"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class MaterialInteraction(models.Model):
    """Modelo para rastrear interacciones específicas con materiales"""
    INTERACTION_TYPES = [
        ('PLAY', 'Reproducir'),
        ('PAUSE', 'Pausar'),
        ('SEEK', 'Buscar'),
        ('DOWNLOAD', 'Descargar'),
        ('COMPLETE', 'Completar'),
        ('ABANDON', 'Abandonar'),
    ]
    
    session = models.ForeignKey(MaterialViewingSession, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Datos adicionales como posición de video, etc.")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Interacción con Material'
        verbose_name_plural = 'Interacciones con Materiales'
    
    def __str__(self):
        return f"{self.session.student.username} - {self.get_interaction_type_display()} - {self.timestamp}"


class MaterialAnalytics(models.Model):
    """Modelo para almacenar KPIs y métricas agregadas de materiales"""
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name='analytics')
    total_views = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    total_duration = models.PositiveIntegerField(default=0, help_text="Duración total en segundos")
    average_duration = models.FloatField(default=0.0, help_text="Duración promedio en segundos")
    completion_rate = models.FloatField(default=0.0, help_text="Tasa de finalización (0-100)")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Analítica de Material'
        verbose_name_plural = 'Analíticas de Materiales'
    
    def __str__(self):
        return f"Analytics - {self.material.name}"
    
    def update_analytics(self):
        """Actualiza las métricas basadas en las sesiones de visualización"""
        sessions = self.material.viewing_sessions.all()
        
        self.total_views = sessions.count()
        self.unique_viewers = sessions.values('student').distinct().count()
        self.total_duration = sum(session.duration_seconds for session in sessions)
        self.average_duration = self.total_duration / self.total_views if self.total_views > 0 else 0
        self.completion_rate = (sessions.filter(is_completed=True).count() / self.total_views * 100) if self.total_views > 0 else 0
        
        self.save()