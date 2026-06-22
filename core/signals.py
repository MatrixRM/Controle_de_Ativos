import threading

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Equipamento, MovimentacaoEstoque, LogAlteracao


_thread_locals = threading.local()


@receiver(pre_save, sender=Equipamento)
def _pre_save_equipamento(sender, instance, **kwargs):
    if instance.pk:
        try:
            _thread_locals.equipamento_old = Equipamento.objects.get(pk=instance.pk)
        except Equipamento.DoesNotExist:
            _thread_locals.equipamento_old = None
    else:
        _thread_locals.equipamento_old = None


@receiver(post_save, sender=Equipamento)
def _post_save_equipamento(sender, instance, created, **kwargs):
    if created:
        return
    old = getattr(_thread_locals, 'equipamento_old', None)
    if old is None:
        return
    skip = {'pk', 'id', 'criado_em', 'atualizado_em'}
    for field in Equipamento._meta.get_fields():
        if field.name in skip or field.is_relation:
            continue
        old_val = getattr(old, field.name)
        new_val = getattr(instance, field.name)
        if old_val != new_val:
            LogAlteracao.objects.create(
                tabela='Equipamento',
                registro_id=instance.pk,
                campo=field.name,
                valor_anterior=str(old_val) if old_val is not None else '',
                valor_novo=str(new_val) if new_val is not None else '',
            )


@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque(sender, instance, created, **kwargs):
    if not created:
        return
    item = instance.item
    if instance.tipo == 'ENTRADA':
        item.quantidade += instance.quantidade
    elif instance.tipo == 'SAIDA':
        item.quantidade -= instance.quantidade
    elif instance.tipo == 'AJUSTE':
        item.quantidade = instance.quantidade
    item.save()
