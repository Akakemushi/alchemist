from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_potionbatch_states'),
        ('reagents', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='potionbatch',
            name='potion_batch_distinct_reagents',
        ),
        migrations.AlterField(
            model_name='potionbatch',
            name='reagent_a',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='uses_in_first_slot',
                to='reagents.reagent',
            ),
        ),
        migrations.AlterField(
            model_name='potionbatch',
            name='reagent_b',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='uses_in_second_slot',
                to='reagents.reagent',
            ),
        ),
        migrations.AddConstraint(
            model_name='potionbatch',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(reagent_a__isnull=True, reagent_b__isnull=True) |
                    (
                        models.Q(reagent_a__isnull=False) &
                        models.Q(reagent_b__isnull=False) &
                        ~models.Q(reagent_a=models.F('reagent_b'))
                    )
                ),
                name='potion_batch_distinct_reagents',
            ),
        ),
    ]
