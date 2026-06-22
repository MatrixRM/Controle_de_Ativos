from django.db.models import F
from .models import ItemEstoque, Notificacao


def alertas_globais(request):
    if request.user.is_authenticated:
        alertas = ItemEstoque.objects.filter(
            quantidade__lt=F('quantidade_minima')
        ).count()
        notificacoes = Notificacao.objects.filter(lida=False).count()
        return {'alertas_estoque': alertas, 'notificacoes_nao_lidas': notificacoes}
    return {'alertas_estoque': 0, 'notificacoes_nao_lidas': 0}
