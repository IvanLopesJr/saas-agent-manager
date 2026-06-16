from __future__ import annotations

from typing import Optional

from django.db import transaction

from ..models import CompanyMember, User


def get_user_member(user: User) -> Optional[CompanyMember]:
    """
    Safe helper to return the member linked to a user (if any).
    """
    if not user or not user.pk:
        return None
    try:
        return user.member_profile
    except CompanyMember.DoesNotExist:
        return None


@transaction.atomic
def ensure_member_for_admin_user(
    user: User,
    consider_as_member: bool,
    member_active: bool,
) -> Optional[CompanyMember]:
    """
    Creates/updates (or detaches) the CompanyMember associated to an admin user.
    """
    if not user or user.role != 'admin_company' or not user.company:
        consider_as_member = False

    member = get_user_member(user)

    if not consider_as_member:
        if member:
            member.user = None
            member.save(update_fields=['user'])
        return None

    # Try to find an existing member in the same company with the same email
    if not member:
        member = CompanyMember.objects.filter(
            company=user.company,
            email__iexact=user.email
        ).first()

    if not member:
        identification = f'AUTO-ADMIN-{user.pk}'
        member = CompanyMember(
            company=user.company,
            name=user.get_full_name() or user.username or user.email,
            email=user.email,
            phone=user.phone or '',
            identification_document=identification,
            status='active'
        )

    member.company = user.company
    member.name = user.get_full_name() or member.name or user.username or user.email
    member.email = user.email
    if user.phone:
        member.phone = user.phone
    if not member.identification_document:
        member.identification_document = f'AUTO-ADMIN-{user.pk}'
    member.status = 'active' if member_active else 'inactive'
    member.user = user
    member.save()
    return member


def link_member_to_admin_user(member: CompanyMember) -> None:
    """
    When a CompanyMember is manually created/edited, try to associate it
    with an existing admin user from the same company (based on email).
    """
    if not member or not member.company or not member.email:
        if member and member.user_id:
            member.user = None
            member.save(update_fields=['user'])
        return

    user = User.objects.filter(
        company=member.company,
        role='admin_company',
        email__iexact=member.email
    ).first()

    if not user:
        if member.user_id:
            member.user = None
            member.save(update_fields=['user'])
        return

    if not user.sync_member_profile:
        user.sync_member_profile = True
        user.save(update_fields=['sync_member_profile'])

    if member.user_id != user.id:
        member.user = user
        member.save(update_fields=['user'])


def unlink_member_from_admin_user(member: CompanyMember) -> None:
    """
    Desassocia um membro do usuário admin correspondente e desativa a sincronização automática.
    """
    if not member:
        return
    user = member.user
    if user:
        user.sync_member_profile = False
        user.save(update_fields=['sync_member_profile'])
        member.user = None
        member.save(update_fields=['user'])
