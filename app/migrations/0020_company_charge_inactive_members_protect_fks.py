from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_squashed_0019'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='charge_inactive_members',
            field=models.BooleanField(
                default=False,
                help_text='Quando ativo, membros sem acesso a chatbot também são cobrados (modo per_user)',
                verbose_name='Cobrar membros sem chatbot',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='users',
                to='app.company',
                verbose_name='Empresa',
            ),
        ),
        migrations.AlterField(
            model_name='companymember',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='members',
                to='app.company',
                verbose_name='Empresa',
            ),
        ),
        migrations.AlterField(
            model_name='companychatbot',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='company_chatbots',
                to='app.company',
                verbose_name='Empresa',
            ),
        ),
        migrations.AlterField(
            model_name='billing',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='billings',
                to='app.company',
                verbose_name='Empresa',
            ),
        ),
    ]
