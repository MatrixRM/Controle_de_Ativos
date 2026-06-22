import logging
from datetime import date, timedelta
from django.db.models import F
from .models import ItemEstoque, Equipamento, Manutencao, Notificacao

logger = logging.getLogger(__name__)


def verificar_estoque_baixo():
    itens = ItemEstoque.objects.filter(quantidade__lt=F('quantidade_minima'))
    criadas = 0
    for item in itens:
        _, created = Notificacao.objects.get_or_create(
            tipo='ESTOQUE_BAIXO',
            mensagem=f'{item.nome} ({item.get_categoria_display()}): {item.quantidade} unidades (mínimo {item.quantidade_minima})',
            link='/estoque/',
        )
        if created:
            criadas += 1
    return criadas


def verificar_garantia_proxima():
    hoje = date.today()
    limite = hoje + timedelta(days=30)
    qs = Equipamento.objects.filter(garantia_ate__gte=hoje, garantia_ate__lte=limite)
    criadas = 0
    for eq in qs:
        dias = (eq.garantia_ate - hoje).days
        _, created = Notificacao.objects.get_or_create(
            tipo='GARANTIA_PROXIMA',
            mensagem=f'{eq.numero_imobilizado} ({eq.marca} {eq.modelo}): garantia vence em {dias} dia(s)',
            link=f'/equipamentos/{eq.pk}/',
        )
        if created:
            criadas += 1
    return criadas


def verificar_manutencao_atrasada():
    limite = date.today() - timedelta(days=7)
    qs = Manutencao.objects.filter(
        status__in=['ABERTA', 'EM_ANDAMENTO'],
        data_abertura__lt=limite,
    ).select_related('equipamento', 'tecnico')
    criadas = 0
    for m in qs:
        dias = (date.today() - m.data_abertura).days
        tecnico = m.tecnico.get_full_name() or m.tecnico.username if m.tecnico else '\u2014'
        _, created = Notificacao.objects.get_or_create(
            tipo='MANUTENCAO_ATRASADA',
            mensagem=f'Manuten\u00e7\u00e3o #{m.id} \u2014 {m.equipamento.numero_imobilizado}: {dias} dia(s) em aberto (t\u00e9cnico: {tecnico})',
            link=f'/manutencoes/',
        )
        if created:
            criadas += 1
    return criadas


def executar_todas():
    total = 0
    total += verificar_estoque_baixo()
    total += verificar_garantia_proxima()
    total += verificar_manutencao_atrasada()
    return total
