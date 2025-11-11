from rest_framework.decorators import api_view
from rest_framework.response import Response
from licenses.models import Cliente

@api_view(['GET'])
def cliente_detalhe(request, pk):
    try:
        cliente = Cliente.objects.get(pk=pk)
        return Response({"nome_completo": cliente.nome_completo})
    except Cliente.DoesNotExist:
        return Response({"nome_completo": ""}, status=404)



@api_view(['GET'])
def verificar_licenca(request):
    cliente_id = request.GET.get('cliente')
    chave = request.GET.get('chave')
    
    try:
        lic = License.objects.get(key=chave, cliente_id=cliente_id)
        
        # Verifica se expirou
        expirada = lic.data_fim and lic.data_fim < timezone.now()
        ativa = lic.is_active and not expirada

        return Response({
            "status": "ativo" if ativa else "inativo",
            "mensagem": "Licença válida" if ativa else ("Licença expirada" if expirada else "Licença desativada"),
            "validade": lic.data_fim.strftime("%d/%m/%Y") if lic.data_fim else "",
            "nome_cliente": lic.cliente.nome_completo if lic.cliente else ""
        })
    except License.DoesNotExist:
        return Response({
            "status": "inativo",
            "mensagem": "Licença inválida"
        })        