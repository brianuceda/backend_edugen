from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import CustomUser
from academic.models import Course, Section, Enrollment
from django.db.models import Count

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    """Endpoint básico para datos del dashboard"""
    user = request.user
    
    # Datos básicos para todos los roles
    data = {
        'user_role': user.role,
        'message': f'Bienvenido, {user.first_name or user.username}',
        'stats': {
            'total_courses': 0,
            'total_students': 0,
            'total_professors': 0
        }
    }
    
    # Si el usuario tiene una institución asignada
    if user.institution:
        # Contar cursos de la institución
        data['stats']['total_courses'] = Course.objects.filter(institution=user.institution).count()
        
        # Contar estudiantes de la institución
        data['stats']['total_students'] = CustomUser.objects.filter(
            institution=user.institution, 
            role='ALUMNO'
        ).count()
        
        # Contar profesores de la institución
        data['stats']['total_professors'] = CustomUser.objects.filter(
            institution=user.institution, 
            role='PROFESOR'
        ).count()
    else:
        # Datos de prueba si no hay institución
        data['stats'] = {
            'total_courses': 12,
            'total_students': 245,
            'total_professors': 18
        }
    
    return Response(data)
