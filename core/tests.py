import json

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from .models import Equipamento, ItemEstoque, Manutencao, MovimentacaoEstoque, LogAlteracao


class LoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teste', password='senha123')

    def test_login_redirects_anonymous(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_login_successful_redirect(self):
        response = self.client.post(reverse('login'), {
            'username': 'teste', 'password': 'senha123'
        })
        self.assertEqual(response.status_code, 302)

    def test_equipamento_list_requires_auth(self):
        response = self.client.get(reverse('listar-equipamentos'))
        self.assertEqual(response.status_code, 302)


class EquipamentoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teste', password='senha123')

    def test_create_equipamento(self):
        eq = Equipamento.objects.create(
            numero_imobilizado='12345',
            tipo='DESKTOP',
            marca='Dell',
            modelo='Optiplex 7090',
            local='Sala 101',
            setor='TI',
            status='ATIVO',
            responsavel='teste',
        )
        self.assertEqual(str(eq), '12345 - Desktop - Optiplex 7090')
        self.assertEqual(Equipamento.objects.count(), 1)

    def test_equipamento_str_method(self):
        eq = Equipamento(
            numero_imobilizado='999',
            tipo='NOTEBOOK',
            marca='Lenovo',
            modelo='ThinkPad',
        )
        self.assertIn('999', str(eq))
        self.assertIn('Notebook', str(eq))

    def test_equipamento_unique_imobilizado(self):
        Equipamento.objects.create(numero_imobilizado='1', tipo='DESKTOP', marca='A', modelo='B', local='X', setor='Y')
        with self.assertRaises(Exception):
            Equipamento.objects.create(numero_imobilizado='1', tipo='NOTEBOOK', marca='A', modelo='B', local='X', setor='Y')


class ManutencaoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tecnico', password='senha123')
        self.equipamento = Equipamento.objects.create(
            numero_imobilizado='100', tipo='DESKTOP', marca='Dell', modelo='Optiplex', local='Sala 1', setor='TI'
        )

    def test_create_manutencao(self):
        m = Manutencao.objects.create(
            equipamento=self.equipamento,
            tipo='CORRETIVA',
            descricao='Troca de fonte',
            tecnico=self.user,
        )
        self.assertEqual(m.status, 'ABERTA')
        self.assertIn('Manutenção', str(m))

    def test_manutencao_equipamento_relation(self):
        Manutencao.objects.create(equipamento=self.equipamento, tipo='PREVENTIVA', descricao='Limpeza')
        self.assertEqual(self.equipamento.manutencoes.count(), 1)


class EstoqueModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teste', password='senha123')

    def test_create_item_estoque(self):
        item = ItemEstoque.objects.create(
            nome='Mouse Óptico',
            categoria='MOUSE',
            quantidade=15,
            quantidade_minima=3,
        )
        self.assertIn('Mouse', str(item))
        self.assertEqual(item.quantidade, 15)

    def test_item_abaixo_do_minimo(self):
        ItemEstoque.objects.create(nome='Teclado', categoria='TECLADO', quantidade=1, quantidade_minima=5)
        abaixo = [i for i in ItemEstoque.objects.all() if i.quantidade < i.quantidade_minima]
        self.assertEqual(len(abaixo), 1)

    def test_movimentacao_entrada_atualiza_estoque(self):
        item = ItemEstoque.objects.create(nome='HD 1TB', categoria='HD_SSD', quantidade=5, quantidade_minima=1)
        MovimentacaoEstoque.objects.create(
            item=item,
            tipo='ENTRADA',
            quantidade=10,
            responsavel=self.user,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 15)

    def test_movimentacao_saida_atualiza_estoque(self):
        item = ItemEstoque.objects.create(nome='Fonte 500W', categoria='FONTE', quantidade=20, quantidade_minima=2)
        MovimentacaoEstoque.objects.create(
            item=item,
            tipo='SAIDA',
            quantidade=5,
            responsavel=self.user,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 15)

    def test_movimentacao_ajuste_define_quantidade(self):
        item = ItemEstoque.objects.create(nome='Cabo HDMI', categoria='CABO', quantidade=10, quantidade_minima=1)
        MovimentacaoEstoque.objects.create(
            item=item,
            tipo='AJUSTE',
            quantidade=50,
            responsavel=self.user,
        )
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 50)

    def test_movimentacao_saida_sem_estoque_suficiente(self):
        item = ItemEstoque.objects.create(nome='Toner', categoria='TONER', quantidade=2, quantidade_minima=1)
        from django.forms import modelform_factory
        from core.forms import MovimentacaoEstoqueForm
        form = MovimentacaoEstoqueForm(data={
            'item': item.pk,
            'tipo': 'SAIDA',
            'quantidade': 999,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('Quantidade insuficiente', str(form.errors))


class GrupoTest(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name='Administrador')
        Group.objects.get_or_create(name='Técnico')

    def test_grupos_criados(self):
        self.assertTrue(Group.objects.filter(name='Administrador').exists())
        self.assertTrue(Group.objects.filter(name='Técnico').exists())


class LogAlteracaoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='senha123')

    def test_log_equipamento_update_cria_registro(self):
        eq = Equipamento.objects.create(
            numero_imobilizado='AUDIT001',
            tipo='DESKTOP',
            marca='Dell', modelo='Optiplex',
            local='Sala 1', setor='TI',
            status='ATIVO',
        )
        eq.marca = 'HP'
        eq.save()
        logs = LogAlteracao.objects.filter(tabela='Equipamento', registro_id=eq.pk)
        self.assertGreater(logs.count(), 0)
        campo_logado = logs.filter(campo='marca').first()
        self.assertIsNotNone(campo_logado)
        self.assertIn('Dell', campo_logado.valor_anterior)
        self.assertIn('HP', campo_logado.valor_novo)

    def test_log_nao_cria_para_criacao(self):
        eq = Equipamento.objects.create(
            numero_imobilizado='AUDIT002',
            tipo='NOTEBOOK',
            marca='Lenovo', modelo='ThinkPad',
            local='Sala 2', setor='RH',
            status='ATIVO',
        )
        logs = LogAlteracao.objects.filter(tabela='Equipamento', registro_id=eq.pk)
        self.assertEqual(logs.count(), 0)

    def test_log_multiplos_campos_alterados(self):
        eq = Equipamento.objects.create(
            numero_imobilizado='AUDIT003',
            tipo='DESKTOP',
            marca='Dell', modelo='Optiplex',
            local='Sala 1', setor='TI',
            status='ATIVO', ip='10.0.0.1',
        )
        eq.marca = 'HP'
        eq.modelo = 'EliteDesk'
        eq.ip = '10.0.0.2'
        eq.save()
        logs = LogAlteracao.objects.filter(tabela='Equipamento', registro_id=eq.pk)
        self.assertGreaterEqual(logs.count(), 3)
        self.assertTrue(logs.filter(campo='marca').exists())
        self.assertTrue(logs.filter(campo='modelo').exists())
        self.assertTrue(logs.filter(campo='ip').exists())

    def test_auditoria_view_requires_auth(self):
        response = self.client.get(reverse('auditoria'))
        self.assertEqual(response.status_code, 302)

    def test_auditoria_view_logged_in(self):
        self.client.login(username='operador', password='senha123')
        response = self.client.get(reverse('auditoria'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/auditoria.html')

    def test_auditoria_view_filtro_tabela(self):
        self.client.login(username='operador', password='senha123')
        eq = Equipamento.objects.create(
            numero_imobilizado='AUDIT004',
            tipo='DESKTOP', marca='Dell', modelo='Optiplex',
            local='X', setor='Y', status='ATIVO',
        )
        eq.marca = 'HP'
        eq.save()
        response = self.client.get(reverse('auditoria'), {'tabela': 'Equipamento'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dell')
        self.assertContains(response, 'HP')

    def test_auditoria_view_busca_por_campo(self):
        self.client.login(username='operador', password='senha123')
        eq = Equipamento.objects.create(
            numero_imobilizado='AUDIT005',
            tipo='DESKTOP', marca='Positivo', modelo='Master',
            local='X', setor='Y', status='ATIVO',
        )
        eq.marca = 'Dell'
        eq.save()
        response = self.client.get(reverse('auditoria'), {'busca': 'Positivo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Positivo')


class DashboardViewContextTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='admin', password='admin123')
        self.client.login(username='admin', password='admin123')
        Equipamento.objects.create(numero_imobilizado='1', tipo='DESKTOP', marca='A', modelo='B', local='X', setor='Y', status='ATIVO')
        Equipamento.objects.create(numero_imobilizado='2', tipo='NOTEBOOK', marca='B', modelo='C', local='X', setor='Y', status='EM_MANUTENCAO')

    def test_dashboard_redirects_when_not_logged_in(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)


TOKEN = 'test-token-123'


@override_settings(INVENTORY_TOKEN=TOKEN)
class SyncAtivosAPITest(TestCase):
    def setUp(self):
        self.url = reverse('sync-ativos')
        self.headers = {'HTTP_AUTHORIZATION': f'Token {TOKEN}'}
        self.payload = [
            {
                'nome': 'PC-FINANCEIRO01',
                'ip': '192.168.0.25',
                'usuario': 'DOMINIO\\usuario',
                'fabricante': 'Dell Inc.',
                'modelo': 'OptiPlex 3090',
                'serial': 'ABC1234',
                'processador': 'Intel Core i5',
                'memoria_gb': 8,
                'sistema': 'Windows 11 Pro',
                'ultimo_logon': '2026-06-11T08:30:00-03:00',
                'status_rede': 'online',
            },
        ]

    def test_requer_token(self):
        response = self.client.post(self.url, json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_token_invalido(self):
        response = self.client.post(self.url, json.dumps(self.payload), content_type='application/json',
                                    HTTP_AUTHORIZATION='Token invalid')
        self.assertEqual(response.status_code, 401)

    def test_cria_equipamento(self):
        response = self.client.post(self.url, json.dumps(self.payload), content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['criados'], 1)
        self.assertEqual(data['atualizados'], 0)
        self.assertEqual(Equipamento.objects.count(), 1)
        eq = Equipamento.objects.get(numero_imobilizado='PC-FINANCEIRO01')
        self.assertEqual(eq.marca, 'Dell Inc.')
        self.assertEqual(eq.local, 'PC')

    def test_atualiza_por_serial(self):
        self.client.post(self.url, json.dumps(self.payload), content_type='application/json', **self.headers)
        payload2 = [dict(self.payload[0], ip='192.168.0.50', usuario='DOMINIO\\novo')]
        response = self.client.post(self.url, json.dumps(payload2), content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['atualizados'], 1)
        eq = Equipamento.objects.get(numero_serie='ABC1234')
        self.assertEqual(eq.local, 'PC')
        self.assertEqual(eq.ip, '192.168.0.50')

    def test_atualiza_por_hostname_quando_sem_serial(self):
        payload = [{'nome': 'PC-SEM-SERIAL', 'ip': '10.0.0.1'}]
        self.client.post(self.url, json.dumps(payload), content_type='application/json', **self.headers)
        payload2 = [{'nome': 'PC-SEM-SERIAL', 'ip': '10.0.0.2'}]
        response = self.client.post(self.url, json.dumps(payload2), content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['atualizados'], 1)
        eq = Equipamento.objects.get(numero_imobilizado='PC-SEM-SERIAL')
        self.assertEqual(eq.local, 'PC')
        self.assertEqual(eq.ip, '10.0.0.2')

    def test_json_invalido(self):
        response = self.client.post(self.url, 'not json', content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 400)

    def test_payload_nao_lista(self):
        response = self.client.post(self.url, json.dumps({}), content_type='application/json', **self.headers)
        self.assertEqual(response.status_code, 400)
