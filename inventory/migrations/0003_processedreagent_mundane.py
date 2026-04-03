from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_add_observed_category_to_reagentsample'),
        ('reagents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='processedreagent',
            name='is_confirmed_mundane',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='processedreagent',
            name='reagent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='processed_reagents',
                to='reagents.reagent',
            ),
        ),
    ]
