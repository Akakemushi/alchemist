from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0002_initial'),
        ('characters', '0001_initial'),
        ('reagents', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PotionUseEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('used_at', models.DateTimeField(auto_now_add=True)),
                ('potency', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('outcome', models.CharField(choices=[('success', 'Success'), ('dud', 'Dud')], max_length=10)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='potion_uses', to='characters.character')),
                ('reagent_a', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='potion_uses_as_first', to='reagents.reagent')),
                ('reagent_b', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='potion_uses_as_second', to='reagents.reagent')),
                ('effects', models.ManyToManyField(blank=True, related_name='use_events', to='reagents.potioneffect')),
            ],
            options={
                'ordering': ['-used_at'],
            },
        ),
    ]
