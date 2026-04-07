"""
Migration 0020: Add game_obj_cleanup to Simulation and create SimulationStepCache.

game_obj_cleanup persists the maze tile object events that need to be cleared
at the start of the next simulation step, enabling stateless step execution on
Vercel serverless functions.

SimulationStepCache stores intermediate cognitive stage results between the
5 separate Vercel function invocations per simulation step.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("translator", "0019_add_character_living_area"),
    ]

    operations = [
        migrations.AddField(
            model_name="simulation",
            name="game_obj_cleanup",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Serialized list of [event_tuple, tile_xy] pairs tracking maze tile "
                    "object events to clear at the start of the next simulation step."
                ),
            ),
        ),
        migrations.CreateModel(
            name="SimulationStepCache",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "simulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="step_caches",
                        to="translator.simulation",
                    ),
                ),
                ("step", models.IntegerField()),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("perceive", "Perceive"),
                            ("retrieve", "Retrieve"),
                            ("plan", "Plan"),
                            ("reflect", "Reflect"),
                            ("execute", "Execute"),
                        ],
                        max_length=20,
                    ),
                ),
                ("data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["simulation", "step"], name="step_cache_sim_step_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="simulationstepcache",
            constraint=models.UniqueConstraint(
                fields=["simulation", "step", "stage"],
                name="unique_simulation_step_stage",
            ),
        ),
    ]
