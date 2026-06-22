from django.core.management.base import BaseCommand
from core.models import Equipamento, Empresa

class Command(BaseCommand):
    help = 'Atribui os equipamentos sem empresa à Carboni Distribuidora'

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.filter(id=1).first()
            if not empresa:
                self.stdout.write(self.style.ERROR('Empresa ID 1 não encontrada'))
                return
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR('Empresa ID 1 não encontrada'))
            return

        sem_empresa = Equipamento.objects.filter(empresa__isnull=True)
        total = sem_empresa.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nenhum equipamento sem empresa'))
            return

        self.stdout.write(f'Atribuindo {total} equipamentos à {empresa.nome} ({empresa.get_segmento_display()})...')
        atualizados = sem_empresa.update(empresa=empresa)
        self.stdout.write(self.style.SUCCESS(f'{atualizados} equipamentos atualizados'))

        self.stdout.write('\nEquipamentos atribuídos:')
        for eq in Equipamento.objects.filter(empresa=empresa).order_by('-criado_em')[:total]:
            self.stdout.write(f'  {eq.numero_imobilizado} | {eq.tipo} | {eq.modelo}')
