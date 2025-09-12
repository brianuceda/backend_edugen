from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info(request):
    """
    Información general de la API para el frontend
    """
    return Response({
        'name': 'EDUGEN API',
        'version': '1.0.0',
        'description': 'API para sistema de gestión educativa',
        'endpoints': {
            'auth': {
                'login': '/api/v1/accounts/login/',
                'me': '/api/v1/accounts/me/',
            },
            'director': {
                'users': '/api/v1/director/users/',
                'sections': '/api/v1/director/sections/',
            },
            'academic': {
                'courses': '/api/v1/academic/courses/',
                'sections': '/api/v1/academic/sections/',
                'enrollments': '/api/v1/academic/enrollments/',
            },
            'institutions': {
                'list': '/api/v1/institutions/',
            }
        },
        'roles': {
            'ADMINISTRATOR': 'Administrador del sistema',
            'DIRECTOR': 'Director de institución',
            'PROFESOR': 'Profesor',
            'ALUMNO': 'Alumno'
        }
    })
