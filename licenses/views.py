from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from .models import License, Cliente
from django.db.models import Q, Exists, OuterRef, Subquery
from .serializers import LicenseSerializer
from django.utils import timezone
from datetime import timedelta, datetime as dt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse




class LicenseViewSet(viewsets.ModelViewSet):
    queryset = License.objects.all()
    serializer_class = LicenseSerializer

    @action(detail=False, methods=['post'])
    def validate(self, request):
        key = request.data.get('key')
        device_id = request.data.get('device_id')  # opcional
        try:
            lic = License.objects.get(key=key, is_active=True)
            if lic.expires_at < timezone.now():
                lic.is_active = False
                lic.save()
                return Response({'valid': False, 'msg': 'Expirada'})
            # Controle simples de dispositivos
            if lic.used_devices >= lic.max_devices:
                return Response({'valid': False, 'msg': 'Limite de dispositivos'})
            return Response({'valid': True, 'expires_at': lic.expires_at})
        except License.DoesNotExist:
            return Response({'valid': False, 'msg': 'Inválida'}, status=404)



# licenses/views.py (API)
@api_view(['GET'])
def verificar_licenca(request):
    cliente_id = request.GET.get('cliente')
    chave = request.GET.get('chave')
    
    try:
        lic = License.objects.get(key=chave, cliente_id=cliente_id, is_active=True)
        if lic.expires_at < timezone.now():
            return Response({"status": "inativo", "mensagem": "Licença expirada"})
        
        return Response({
            "status": "ativo",
            "mensagem": "Licença válida",
            "validade": lic.expires_at.strftime("%d/%m/%Y"),
            "nome_cliente": lic.cliente.nome_completo  # ← NOVO
        })
    except License.DoesNotExist:
        return Response({"status": "inativo", "mensagem": "Licença inválida"})          



def admin_clientes(request):
    if not request.user.is_superuser:
        return redirect('/admin/')

    query = request.GET.get('q', '').strip()

    # 1. Base de clientes
    clientes = Cliente.objects.all().order_by('-criado_em')

    # 2. APLICAR FILTRO DE BUSCA PRIMEIRO
    if query:
        clientes = clientes.filter(
            Q(nome_completo__icontains=query) |
            Q(email__icontains=query) |
            Q(telefone__icontains=query)
        )

    # 3. APÓS O FILTRO → ANOTAR com licença ativa
    licenca_mais_longa = License.objects.filter(
        cliente=OuterRef('pk'),
        is_active=True
    ).order_by('-data_fim').values('data_fim')[:1]

    clientes = clientes.annotate(
        licenca_ativa=Exists(
            License.objects.filter(cliente=OuterRef('pk'), is_active=True)
        ),
        licenca_expiracao=Subquery(licenca_mais_longa)
    )

    return render(request, 'admin_clientes.html', {
        'clientes': clientes,
        'query': query
    })

# View dedicada para criar cliente
def criar_cliente(request):
    if not request.user.is_superuser:
        return redirect('/admin/')

    if request.method == 'POST':
        nome = request.POST['nome_completo'].strip()
        email = request.POST.get('email', '').strip()
        tel = request.POST.get('telefone', '').strip()

        if not nome:
            messages.error(request, "Nome completo é obrigatório.")
        else:
            Cliente.objects.create(
                nome_completo=nome,
                email=email,
                telefone=tel
            )
            messages.success(request, f"Cliente '{nome}' criado com sucesso!")
            return redirect('admin_clientes')

    return render(request, 'cliente_criar.html')



def gerenciar_clientes(request):
    query = request.GET.get("q", "")

    # Subqueries para pegar dados da licença mais recente
    licenca_sub = License.objects.filter(cliente=OuterRef('pk')).order_by('-data_inicio')

    clientes = (
        Cliente.objects.all()
        .annotate(
            licenca_chave=Subquery(licenca_sub.values('key')[:1]),
            licenca_status=Subquery(licenca_sub.values('is_active')[:1]),
            licenca_expira_em=Subquery(licenca_sub.values('expires_at')[:1]),
        )
    )

    if query:
        clientes = clientes.filter(
            nome_completo__icontains=query
        ) | clientes.filter(
            email__icontains=query
        ) | clientes.filter(
            telefone__icontains=query
        )

    # Convertendo o status booleano para texto antes de mandar ao template
    for c in clientes:
        if c.licenca_status is True:
            c.licenca_status = "Ativo"
        elif c.licenca_status is False:
            c.licenca_status = "Expirado"
        else:
            c.licenca_status = None

    return render(request, "admin_clientes.html", {"clientes": clientes, "query": query})


def admin_licensas(request):
    if not request.user.is_superuser:
        return redirect('/admin/')

    if request.method == 'POST' and request.POST.get('acao') == 'criar':
        cliente_id = request.POST.get('cliente_id')
        dias = int(request.POST.get('dias', 365))
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            License.objects.create(
                cliente=cliente,
                expires_at=timezone.now() + timedelta(days=dias)
            )
            messages.success(request, f"Licença criada para {cliente.nome_completo}")
        except Cliente.DoesNotExist:
            messages.error(request, "Cliente inválido.")
        return redirect('admin_licensas')

    # ADIÇÃO: Verifica e desativa licenças expiradas
    expiradas = 0
    for lic in License.objects.select_related('cliente').all():
        if lic.data_fim and lic.data_fim < timezone.now() and lic.is_active:
            lic.is_active = False
            lic.save()
            expiradas += 1
    if expiradas:
        messages.warning(request, f"{expiradas} licença(s) expirada(s) foram desativadas automaticamente.")

    licenses = License.objects.select_related('cliente').all()
    clientes = Cliente.objects.all().order_by('nome_completo')

    return render(request, 'admin_licensas.html', {
        'licenses': licenses,
        'clientes': clientes
    })

