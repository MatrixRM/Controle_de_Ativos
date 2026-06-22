from django.apps import AppConfig
from django.db.models.signals import post_migrate


def criar_grupos(sender, **kwargs):
    from django.contrib.auth.models import Group
    Group.objects.get_or_create(name='Administrador')
    Group.objects.get_or_create(name='Técnico')


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        post_migrate.connect(criar_grupos, sender=self)
        import core.signals  # noqa: F401 — registra @receiver
