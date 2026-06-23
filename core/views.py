import csv
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView as AuthLoginView
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from .forms import (CompraForm, EmpresaForm, EquipamentoForm, ItemCompraForm,
                     ManutencaoForm, ItemEstoqueForm, MovimentacaoEstoqueForm)
from .mapeamento_empresas import detectar_empresa_por_hostname
from .models import (Compra, Empresa, Equipamento, ItemCompra, Manutencao,
                     ItemEstoque, MovimentacaoEstoque, LogAlteracao, Notificacao)


class LoginView(AuthLoginView):
    template_name = 'registration/login.html'


class LoginRequired(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class GrupoAdministradorMixin(UserPassesTestMixin):
    login_url = reverse_lazy('login')

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name='Administrador').exists()


class DashboardView(LoginRequired, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_ativos'] = Equipamento.objects.filter(status='ATIVO').count()
        context['total_manutencao'] = Equipamento.objects.filter(status='EM_MANUTENCAO').count()
        context['total_emprestado'] = Equipamento.objects.filter(status='EMPRESTADO').count()
        context['total_estoque'] = Equipamento.objects.filter(status='ESTOQUE').count()
        context['total_descartado'] = Equipamento.objects.filter(status='DESCARTADO').count()
        context['manutencoes_abertas'] = Manutencao.objects.exclude(status='CONCLUIDA').count()
        context['itens_abaixo_minimo'] = ItemEstoque.objects.filter(quantidade__lt=F('quantidade_minima'))
        context['preventivas_pendentes'] = Equipamento.objects.filter(
            proxima_manutencao__lte=timezone.now().date(),
            periodicidade_dias__isnull=False,
        ).exclude(status='DESCARTADO').count()
        context['ultimas_manutencoes'] = Manutencao.objects.select_related('equipamento', 'tecnico').order_by('-data_abertura')[:5]
        context['total_equipamentos'] = Equipamento.objects.count()
        context['total_empresas'] = Empresa.objects.count()
        context['equipamentos'] = Equipamento.objects.select_related('empresa').order_by('-criado_em')[:5]
        return context


class EmpresaListView(LoginRequired, ListView):
    model = Empresa
    template_name = 'core/empresa_list.html'
    context_object_name = 'empresas'
    paginate_by = 20

    def get_queryset(self):
        qs = Empresa.objects.all()
        busca = self.request.GET.get('busca')
        if busca:
            qs = qs.filter(nome__icontains=busca)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['busca'] = self.request.GET.get('busca', '')
        return context


class EmpresaCreateView(LoginRequired, GrupoAdministradorMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_form.html'
    success_url = reverse_lazy('listar-empresas')

    def form_valid(self, form):
        messages.success(self.request, 'Empresa cadastrada com sucesso!')
        return super().form_valid(form)


class EmpresaUpdateView(LoginRequired, GrupoAdministradorMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'core/empresa_form.html'
    success_url = reverse_lazy('listar-empresas')

    def form_valid(self, form):
        messages.success(self.request, 'Empresa atualizada com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context


class EmpresaDeleteView(LoginRequired, GrupoAdministradorMixin, DeleteView):
    model = Empresa
    template_name = 'core/empresa_confirm_delete.html'
    success_url = reverse_lazy('listar-empresas')

    def form_valid(self, form):
        messages.success(self.request, 'Empresa excluída com sucesso!')
        return super().form_valid(form)


class EquipamentoListView(LoginRequired, ListView):
    model = Equipamento
    template_name = 'core/equipamento_list.html'
    context_object_name = 'equipamentos'
    paginate_by = 20

    def get_queryset(self):
        from datetime import date, timedelta
        qs = Equipamento.objects.select_related('empresa').all()
        tipo = self.request.GET.get('tipo')
        status = self.request.GET.get('status')
        setor = self.request.GET.get('setor')
        empresa = self.request.GET.get('empresa')
        busca = self.request.GET.get('busca')
        garantia = self.request.GET.get('garantia')
        depreciacao = self.request.GET.get('depreciacao')
        fornecedor = self.request.GET.get('fornecedor')
        compra_inicio = self.request.GET.get('compra_inicio')
        compra_fim = self.request.GET.get('compra_fim')

        if tipo:
            qs = qs.filter(tipo=tipo)
        if status:
            qs = qs.filter(status=status)
        if setor:
            qs = qs.filter(setor__icontains=setor)
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        if busca:
            qs = qs.filter(
                Q(numero_imobilizado__icontains=busca) |
                Q(modelo__icontains=busca) |
                Q(marca__icontains=busca) |
                Q(ultimo_usuario__icontains=busca) |
                Q(numero_serie__icontains=busca)
            )

        hoje = date.today()
        itens_qs = ItemCompra.objects.all()

        if garantia == 'em_garantia':
            pks = list(itens_qs.filter(data_fim_garantia__gte=hoje).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)
        elif garantia == 'fora_garantia':
            pks = list(itens_qs.filter(data_fim_garantia__lt=hoje).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)
        elif garantia == 'proximo_vencer':
            pks = list(itens_qs.filter(
                data_fim_garantia__gte=hoje,
                data_fim_garantia__lte=hoje + timedelta(days=30),
            ).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)

        if depreciacao == 'depreciado':
            pks = list(itens_qs.filter(data_fim_depreciacao__lt=hoje).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)
        elif depreciacao == 'em_depreciacao':
            pks = list(itens_qs.filter(data_fim_depreciacao__gte=hoje).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)

        if fornecedor:
            compra_ids = Compra.objects.filter(fornecedor_nome__icontains=fornecedor).values_list('id', flat=True)
            pks = list(itens_qs.filter(compra_id__in=compra_ids).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)

        if compra_inicio and compra_fim:
            compra_ids = Compra.objects.filter(
                data_compra__gte=compra_inicio, data_compra__lte=compra_fim,
            ).values_list('id', flat=True)
            pks = list(itens_qs.filter(compra_id__in=compra_ids).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)
        elif compra_inicio:
            compra_ids = Compra.objects.filter(data_compra__gte=compra_inicio).values_list('id', flat=True)
            pks = list(itens_qs.filter(compra_id__in=compra_ids).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)
        elif compra_fim:
            compra_ids = Compra.objects.filter(data_compra__lte=compra_fim).values_list('id', flat=True)
            pks = list(itens_qs.filter(compra_id__in=compra_ids).values_list('equipamento_id', flat=True))
            qs = qs.filter(pk__in=pks)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos'] = Equipamento.TIPOS
        context['status_list'] = Equipamento.STATUS
        context['empresas'] = Empresa.objects.all()
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_setor'] = self.request.GET.get('setor', '')
        context['filtro_empresa'] = self.request.GET.get('empresa', '')
        context['busca'] = self.request.GET.get('busca', '')
        context['filtro_garantia'] = self.request.GET.get('garantia', '')
        context['filtro_depreciacao'] = self.request.GET.get('depreciacao', '')
        context['filtro_fornecedor'] = self.request.GET.get('fornecedor', '')
        context['filtro_compra_inicio'] = self.request.GET.get('compra_inicio', '')
        context['filtro_compra_fim'] = self.request.GET.get('compra_fim', '')
        context['fornecedores'] = Compra.objects.values_list('fornecedor_nome', flat=True).distinct().order_by('fornecedor_nome')
        return context


class EquipamentoDetailView(LoginRequired, DetailView):
    model = Equipamento
    template_name = 'core/equipamento_detail.html'
    context_object_name = 'equipamento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['manutencoes'] = self.object.manutencoes.select_related('tecnico').all()
        context['itens_compra'] = self.object.itens_compra.select_related('compra').all()
        return context


class EquipamentoCreateView(LoginRequired, CreateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'core/equipamento_form.html'
    success_url = reverse_lazy('listar-equipamentos')

    def form_valid(self, form):
        messages.success(self.request, 'Equipamento cadastrado com sucesso!')
        return super().form_valid(form)


class EquipamentoUpdateView(LoginRequired, UpdateView):
    model = Equipamento
    form_class = EquipamentoForm
    template_name = 'core/equipamento_form.html'
    success_url = reverse_lazy('listar-equipamentos')

    def form_valid(self, form):
        messages.success(self.request, 'Equipamento atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context


class EquipamentoDeleteView(LoginRequired, GrupoAdministradorMixin, DeleteView):
    model = Equipamento
    template_name = 'core/equipamento_confirm_delete.html'
    success_url = reverse_lazy('listar-equipamentos')

    def form_valid(self, form):
        messages.success(self.request, 'Equipamento excluído com sucesso!')
        return super().form_valid(form)


class ManutencaoListView(LoginRequired, ListView):
    model = Manutencao
    template_name = 'core/manutencao_list.html'
    context_object_name = 'manutencoes'
    paginate_by = 20

    def get_queryset(self):
        qs = Manutencao.objects.select_related('equipamento', 'tecnico').all()
        status = self.request.GET.get('status')
        equipamento = self.request.GET.get('equipamento')
        if status:
            qs = qs.filter(status=status)
        if equipamento:
            qs = qs.filter(equipamento_id=equipamento)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_list'] = Manutencao.STATUS_MANUTENCAO
        context['filtro_status'] = self.request.GET.get('status', '')
        return context


class ManutencaoCreateView(LoginRequired, CreateView):
    model = Manutencao
    form_class = ManutencaoForm
    template_name = 'core/manutencao_form.html'
    success_url = reverse_lazy('listar-manutencoes')

    def get_initial(self):
        initial = super().get_initial()
        equipamento_pk = self.kwargs.get('equipamento_pk') or self.request.GET.get('equipamento')
        if equipamento_pk:
            initial['equipamento'] = equipamento_pk
        return initial

    def form_valid(self, form):
        if not form.instance.tecnico_id:
            form.instance.tecnico = self.request.user
        messages.success(self.request, 'Manutenção registrada com sucesso!')
        return super().form_valid(form)


class ManutencaoUpdateView(LoginRequired, UpdateView):
    model = Manutencao
    form_class = ManutencaoForm
    template_name = 'core/manutencao_form.html'
    success_url = reverse_lazy('listar-manutencoes')

    def form_valid(self, form):
        messages.success(self.request, 'Manutenção atualizada com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context


class EstoqueListView(LoginRequired, ListView):
    model = ItemEstoque
    template_name = 'core/estoque_list.html'
    context_object_name = 'itens'
    paginate_by = 20

    def get_queryset(self):
        qs = ItemEstoque.objects.all()
        categoria = self.request.GET.get('categoria')
        busca = self.request.GET.get('busca')
        if categoria:
            qs = qs.filter(categoria=categoria)
        if busca:
            qs = qs.filter(nome__icontains=busca)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = ItemEstoque.CATEGORIAS
        context['filtro_categoria'] = self.request.GET.get('categoria', '')
        context['busca'] = self.request.GET.get('busca', '')
        context['itens_abaixo_minimo'] = ItemEstoque.objects.filter(quantidade__lt=F('quantidade_minima'))
        return context


class ItemEstoqueCreateView(LoginRequired, GrupoAdministradorMixin, CreateView):
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'core/itemestoque_form.html'
    success_url = reverse_lazy('listar-estoque')

    def form_valid(self, form):
        messages.success(self.request, 'Item cadastrado no estoque com sucesso!')
        return super().form_valid(form)


class ItemEstoqueUpdateView(LoginRequired, GrupoAdministradorMixin, UpdateView):
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'core/itemestoque_form.html'
    success_url = reverse_lazy('listar-estoque')

    def form_valid(self, form):
        messages.success(self.request, 'Item de estoque atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context


class MovimentacaoCreateView(LoginRequired, GrupoAdministradorMixin, CreateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    template_name = 'core/movimentacao_form.html'
    success_url = reverse_lazy('listar-movimentacoes')

    def form_valid(self, form):
        form.instance.responsavel = self.request.user
        messages.success(self.request, 'Movimentação registrada com sucesso!')
        return super().form_valid(form)


class MovimentacaoListView(LoginRequired, ListView):
    model = MovimentacaoEstoque
    template_name = 'core/movimentacao_list.html'
    context_object_name = 'movimentacoes'
    paginate_by = 20

    def get_queryset(self):
        return MovimentacaoEstoque.objects.select_related('item', 'responsavel', 'equipamento', 'empresa_origem', 'empresa_destino').all()


@method_decorator(csrf_exempt, name='dispatch')
class RedePendentesView(View):
    http_method_names = ['get']

    def get(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth != f'Token {settings.INVENTORY_TOKEN}':
            return JsonResponse({'erro': 'Token inválido'}, status=401)

        hostnames = list(
            Equipamento.objects.filter(tipo__in=['DESKTOP', 'NOTEBOOK'])
            .values_list('numero_imobilizado', flat=True)
        )
        return JsonResponse({'hostnames': hostnames})


@method_decorator(csrf_exempt, name='dispatch')
class AtualizarRedeView(View):
    http_method_names = ['post']

    def post(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth != f'Token {settings.INVENTORY_TOKEN}':
            return JsonResponse({'erro': 'Token inválido'}, status=401)

        try:
            dados = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON inválido'}, status=400)

        if not isinstance(dados, list):
            return JsonResponse({'erro': 'Payload deve ser uma lista'}, status=400)

        atualizados = 0
        erros = []

        for item in dados:
            hostname = (item.get('hostname') or '').strip().upper()
            if not hostname:
                erros.append({'hostname': hostname, 'erro': 'hostname vazio'})
                continue

            try:
                eq = Equipamento.objects.filter(numero_imobilizado=hostname).first()
                if not eq:
                    erros.append({'hostname': hostname, 'erro': 'equipamento não encontrado'})
                    continue

                changed = False
                ip = item.get('ip')
                if ip and eq.ip != ip:
                    eq.ip = ip
                    changed = True

                tv = item.get('teamviewer_id')
                if tv and eq.teamviewer_id != tv:
                    eq.teamviewer_id = tv
                    changed = True

                if changed:
                    eq.save(update_fields=['ip', 'teamviewer_id'])
                    atualizados += 1
            except Exception as e:
                erros.append({'hostname': hostname, 'erro': str(e)})

        return JsonResponse({
            'atualizados': atualizados,
            'erros': erros,
        })


@method_decorator(csrf_exempt, name='dispatch')
class SyncAtivosView(View):
    http_method_names = ['post']

    def post(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if auth != f'Token {settings.INVENTORY_TOKEN}':
            return JsonResponse({'erro': 'Token inválido'}, status=401)

        try:
            dados = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'erro': 'JSON inválido'}, status=400)

        if not isinstance(dados, list):
            return JsonResponse({'erro': 'Payload deve ser uma lista'}, status=400)

        criados = 0
        atualizados = 0
        erros = []

        for idx, item in enumerate(dados):
            try:
                result = self._processar_equipamento(item)
                if result:
                    if result['acao'] == 'criado':
                        criados += 1
                    else:
                        atualizados += 1
            except Exception as e:
                erros.append({'indice': idx, 'erro': str(e)})

        return JsonResponse({
            'criados': criados,
            'atualizados': atualizados,
            'erros': erros,
        })

    def _detectar_tipo(self, modelo, fabricante, hostname=''):
        m = (modelo or '').upper()
        f = (fabricante or '').upper()
        h = (hostname or '').upper()

        if any(p in m for p in ['NOTEBOOK', 'LAPTOP', 'MOBILE', 'THINKPAD', 'LATITUDE', 'ELITEBOOK', 'PROBOOK']):
            return 'NOTEBOOK'
        if any(p in f for p in ['NOTEBOOK', 'LAPTOP']):
            return 'NOTEBOOK'
        if h.startswith('SRV-') or h.startswith('SERVER'):
            return 'OUTRO'
        if 'SERVER' in m or 'POWEREDGE' in m or 'PROLIANT' in m:
            return 'OUTRO'
        if 'MONITOR' in m:
            return 'MONITOR'
        if any(p in m for p in ['SWITCH', 'ROTEADOR', 'ROUTER']):
            return 'SWITCH'
        if 'IMPRESSORA' in m or 'PRINTER' in m:
            return 'IMPRESSORA'
        if 'NOBREAK' in m or 'UPS' in m:
            return 'NOBREAK'
        return 'DESKTOP'

    def _montar_observacoes(self, item):
        partes = ['Sincronizado automaticamente via inventário de rede']
        proc = (item.get('processador') or '').strip()
        if proc:
            partes.append(f'Processador: {proc}')
        mem = item.get('memoria_gb')
        if mem:
            partes.append(f'Memória: {mem} GB')
        usuario = (item.get('usuario') or '').strip()
        if usuario:
            partes.append(f'Último usuário: {usuario}')
        ip = item.get('ip') or ''
        if ip:
            partes.append(f'IP: {ip}')
        return ' | '.join(partes)

    def _processar_equipamento(self, item):
        hostname = (item.get('nome') or '').strip().upper()
        serial = (item.get('serial') or '').strip().upper()
        if not hostname:
            return None

        fabricante = (item.get('fabricante') or '').strip()
        modelo = (item.get('modelo') or '').strip()
        sistema = (item.get('sistema') or item.get('sistema_operacional') or '').strip()
        status_rede = item.get('status_rede', 'desconhecido')

        empresa_id = detectar_empresa_por_hostname(hostname)

        defaults = {
            'numero_imobilizado': hostname,
            'numero_serie': serial,
            'tipo': self._detectar_tipo(modelo, fabricante, hostname),
            'marca': fabricante,
            'modelo': modelo,
            'local': hostname.split('-')[0].strip(),
            'ip': item.get('ip') or None,
            'ultimo_usuario': (item.get('usuario') or '').strip(),
            'sistema_operacional': sistema,
            'status': 'ATIVO' if status_rede == 'online' else 'OFFLINE',
            'empresa_id': empresa_id,
            'observacoes': self._montar_observacoes(item),
        }

        if serial:
            eq = Equipamento.objects.filter(numero_serie=serial).first()
            if eq:
                for k, v in defaults.items():
                    setattr(eq, k, v)
                eq.save()
                return {'acao': 'atualizado'}
            else:
                Equipamento.objects.create(**defaults)
                return {'acao': 'criado'}
        else:
            eq = Equipamento.objects.filter(numero_imobilizado=hostname).first()
            if eq:
                for k, v in defaults.items():
                    setattr(eq, k, v)
                eq.save()
                return {'acao': 'atualizado'}
            else:
                Equipamento.objects.create(**defaults)
                return {'acao': 'criado'}


class BuscaAvancadaView(LoginRequired, ListView):
    model = Equipamento
    template_name = 'core/busca_avancada.html'
    context_object_name = 'equipamentos'
    paginate_by = 30

    def get_queryset(self):
        qs = Equipamento.objects.select_related('empresa').all()
        q = self.request.GET.get('q', '').strip()
        tipo = self.request.GET.get('tipo')
        status = self.request.GET.get('status')
        empresa = self.request.GET.get('empresa')
        setor = self.request.GET.get('setor')
        campo = self.request.GET.get('campo', '')

        if q:
            base_q = Q()
            fields = ['numero_imobilizado', 'numero_serie', 'modelo', 'marca',
                      'ip', 'mac_ethernet', 'mac_wifi', 'teamviewer_id',
                      'sistema_operacional', 'versao_so', 'observacoes']
            if campo:
                fields = [campo]
            for f in fields:
                base_q |= Q(**{f'{f}__icontains': q})
            qs = qs.filter(base_q)

        if tipo:
            qs = qs.filter(tipo=tipo)
        if status:
            qs = qs.filter(status=status)
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        if setor:
            qs = qs.filter(setor__icontains=setor)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['tipos'] = Equipamento.TIPOS
        context['status_list'] = Equipamento.STATUS
        context['empresas'] = Empresa.objects.all()
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_setor'] = self.request.GET.get('setor', '')
        context['filtro_empresa'] = self.request.GET.get('empresa', '')
        context['campo'] = self.request.GET.get('campo', '')
        context['total_resultados'] = self.object_list.count() if hasattr(self, 'object_list') else 0
        return context


class AuditoriaView(LoginRequired, ListView):
    model = LogAlteracao
    template_name = 'core/auditoria.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = LogAlteracao.objects.select_related('usuario').all()
        busca = self.request.GET.get('busca')
        tabela = self.request.GET.get('tabela')
        if busca:
            qs = qs.filter(
                Q(registro_id__icontains=busca) |
                Q(campo__icontains=busca) |
                Q(valor_anterior__icontains=busca) |
                Q(valor_novo__icontains=busca)
            )
        if tabela:
            qs = qs.filter(tabela=tabela)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['busca'] = self.request.GET.get('busca', '')
        context['filtro_tabela'] = self.request.GET.get('tabela', '')
        context['tabelas'] = LogAlteracao.objects.values_list('tabela', flat=True).distinct().order_by('tabela')
        return context


class NotificacaoListView(LoginRequired, ListView):
    model = Notificacao
    template_name = 'core/notificacao_list.html'
    context_object_name = 'notificacoes'
    paginate_by = 30

    def get_queryset(self):
        qs = Notificacao.objects.all()
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['tipos'] = Notificacao.TIPOS
        return context

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        if data.get('marcar_todas'):
            Notificacao.objects.filter(lida=False).update(lida=True)
        elif data.get('id'):
            Notificacao.objects.filter(pk=data['id']).update(lida=True)
        return JsonResponse({'ok': True})


class ChatBotView(LoginRequired, TemplateView):
    template_name = 'core/chatbot.html'

    def post(self, request):
        import json
        from .chatbot import processar
        data = json.loads(request.body)
        mensagem = data.get('mensagem', '').strip()
        if not mensagem:
            return JsonResponse({'resposta': 'Digite uma mensagem.'})
        resposta = processar(mensagem)
        return JsonResponse({'resposta': resposta})


class RelatorioEstoqueView(LoginRequired, TemplateView):
    template_name = 'core/relatorio_estoque.html'

    def get_queryset(self):
        qs = ItemEstoque.objects.all()
        busca = self.request.GET.get('busca')
        categoria = self.request.GET.get('categoria')
        localizacao = self.request.GET.get('localizacao')
        if busca:
            qs = qs.filter(nome__icontains=busca)
        if categoria:
            qs = qs.filter(categoria=categoria)
        if localizacao:
            qs = qs.filter(localizacao__icontains=localizacao)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['qs'] = qs
        context['total_itens'] = qs.count()
        context['total_geral'] = ItemEstoque.objects.count()
        context['itens_abaixo_minimo'] = qs.filter(quantidade__lt=F('quantidade_minima'))
        context['total_categorias'] = ItemEstoque.objects.values('categoria').distinct().count()
        context['por_categoria'] = list(
            qs.values('categoria').annotate(total=Count('id')).order_by('-total')
        )
        context['categorias'] = ItemEstoque.CATEGORIAS
        context['filtro_categoria'] = self.request.GET.get('categoria', '')
        context['filtro_localizacao'] = self.request.GET.get('localizacao', '')
        context['busca'] = self.request.GET.get('busca', '')
        return context

    def get(self, request, *args, **kwargs):
        if 'export' in request.GET:
            return self._export_csv()
        return super().get(request, *args, **kwargs)

    def _export_csv(self):
        qs = self.get_queryset()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_estoque.csv"'
        response.write('\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        writer.writerow(['Nome', 'Categoria', 'Quantidade', 'Mínimo', 'Unidade', 'Localização', 'Observações'])
        for item in qs:
            writer.writerow([
                item.nome, item.get_categoria_display(), item.quantidade,
                item.quantidade_minima, item.unidade, item.localizacao, item.observacoes,
            ])
        return response


class RelatorioEquipamentosView(LoginRequired, TemplateView):
    template_name = 'core/relatorio_equipamentos.html'

    def get_queryset(self):
        qs = Equipamento.objects.select_related('empresa').all()
        busca = self.request.GET.get('busca')
        tipo = self.request.GET.get('tipo')
        status = self.request.GET.get('status')
        setor = self.request.GET.get('setor')
        empresa = self.request.GET.get('empresa')
        if busca:
            qs = qs.filter(
                Q(numero_imobilizado__icontains=busca) |
                Q(modelo__icontains=busca) |
                Q(marca__icontains=busca) |
                Q(numero_serie__icontains=busca)
            )
        if tipo:
            qs = qs.filter(tipo=tipo)
        if status:
            qs = qs.filter(status=status)
        if setor:
            qs = qs.filter(setor__icontains=setor)
        if empresa:
            qs = qs.filter(empresa_id=empresa)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_filtrado'] = qs.count()
        context['total_geral'] = Equipamento.objects.count()
        context['qs'] = qs[:500]
        context['por_status'] = list(
            qs.values('status').annotate(total=Count('id')).order_by('status')
        )
        context['por_tipo'] = list(
            qs.values('tipo').annotate(total=Count('id')).order_by('-total')
        )
        context['por_empresa'] = list(
            qs.values('empresa__nome').annotate(total=Count('id')).order_by('-total')
        )
        context['tipos'] = Equipamento.TIPOS
        context['status_list'] = Equipamento.STATUS
        context['empresas'] = Empresa.objects.all()
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['filtro_status'] = self.request.GET.get('status', '')
        context['filtro_setor'] = self.request.GET.get('setor', '')
        context['filtro_empresa'] = self.request.GET.get('empresa', '')
        context['busca'] = self.request.GET.get('busca', '')
        return context

    def get(self, request, *args, **kwargs):
        if 'export' in request.GET:
            return self._export_csv()
        return super().get(request, *args, **kwargs)

    def _export_csv(self):
        qs = self.get_queryset()[:5000]
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_equipamentos.csv"'
        response.write('\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        writer.writerow([
            'Nº Imobilizado', 'Nº Série', 'Tipo', 'Marca', 'Modelo',
            'Local', 'Setor', 'Empresa', 'Status', 'IP', 'TeamViewer',
            'Sistema Operacional', 'Versão SO', 'MAC Ethernet', 'MAC Wi-Fi',
            'Versão Office', 'Observações',
        ])
        for eq in qs:
            writer.writerow([
                eq.numero_imobilizado, eq.numero_serie, eq.get_tipo_display(),
                eq.marca, eq.modelo, eq.local, eq.setor,
                eq.empresa.nome if eq.empresa else '',
                eq.get_status_display(), eq.ip or '', eq.teamviewer_id or '',
                eq.sistema_operacional, eq.versao_so,
                eq.mac_ethernet, eq.mac_wifi,
                eq.versao_office, eq.observacoes,
            ])
        return response


class CompraListView(LoginRequired, ListView):
    model = Compra
    template_name = 'core/compra_list.html'
    context_object_name = 'compras'
    paginate_by = 20

    def get_queryset(self):
        qs = Compra.objects.prefetch_related('itens').all()
        busca = self.request.GET.get('busca')
        fornecedor = self.request.GET.get('fornecedor')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        if busca:
            qs = qs.filter(
                Q(numero_nf__icontains=busca) |
                Q(fornecedor_nome__icontains=busca) |
                Q(fornecedor_cnpj__icontains=busca)
            )
        if fornecedor:
            qs = qs.filter(fornecedor_nome__icontains=fornecedor)
        if data_inicio:
            qs = qs.filter(data_compra__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_compra__lte=data_fim)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['busca'] = self.request.GET.get('busca', '')
        context['filtro_fornecedor'] = self.request.GET.get('fornecedor', '')
        context['filtro_data_inicio'] = self.request.GET.get('data_inicio', '')
        context['filtro_data_fim'] = self.request.GET.get('data_fim', '')
        context['fornecedores'] = Compra.objects.values_list('fornecedor_nome', flat=True).distinct().order_by('fornecedor_nome')
        return context


class CompraDetailView(LoginRequired, DetailView):
    model = Compra
    template_name = 'core/compra_detail.html'
    context_object_name = 'compra'


class CompraCreateView(LoginRequired, CreateView):
    model = Compra
    form_class = CompraForm
    template_name = 'core/compra_form.html'
    success_url = reverse_lazy('listar-compras')

    def form_valid(self, form):
        messages.success(self.request, 'Compra cadastrada com sucesso!')
        return super().form_valid(form)


class CompraUpdateView(LoginRequired, UpdateView):
    model = Compra
    form_class = CompraForm
    template_name = 'core/compra_form.html'
    success_url = reverse_lazy('listar-compras')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Compra atualizada com sucesso!')
        return super().form_valid(form)


class CompraDeleteView(LoginRequired, DeleteView):
    model = Compra
    template_name = 'core/compra_confirm_delete.html'
    success_url = reverse_lazy('listar-compras')
    context_object_name = 'compra'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Compra excluída com sucesso!')
        return super().delete(request, *args, **kwargs)


class ItemCompraCreateView(LoginRequired, CreateView):
    model = ItemCompra
    form_class = ItemCompraForm
    template_name = 'core/itemcompra_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.compra = Compra.objects.get(pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.compra = self.compra
        messages.success(self.request, 'Item adicionado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('detalhe-compra', kwargs={'pk': self.compra.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['compra'] = self.compra
        return context


class ItemCompraUpdateView(LoginRequired, UpdateView):
    model = ItemCompra
    form_class = ItemCompraForm
    template_name = 'core/itemcompra_form.html'

    def get_success_url(self):
        return reverse_lazy('detalhe-compra', kwargs={'pk': self.object.compra.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editando'] = True
        context['compra'] = self.object.compra
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Item atualizado com sucesso!')
        return super().form_valid(form)


class ItemCompraDeleteView(LoginRequired, DeleteView):
    model = ItemCompra
    template_name = 'core/itemcompra_confirm_delete.html'
    context_object_name = 'item'

    def get_success_url(self):
        return reverse_lazy('detalhe-compra', kwargs={'pk': self.object.compra.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Item excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
