from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("translator", "0018_add_simulation_membership_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="living_area",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
