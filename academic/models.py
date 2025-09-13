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
