"""
Django signals for automatic actions
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _

from django.contrib.auth.signals import user_logged_in
from django.utils import translation

from .models import (
    CompanyMember, User, UserStatusHistory, AuditLog
)


@receiver(post_save, sender=CompanyMember)
def create_member_status_history(sender, instance, created, **kwargs):
    """Create status history when member is created"""
    if created:
        UserStatusHistory.objects.create(
            member=instance,
            status=instance.status,
            date_start=timezone.now().date(),
            date_end=None,
            created_by=None  # Will be set by the view
        )


@receiver(pre_save, sender=CompanyMember)
def update_member_status_history(sender, instance, **kwargs):
    """Update status history when member status changes"""
    if not instance.pk:
        return
    
    try:
        old_instance = CompanyMember.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            # Close previous status history
            UserStatusHistory.objects.filter(
                member=instance,
                date_end__isnull=True
            ).update(date_end=timezone.now().date())
            
            # Create new status history
            UserStatusHistory.objects.create(
                member=instance,
                status=instance.status,
                date_start=timezone.now().date(),
                date_end=None,
                created_by=None  # Will be set by the view
            )
            
            # Log the change
            AuditLog.objects.create(
                user=None,  # Will be set by middleware
                action='member_status_changed',
                description=_('Status do membro %(nome)s alterado de %(anterior)s para %(novo)s') % {
                    'nome': instance.name,
                    'anterior': old_instance.get_status_display(),
                    'novo': instance.get_status_display(),
                },
                ip_address=None
            )
    except CompanyMember.DoesNotExist:
        pass


@receiver(post_save, sender=User)
def create_user_status_history(sender, instance, created, **kwargs):
    """Create status history when user is created"""
    if created:
        UserStatusHistory.objects.create(
            user=instance,
            status=instance.status,
            date_start=timezone.now().date(),
            date_end=None,
            created_by=None
        )


@receiver(pre_save, sender=User)
def update_user_status_history(sender, instance, **kwargs):
    """Update status history when user status changes"""
    if not instance.pk:
        return
    
    try:
        old_instance = User.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            # Close previous status history
            UserStatusHistory.objects.filter(
                user=instance,
                date_end__isnull=True
            ).update(date_end=timezone.now().date())
            
            # Create new status history
            UserStatusHistory.objects.create(
                user=instance,
                status=instance.status,
                date_start=timezone.now().date(),
                date_end=None,
                created_by=None
            )
    except User.DoesNotExist:
        pass


@receiver(post_save, sender=User)
def log_super_admin_creation(sender, instance, created, **kwargs):
    """Log when a Super Admin is created"""
    if created and instance.role == 'super_admin':
        AuditLog.objects.create(
            user=None,  # Will be set by middleware
            action='super_admin_created',
            description=_('Super Admin criado: %(usuario)s (%(email)s)') % {
                'usuario': instance.username,
                'email': instance.email,
            },
            ip_address=None
        )


@receiver(post_delete, sender=User)
def clean_orphan_member_on_user_delete(sender, instance, **kwargs):
    """When a User is deleted, detach the linked CompanyMember
    and reset its billing state so it doesn't cause phantom charges."""
    try:
        member = instance.member_profile
    except CompanyMember.DoesNotExist:
        return
    if member:
        CompanyMember.objects.filter(pk=member.pk).update(
            user=None,
            first_cycle_price_snapshot=None,
            first_cycle_completed=False,
        )


@receiver(user_logged_in)
def set_company_language(sender, request, user, **kwargs):
    """Set session language to the user's company preferred language on login."""
    if user.is_admin_company() and user.company and user.company.language:
        request.session[translation.LANGUAGE_SESSION_KEY] = user.company.language
