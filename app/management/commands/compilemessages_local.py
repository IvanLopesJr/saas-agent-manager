from django.core.management.base import BaseCommand

from app.utils.i18n import compile_locale_files


class Command(BaseCommand):
    help = "Compile .po files to .mo files using polib (gettext-free)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recompile .mo files even if timestamps are unchanged.',
        )

    def handle(self, *args, **options):
        compiled = compile_locale_files(force=options['force'])
        if not compiled:
            self.stdout.write(self.style.WARNING("No translation files required compilation."))
            return

        for po_path, mo_path in compiled:
            self.stdout.write(self.style.SUCCESS(f"Compiled {po_path} -> {mo_path}"))
