# Generated manually to track chatbot access validity periods.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0022_systemsettings_cutoff_validator'),
    ]

    operations = [
        migrations.AddField(
            model_name='memberchatbotaccess',
            name='deactivation_date',
            field=models.DateField(blank=True, null=True, verbose_name='Data de Desativação'),
        ),
    ]
