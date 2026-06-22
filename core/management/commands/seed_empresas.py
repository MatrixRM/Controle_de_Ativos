from django.core.management.base import BaseCommand
from core.models import Empresa

EMPRESAS = [
    {'nome': 'CARBONI DISTRIBUIDORA DE VEÍCULOS LTDA', 'segmento': 'IVECO'},
    {'nome': 'EURODIESEL SERVIÇOS TÉCNICOS LTDA', 'segmento': 'IVECO'},
    {'nome': 'AGROPECUÁRIA CARBONI LTDA', 'segmento': 'AGROP.'},
    {'nome': 'RODOVIÁRIO MONTE SERENO LTDA', 'segmento': 'ROD.'},
    {'nome': 'VERDE VALE TRANSPORTE E COMERCIO LTDA', 'segmento': 'V. VALE'},
    {'nome': 'MONTE SERENO PARTICIPAÇÕES S/A', 'segmento': 'IVECO'},
    {'nome': 'ELETRO DIESEL CARBONI LTDA', 'segmento': 'IVECO'},
    {'nome': 'CARBONI CORRETORA DE SEGUROS', 'segmento': 'SEGUROS'},
    {'nome': 'CARBONI MÁQUINAS AGRÍCOLAS LTDA', 'segmento': 'CASE'},
    {'nome': 'CARBONI VEÍCULOS LTDA', 'segmento': 'FIAT'},
    {'nome': 'MALIZA LOCADORA DE VEICULOS LTDA', 'segmento': 'LOCADORA'},
]


class Command(BaseCommand):
    help = 'Popula a tabela de empresas com os dados iniciais'

    def handle(self, *args, **options):
        created = 0
        for data in EMPRESAS:
            _, is_new = Empresa.objects.get_or_create(**data)
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'{created} empresas criadas.'))
