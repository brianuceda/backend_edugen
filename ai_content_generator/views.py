from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationMessage, ContentTemplate, GeneratedContent
from .serializers import (
    ConversationSerializer, ConversationMessageSerializer, ContentTemplateSerializer,
    GeneratedContentSerializer, CreateConversationSerializer, SendMessageSerializer,
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
            error_message = str(e)
            
            # Manejar errores específicos de la API
            if "401" in error_message or "Unauthorized" in error_message:
                # Crear respuesta de respaldo inteligente
                fallback_content = self._create_fallback_response(message_content)
                
                assistant_message = ConversationMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=fallback_content
                )
                
                return Response({
                    'user_message': ConversationMessageSerializer(user_message).data,
                    'assistant_message': ConversationMessageSerializer(assistant_message).data
                })
            elif "429" in error_message or "rate limit" in error_message.lower():
                return Response(
                    {'error': 'Límite de solicitudes excedido. Por favor, intenta de nuevo en unos minutos.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                return Response(
                    {'error': f'Error en el chat: {error_message}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    def _create_fallback_response(self, user_message: str) -> str:
        """Crear respuesta de respaldo inteligente basada en el mensaje del usuario"""
        message_lower = user_message.lower()
        
        # Detectar tipo de contenido solicitado
        if any(word in message_lower for word in ['polinomios', 'matemáticas', 'math', 'álgebra']):
            return """¡Excelente! Veo que quieres crear contenido sobre **POLINOMIOS** para **MATEMÁTICAS**.

Aunque hay un problema temporal con el servicio de IA, puedo ayudarte a refinar los requisitos. Basándome en tu mensaje, veo que necesitas:

📚 **Tema**: Polinomios
🎓 **Materia**: Matemáticas  
📊 **Nivel**: Secundaria
📝 **Tipo**: Lección

Para completar la información, por favor comparte:

1. **Objetivos específicos**: ¿Qué conceptos de polinomios quieres cubrir? (suma, resta, multiplicación, factorización, etc.)
2. **Duración estimada**: ¿Cuánto tiempo durará la lección?
3. **Ejercicios**: ¿Qué tipo de ejercicios prefieres incluir?
4. **Recursos**: ¿Necesitas gráficos, ejemplos visuales, o interactivos?

**¿Estás conforme con esta información o quieres agregar algo más?** Una vez que confirmes, podrás usar "Extraer Requisitos" para generar tu contenido."""
        
        elif any(word in message_lower for word in ['ciencias', 'science', 'física', 'química', 'biología']):
            return """¡Perfecto! Veo que quieres crear contenido de **CIENCIAS**.

Aunque hay un problema temporal con el servicio de IA, puedo ayudarte a refinar los requisitos. Basándome en tu mensaje, veo que necesitas:

📚 **Materia**: Ciencias
📊 **Nivel**: Secundaria
📝 **Tipo**: Lección

Para completar la información, por favor comparte:

1. **Tema específico**: ¿Qué tema de ciencias quieres enseñar?
2. **Objetivos**: ¿Qué quieres que aprendan los estudiantes?
3. **Experimentos**: ¿Incluirás experimentos o actividades prácticas?
4. **Recursos**: ¿Necesitas diagramas, imágenes o videos?

**¿Estás conforme con esta información o quieres agregar algo más?** Una vez que confirmes, podrás usar "Extraer Requisitos" para generar tu contenido."""
        
        else:
            return """¡Hola! Aunque hay un problema temporal con el servicio de IA, puedo ayudarte a crear contenido educativo.

Por favor, comparte más detalles sobre lo que necesitas:

1. **Materia o tema**: ¿Qué materia quieres enseñar?
2. **Nivel educativo**: ¿Para qué nivel es el contenido? (básico, intermedio, avanzado)
3. **Tipo de contenido**: ¿Qué tipo de contenido necesitas? (lección, ejercicios, evaluación)
4. **Objetivos**: ¿Qué quieres que aprendan los estudiantes?

**¿Estás conforme con esta información o quieres agregar algo más?** Una vez que confirmes, podrás usar "Extraer Requisitos" para generar tu contenido educativo."""
    
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
        
        # Verificar si hay mensajes
        if not message_history:
            return Response(
                {'error': 'No hay mensajes en la conversación para extraer requisitos.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
            error_message = str(e)
            
            # Manejar errores específicos de la API
            if "401" in error_message or "Unauthorized" in error_message:
                return Response(
                    {'error': 'Error de autenticación con el servicio de IA. Por favor, contacta al administrador.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            elif "429" in error_message or "rate limit" in error_message.lower():
                return Response(
                    {'error': 'Límite de solicitudes excedido. Por favor, intenta de nuevo en unos minutos.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                return Response(
                    {'error': f'Error al extraer requisitos: {error_message}'},
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