"""
Management command to create initial Super Admin user
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create initial Super Admin user if none exists'

    def handle(self, *args, **kwargs):
        if User.objects.filter(role='super_admin').exists():
            self.stdout.write(
                self.style.WARNING('Super Admin already exists. Skipping creation.')
            )
            return

        admin_password = os.environ.get('ADMIN_PASSWORD')
        if not admin_password:
            raise CommandError('ADMIN_PASSWORD must be set to create the initial Super Admin.')

        try:
            user = User.objects.create_user(
                username='admin',
                email='admin@sistema.com',
                password=admin_password,
                first_name='Super',
                last_name='Admin',
                role='super_admin',
                status='active',
                is_staff=True,
                is_superuser=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Super Admin created successfully!\n'
                    f'  Username: {user.username}\n'
                    f'  IMPORTANT: Store the configured password securely.'
                )
            )
        except Exception as e:
            raise CommandError(f'Error creating Super Admin: {str(e)}') from e
