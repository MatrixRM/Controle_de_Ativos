from django.core.management.base import BaseCommand
from core.notifications import executar_todas


class Command(BaseCommand):
    help = 'Gera notificacoes automaticas (estoque baixo, garantia proxima, manutencao atrasada)'

    def handle(self, *args, **options):
        total = executar_todas()
        if total:
            self.stdout.write(self.style.SUCCESS(f'{total} notifica\u00e7\u00f5(es) criada(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('Nenhuma notifica\u00e7\u00e3o criada'))
