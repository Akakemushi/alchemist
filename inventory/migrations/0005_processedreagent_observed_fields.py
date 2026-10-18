from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_processedreagent_source_biome'),
    ]

    operations = [
        migrations.AddField(
            model_name='processedreagent',
            name='observed_category',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='processedreagent',
            name='observed_description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
