"""
URL configuration for license_control project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from licenses import views  # ✅ CORRIGIDO
from django.contrib import admin
from django.views.generic import TemplateView
from licenses.views import LicenseViewSet  # se estiver usando o viewset
from licenses.api import cliente_detalhe

router = DefaultRouter()
router.register(r'licenses', LicenseViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('', TemplateView.as_view(template_name='index.html')),
    path('home/', TemplateView.as_view(template_name='index.html'), name='home'),

    path('api/verificar_licenca', views.verificar_licenca),
    path('licencas/', views.admin_licensas, name='admin_licensas'),
    path('clientes2/', views.admin_clientes, name='admin_clientes'),
    path('clientes/criar/', views.criar_cliente, name='criar_cliente'),
    path('clientes/cadastrar/', views.cadastrar_clientes, name='cadastrar_clientes'),
    path('clientes/', views.gerenciar_clientes, name='gerenciar_clientes'),
    path('licencas/criar/', views.criar_licenca, name='criar_licenca'),
    path('listar/', views.listar_licencas, name='listar_licencas'),
    #path('editar/<int:id>/', views.editar_licenca, name='editar_licenca'),
    #path('excluir/<int:id>/', views.excluir_licenca, name='excluir_licenca'),

    path("api/verificar_licenca", views.verificar_licenca, name="verificar_licenca"),
    path('api/cliente/<int:pk>/', cliente_detalhe, name='cliente_detalhe'),
    path('licencas/editar/<int:pk>/', views.editar_licenca, name='editar_licenca'),
    path('licencas/desativar/<int:pk>/', views.desativar_licenca, name='desativar_licenca'),
    path('licencas/excluir/<int:pk>/', views.excluir_licenca, name='excluir_licenca'),

]



