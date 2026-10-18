from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_potionbatch_effects'),
    ]

    operations = [
        migrations.AddField(
            model_name='potionbatch',
            name='state_a',
            field=models.CharField(
                choices=[('crude', 'Crude'), ('refined', 'Refined')],
                default='crude',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='potionbatch',
            name='state_b',
            field=models.CharField(
                choices=[('crude', 'Crude'), ('refined', 'Refined')],
                default='crude',
                max_length=10,
            ),
        ),
    ]
