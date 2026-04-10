from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_processedreagent_observed_fields'),
        ('reagents', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='potionbatch',
            name='discovered_effect',
        ),
        migrations.AddField(
            model_name='potionbatch',
            name='effects',
            field=models.ManyToManyField(
                blank=True,
                related_name='potion_batches',
                to='reagents.potioneffect',
            ),
        ),
    ]
