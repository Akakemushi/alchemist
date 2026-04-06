from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_processedreagent_mundane'),
        ('reagents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='processedreagent',
            name='source_biome',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='processed_reagents',
                to='reagents.biome',
            ),
        ),
    ]
