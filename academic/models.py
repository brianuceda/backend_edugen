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

    def __str__(self):
        return f"{self.code} - {self.name}"


class Section(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROFESOR'}
    )
    term = models.ForeignKey('institutions.Term', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course.name} - {self.name}"


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
