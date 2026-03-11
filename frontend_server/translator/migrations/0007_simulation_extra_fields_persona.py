# Generated for US-003 - Add Simulation extra fields and Persona model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0006_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="simulation",
            name="fork_sim_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="simulation",
            name="start_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="simulation",
            name="curr_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="simulation",
            name="sec_per_step",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="simulation",
            name="maze_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="simulation",
            name="step",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="simulation",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.CreateModel(
            name="Persona",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("first_name", models.CharField(blank=True, default="", max_length=255)),
                ("last_name", models.CharField(blank=True, default="", max_length=255)),
                ("age", models.IntegerField(blank=True, null=True)),
                ("innate", models.TextField(blank=True, default="")),
                ("learned", models.TextField(blank=True, default="")),
                ("currently", models.TextField(blank=True, default="")),
                ("lifestyle", models.TextField(blank=True, default="")),
                ("living_area", models.CharField(blank=True, default="", max_length=500)),
                ("daily_plan_req", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "simulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="personas",
                        to="translator.simulation",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="persona",
            unique_together={("simulation", "name")},
        ),
    ]
