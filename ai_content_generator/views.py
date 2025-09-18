from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMessage, ContentTemplate, GeneratedContent
from .serializers import (
    ConversationSerializer, ConversationMessageSerializer, ContentTemplateSerializer,
    GeneratedContentSerializer, CreateConversationSerializer, SendMessageSerializer,
    GenerateContentSerializer
)
from .services import DeepSeekChatService

class AIContentGeneratorViewSet(viewsets.ModelViewSet):
    """ViewSet para el generador de contenido con IA"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'messages':
            return ConversationMessageSerializer
        elif self.action == 'create':
            return CreateConversationSerializer
        elif self.action == 'send_message':
            return SendMessageSerializer
        elif self.action == 'generate_content':
            return GenerateContentSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear nueva conversación"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'], url_path='messages')
    def messages(self, request, pk=None):
        """Obtener mensajes de la conversación"""
        conversation = self.get_object()
        messages = conversation.messages.all().order_by('timestamp')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='send-message')
    def send_message(self, request, pk=None):
        """Enviar mensaje al chat de DeepSeek"""
        conversation = self.get_object()
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message_content = serializer.validated_data['content']
        
        # Guardar mensaje del usuario
        user_message = ConversationMessage.objects.create(
            conversation=conversation,
            role='user',
            content=message_content
        )
        
        # Obtener historial de conversación
        messages = conversation.messages.all().order_by('timestamp')
        message_history = [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
        ]
        
        # Enviar a DeepSeek
        deepseek_service = DeepSeekChatService()
        
        try:
            response = deepseek_service.chat_with_user(message_history)
            assistant_content = response['choices'][0]['message']['content']
            
            # Guardar respuesta del asistente
            assistant_message = ConversationMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=assistant_content
            )
            
            return Response({
                'user_message': ConversationMessageSerializer(user_message).data,
                'assistant_message': ConversationMessageSerializer(assistant_message).data
            })
            
        except Exception as e:
            # Error handling
            return Response(
                {'error': f'Error en el chat: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='extract-requirements')
    def extract_requirements(self, request, pk=None):
        """Extraer requisitos de la conversación"""
        conversation = self.get_object()
        
        # Obtener historial de conversación
        messages = conversation.messages.all().order_by('timestamp')
        message_history = [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
        ]
        
        # Extraer requisitos usando DeepSeek
        deepseek_service = DeepSeekChatService()
        
        try:
            requirements = deepseek_service.extract_requirements(message_history)
            
            if requirements:
                # Guardar requisitos en la conversación
                conversation.requirements = requirements
                conversation.save()
                
                return Response({
                    'requirements': requirements,
                    'message': 'Requisitos extraídos exitosamente'
                })
            else:
                return Response(
                    {'error': 'El contenido aún no está listo para generar. Continúa la conversación con el asistente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'error': f'Error al extraer requisitos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='generate-content')
    def generate_content(self, request, pk=None):
        """Generar contenido basado en los requisitos"""
        try:
            conversation = self.get_object()
            
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            requirements = serializer.validated_data['requirements']
            title = serializer.validated_data['title']
            
        except Exception as e:
            return Response(
                {'error': f'Error en setup: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Generar contenido usando DeepSeek
        deepseek_service = DeepSeekChatService()
        
        try:
            # Generar contenido
            generated_content = deepseek_service.generate_content(requirements)
            
            # Validar que el contenido generado tenga las claves esperadas
            if not all(key in generated_content for key in ['html', 'css', 'js']):
                raise Exception(f"Generated content missing required keys. Got: {list(generated_content.keys())}")
            
            # Guardar contenido generado
            content = GeneratedContent.objects.create(
                conversation=conversation,
                title=title,
                html_content=generated_content['html'],
                css_content=generated_content['css'],
                js_content=generated_content['js'],
                grapesjs_components={}
            )
            
            return Response({
                'content': GeneratedContentSerializer(content).data,
                'message': 'Contenido generado exitosamente'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error generando contenido: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def generate_content_streaming(self, request, pk=None):
        """Genera contenido educativo con streaming para mostrar progreso"""
        try:
            conversation = self.get_object()
            requirements = conversation.requirements
            title = request.data.get('title', 'Contenido Educativo Generado')
            
            if not requirements or not requirements.get('is_complete', False):
                return Response(
                    {'error': 'Los requisitos no están completos. Completa la conversación primero.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar contenido (sin timeout en Windows)
            deepseek_service = DeepSeekChatService()
            generated_content = deepseek_service.generate_content(requirements)
            
            # Guardar contenido generado
            content = GeneratedContent.objects.create(
                conversation=conversation,
                title=title,
                html_content=generated_content['html'],
                css_content=generated_content['css'],
                js_content=generated_content['js'],
                grapesjs_components={}
            )
            
            return Response({
                'content': GeneratedContentSerializer(content).data,
                'message': 'Contenido generado exitosamente'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error generando contenido: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ContentTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet para plantillas de contenido"""
    queryset = ContentTemplate.objects.filter(is_active=True)
    serializer_class = ContentTemplateSerializer
    permission_classes = [IsAuthenticated]

class GeneratedContentViewSet(viewsets.ModelViewSet):
    """ViewSet para contenido generado"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return GeneratedContent.objects.filter(conversation__user=self.request.user)
    
    def get_serializer_class(self):
        return GeneratedContentSerializer