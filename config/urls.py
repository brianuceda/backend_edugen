"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("api.urls")),
    path("api/v1/accounts/",   include("accounts.urls")),
    path("api/v1/academic/",   include("academic.urls")),
    path("api/v1/portfolio/",  include("portfolios.urls")),
    path("api/v1/institutions/",include("institutions.urls")),
    path("api/v1/analytics/",  include("analytics.urls")),
    path("api/v1/ai/",         include("ai_content_generator.urls")),
    path("api/v1/scorm/",      include("scorm_packager.urls")),
    path("api/v1/dashboard/",  include("dashboard.urls")),
    path("api/v1/director/",   include("director.urls")),
]

# Servir archivos de media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)