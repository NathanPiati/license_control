from django.contrib import admin
from .models import Cliente, License

# Register your models here.
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'email', 'telefone', 'criado_em')
    search_fields = ('nome_completo', 'email')

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('key', 'cliente', 'expires_at', 'is_active')
    list_filter = ('is_active',)