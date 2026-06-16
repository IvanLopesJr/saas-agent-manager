from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0020_company_charge_inactive_members_protect_fks'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='light_color',
            field=models.CharField(blank=True, default='#f8f9fa', max_length=7, verbose_name='Cor Clara (cards, cabeçalhos)'),
        ),
    ]
