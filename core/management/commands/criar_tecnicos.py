from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

TECNICOS = [
    'Marcos Chaves Bemerguy',
    'Roberto Manica',
    'Andre Hoffmann',
    'Alexandre Zuffo',
    'Luiz Felipe Steilein Zardo',
    'Augusto Lima Hagemeier',
    'Gustavo Manenti',
]

class Command(BaseCommand):
    help = 'Cria usuários técnicos para manutenção'

    def handle(self, *args, **options):
        criados = 0
        for nome in TECNICOS:
            partes = nome.lower().split()
            username = '.'.join(partes)
            existing = User.objects.filter(username=username).first()
            if existing:
                self.stdout.write(f'  Já existe: {nome} ({username})')
                continue
            User.objects.create_user(
                username=username,
                password='senha123',
                first_name=partes[0].capitalize(),
                last_name=' '.join(partes[1:]).capitalize() if len(partes) > 1 else '',
                is_staff=True,
            )
            self.stdout.write(self.style.SUCCESS(f'  Criado: {nome} ({username})'))
            criados += 1

        self.stdout.write(self.style.SUCCESS(f'\n{criados} técnicos criados'))
