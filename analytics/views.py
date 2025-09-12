from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # This will be implemented based on user role
        user = request.user
        data = {
            'user_role': user.role,
            'message': f'Dashboard for {user.get_role_display()}',
            'stats': {
                'total_courses': 0,
                'total_students': 0,
                'total_professors': 0,
            }
        }
        return Response(data)


class KPIsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # This will be implemented with actual KPIs
        data = {
            'kpis': [
                {'name': 'Total Students', 'value': 0},
                {'name': 'Active Courses', 'value': 0},
                {'name': 'Completion Rate', 'value': 0},
            ]
        }
        return Response(data)