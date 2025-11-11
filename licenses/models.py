import uuid
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Cliente(models.Model):
    nome_completo = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=150, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome_completo

class License(models.Model):
    key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cliente = models.ForeignKey(
        'Cliente',
        on_delete=models.CASCADE,
        related_name='licenses',
        null=True,
        blank=True
    )
    data_inicio = models.DateTimeField(default=timezone.now)
    data_fim = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_devices = models.IntegerField(default=1)
    used_devices = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Garante que data_fim tenha fuso
        if self.data_fim and self.data_fim.tzinfo is None:
            self.data_fim = timezone.make_aware(self.data_fim)

        if self.data_inicio and self.data_inicio.tzinfo is None:
            self.data_inicio = timezone.make_aware(self.data_inicio)

        # Define data_fim se não tiver
        if not self.data_fim:
            self.data_fim = self.data_inicio + timedelta(days=365)

        self.expires_at = self.data_fim

        # Desativa se expirada
        if self.data_fim and self.data_fim < timezone.now():
            self.is_active = False

        super().save(*args, **kwargs)

    def __str__(self):
        status = "ATIVA" if self.is_active else "INATIVA"
        return f"{self.key} - {self.cliente or 'Sem cliente'} ({status})"

    class Meta:
        verbose_name = "Licença"
        verbose_name_plural = "Licenças"
        ordering = ['-data_inicio']
