from django.contrib import admin
from .models import Institution, Term, GradeLevel


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'email', 'phone', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'code', 'email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code')
        }),
        ('Contacto', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active', 'institution', 'start_date']
    search_fields = ['name', 'institution__name']
    date_hierarchy = 'start_date'
    ordering = ['-start_date']


@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'institution']
    list_filter = ['institution', 'level']
    search_fields = ['name', 'institution__name']
    ordering = ['institution', 'level']