def criar_licenca(request):
    clientes = Cliente.objects.all().order_by('nome_completo')

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        dias = int(request.POST.get('dias', 365))
        max_devices = int(request.POST.get('max_devices', 1))

        cliente = Cliente.objects.filter(id=cliente_id).first()
        if not cliente:
            messages.error(request, "Cliente não encontrado.")
            return redirect('criar_licenca')

        data_inicio = timezone.now()
        data_fim = data_inicio + timedelta(days=dias)

        licenca = License.objects.create(
            cliente=cliente,
            data_inicio=data_inicio,
            data_fim=data_fim,
            expires_at=data_fim,
            max_devices=max_devices,
            used_devices=0,
            is_active=True
        )

        messages.success(request, f"Licença criada com sucesso para {cliente.nome_completo}!")
        return redirect('listar_licencas')

    return render(request, 'licenca_criar.html', {'clientes': clientes})

def editar_licenca(request, pk):
    if not request.user.is_superuser:
        return redirect('/admin/')
    
    licenca = get_object_or_404(License, pk=pk)
    
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente_id')
            data_inicio_str = request.POST.get('data_inicio')
            data_fim_str = request.POST.get('data_fim')
            max_devices = int(request.POST.get('max_devices', 1))
            used_devices = int(request.POST.get('used_devices', 0))
            is_active = request.POST.get('is_active') == 'on'

            # Validações
            if used_devices > max_devices:
                messages.error(request, "Dispositivos usados não pode exceder o máximo.")
                return redirect('editar_licenca', pk=pk)

            # Cliente
            cliente = Cliente.objects.get(id=cliente_id)

            # Converte datas com fuso (UTC)
            data_inicio = dt.strptime(data_inicio_str, '%Y-%m-%dT%H:%M')
            data_inicio = timezone.make_aware(data_inicio)  # ← ADICIONA FUSO

            if data_fim_str:
                data_fim = dt.strptime(data_fim_str, '%Y-%m-%dT%H:%M')
                data_fim = timezone.make_aware(data_fim)  # ← ADICIONA FUSO
            else:
                data_fim = data_inicio + timedelta(days=365)

            # Atualiza campos
            licenca.cliente = cliente
            licenca.data_inicio = data_inicio
            licenca.data_fim = data_fim
            licenca.expires_at = data_fim
            licenca.max_devices = max_devices
            licenca.used_devices = used_devices
            licenca.is_active = is_active  # ← será sobrescrito se expirada

            # Salva (o model desativa se expirada)
            licenca.save()

            messages.success(request, "Licença atualizada com sucesso!")
            return redirect('admin_licensas')  # ← corrigido: era 'admin_licensas'

        except Exception as e:
            messages.error(request, f"Erro ao salvar: {e}")
    
    clientes = Cliente.objects.all().order_by('nome_completo')
    return render(request, 'licenca_editar.html', {
        'licenca': licenca,
        'clientes': clientes
    })

def desativar_licenca(request, pk):
    if not request.user.is_superuser:
        return redirect('/admin/')
    
    licenca = get_object_or_404(License, pk=pk)
    if request.method == 'POST':
        licenca.is_active = False
        licenca.save()
        messages.success(request, f"Licença de {licenca.cliente.nome_completo} desativada.")
    return redirect('admin_licensas')

def excluir_licenca(request, pk):
    if not request.user.is_superuser:
        return redirect('/admin/')
    
    licenca = get_object_or_404(License, pk=pk)
    if request.method == 'POST':
        nome = licenca.cliente.nome_completo
        licenca.delete()
        messages.success(request, f"Licença de {nome} excluída permanentemente.")
    return redirect('admin_licensas')


def listar_licencas(request):
    licencas = License.objects.all().order_by('-data_inicio')
    return render(request, 'listar_licencas.html', {'licencas': licencas})    


def admin_licencas(request):
    return render(request, 'admin_licensas.html')    


def cadastrar_clientes(request):
    return render(request, 'cliente_criar.html')

def admin_clientes(request):
    return render(request, 'admin_clientes.html')    



def verificar_licenca(request):
    cliente = request.GET.get("cliente")
    chave = request.GET.get("chave")

    if not cliente or not chave:
        return JsonResponse({"status": "erro", "mensagem": "Parâmetros ausentes"}, status=400)

    try:
        licenca = License.objects.select_related("cliente").get(key=chave, cliente__id=cliente)
    except License.DoesNotExist:
        return JsonResponse({
            "status": "inativo",
            "mensagem": "Licença não encontrada"
        }, status=404)

    # Data de validade
    validade_str = licenca.data_fim.strftime("%d/%m/%Y") if licenca.data_fim else None

    # Verifica se está inativa
    if not licenca.is_active:
        return JsonResponse({
            "status": "inativo",
            "mensagem": "Licença inativa",
            "validade": validade_str,
            "nome_cliente": licenca.cliente.nome_completo if licenca.cliente else ""
        })

    # Verifica expiração
    if licenca.data_fim and timezone.now() > licenca.data_fim:
        licenca.is_active = False
        licenca.save()
        return JsonResponse({
            "status": "inativo",
            "mensagem": "Licença expirada",
            "validade": validade_str,
            "nome_cliente": licenca.cliente.nome_completo if licenca.cliente else ""
        })

    # Licença ativa e válida
    return JsonResponse({
        "status": "ativo",
        "mensagem": f"Licença válida para {licenca.cliente.nome_completo}",
        "validade": validade_str,
        "nome_cliente": licenca.cliente.nome_completo if licenca.cliente else ""
    })