from collections import Counter
from django.core.management.base import BaseCommand, CommandParser
from core.models import Equipamento, Empresa
from core.mapeamento_empresas import PREFIXO_PARA_EMPRESA, detectar_empresa_por_hostname


class Command(BaseCommand):
    help = 'Vincula equipamentos às empresas com base no prefixo do hostname'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--force', action='store_true', help='Sobrescreve vínculos existentes')

    def handle(self, *args, **options):
        total = Equipamento.objects.count()
        ja_vinculados = Equipamento.objects.filter(empresa__isnull=False).count()
        sem_empresa = Equipamento.objects.filter(empresa__isnull=True)

        self.stdout.write(f'Total equipamentos: {total}')
        self.stdout.write(f'Já vinculados: {ja_vinculados}')
        self.stdout.write(f'Sem empresa: {sem_empresa.count()}')

        if ja_vinculados > 0 and not options['force']:
            self.stdout.write(self.style.WARNING('Use --force para sobrescrever vínculos existentes'))
            qs = sem_empresa
        else:
            qs = Equipamento.objects.all()

        atualizados = 0
        sem_match = 0
        erros = 0
        empresas_count = Counter()
        sem_match_prefixos = Counter()

        for eq in qs.iterator():
            empresa_id = detectar_empresa_por_hostname(eq.numero_imobilizado)
            if empresa_id:
                try:
                    eq.empresa_id = empresa_id
                    eq.save(update_fields=['empresa'])
                    atualizados += 1
                    nome_empresa = Empresa.objects.get(id=empresa_id).segmento
                    empresas_count[nome_empresa] += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Erro ao atualizar {eq.numero_imobilizado}: {e}'))
                    erros += 1
            else:
                sem_match += 1
                if eq.numero_imobilizado:
                    prefixo = eq.numero_imobilizado.split('-')[0] if '-' in eq.numero_imobilizado else eq.numero_imobilizado
                    sem_match_prefixos[prefixo] += 1

        self.stdout.write(self.style.SUCCESS(f'\n\n=== RESULTADO ==='))
        self.stdout.write(f'Atualizados: {atualizados}')
        self.stdout.write(f'Sem match: {sem_match}')
        self.stdout.write(f'Erros: {erros}')

        if empresas_count:
            self.stdout.write('\nDistribuição por empresa:')
            for nome, count in empresas_count.most_common():
                self.stdout.write(f'  {nome}: {count}')

        if sem_match_prefixos:
            self.stdout.write('\nPrefixos sem match (precisam de ajuste manual):')
            for prefixo, count in sem_match_prefixos.most_common(20):
                amostra = Equipamento.objects.filter(
                    empresa__isnull=True,
                    numero_imobilizado__startswith=prefixo
                ).values_list('numero_imobilizado', flat=True).first()
                self.stdout.write(f'  {prefixo:<10} {count:>3} equip. Ex: {amostra}')
