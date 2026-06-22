from django.db import models
from django.conf import settings
from django.utils import timezone


class LogAlteracao(models.Model):
    tabela = models.CharField(max_length=100, verbose_name='Tabela')
    registro_id = models.IntegerField(verbose_name='ID do Registro')
    campo = models.CharField(max_length=100, verbose_name='Campo')
    valor_anterior = models.TextField(blank=True, verbose_name='Valor Anterior')
    valor_novo = models.TextField(blank=True, verbose_name='Valor Novo')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name='Usuário')
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data')

    class Meta:
        verbose_name = 'Log de Alteração'
        verbose_name_plural = 'Logs de Alterações'
        ordering = ['-data']

    def __str__(self):
        return f'{self.tabela}#{self.registro_id} - {self.campo}'


class Empresa(models.Model):
    SEGMENTOS = [
        ('IVECO', 'IVECO'),
        ('AGROP.', 'Agrop.'),
        ('ROD.', 'Rod.'),
        ('V. VALE', 'V. Vale'),
        ('SEGUROS', 'Seguros'),
        ('CASE', 'Case'),
        ('FIAT', 'Fiat'),
        ('LOCADORA', 'Locadora'),
        ('OUTRO', 'Outro'),
    ]

    nome = models.CharField(max_length=255, verbose_name='Razão Social')
    segmento = models.CharField(max_length=20, choices=SEGMENTOS, verbose_name='Segmento')

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome']
        unique_together = ['nome', 'segmento']

    def __str__(self):
        return f'{self.nome} ({self.get_segmento_display()})'


class Equipamento(models.Model):
    TIPOS = [
        ('DESKTOP', 'Desktop'),
        ('NOTEBOOK', 'Notebook'),
        ('MONITOR', 'Monitor'),
        ('IMPRESSORA', 'Impressora'),
        ('SCANNER', 'Scanner'),
        ('NOBREAK', 'Nobreak'),
        ('SWITCH', 'Switch'),
        ('ROTEADOR', 'Roteador'),
        ('TELEFONE_IP', 'Telefone IP'),
        ('PROJETOR', 'Projetor'),
        ('TABLET', 'Tablet'),
        ('OUTRO', 'Outro'),
    ]
    STATUS = [
        ('ATIVO', 'Ativo'),
        ('OFFLINE', 'Offline'),
        ('EM_MANUTENCAO', 'Em Manutenção'),
        ('EMPRESTADO', 'Emprestado'),
        ('ESTOQUE', 'Estoque'),
        ('DESCARTADO', 'Descartado'),
    ]

    numero_imobilizado = models.CharField(max_length=100, unique=True, verbose_name='Nº Imobilizado')
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name='Nº de Série')
    tipo = models.CharField(max_length=50, choices=TIPOS, verbose_name='Tipo')
    marca = models.CharField(max_length=100, verbose_name='Marca')
    modelo = models.CharField(max_length=100, verbose_name='Modelo')
    local = models.CharField(max_length=150, verbose_name='Local')
    setor = models.CharField(max_length=150, verbose_name='Setor')
    responsavel = models.CharField(
        max_length=150, blank=True, default='',
        verbose_name='Responsável',
    )
    empresa = models.ForeignKey(
        Empresa,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='equipamentos',
        verbose_name='Empresa',
    )
    status = models.CharField(max_length=30, choices=STATUS, default='ATIVO', verbose_name='Status')
    sistema_operacional = models.CharField(max_length=100, blank=True, verbose_name='Sistema Operacional')
    versao_so = models.CharField(max_length=50, blank=True, verbose_name='Versão do SO')
    mac_ethernet = models.CharField(max_length=17, blank=True, verbose_name='MAC Ethernet')
    mac_wifi = models.CharField(max_length=17, blank=True, verbose_name='MAC Wi-Fi')
    ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='Endereço IP')
    teamviewer_id = models.CharField(max_length=50, blank=True, verbose_name='TeamViewer ID')
    versao_office = models.CharField(max_length=100, blank=True, verbose_name='Versão do Office')
    ultimo_usuario = models.CharField(max_length=200, blank=True, verbose_name='Último Usuário')
    data_aquisicao = models.DateField(null=True, blank=True, verbose_name='Data de Aquisição')
    valor_aquisicao = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Valor de Aquisição')
    garantia_ate = models.DateField(null=True, blank=True, verbose_name='Garantia até')
    periodicidade_dias = models.IntegerField(null=True, blank=True, verbose_name='Periodicidade (dias)')
    proxima_manutencao = models.DateField(null=True, blank=True, verbose_name='Próxima Manutenção')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Equipamento'
        verbose_name_plural = 'Equipamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.numero_imobilizado} - {self.get_tipo_display()} - {self.modelo}'


