from django import template
from django.db.models import F

register = template.Library()

MANUTENCAO_STATUS_CLASSES = {
    'ABERTA': 'bg-danger text-white',
    'EM_ANDAMENTO': 'bg-warning text-dark',
    'CONCLUIDA': 'bg-success text-white',
}

MANUTENCAO_STATUS_LABELS = {
    'ABERTA': 'Aberta',
    'EM_ANDAMENTO': 'Em andamento',
    'CONCLUIDA': 'Concluída',
}

EQUIPAMENTO_STATUS_CLASSES = {
    'ATIVO': 'badge-ativo',
    'OFFLINE': 'badge-offline',
    'EM_MANUTENCAO': 'badge-manutencao',
    'EMPRESTADO': 'badge-emprestado',
    'ESTOQUE': 'badge-estoque',
    'DESCARTADO': 'badge-descartado',
}

EQUIPAMENTO_STATUS_LABELS = {
    'ATIVO': 'Ativo',
    'OFFLINE': 'Offline',
    'EM_MANUTENCAO': 'Em manutenção',
    'EMPRESTADO': 'Emprestado',
    'ESTOQUE': 'Em estoque',
    'DESCARTADO': 'Descartado',
}

MOVIMENTACAO_TIPO_CLASSES = {
    'ENTRADA': 'bg-success text-white',
    'SAIDA': 'bg-danger text-white',
    'TRANSFERENCIA': 'bg-info text-white',
    'AJUSTE': 'bg-secondary text-white',
}

MOVIMENTACAO_TIPO_LABELS = {
    'ENTRADA': 'Entrada',
    'SAIDA': 'Saída',
    'TRANSFERENCIA': 'Transferência',
    'AJUSTE': 'Ajuste',
}

EQUIPAMENTO_ICONS = {
    'DESKTOP': 'bi-pc-display',
    'NOTEBOOK': 'bi-laptop',
    'MONITOR': 'bi-display',
    'IMPRESSORA': 'bi-printer',
    'SCANNER': 'bi-scanner',
    'NOBREAK': 'bi-battery-charging',
    'SWITCH': 'bi-diagram-3',
    'ROTEADOR': 'bi-wifi',
    'TELEFONE_IP': 'bi-telephone',
    'PROJETOR': 'bi-projector',
    'TABLET': 'bi-tablet',
    'OUTRO': 'bi-box',
}

@register.filter
def status_badge_class(value):
    """Returns CSS class for equipamento status badge."""
    return EQUIPAMENTO_STATUS_CLASSES.get(value, 'badge-estoque')


@register.filter
def status_label(value):
    """Returns human-readable label for equipamento status."""
    return EQUIPAMENTO_STATUS_LABELS.get(value, value)


@register.filter
def manutencao_status_class(value):
    """Returns Bootstrap class for manutencao status."""
    return MANUTENCAO_STATUS_CLASSES.get(value, 'bg-secondary text-white')


@register.filter
def manutencao_status_label(value):
    """Returns human-readable label for manutencao status."""
    return MANUTENCAO_STATUS_LABELS.get(value, value)


@register.filter
def movimentacao_tipo_class(value):
    """Returns Bootstrap class for movimentacao tipo."""
    return MOVIMENTACAO_TIPO_CLASSES.get(value, 'bg-secondary text-white')


@register.filter
def movimentacao_tipo_label(value):
    """Returns human-readable label for movimentacao tipo."""
    return MOVIMENTACAO_TIPO_LABELS.get(value, value)


@register.filter
def user_display_name(user):
    if user is None:
        return ''
    return user.get_full_name() or user.username


@register.filter
def equipamento_icon(value):
    """Returns Bootstrap icon class for equipamento tipo."""
    return EQUIPAMENTO_ICONS.get(value, 'bi-box')


@register.simple_tag
def stock_alert_class(quantidade, quantidade_minima):
    """Returns CSS class based on stock levels."""
    if quantidade <= 0:
        return 'text-danger fw-bold'
    if quantidade < quantidade_minima:
        return 'text-warning fw-bold'
    return ''


@register.simple_tag
def row_class(quantidade, quantidade_minima):
    """Returns table row class for stock alerts."""
    if quantidade < quantidade_minima:
        return 'row-alert'
    return ''
