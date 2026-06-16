# Generated manually to align model validators.

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_systemsettings_light_color'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemsettings',
            name='billing_cutoff_day',
            field=models.IntegerField(
                default=15,
                help_text='Dia do mês para corte de cobrança integral',
                validators=[MinValueValidator(1), MaxValueValidator(28)],
                verbose_name='Dia de Corte',
            ),
        ),
    ]