class Manutencao(models.Model):
    TIPOS_MANUTENCAO = [
        ('CORRETIVA', 'Corretiva'),
        ('PREVENTIVA', 'Preventiva'),
        ('UPGRADE', 'Upgrade'),
    ]
    STATUS_MANUTENCAO = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name='manutencoes',
        verbose_name='Equipamento',
    )
    data_abertura = models.DateField(auto_now_add=True, verbose_name='Data de Abertura')
    data_conclusao = models.DateField(null=True, blank=True, verbose_name='Data de Conclusão')
    tipo = models.CharField(max_length=30, choices=TIPOS_MANUTENCAO, verbose_name='Tipo')
    descricao = models.TextField(verbose_name='Descrição')
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Técnico',
    )
    custo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Custo')
    status = models.CharField(max_length=30, choices=STATUS_MANUTENCAO, default='ABERTA', verbose_name='Status')

    class Meta:
        verbose_name = 'Manutenção'
        verbose_name_plural = 'Manutenções'
        ordering = ['-data_abertura']

    def __str__(self):
        return f'Manutenção #{self.id} - {self.equipamento} - {self.get_status_display()}'


class ItemEstoque(models.Model):
    CATEGORIAS = [
        ('MEMORIA', 'Memória'),
        ('HD_SSD', 'HD / SSD'),
        ('FONTE', 'Fonte'),
        ('TECLADO', 'Teclado'),
        ('MOUSE', 'Mouse'),
        ('CABO', 'Cabo'),
        ('TONER', 'Toner'),
        ('OUTRO', 'Outro'),
    ]

    nome = models.CharField(max_length=150, verbose_name='Nome')
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, verbose_name='Categoria')
    quantidade = models.IntegerField(default=0, verbose_name='Quantidade')
    quantidade_minima = models.IntegerField(default=1, verbose_name='Quantidade Mínima')
    unidade = models.CharField(max_length=20, default='unidade', verbose_name='Unidade')
    localizacao = models.CharField(max_length=100, blank=True, verbose_name='Localização')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Item de Estoque'
        verbose_name_plural = 'Itens de Estoque'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.quantidade} {self.unidade})'


class MovimentacaoEstoque(models.Model):
    TIPOS = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('TRANSFERENCIA', 'Transferência'),
        ('AJUSTE', 'Ajuste'),
    ]

    item = models.ForeignKey(
        ItemEstoque,
        on_delete=models.CASCADE,
        related_name='movimentacoes',
        verbose_name='Item',
    )
    tipo = models.CharField(max_length=30, choices=TIPOS, verbose_name='Tipo')
    quantidade = models.IntegerField(verbose_name='Quantidade')
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, on_delete=models.SET_NULL,
        verbose_name='Responsável',
    )
    empresa_origem = models.ForeignKey(
        Empresa,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='movimentacoes_origem',
        verbose_name='Empresa Origem',
    )
    empresa_destino = models.ForeignKey(
        Empresa,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='movimentacoes_destino',
        verbose_name='Empresa Destino',
    )
    equipamento = models.ForeignKey(
        Equipamento,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Equipamento',
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')

    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.item.nome} ({self.quantidade})'


class Notificacao(models.Model):
    TIPOS = [
        ('ESTOQUE_BAIXO', 'Estoque Baixo'),
        ('GARANTIA_PROXIMA', 'Garantia Próxima do Vencimento'),
        ('MANUTENCAO_ATRASADA', 'Manutenção Atrasada'),
        ('INFO', 'Informativo'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPOS, verbose_name='Tipo')
    mensagem = models.TextField(verbose_name='Mensagem')
    lida = models.BooleanField(default=False, verbose_name='Lida')
    link = models.CharField(max_length=255, blank=True, verbose_name='Link')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criado_em']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.mensagem[:60]}'



