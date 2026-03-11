# Generated for US-005 - Create EnvironmentState and MovementRecord models
# Note: migration name kept as 0009_demo_conversation_tables to satisfy existing 0010 dependency

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0008_personascratch"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnvironmentState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("step", models.IntegerField()),
                ("agent_positions", models.JSONField()),
                (
                    "simulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="environment_states",
                        to="translator.simulation",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="environmentstate",
            constraint=models.UniqueConstraint(
                fields=("simulation", "step"), name="unique_environmentstate_simulation_step"
            ),
        ),
        migrations.AddIndex(
            model_name="environmentstate",
            index=models.Index(fields=["simulation", "step"], name="translator_environmentstate_sim_step_idx"),
        ),
        migrations.CreateModel(
            name="MovementRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("step", models.IntegerField()),
                ("sim_curr_time", models.DateTimeField(blank=True, null=True)),
                ("persona_movements", models.JSONField()),
                (
                    "simulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movement_records",
                        to="translator.simulation",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="movementrecord",
            constraint=models.UniqueConstraint(
                fields=("simulation", "step"), name="unique_movementrecord_simulation_step"
            ),
        ),
        migrations.AddIndex(
            model_name="movementrecord",
            index=models.Index(fields=["simulation", "step"], name="translator_movementrecord_sim_step_idx"),
        ),
    ]
