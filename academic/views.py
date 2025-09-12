from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, Section, Enrollment, Assessment, Grade
from .serializers import CourseSerializer, SectionSerializer, EnrollmentSerializer, AssessmentSerializer, GradeSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar cursos de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Course.objects.filter(institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Course.objects.filter(sections__professor=self.request.user)
        else:  # ALUMNO
            return Course.objects.filter(sections__enrollment__student=self.request.user)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar secciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Section.objects.filter(course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Section.objects.filter(professor=self.request.user)
        else:  # ALUMNO
            return Section.objects.filter(enrollment__student=self.request.user)


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar matrículas de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Enrollment.objects.filter(section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Enrollment.objects.filter(section__professor=self.request.user)
        else:  # ALUMNO
            return Enrollment.objects.filter(student=self.request.user)


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar evaluaciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Assessment.objects.filter(section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Assessment.objects.filter(section__professor=self.request.user)
        else:  # ALUMNO
            return Assessment.objects.filter(section__enrollment__student=self.request.user)


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar calificaciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Grade.objects.filter(assessment__section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Grade.objects.filter(assessment__section__professor=self.request.user)
        else:  # ALUMNO
            return Grade.objects.filter(student=self.request.user)
