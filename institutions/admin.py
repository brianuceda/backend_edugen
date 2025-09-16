from django.contrib import admin
from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'email', 'phone']
    search_fields = ['name', 'code', 'email']
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code')
        }),
        ('Contacto', {
            'fields': ('address', 'phone', 'email')
        }),
    )
