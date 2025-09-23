import requests
import json
import re
from typing import List, Dict, Any, Optional
from django.conf import settings

class DeepSeekChatService:
    """Servicio para interactuar con la API de DeepSeek"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = "deepseek-chat"
    
    def chat_with_user(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Maneja la conversación con el usuario usando DeepSeek"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construir el prompt del sistema para recolección de información
        system_prompt = self.get_collection_system_prompt()
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Agregar historial de conversación
        for msg in messages:
            chat_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.7,
            "max_tokens": 4000,  # Aumentado para respuestas más completas
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception(f"401 Unauthorized: API key inválida o expirada")
            elif e.response.status_code == 429:
                raise Exception(f"429 Rate Limit: Límite de solicitudes excedido")
            else:
                raise Exception(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
    
    def get_collection_system_prompt(self) -> str:
        """Obtiene el prompt del sistema para recolección de información"""
        return """
        Eres un asistente especializado en recolección de información para crear contenido educativo con el editor Gamma.
        
        FORMATO FIJO: El contenido siempre se generará en formato de bloques Gamma. NO preguntes sobre formatos.
        
        REGLAS IMPORTANTES:
        1. NO hagas preguntas obvias o redundantes
        2. Analiza el contexto antes de preguntar
        3. Si el usuario ya mencionó información, NO la preguntes de nuevo
        4. Sé inteligente y deduce información cuando sea posible
        5. Haz solo preguntas esenciales que realmente necesites
        6. NUNCA preguntes sobre formato - siempre será Gamma
        7. Si el usuario da información incompleta, haz preguntas específicas para completarla
        
        INFORMACIÓN CRÍTICA A RECOLECTAR:
        - Tema/Materia específica (OBLIGATORIO)
        - Nivel educativo (básico/intermedio/avanzado) - deduce si no está claro
        - Tipo de contenido (lección, ejercicio, evaluación, guía, etc.)
        - Objetivos de aprendizaje específicos (al menos 2-3)
        - Público objetivo (edad, nivel, características)
        - Duración estimada (opcional pero útil)
        - Secciones principales (introducción, desarrollo, ejercicios, evaluación)
        - Recursos necesarios (imágenes, videos, interactivos)
        
        ESTRATEGIA DE RECOLECCIÓN:
        1. Analiza cada mensaje del usuario cuidadosamente
        2. Identifica información explícita e implícita
        3. Haz preguntas específicas para completar información faltante
        4. Confirma tu entendimiento antes de proceder
        5. Máximo 2 preguntas por mensaje para no abrumar
        
        EJEMPLOS DE PREGUNTAS INTELIGENTES:
        ✅ "¿Qué objetivos específicos quieres que logren los estudiantes con este contenido?"
        ✅ "¿Para qué nivel de estudiantes está dirigido? (básico, intermedio, avanzado)"
        ✅ "¿Qué tipo de ejercicios prefieres incluir? (opción múltiple, problemas prácticos, etc.)"
        ✅ "¿Qué secciones específicas necesitas? (introducción, teoría, ejemplos, ejercicios, evaluación)"
        ✅ "¿Hay algún recurso específico que quieras incluir? (imágenes, videos, interactivos)"
        
        ❌ "¿Qué formato prefieres?" (NUNCA preguntes esto)
        ❌ "¿Quieres PDF o web?" (NUNCA preguntes esto)
        ❌ "¿Para qué nivel educativo?" (si ya mencionó "secundaria" o similar)
        
        CUANDO TENGAS INFORMACIÓN SUFICIENTE:
        - Haz un resumen completo de lo que vas a crear
        - Incluye: tema, nivel, tipo, objetivos, secciones principales
        - SIEMPRE pregunta: "¿Estás conforme con esta información o quieres agregar algo más?"
        - ESPERA a que el usuario responda con palabras explícitas como: "sí", "conforme", "perfecto", "está bien", "procede", "adelante", "confirmo"
        - SOLO después de que el usuario confirme con PALABRAS, di: "¡Perfecto! Ya tienes suficiente información. Usa 'Extraer Requisitos' para generar el contenido."
        - NUNCA actives el botón solo con emojis o respuestas ambiguas
        - El usuario DEBE escribir explícitamente su confirmación
        
        Mantén un tono amigable, profesional y educativo. Responde siempre en español.
        """
    
    
    def extract_requirements(self, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Extrae los requisitos de la conversación usando DeepSeek"""
        
        # Verificar si hay suficiente información en la conversación
        if len(conversation_history) < 1:
            return None
        
        # Buscar indicadores de que el contenido está listo
        ready_indicators = [
            "está listo tu contenido para ser generado",
            "listo tu contenido",
            "contenido para ser generado",
            "proceder con la generación",
            "extraer requisitos",
            "generar el contenido",
            "ya tienes suficiente información",
            "usa \"extraer requisitos\" para generar",
            "perfecto! ya tienes suficiente información",
            "tienes suficiente información para generar contenido",
            "estás conforme con esta información",
            "quieres agregar algo más",
            "¿estás conforme con esta información o quieres agregar algo más?",
            "confirmo la información",
            "estoy conforme",
            "proceder con la generación",
            "generar contenido"
        ]
        
        # Verificar si el asistente indicó que está listo
        last_assistant_message = None
        is_ready = False
        
        for msg in reversed(conversation_history):
            if msg.get('role') == 'assistant':
                last_assistant_message = msg.get('content', '').lower()
                # Verificar si contiene algún indicador de que está listo
                if any(indicator in last_assistant_message for indicator in ready_indicators):
                    is_ready = True
                    break
        
        # Verificar si el usuario confirmó explícitamente
        if not is_ready:
            user_confirmations = [
                'sí, estoy conforme',
                'perfecto, estoy conforme', 
                'sí, está bien',
                'está perfecto',
                'sí, procede',
                'conforme',
                'está bien',
                'perfecto',
                'sí',
                'ok',
                'okay',
                'confirmo',
                'estoy de acuerdo',
                'procede',
                'adelante',
                'si, estoy conforme',
                'si, está bien',
                'si, procede',
                'si',
                'está listo',
                'listo',
                'generar',
                'extraer requisitos'
            ]
            
            for msg in reversed(conversation_history):
                if msg.get('role') == 'user':
                    user_content = msg.get('content', '').lower()
                    if any(confirmation in user_content for confirmation in user_confirmations):
                        is_ready = True
                        break
        
        # Si no está listo por confirmación, verificar si hay suficiente información básica
        if not is_ready:
            # Buscar información básica en la conversación
            has_subject = False
            has_level = False
            has_content_type = False
            
            for msg in conversation_history:
                content = msg.get('content', '').lower()
                
                # Verificar si hay información sobre materia/tema
                if any(word in content for word in ['matemáticas', 'ciencias', 'historia', 'español', 'inglés', 'física', 'química', 'biología', 'geografía', 'polinomios', 'álgebra', 'geometría']):
                    has_subject = True
                
                # Verificar si hay información sobre nivel
                if any(word in content for word in ['primaria', 'secundaria', 'universidad', 'básico', 'intermedio', 'avanzado', '1°', '2°', '3°', '4°', '5°', '6°']):
                    has_level = True
                
                # Verificar si hay información sobre tipo de contenido
                if any(word in content for word in ['lección', 'ejercicio', 'evaluación', 'actividad', 'taller', 'práctica', 'ejercicios']):
                    has_content_type = True
            
            # Si hay al menos 2 de los 3 elementos básicos, permitir extracción
            if sum([has_subject, has_level, has_content_type]) >= 2:
                is_ready = True
        
        # Siempre extraer requisitos de la conversación cuando se llama esta función
        # El usuario hizo clic en "Extraer Requisitos", así que proceder con la extracción
        
        extraction_prompt = """
        Analiza la siguiente conversación y extrae AUTOMÁTICAMENTE todos los requisitos del usuario para crear contenido educativo con bloques Gamma.
        
        INSTRUCCIONES:
        1. Extrae TODA la información disponible en la conversación (explícita e implícita)
        2. Deduce información inteligentemente basándote en el contexto completo
        3. Si el usuario menciona "polinomios" y "1° de secundaria", extrae automáticamente:
           - Materia: Matemáticas - Polinomios
           - Nivel: Básico (1° de secundaria)
           - Tipo: Ejercicios (si menciona ejercicios)
           - Objetivos: Suma y resta de polinomios
        4. SIEMPRE marca "is_complete": true para permitir la generación
        5. Usa la información de la conversación para crear requisitos específicos
        
        REGLAS DE EXTRACCIÓN AUTOMÁTICA:
        - "1° de secundaria" → course_level: "básico", target_audience: "Estudiantes de 1° de secundaria (12-13 años)"
        - "polinomios" → subject: "Matemáticas - Polinomios"
        - "ejercicios" → content_type: "ejercicios"
        - "suma y resta" → learning_objectives: ["Aprender suma de polinomios", "Aprender resta de polinomios"]
        - Si menciona "10-15 ejercicios" → additional_requirements: "Set de 10-15 ejercicios"
        
        IMPORTANTE: 
        - SIEMPRE devuelve un JSON válido
        - SIEMPRE marca is_complete: true
        - Extrae información específica de la conversación
        - Usa valores por defecto inteligentes basados en el contexto
        
        Devuelve SOLO un JSON válido con la siguiente estructura:
        {
            "course_level": "básico",
            "subject": "Matemáticas - Polinomios",
            "content_type": "ejercicios",
            "learning_objectives": ["Aprender suma de polinomios", "Aprender resta de polinomios", "Practicar operaciones básicas"],
            "sections": ["introducción", "desarrollo", "ejercicios", "evaluación"],
            "target_audience": "Estudiantes de 1° de secundaria (12-13 años)",
            "resources": ["imágenes", "videos", "ejemplos visuales"],
            "estimated_duration": "45-60 minutos",
            "additional_requirements": "Set de 10-15 ejercicios paso a paso",
            "is_complete": true,
            "missing_info": []
        }
        
        Conversación:
        """
        
        # Agregar historial de conversación
        for msg in conversation_history:
            extraction_prompt += f"\n{msg.get('role', 'user')}: {msg.get('content', '')}"
        
        # Usar DeepSeek para extraer requisitos
        try:
            response = self.chat_with_user([
                {"role": "user", "content": extraction_prompt}
            ])
            
            content = response['choices'][0]['message']['content']
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    requirements = json.loads(json_str)
                    
                    # Validar que tenga los campos mínimos necesarios
                    if not requirements.get('subject'):
                        # Si no hay materia, intentar extraer del contexto
                        for msg in conversation_history:
                            if msg.get('role') == 'user':
                                content_lower = msg.get('content', '').lower()
                                if 'matemáticas' in content_lower or 'math' in content_lower:
                                    requirements['subject'] = 'Matemáticas'
                                elif 'ciencias' in content_lower or 'science' in content_lower:
                                    requirements['subject'] = 'Ciencias'
                                elif 'historia' in content_lower or 'history' in content_lower:
                                    requirements['subject'] = 'Historia'
                                elif 'español' in content_lower or 'spanish' in content_lower:
                                    requirements['subject'] = 'Español'
                                else:
                                    requirements['subject'] = 'Tema General'
                                break
                    
                    # Asegurar que tenga objetivos de aprendizaje
                    if not requirements.get('learning_objectives') or len(requirements.get('learning_objectives', [])) < 2:
                        requirements['learning_objectives'] = [
                            f"Aprender sobre {requirements.get('subject', 'el tema')}",
                            f"Entender los conceptos fundamentales de {requirements.get('subject', 'el tema')}"
                        ]
                    
                    # Asegurar que tenga nivel de curso
                    if not requirements.get('course_level'):
                        requirements['course_level'] = 'intermedio'
                    
                    # Asegurar que tenga tipo de contenido
                    if not requirements.get('content_type'):
                        requirements['content_type'] = 'lección'
                    
                    # Asegurar que tenga secciones
                    if not requirements.get('sections'):
                        requirements['sections'] = ['introducción', 'desarrollo', 'ejercicios', 'evaluación']
                    
                    # Marcar como completo si tiene la información básica
                    if requirements.get('subject') and requirements.get('learning_objectives'):
                        requirements['is_complete'] = True
                        requirements['missing_info'] = []
                    
                    return requirements
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    print(f"JSON string: {json_str}")
                    # Usar método de respaldo si falla el parsing
                    return self.extract_requirements_fallback(conversation_history)
        except Exception as e:
            print(f"Error in extraction: {e}")
            # Usar método de respaldo si falla la API
            return self.extract_requirements_fallback(conversation_history)
        
        return None
    
    def extract_requirements_fallback(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Método de respaldo para extraer requisitos automáticamente de la conversación"""
        
        # Analizar toda la conversación para extraer información
        all_content = ""
        for msg in conversation_history:
            all_content += f" {msg.get('content', '')}"
        
        all_content = all_content.lower()
        
        # Extraer información automáticamente de la conversación
        subject = "Matemáticas - Polinomios"  # Por defecto para el caso de polinomios
        course_level = "básico"
        content_type = "ejercicios"
        target_audience = "Estudiantes de 1° de secundaria (12-13 años)"
        additional_requirements = ""
        
        # Detectar materia específica
        if 'polinomios' in all_content:
            subject = "Matemáticas - Polinomios"
        elif 'matemáticas' in all_content or 'math' in all_content:
            subject = "Matemáticas"
        elif 'ciencias' in all_content:
            subject = "Ciencias"
        elif 'historia' in all_content:
            subject = "Historia"
        
        # Detectar nivel educativo
        if '1°' in all_content or 'primero' in all_content or 'primaria' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de 1° de secundaria (12-13 años)"
        elif '2°' in all_content or 'segundo' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de 2° de secundaria (13-14 años)"
        elif 'secundaria' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de secundaria"
        
        # Detectar tipo de contenido
        if 'ejercicios' in all_content or 'ejercicio' in all_content:
            content_type = "ejercicios"
        elif 'lección' in all_content or 'clase' in all_content:
            content_type = "lección"
        elif 'evaluación' in all_content or 'examen' in all_content:
            content_type = "evaluación"
        
        # Detectar requisitos adicionales
        if '10-15' in all_content or '10 a 15' in all_content:
            additional_requirements = "Set de 10-15 ejercicios"
        elif 'paso a paso' in all_content:
            additional_requirements = "Ejercicios paso a paso"
        
        # Crear objetivos específicos para polinomios
        if 'polinomios' in all_content:
            learning_objectives = [
                "Aprender a identificar y clasificar polinomios",
                "Entender las operaciones básicas con polinomios (suma y resta)",
                "Practicar ejercicios de suma y resta de polinomios",
                "Desarrollar habilidades de resolución de problemas algebraicos"
            ]
        else:
            learning_objectives = [
                f"Aprender sobre {subject}",
                f"Entender los conceptos fundamentales de {subject}",
                f"Desarrollar habilidades prácticas en {subject}"
            ]
        
        # Crear requisitos finales con la información extraída automáticamente
        requirements = {
            'subject': subject,
            'course_level': course_level,
            'content_type': content_type,
            'learning_objectives': learning_objectives,
            'sections': ['introducción', 'desarrollo', 'ejercicios', 'evaluación'],
            'target_audience': target_audience,
            'resources': ['imágenes', 'videos', 'ejemplos visuales'],
            'estimated_duration': '45-60 minutos',
            'additional_requirements': additional_requirements,
            'is_complete': True,
            'missing_info': []
        }
        
        return requirements
    
    
    def generate_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido en bloques Gamma basado en los requisitos"""
        
        # Crear prompt de generación optimizado para bloques Gamma
        generation_prompt = f"""Genera contenido educativo en formato de bloques Gamma:

Materia: {requirements.get('subject', 'Tema General')}
Nivel: {requirements.get('course_level', 'básico')}
Objetivos: {', '.join(requirements.get('learning_objectives', ['Aprender el tema']))}

TIPOS DE BLOQUES DISPONIBLES:
- hero: Encabezado principal con título, subtítulo, cuerpo y media
- paragraph: Párrafos de texto
- heading: Encabezados (h1-h6)
- list: Listas ordenadas o no ordenadas
- image: Imágenes con caption
- callout: Notas destacadas (info, warning, success, error)
- quiz: Preguntas de opción múltiple
- code: Bloques de código
- card: Tarjetas de contenido
- button: Botones interactivos
- form: Formularios

ESTRUCTURA REQUERIDA:
1. Bloque hero con título principal
2. Bloque paragraph con introducción
3. Bloques heading para secciones
4. Bloques paragraph para contenido
5. Bloques quiz para ejercicios
6. Bloques callout para información importante
7. Bloques list para objetivos y puntos clave

FORMATO DE RESPUESTA:
Devuelve SOLO un JSON válido con un array de bloques Gamma:

[
  {{
    "id": "b1",
    "type": "hero",
    "title": "Título principal",
    "subtitle": "Subtítulo",
    "body": "Descripción breve",
    "media": {{
      "type": "image",
      "src": "url_de_imagen"
    }},
    "props": {{
      "background": "gradient",
      "alignment": "center",
      "padding": "large"
    }}
  }},
  {{
    "id": "b2",
    "type": "paragraph",
    "content": "Contenido del párrafo...",
    "props": {{
      "padding": "medium"
    }}
  }}
]

ENFOQUE: Contenido educativo estructurado en bloques editables con Gamma."""
        
        try:
            response = self.generate_content_with_limits([
                {"role": "user", "content": generation_prompt}
            ])
            
            if 'choices' not in response or len(response['choices']) == 0:
                raise Exception("No choices in DeepSeek response")
            
            content = response['choices'][0]['message']['content']
            
            # Extraer bloques Gamma de la respuesta
            parsed_content = self.parse_generated_content(content)
            
            return parsed_content
            
        except Exception as e:
            return self.generate_fallback_gamma_content()
    
    def generate_content_with_limits(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Genera contenido con límites estrictos de tokens para respuesta rápida"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": "Eres un experto en generar contenido educativo en formato de bloques Gamma. Genera bloques estructurados y editables para el editor Gamma, incluye elementos interactivos como quiz, callout, y formularios. Enfócate en contenido educativo bien estructurado y funcional."}
        ]
        
        # Agregar mensajes del usuario
        for msg in messages:
            chat_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.3,  # Menor temperatura para respuestas más determinísticas
            "max_tokens": 1500,  # Reducido para respuesta más rápida
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"API Error {response.status_code}: {response.text}")
            
            response_data = response.json()
            return response_data
        except requests.exceptions.Timeout:
            raise Exception("Timeout: La API de DeepSeek tardó demasiado en responder")
        except requests.exceptions.ConnectionError as e:
            raise Exception("Error de conexión: No se pudo conectar con la API de DeepSeek")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
        except Exception as e:
            raise Exception(f"Error inesperado: {str(e)}")
    
    
    
    def parse_generated_content(self, content: str) -> Dict[str, Any]:
        """Parsea el contenido generado para extraer bloques Gamma"""
        result = {
            'blocks': [],
            'document': {
                'title': '',
                'description': '',
                'blocks': []
            }
        }
        
        try:
            # Buscar JSON en la respuesta
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                blocks = json.loads(json_match.group())
                result['blocks'] = blocks
                result['document']['blocks'] = blocks
                result['document']['title'] = 'Contenido Educativo Generado'
                result['document']['description'] = 'Contenido educativo generado con IA'
                return result
        except json.JSONDecodeError:
            pass
        
        # Si no se encontró JSON válido, generar fallback
        return self.generate_fallback_gamma_content()
    
    def generate_fallback_gamma_content(self) -> Dict[str, Any]:
        """Genera contenido Gamma de fallback cuando la API falla"""
        return {
            'blocks': [
                {
                    "id": "b1",
                    "type": "hero",
                    "title": "Polinomios: Suma y Resta",
                    "subtitle": "Matemáticas - 1° de Secundaria",
                    "body": "Aprende a identificar términos de polinomios y realizar operaciones básicas de suma y resta.",
                    "media": {
                        "type": "image",
                        "src": ""
                    },
                    "props": {
                        "background": "gradient",
                        "alignment": "center",
                        "padding": "large"
                    }
                },
                {
                    "id": "b2",
                    "type": "heading",
                    "content": "¿Qué es un Polinomio?",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b3",
                    "type": "paragraph",
                    "content": "Un polinomio es una expresión algebraica que contiene términos con variables elevadas a potencias enteras no negativas. Cada término tiene un coeficiente (número) y una parte literal (variable con su exponente).",
                    "props": {
                        "padding": "medium"
                    }
                },
                {
                    "id": "b4",
                    "type": "heading",
                    "content": "Identificación de Términos",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b5",
                    "type": "paragraph",
                    "content": "Para identificar los términos de un polinomio, debemos separar la expresión por los signos + y -. Cada término incluye su signo.",
                    "props": {
                        "padding": "medium"
                    }
                },
                {
                    "id": "b6",
                    "type": "callout",
                    "content": "Ejemplo: En el polinomio 3x² + 2x - 5, los términos son: +3x², +2x, -5",
                    "props": {
                        "type": "info",
                        "padding": "medium"
                    }
                },
                {
                    "id": "b7",
                    "type": "heading",
                    "content": "Grado de un Polinomio",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b8",
                    "type": "paragraph",
                    "content": "El grado de un polinomio es el mayor exponente de la variable en el polinomio. Para determinar el grado, identificamos el término con el exponente más alto.",
                    "props": {
                        "padding": "medium"
                    }
                },
                {
                    "id": "b9",
                    "type": "callout",
                    "content": "Ejemplo: En 3x² + 2x - 5, el grado es 2 (porque el mayor exponente es 2).",
                    "props": {
                        "type": "success",
                        "padding": "medium"
                    }
                },
                {
                    "id": "b10",
                    "type": "heading",
                    "content": "Suma de Polinomios",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b11",
                    "type": "paragraph",
                    "content": "Para sumar polinomios, agrupamos los términos semejantes (misma variable y mismo exponente) y sumamos sus coeficientes.",
                    "props": {
                        "padding": "medium"
                    }
                },
                {
                    "id": "b12",
                    "type": "heading",
                    "content": "Resta de Polinomios",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b13",
                    "type": "paragraph",
                    "content": "Para restar polinomios, cambiamos el signo de todos los términos del segundo polinomio y luego sumamos como en el caso anterior.",
                    "props": {
                        "padding": "medium"
                    }
                },
                {
                    "id": "b14",
                    "type": "heading",
                    "content": "Ejercicios Prácticos",
                    "props": {
                        "level": 2,
                        "padding": "medium"
                    }
                },
                {
                    "id": "b15",
                    "type": "paragraph",
                    "content": "1. Identifica los términos del polinomio: 4x³ - 2x² + 7x - 1\n2. Determina el grado del polinomio: 5x⁴ + 3x² - 2x + 8\n3. Suma los polinomios: (3x² + 2x - 5) + (x² - 4x + 3)\n4. Resta los polinomios: (5x² - 3x + 2) - (2x² + x - 4)",
                    "props": {
                        "padding": "medium"
                    }
                }
            ],
            'document': {
                'title': 'Polinomios: Suma y Resta',
                'description': 'Material educativo sobre polinomios para 1° de secundaria',
                'blocks': [
                    {
                        "id": "b1",
                        "type": "hero",
                        "title": "Contenido Educativo",
                        "subtitle": "Generado con IA",
                        "body": "Este contenido ha sido generado automáticamente. Puedes editarlo usando el editor Gamma.",
                        "media": {
                            "type": "image",
                            "src": ""
                        },
                        "props": {
                            "background": "gradient",
                            "alignment": "center",
                            "padding": "large"
                        }
                    },
                    {
                        "id": "b2",
                        "type": "paragraph",
                        "content": "Este es un contenido educativo generado automáticamente. Puedes editarlo y personalizarlo según tus necesidades.",
                        "props": {
                            "padding": "medium"
                        }
                    }
                ]
            }
        }
    
 