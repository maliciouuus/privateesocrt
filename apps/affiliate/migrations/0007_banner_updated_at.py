from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        (
            "affiliate",
            "0006_alter_challengeprogress_unique_together_and_more",
        ),  # Correction de la dépendance
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
