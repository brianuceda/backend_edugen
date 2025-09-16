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
    
    def chat_with_user(self, messages: List[Dict[str, str]], context: Optional[str] = None) -> Dict[str, Any]:
        """Maneja la conversación con el usuario usando DeepSeek"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construir el prompt del sistema para recolección de información
        system_prompt = self.get_collection_system_prompt()
        
        # Agregar contexto si existe
        if context:
            system_prompt += f"\n\nContexto actual: {context}"
        
        # Analizar el contexto para evitar preguntas redundantes
        context_analysis = self.analyze_context(messages)
        if context_analysis:
            system_prompt += f"\n\nInformación ya disponible: {context_analysis}"
        
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
            "max_tokens": 1000,  # Reducido para respuestas más concisas
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
    
    def get_collection_system_prompt(self) -> str:
        """Obtiene el prompt del sistema para recolección de información"""
        return """
        Eres un asistente especializado en recolección de información para crear contenido educativo interactivo con GrapesJS.
        
        REGLAS IMPORTANTES:
        1. NO hagas preguntas obvias o redundantes
        2. Analiza el contexto antes de preguntar
        3. Si el usuario ya mencionó información, NO la preguntes de nuevo
        4. Sé inteligente y deduce información cuando sea posible
        5. Haz solo preguntas esenciales que realmente necesites
        
        INFORMACIÓN A RECOLECTAR (solo si no está clara):
        - Nivel del curso (solo si no es obvio del contexto)
        - Materia o tema específico (solo si no está claro)
        - Tipo de contenido educativo (lección, ejercicio, evaluación, etc.)
        - Objetivos de aprendizaje específicos
        - Duración estimada del contenido
        - Estilo visual (solo si es relevante para el contenido)
        - Secciones necesarias (solo si no son obvias)
        - Recursos necesarios (solo si son específicos)
        
        EJEMPLOS DE PREGUNTAS INTELIGENTES:
        ✅ "¿Qué objetivos específicos quieres que logren los estudiantes?"
        ✅ "¿Qué tipo de ejercicios prefieres incluir?"
        ❌ "¿Para qué nivel educativo va dirigido?" (si ya mencionó "secundaria")
        ❌ "¿Qué estilo visual prefieres?" (si no es relevante)
        
        ESTRATEGIA:
        1. Analiza lo que el usuario ya dijo
        2. Identifica qué información falta realmente
        3. Haz solo 1-2 preguntas esenciales por mensaje
        4. Si tienes suficiente información, confirma y procede
        
        Mantén un tono amigable y profesional. Responde siempre en español.
        """
    
    def get_generation_system_prompt(self) -> str:
        """Obtiene el prompt del sistema para generación de contenido educativo"""
        return """
        Eres un experto en educación y diseño de contenido educativo. Tu especialidad es crear contenido RICO EN TEXTO, SIMPLE y ORDENADO.
        
        INSTRUCCIONES IMPORTANTES:
        - ENFOQUE PRINCIPAL: Contenido educativo RICO EN TEXTO y bien estructurado
        - Diseño SIMPLE, LIMPIO y ORDENADO - evita complejidad visual
        - Máximo 4-5 secciones principales (introducción, desarrollo, ejercicios, evaluación)
        - CSS MÍNIMO y funcional - solo lo esencial para legibilidad
        - JavaScript BÁSICO - solo para funcionalidades educativas esenciales
        - Compatible con GrapesJS
        - Diseño responsive para dispositivos móviles
        - PRIORIZA EL CONTENIDO EDUCATIVO sobre el diseño visual
        - Usa tipografía clara y colores suaves
        - Estructura clara y fácil de seguir
        
        OBJETIVO: Crear contenido educativo que sea FÁCIL DE LEER, COMPRENDER y EDITAR.
        
        Formato de respuesta:
        ```html
        [HTML semántico con CONTENIDO EDUCATIVO RICO EN TEXTO]
        ```
        
        ```css
        [CSS SIMPLE y LIMPIO - solo lo esencial]
        ```
        
        ```javascript
        [JavaScript BÁSICO para funcionalidades educativas]
        ```
        
        Responde siempre en español.
        """
    
    def extract_requirements(self, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Extrae los requisitos de la conversación usando DeepSeek"""
        extraction_prompt = """
        Analiza la siguiente conversación y extrae los requisitos del usuario para crear contenido educativo interactivo.
        
        INSTRUCCIONES:
        1. Extrae SOLO la información que está explícitamente mencionada
        2. NO inventes información que no esté en la conversación
        3. Si falta información importante, marca "is_complete": false
        4. Si hay suficiente información para generar contenido, marca "is_complete": true
        5. Para "missing_info", incluye solo información realmente necesaria
        
        Devuelve SOLO un JSON válido con la siguiente estructura:
        {
            "course_level": "básico/intermedio/avanzado" (solo si se menciona),
            "subject": "materia o tema específico",
            "content_type": "tipo de contenido educativo",
            "learning_objectives": ["objetivo1", "objetivo2"],
            "duration": "duración estimada" (solo si se menciona),
            "style": "estilo visual" (solo si se menciona),
            "colors": ["color1", "color2"] (solo si se mencionan),
            "sections": ["introducción", "desarrollo", "ejercicios", "evaluación"],
            "interactive_elements": ["quiz", "ejercicios", "videos", "animaciones"] (solo si se mencionan),
            "target_audience": "público objetivo" (solo si se menciona),
            "resources": ["imágenes", "videos", "audios"] (solo si se mencionan),
            "responsive": true/false (por defecto true),
            "is_complete": true/false,
            "missing_info": ["información realmente faltante y necesaria"]
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
                return json.loads(json_match.group())
        except Exception as e:
            pass
        
        return None
    
    def analyze_context(self, messages: List[Dict[str, str]]) -> str:
        """Analiza el contexto de la conversación para identificar información ya disponible"""
        context_info = []
        
        # Analizar mensajes del usuario para extraer información clave
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                
                # Detectar nivel educativo
                if any(level in content for level in ['secundaria', 'básico', 'intermedio', 'avanzado', 'universidad', 'primaria']):
                    if 'secundaria' in content or 'básico' in content:
                        context_info.append("Nivel educativo: secundaria/básico")
                    elif 'intermedio' in content:
                        context_info.append("Nivel educativo: intermedio")
                    elif 'avanzado' in content or 'universidad' in content:
                        context_info.append("Nivel educativo: avanzado/universidad")
                
                # Detectar materia o tema
                subjects = ['matemáticas', 'ciencias', 'historia', 'geografía', 'literatura', 'física', 'química', 'biología', 'inglés', 'español']
                for subject in subjects:
                    if subject in content:
                        context_info.append(f"Materia: {subject}")
                        break
                
                # Detectar tipo de contenido
                content_types = ['lección', 'ejercicio', 'evaluación', 'presentación', 'taller', 'práctica']
                for content_type in content_types:
                    if content_type in content:
                        context_info.append(f"Tipo de contenido: {content_type}")
                        break
                
                # Detectar objetivos de aprendizaje
                if 'objetivo' in content or 'aprender' in content or 'lograr' in content:
                    context_info.append("Objetivos de aprendizaje mencionados")
                
                # Detectar duración
                if any(duration in content for duration in ['minutos', 'horas', 'sesión', 'clase']):
                    context_info.append("Duración mencionada")
                
                # Detectar estilo visual
                if any(style in content for style in ['moderno', 'clásico', 'colorido', 'minimalista', 'formal']):
                    context_info.append("Estilo visual mencionado")
        
        return "; ".join(context_info) if context_info else ""
    
    def generate_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido HTML/CSS/JS basado en los requisitos"""
        
        # Por ahora usar solo el fallback hasta que se resuelva el problema de la API
        return self.generate_fallback_content(requirements)
        
        # TODO: Restaurar la llamada a la API cuando se resuelva el problema de conectividad
        # try:
        #     print(f"Calling DeepSeek API...")
        #     response = self.generate_content_with_limits([
        #         {"role": "user", "content": generation_prompt}
        #     ])
        #     print(f"DeepSeek API response received")
        #     
        #     if 'choices' not in response or len(response['choices']) == 0:
        #         raise Exception("No choices in DeepSeek response")
        #     
        #     content = response['choices'][0]['message']['content']
        #     print(f"Generated content length: {len(content)}")
        #     
        #     # Extraer HTML, CSS y JS de la respuesta
        #     parsed_content = self.parse_generated_content(content)
        #     print(f"Parsed content - HTML: {len(parsed_content.get('html', ''))}, CSS: {len(parsed_content.get('css', ''))}, JS: {len(parsed_content.get('js', ''))}")
        #     
        #     return parsed_content
        # except Exception as e:
        #     print(f"Error in generate_content: {str(e)}")
        #     print("Falling back to basic content generation...")
        #     return self.generate_fallback_content(requirements)
    
    def generate_content_with_limits(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Genera contenido con límites estrictos de tokens para respuesta rápida"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": self.get_generation_system_prompt()}
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
            "temperature": 0.5,  # Menor temperatura para respuestas más determinísticas
            "max_tokens": 1000,  # Reducido aún más para respuesta más rápida
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=10
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
    
    def build_generation_prompt(self, requirements: Dict[str, Any]) -> str:
        """Construye el prompt para generar contenido educativo"""
        # Asegurar que los campos sean listas válidas
        learning_objectives = requirements.get('learning_objectives', [])
        if not isinstance(learning_objectives, list):
            learning_objectives = []
        
        colors = requirements.get('colors', ['azul', 'blanco'])
        if not isinstance(colors, list):
            colors = ['azul', 'blanco']
            
        sections = requirements.get('sections', ['introducción', 'desarrollo', 'ejercicios'])
        if not isinstance(sections, list):
            sections = ['introducción', 'desarrollo', 'ejercicios']
            
        interactive_elements = requirements.get('interactive_elements', [])
        if not isinstance(interactive_elements, list):
            interactive_elements = []
        
        return f"""
        Genera contenido educativo RICO EN TEXTO, SIMPLE y ORDENADO basado en estos requisitos:
        
        Nivel del curso: {requirements.get('course_level', 'básico')}
        Materia: {requirements.get('subject', 'general')}
        Tipo de contenido: {requirements.get('content_type', 'lección')}
        Objetivos de aprendizaje: {', '.join(learning_objectives)}
        Duración: {requirements.get('duration', '30 minutos')}
        Estilo: {requirements.get('style', 'simple y ordenado')}
        Colores: {', '.join(colors)}
        Secciones: {', '.join(sections)}
        Elementos interactivos: {', '.join(interactive_elements)}
        Público objetivo: {requirements.get('target_audience', 'estudiantes')}
        
        REQUISITOS ESPECÍFICOS:
        - HTML semántico con CONTENIDO EDUCATIVO RICO EN TEXTO (máximo 5 secciones)
        - CSS SIMPLE y LIMPIO - solo lo esencial para legibilidad
        - JavaScript BÁSICO - solo para funcionalidades educativas esenciales
        - Diseño responsive para dispositivos móviles
        - Compatible con GrapesJS
        - PRIORIZA EL CONTENIDO EDUCATIVO sobre el diseño visual
        - Usa tipografía clara y colores suaves
        - Estructura clara y fácil de seguir
        
        IMPORTANTE: Genera contenido que sea FÁCIL DE LEER, COMPRENDER y EDITAR.
        El profesor editará el contenido después, así que enfócate en una base sólida educativa.
        """
    
    def generate_content_with_streaming(self, requirements: Dict[str, Any], progress_callback=None):
        """Genera contenido educativo con streaming para mostrar progreso"""
        system_prompt = self.get_generation_system_prompt()
        generation_prompt = self.build_generation_prompt(requirements)
        
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": generation_prompt}
        ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.5,
            "max_tokens": 3000,
            "stream": True
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            full_content = ""
            total_chunks = 0
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_content += content
                                    total_chunks += 1
                                    
                                    # Llamar callback de progreso si existe
                                    if progress_callback:
                                        # Simular progreso basado en chunks recibidos
                                        progress = min(95, (total_chunks * 2))  # Máximo 95% hasta completar
                                        progress_callback(progress, content)
                        except json.JSONDecodeError:
                            continue
            
            # Simular los últimos 5% del progreso
            if progress_callback:
                import time
                for i in range(5):
                    progress_callback(95 + i, "")
                    time.sleep(0.1)
                progress_callback(100, "")
            
            # Parsear el contenido generado
            parsed_content = self.parse_generated_content(full_content)
            return parsed_content
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
    
    def parse_generated_content(self, content: str) -> Dict[str, str]:
        """Parsea el contenido generado para extraer HTML, CSS y JS"""
        result = {
            'html': '',
            'css': '',
            'js': ''
        }
        
        # Extraer HTML
        html_match = re.search(r'```html\s*(.*?)\s*```', content, re.DOTALL)
        if html_match:
            result['html'] = html_match.group(1).strip()
        
        # Extraer CSS
        css_match = re.search(r'```css\s*(.*?)\s*```', content, re.DOTALL)
        if css_match:
            result['css'] = css_match.group(1).strip()
        
        # Extraer JavaScript
        js_match = re.search(r'```javascript\s*(.*?)\s*```', content, re.DOTALL)
        if js_match:
            result['js'] = js_match.group(1).strip()
        
        return result
    
    def generate_fallback_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido básico como fallback cuando la API falla"""
        subject = requirements.get('subject', 'Tema General')
        course_level = requirements.get('course_level', 'básico')
        sections = requirements.get('sections', ['introducción', 'desarrollo', 'ejercicios'])
        learning_objectives = requirements.get('learning_objectives', ['Aprender el tema'])
        
        # Generar HTML básico con contenido rico en texto
        html_content = f"""
        <div class="educational-content">
            <header class="content-header">
                <h1>{subject}</h1>
                <p class="course-level">Nivel: {course_level}</p>
            </header>
            
            <main class="content-main">
                <section class="introduction">
                    <h2>Introducción</h2>
                    <p>Bienvenido a esta lección sobre <strong>{subject}</strong>. En esta lección aprenderás los conceptos fundamentales y desarrollarás una comprensión sólida del tema.</p>
                    <p>Los objetivos de aprendizaje de esta lección son:</p>
                    <ul>
                        <li>Comprender los conceptos básicos de {subject}</li>
                        <li>Identificar las características principales</li>
                        <li>Aplicar los conocimientos en situaciones prácticas</li>
                    </ul>
                </section>
                
                <section class="development">
                    <h2>Desarrollo del Tema</h2>
                    <p>En esta sección exploraremos en profundidad los aspectos más importantes de <strong>{subject}</strong>.</p>
                    
                    <h3>Conceptos Fundamentales</h3>
                    <p>Para comprender completamente {subject}, es esencial dominar los siguientes conceptos:</p>
                    <ul>
                        <li><strong>Concepto 1:</strong> Explicación detallada del primer concepto fundamental que forma la base del conocimiento.</li>
                        <li><strong>Concepto 2:</strong> Descripción del segundo concepto que complementa y enriquece la comprensión.</li>
                        <li><strong>Concepto 3:</strong> Análisis del tercer concepto que completa la visión integral del tema.</li>
                    </ul>
                    
                    <h3>Aplicaciones Prácticas</h3>
                    <p>Estos conceptos se aplican en diversas situaciones de la vida real, permitiendo una comprensión más profunda y práctica del tema.</p>
                </section>
                
                <section class="exercises">
                    <h2>Ejercicios de Práctica</h2>
                    <p>Ahora es momento de poner en práctica lo que has aprendido. Completa los siguientes ejercicios:</p>
                    
                    <div class="exercise-item">
                        <h3>Ejercicio 1: Comprensión</h3>
                        <p>Explica con tus propias palabras qué es {subject} y por qué es importante:</p>
                        <textarea placeholder="Escribe tu respuesta aquí..." rows="4"></textarea>
                    </div>
                    
                    <div class="exercise-item">
                        <h3>Ejercicio 2: Análisis</h3>
                        <p>Identifica las características principales de {subject} y explica su relevancia:</p>
                        <textarea placeholder="Describe las características principales..." rows="4"></textarea>
                    </div>
                </section>
                
                <section class="evaluation">
                    <h2>Autoevaluación</h2>
                    <p>Evalúa tu comprensión del tema respondiendo las siguientes preguntas:</p>
                    
                    <div class="quiz-question">
                        <h3>Pregunta 1</h3>
                        <p>¿Cuál es el objetivo principal de estudiar {subject}?</p>
                        <input type="radio" name="q1" value="a"> A) Memorizar información<br>
                        <input type="radio" name="q1" value="b"> B) Comprender conceptos fundamentales<br>
                        <input type="radio" name="q1" value="c"> C) Aprobar un examen<br>
                    </div>
                    
                    <div class="quiz-question">
                        <h3>Pregunta 2</h3>
                        <p>¿Qué aspecto de {subject} te parece más interesante?</p>
                        <input type="radio" name="q2" value="a"> A) Su aplicación práctica<br>
                        <input type="radio" name="q2" value="b"> B) Su fundamento teórico<br>
                        <input type="radio" name="q2" value="c"> C) Su relevancia actual<br>
                    </div>
                </section>
            </main>
        </div>
        """
        
        # Generar CSS simple y limpio
        css_content = """
        .educational-content {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }
        
        .content-header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
        }
        
        .content-header h1 {
            margin: 0 0 10px 0;
            font-size: 2.2em;
            color: #2c3e50;
        }
        
        .course-level {
            margin: 0;
            font-size: 1.1em;
            color: #6c757d;
        }
        
        .content-main section {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
        }
        
        .content-main h2 {
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 1.6em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        .content-main h3 {
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.3em;
        }
        
        .content-main p {
            margin-bottom: 15px;
            text-align: justify;
        }
        
        .content-main ul {
            margin: 15px 0;
            padding-left: 20px;
        }
        
        .content-main li {
            margin-bottom: 8px;
        }
        
        .exercise-item {
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        
        .exercise-item h3 {
            color: #495057;
            margin-top: 0;
            margin-bottom: 10px;
        }
        
        .exercise-item textarea {
            width: 100%;
            margin-top: 10px;
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-family: inherit;
            resize: vertical;
            font-size: 14px;
        }
        
        .quiz-question {
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        
        .quiz-question h3 {
            color: #495057;
            margin-top: 0;
            margin-bottom: 10px;
        }
        
        .quiz-question input[type="radio"] {
            margin-right: 8px;
        }
        
        .quiz-question br {
            margin-bottom: 5px;
        }
        
        @media (max-width: 768px) {
            .educational-content {
                padding: 15px;
            }
            
            .content-header h1 {
                font-size: 1.8em;
            }
            
            .content-main section {
                padding: 15px;
            }
        }
        """
        
        # Generar JavaScript simple
        js_content = """
        document.addEventListener('DOMContentLoaded', function() {
            // Interactividad básica para textareas
            const textareas = document.querySelectorAll('textarea');
            textareas.forEach(textarea => {
                textarea.addEventListener('input', function() {
                    this.style.borderColor = '#3498db';
                });
            });
            
            // Interactividad básica para radio buttons
            const radioButtons = document.querySelectorAll('input[type="radio"]');
            radioButtons.forEach(radio => {
                radio.addEventListener('change', function() {
                    const question = this.closest('.quiz-question');
                    question.style.backgroundColor = '#e8f4f8';
                });
            });
        });
        """
        
        return {
            'html': html_content.strip(),
            'css': css_content.strip(),
            'js': js_content.strip()
        }
