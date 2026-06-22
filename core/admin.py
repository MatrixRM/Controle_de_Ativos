from django.contrib import admin
from .models import Empresa, Equipamento, Manutencao, ItemEstoque, MovimentacaoEstoque, Notificacao


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'segmento']
    list_filter = ['segmento']
    search_fields = ['nome']


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ['numero_imobilizado', 'tipo', 'marca', 'modelo', 'empresa', 'status', 'ip', 'teamviewer_id', 'setor', 'ultimo_usuario', 'responsavel']
    list_filter = ['tipo', 'status', 'setor']
    search_fields = ['numero_imobilizado', 'numero_serie', 'modelo', 'marca']
    date_hierarchy = 'criado_em'


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'equipamento', 'tipo', 'status', 'data_abertura', 'tecnico']
    list_filter = ['tipo', 'status']
    search_fields = ['equipamento__numero_imobilizado', 'descricao']
    date_hierarchy = 'data_abertura'


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'quantidade', 'quantidade_minima', 'localizacao']
    list_filter = ['categoria']
    search_fields = ['nome']
    list_editable = ['quantidade']


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['item', 'tipo', 'quantidade', 'empresa_origem', 'empresa_destino', 'data', 'responsavel']
    list_filter = ['tipo']
    search_fields = ['item__nome', 'observacao']
    date_hierarchy = 'data'
    readonly_fields = ['data']


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'mensagem', 'lida', 'criado_em']
    list_filter = ['tipo', 'lida']
    search_fields = ['mensagem']
    date_hierarchy = 'criado_em'
    readonly_fields = ['criado_em']



