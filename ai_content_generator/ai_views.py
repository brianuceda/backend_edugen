import os
import json
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from openai import OpenAI
import requests
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
from django.conf import settings

DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Initialize client only if API key is available
client = None
if DEEPSEEK_API_KEY:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_gamma_blocks(request):
    """Convierte un brief en JSON de bloques para el editor Gamma."""
    prompt = request.data.get("prompt", "")
    model = request.data.get("model", "deepseek-chat")
    content_type = request.data.get("content_type", "lesson")
    educational_level = request.data.get("educational_level", "intermediate")
    language = request.data.get("language", "es")
    requirements = request.data.get("requirements", {})

    try:
        # Verificar si el cliente está disponible
        if not client:
            # Devolver bloques de ejemplo cuando la API no está configurada
            example_blocks = [
                {
                    "id": "b1",
                    "type": "hero",
                    "title": "Contenido Educativo",
                    "subtitle": "Generado automáticamente",
                    "body": f"Este es contenido de ejemplo sobre: {prompt}",
                    "media": {
                        "type": "icon",
                        "value": "📚"
                    },
                    "props": {
                        "alignment": "center",
                        "padding": "large"
                    }
                },
                {
                    "id": "b2",
                    "type": "paragraph",
                    "content": "Para habilitar la generación real de contenido con IA, configure la variable de entorno DEEPSEEK_API_KEY con su clave de API de DeepSeek.",
                    "props": {
                        "alignment": "left",
                        "padding": "medium"
                    }
                }
            ]
            return Response({
                "success": True,
                "blocks": example_blocks,
                "message": "Bloques de ejemplo generados (API key no configurada)"
            }, status=status.HTTP_200_OK)
        
        # Crear el prompt específico para generar bloques Gamma
        system_prompt = f"""Eres un generador de bloques educativos para el editor Gamma. 
        Genera contenido educativo en formato JSON con bloques específicos.
        
        Tipos de bloques disponibles:
        - hero: Encabezado principal con título, subtítulo, cuerpo y media
        - paragraph: Párrafos de texto
        - heading: Encabezados (h1-h6)
        - list: Listas ordenadas o no ordenadas
        - image: Imágenes con caption
        - callout: Notas destacadas (info, warning, success, error)
        - quiz: Preguntas de opción múltiple
        - code: Bloques de código
        - card: Tarjetas de contenido
        
        Nivel educativo: {educational_level}
        Idioma: {language}
        Tipo de contenido: {content_type}
        
        Responde SOLO con un JSON válido, sin texto adicional."""

        user_prompt = f"""
        Crea contenido educativo sobre: {prompt}
        
        Genera un array de bloques JSON con la siguiente estructura:
        [
          {{
            "id": "b1",
            "type": "hero",
            "title": "Título principal",
            "subtitle": "Subtítulo opcional",
            "body": "Descripción del contenido",
            "media": {{
              "type": "image",
              "src": "/api/placeholder/800/400",
              "alt": "Descripción de la imagen"
            }},
            "props": {{
              "bg": "gradient",
              "align": "center",
              "padding": "medium"
            }}
          }},
          {{
            "id": "b2",
            "type": "paragraph",
            "content": "Contenido del párrafo...",
            "props": {{
              "align": "left",
              "padding": "medium"
            }}
          }},
          {{
            "id": "b3",
            "type": "heading",
            "level": 2,
            "content": "Título de sección",
            "props": {{
              "align": "left"
            }}
          }},
          {{
            "id": "b4",
            "type": "list",
            "listType": "unordered",
            "items": ["Elemento 1", "Elemento 2", "Elemento 3"],
            "props": {{
              "padding": "medium"
            }}
          }},
          {{
            "id": "b5",
            "type": "callout",
            "variant": "info",
            "title": "Nota importante",
            "content": "Información destacada",
            "props": {{
              "padding": "medium"
            }}
          }}
        ]
        """

        res = client.chat.completions.create(
            model=model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        content = res.choices[0].message.content.strip()
        
        # Intentar parsear el JSON para validar
        try:
            blocks = json.loads(content)
            if not isinstance(blocks, list):
                raise ValueError("El contenido debe ser un array de bloques")
        except json.JSONDecodeError as e:
            # Si no es JSON válido, crear un bloque de error
            blocks = [{
                "id": "b1",
                "type": "callout",
                "variant": "error",
                "title": "Error en la generación",
                "content": f"No se pudo generar contenido válido. Error: {str(e)}",
                "props": {
                    "padding": "medium"
                }
            }]
        
        return Response({
            "success": True,
            "blocks": blocks,
            "message": f"Se generaron {len(blocks)} bloques educativos"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "blocks": []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def improve_gamma_block(request):
    """Mejora un bloque específico del editor Gamma."""
    block = request.data.get("block", {})
    improvement_type = request.data.get("improvement_type", "enhance")
    tone = request.data.get("tone", "educativo y claro")
    language = request.data.get("language", "es")
    
    try:
        system_prompt = f"""Eres un asistente de IA especializado en mejorar contenido educativo.
        Mejora el bloque proporcionado según el tipo de mejora solicitado.
        
        Tipos de mejora disponibles:
        - enhance: Mejorar el contenido general
        - simplify: Simplificar el lenguaje
        - expand: Expandir el contenido
        - summarize: Resumir el contenido
        - translate: Traducir a otro idioma
        
        Tono: {tone}
        Idioma: {language}
        
        Responde SOLO con el bloque JSON mejorado, sin texto adicional."""

        user_prompt = f"""
        Mejora este bloque educativo:
        {json.dumps(block, ensure_ascii=False, indent=2)}
        
        Tipo de mejora: {improvement_type}
        """

        # Verificar si el cliente está disponible
        if not client:
            return Response({
                "success": False,
                "error": "API key de DeepSeek no configurada",
                "block": block
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        res = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.6,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        content = res.choices[0].message.content.strip()
        
        try:
            improved_block = json.loads(content)
        except json.JSONDecodeError:
            # Si no es JSON válido, devolver el bloque original
            improved_block = block
        
        return Response({
            "success": True,
            "block": improved_block,
            "message": "Bloque mejorado exitosamente"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "block": block
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_educational_image(request):
    """Genera imagen educativa usando FAL AI."""
    prompt = request.data.get("prompt", "")
    style = request.data.get("style", "realistic")
    size = request.data.get("size", "1024x1024")
    
    try:
        # Mejorar el prompt para contenido educativo
        educational_prompt = f"Educational illustration: {prompt}. Style: {style}. Clean, professional, suitable for educational content."
        
        r = requests.post(
            "https://api.fal.ai/fal-ai/janus-pro",
            headers={
                "Authorization": f"Key {os.getenv('FAL_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": educational_prompt,
                "num_images": 1,
                "size": size
            }
        )
        
        if r.status_code == 200:
            data = r.json()
            image_url = (data.get("images") or [{}])[0].get("url")
            
            return Response({
                "success": True,
                "image_url": image_url,
                "alt_text": f"Imagen educativa: {prompt}"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "error": f"Error de FAL AI: {r.status_code}",
                "image_url": None
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "image_url": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_quiz_questions(request):
    """Genera preguntas de quiz para contenido educativo."""
    topic = request.data.get("topic", "")
    difficulty = request.data.get("difficulty", "medium")
    num_questions = request.data.get("num_questions", 5)
    language = request.data.get("language", "es")
    
    try:
        system_prompt = f"""Eres un generador de preguntas de quiz educativas.
        Genera preguntas de opción múltiple sobre el tema dado.
        
        Dificultad: {difficulty}
        Idioma: {language}
        Número de preguntas: {num_questions}
        
        Responde SOLO con un JSON válido, sin texto adicional."""

        user_prompt = f"""
        Genera {num_questions} preguntas de quiz sobre: {topic}
        
        Dificultad: {difficulty}
        
        Formato JSON:
        [
          {{
            "id": "q1",
            "type": "quiz",
            "question": "Pregunta aquí",
            "options": ["Opción A", "Opción B", "Opción C", "Opción D"],
            "correctAnswer": 0,
            "explanation": "Explicación de la respuesta correcta",
            "points": 10,
            "props": {{
              "padding": "medium"
            }}
          }}
        ]
        """

        # Verificar si el cliente está disponible
        if not client:
            return Response({
                "success": False,
                "error": "API key de DeepSeek no configurada",
                "questions": []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        res = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        content = res.choices[0].message.content.strip()
        
        try:
            questions = json.loads(content)
            if not isinstance(questions, list):
                raise ValueError("El contenido debe ser un array de preguntas")
        except json.JSONDecodeError as e:
            questions = [{
                "id": "q1",
                "type": "quiz",
                "question": f"Error al generar preguntas sobre {topic}",
                "options": ["Error", "No disponible", "Intenta de nuevo", "Contacta soporte"],
                "correctAnswer": 0,
                "explanation": f"Error: {str(e)}",
                "points": 0,
                "props": {
                    "padding": "medium"
                }
            }]
        
        return Response({
            "success": True,
            "questions": questions,
            "message": f"Se generaron {len(questions)} preguntas de quiz"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "questions": []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def translate_gamma_blocks(request):
    """Traduce bloques del editor Gamma a otro idioma."""
    blocks = request.data.get("blocks", [])
    target_language = request.data.get("target_language", "en")
    source_language = request.data.get("source_language", "es")
    
    try:
        system_prompt = f"""Eres un traductor especializado en contenido educativo.
        Traduce los bloques del editor Gamma del {source_language} al {target_language}.
        
        Mantén la estructura JSON y solo traduce el contenido textual.
        Responde SOLO con el JSON traducido, sin texto adicional."""

        user_prompt = f"""
        Traduce estos bloques educativos:
        {json.dumps(blocks, ensure_ascii=False, indent=2)}
        
        De {source_language} a {target_language}
        """

        # Verificar si el cliente está disponible
        if not client:
            return Response({
                "success": False,
                "error": "API key de DeepSeek no configurada",
                "blocks": blocks
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        res = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        content = res.choices[0].message.content.strip()
        
        try:
            translated_blocks = json.loads(content)
        except json.JSONDecodeError:
            translated_blocks = blocks
        
        return Response({
            "success": True,
            "blocks": translated_blocks,
            "message": f"Bloques traducidos al {target_language}"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "blocks": blocks
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_and_generate_content(request):
    """Confirma los requisitos y genera contenido Gamma completo."""
    conversation_id = request.data.get("conversation_id")
    requirements = request.data.get("requirements", {})
    title = request.data.get("title", "Contenido Educativo")
    user = request.user
    
    try:
        # Validar que tenemos todos los requisitos necesarios
        required_fields = ['subject', 'content_type', 'course_level']
        missing_fields = [field for field in required_fields if not requirements.get(field)]
        
        if missing_fields:
            return Response({
                "success": False,
                "error": f"Faltan campos requeridos: {', '.join(missing_fields)}",
                "content": None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generar el prompt basado en los requisitos
        prompt = f"""
        Genera contenido educativo completo sobre: {requirements['subject']}
        
        Detalles:
        - Nivel educativo: {requirements.get('course_level', 'intermedio')}
        - Tipo de contenido: {requirements.get('content_type', 'lección')}
        - Objetivos de aprendizaje: {requirements.get('learning_objectives', 'Aprender el tema')}
        - Duración estimada: {requirements.get('estimated_duration', '30 minutos')}
        - Idioma: {requirements.get('language', 'es')}
        
        Requisitos adicionales: {requirements.get('additional_requirements', 'Ninguno')}
        """
        
        # Generar bloques Gamma usando el servicio
        from .services import DeepSeekChatService
        
        service = DeepSeekChatService()
        try:
            gamma_content = service.generate_content(requirements)
        except Exception as e:
            # Como última instancia, construir contenido mínimo local
            logger.exception("Error generando contenido Gamma, usando respaldo local: %s", str(e))
            subject = requirements.get('subject', 'Contenido Educativo')
            blocks = [{
                'id': 'b1',
                'type': 'paragraph',
                'content': f"No se pudo contactar a IA. Respaldo local para: {subject}",
                'props': {'padding': 'medium'}
            }]
            gamma_content = {
                'blocks': blocks,
                'document': {
                    'title': 'Contenido de Respaldo',
                    'description': f'Respaldo generado localmente para {subject}',
                    'blocks': blocks
                },
                'fallback': True
            }
        
        if not gamma_content or 'blocks' not in gamma_content:
            return Response({
                "success": False,
                "error": "No se pudieron generar los bloques Gamma",
                "content": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # Si hubo fallback, seguimos pero indicamos en el mensaje
        fallback_used = bool(gamma_content.get('fallback'))

        blocks = gamma_content.get('blocks', [])
        
        # Crear el documento Gamma completo
        gamma_document = {
            "id": f"doc_{int(time.time())}",
            "title": title,
            "description": f"Contenido educativo generado con IA - {requirements['subject']}",
            "blocks": blocks,
            "metadata": {
                "author": f"{user.first_name} {user.last_name}",
                "tags": ["generado", "ia", "educativo", requirements.get('subject', '').lower()],
                "category": "educativo",
                "difficulty": requirements.get('course_level', 'intermediate'),
                "estimatedTime": 45,  # Valor por defecto para polinomios
                "language": requirements.get('language', 'es'),
                "learning_objectives": requirements.get('learning_objectives', []),
                "content_type": requirements.get('content_type', 'lección')
            },
            "settings": {
                "theme": "light",
                "fontSize": "medium",
                "showOutline": True,
                "allowComments": True,
                "allowCollaboration": False
            },
            "createdAt": timezone.now().isoformat(),
            "updatedAt": timezone.now().isoformat(),
            "version": 1
        }
        
        # Crear el contenido generado en la base de datos
        from .models import GeneratedContent, Conversation
        
        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
            except Conversation.DoesNotExist:
                pass
        
        generated_content = GeneratedContent.objects.create(
            conversation=conversation,
            title=title,
            description=gamma_document["description"],
            content_type='gamma',
            gamma_blocks=blocks,
            gamma_document=gamma_document,
            is_public=False
        )
        
        # Guardar archivo JSON adicional en media/materials/
        try:
            import os
            materials_dir = os.path.join(settings.MEDIA_ROOT, 'materials', f'content_{generated_content.id}')
            os.makedirs(materials_dir, exist_ok=True)
            file_path = os.path.join(materials_dir, 'gamma_content.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(gamma_document, f, ensure_ascii=False, indent=2)
            relative_path = f"materials/content_{generated_content.id}/gamma_content.json"
            file_url = f"{settings.MEDIA_URL}{relative_path}"
        except Exception:
            # Si falla el guardado de archivo, continuar sin bloquear la respuesta
            relative_path = None
            file_url = None
        
        return Response({
            "success": True,
            "content": {
                "id": generated_content.id,
                "title": generated_content.title,
                "description": generated_content.description,
                "content_type": generated_content.content_type,
                "gamma_blocks": generated_content.gamma_blocks,
                "gamma_document": generated_content.gamma_document,
                "media_file_path": relative_path,
                "media_file_url": file_url,
                "created_at": generated_content.created_at.isoformat(),
                "updated_at": generated_content.updated_at.isoformat()
            },
            "message": "Contenido generado exitosamente" + (" (respaldo)" if fallback_used else "")
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e),
            "content": None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
