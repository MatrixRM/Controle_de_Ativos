from datetime import date, timedelta

from django.core.management.base import BaseCommand

from core.models import Equipamento, Manutencao


class Command(BaseCommand):
    help = 'Verifica e cria manutenções preventivas agendadas'

    def handle(self, *args, **options):
        hoje = date.today()
        qs = Equipamento.objects.filter(
            proxima_manutencao__lte=hoje,
            periodicidade_dias__isnull=False,
        ).exclude(status='DESCARTADO')
        criadas = 0
        for eq in qs:
            Manutencao.objects.create(
                equipamento=eq,
                tipo='PREVENTIVA',
                descricao=f'Manutenção preventiva automática — {eq.numero_imobilizado}',
                status='ABERTA',
            )
            eq.proxima_manutencao = hoje + timedelta(days=eq.periodicidade_dias)
            eq.save(update_fields=['proxima_manutencao'])
            criadas += 1
        self.stdout.write(self.style.SUCCESS(f'{criadas} manutenção(ões) preventiva(s) criada(s).'))
