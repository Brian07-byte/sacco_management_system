from django.db.models.signals import post_save
from django.dispatch import receiver
from members.models import Member
from .models import SavingsAccount


@receiver(post_save, sender=Member)
def create_savings_account(sender, instance, created, **kwargs):
    if created:
        SavingsAccount.objects.create(member=instance)