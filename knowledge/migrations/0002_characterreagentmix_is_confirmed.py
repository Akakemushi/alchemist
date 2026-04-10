from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='characterreagentmix',
            name='is_confirmed',
            field=models.BooleanField(default=False),
        ),
    ]
