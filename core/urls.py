from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    path('empresas/', views.EmpresaListView.as_view(), name='listar-empresas'),
    path('empresas/nova/', views.EmpresaCreateView.as_view(), name='criar-empresa'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='editar-empresa'),
    path('empresas/<int:pk>/excluir/', views.EmpresaDeleteView.as_view(), name='excluir-empresa'),

    path('equipamentos/', views.EquipamentoListView.as_view(), name='listar-equipamentos'),
    path('equipamentos/novo/', views.EquipamentoCreateView.as_view(), name='criar-equipamento'),
    path('equipamentos/<int:pk>/', views.EquipamentoDetailView.as_view(), name='detalhe-equipamento'),
    path('equipamentos/<int:pk>/editar/', views.EquipamentoUpdateView.as_view(), name='editar-equipamento'),
    path('equipamentos/<int:pk>/excluir/', views.EquipamentoDeleteView.as_view(), name='excluir-equipamento'),

    path('manutencoes/', views.ManutencaoListView.as_view(), name='listar-manutencoes'),
    path('manutencoes/nova/', views.ManutencaoCreateView.as_view(), name='criar-manutencao'),
    path('manutencoes/nova/<int:equipamento_pk>/', views.ManutencaoCreateView.as_view(), name='criar-manutencao-equipamento'),
    path('manutencoes/<int:pk>/editar/', views.ManutencaoUpdateView.as_view(), name='editar-manutencao'),

    path('estoque/', views.EstoqueListView.as_view(), name='listar-estoque'),
    path('estoque/novo/', views.ItemEstoqueCreateView.as_view(), name='criar-item-estoque'),
    path('estoque/<int:pk>/editar/', views.ItemEstoqueUpdateView.as_view(), name='editar-item-estoque'),
    path('estoque/movimentacao/nova/', views.MovimentacaoCreateView.as_view(), name='criar-movimentacao'),
    path('estoque/movimentacoes/', views.MovimentacaoListView.as_view(), name='listar-movimentacoes'),

    path('notificacoes/', views.NotificacaoListView.as_view(), name='listar-notificacoes'),
    path('api/equipamentos/rede-pendentes/', views.RedePendentesView.as_view(), name='rede-pendentes'),
    path('api/equipamentos/atualizar-rede/', views.AtualizarRedeView.as_view(), name='atualizar-rede'),
    path('chatbot/', views.ChatBotView.as_view(), name='chatbot'),
    path('busca/', views.BuscaAvancadaView.as_view(), name='busca-avancada'),
    path('auditoria/', views.AuditoriaView.as_view(), name='auditoria'),
    path('compras/', views.CompraListView.as_view(), name='listar-compras'),
    path('compras/nova/', views.CompraCreateView.as_view(), name='criar-compra'),
    path('compras/<int:pk>/', views.CompraDetailView.as_view(), name='detalhe-compra'),
    path('compras/<int:pk>/editar/', views.CompraUpdateView.as_view(), name='editar-compra'),
    path('compras/<int:pk>/excluir/', views.CompraDeleteView.as_view(), name='excluir-compra'),
    path('compras/<int:pk>/itens/novo/', views.ItemCompraCreateView.as_view(), name='criar-item-compra'),
    path('compras/itens/<int:pk>/editar/', views.ItemCompraUpdateView.as_view(), name='editar-item-compra'),
    path('compras/itens/<int:pk>/excluir/', views.ItemCompraDeleteView.as_view(), name='excluir-item-compra'),
    path('relatorios/estoque/', views.RelatorioEstoqueView.as_view(), name='relatorio-estoque'),
    path('relatorios/equipamentos/', views.RelatorioEquipamentosView.as_view(), name='relatorio-equipamentos'),
    path('api/ativos/sync/', views.SyncAtivosView.as_view(), name='sync-ativos'),
]
