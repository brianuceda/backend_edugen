from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse, FileResponse
from django.conf import settings
import os
import tempfile
from .services import SCORMPackager
from ai_content_generator.models import GeneratedContent

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def export_content_as_scorm(request):
    """Exporta contenido generado como paquete SCORM"""
    content_id = request.data.get('content_id')
    
    if not content_id:
        return Response({
            'error': 'content_id es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Obtener el contenido generado
        content = GeneratedContent.objects.get(id=content_id, conversation__user=request.user)
        
        # Preparar datos del contenido
        content_data = {
            'title': content.title,
            'description': content.description,
            'blocks': []
        }
        
        # Si tiene bloques Gamma, usarlos
        if content.gamma_blocks:
            content_data['blocks'] = content.gamma_blocks
        elif content.gamma_document and content.gamma_document.get('blocks'):
            content_data['blocks'] = content.gamma_document['blocks']
        else:
            # Crear un bloque básico si no hay bloques Gamma
            content_data['blocks'] = [{
                'id': 'b1',
                'type': 'paragraph',
                'content': content.html_content or 'Contenido no disponible'
            }]
        
        # Crear paquete SCORM
        packager = SCORMPackager()
        zip_path = packager.create_scorm_package(content_data, content.title)
        
        # Preparar respuesta con el archivo ZIP
        zip_filename = f"{content.title.replace(' ', '_')}_scorm.zip"
        
        def file_generator():
            with open(zip_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
            # Limpiar archivos temporales
            try:
                os.unlink(zip_path)
                import shutil
                shutil.rmtree(os.path.dirname(zip_path), ignore_errors=True)
            except Exception:
                pass  # Ignorar errores de limpieza
        
        # Obtener el tamaño del archivo antes de crear la respuesta
        file_size = os.path.getsize(zip_path)
        
        response = HttpResponse(file_generator(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = file_size
        
        return response
        
    except GeneratedContent.DoesNotExist:
        return Response({
            'error': 'Contenido no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"SCORM Export Error: {str(e)}")
        print(f"Traceback: {error_details}")
        return Response({
            'error': f'Error al generar paquete SCORM: {str(e)}',
            'details': error_details
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview_scorm_content(request, content_id):
    """Vista previa del contenido SCORM sin empaquetar"""
    try:
        content = GeneratedContent.objects.get(id=content_id, conversation__user=request.user)
        
        # Preparar datos del contenido
        content_data = {
            'title': content.title,
            'description': content.description,
            'blocks': []
        }
        
        # Si tiene bloques Gamma, usarlos
        if content.gamma_blocks:
            content_data['blocks'] = content.gamma_blocks
        elif content.gamma_document and content.gamma_document.get('blocks'):
            content_data['blocks'] = content.gamma_document['blocks']
        else:
            # Crear un bloque básico si no hay bloques Gamma
            content_data['blocks'] = [{
                'id': 'b1',
                'type': 'paragraph',
                'content': content.html_content or 'Contenido no disponible'
            }]
        
        # Generar HTML del contenido
        packager = SCORMPackager()
        html_content = packager._generate_html_content(content_data, content.title)
        
        # Crear HTML completo para vista previa
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vista Previa: {content.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .preview-container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .preview-header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #667eea; }}
        .preview-header h1 {{ color: #333; margin-bottom: 10px; }}
        .preview-header p {{ color: #666; }}
        .export-button {{ text-align: center; margin: 30px 0; }}
        .export-button button {{ background: #667eea; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }}
        .export-button button:hover {{ background: #5a6fd8; }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-header">
            <h1>Vista Previa del Contenido SCORM</h1>
            <p><strong>Título:</strong> {content.title}</p>
            <p><strong>ID:</strong> {content.id} | <strong>Fecha:</strong> {content.created_at.strftime('%d/%m/%Y')}</p>
        </div>
        
        <div class="export-button">
            <button onclick="exportAsSCORM()">📦 Exportar como SCORM</button>
        </div>
        
        {html_content}
    </div>
    
    <script>
        function exportAsSCORM() {{
            // Crear formulario para enviar POST request
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/api/v1/scorm/export/';
            
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'content_id';
            input.value = '{content_id}';
            
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
        }}
    </script>
</body>
</html>"""
        
        return HttpResponse(full_html, content_type='text/html')
        
    except GeneratedContent.DoesNotExist:
        return Response({
            'error': 'Contenido no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error al generar vista previa: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
